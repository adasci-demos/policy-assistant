"""Eval gate for the Harbourline policy assistant (fictional).

Sends every golden-set question to a running service, scores each answer and exits
0 (pass), 1 (fail) or 2 (config or environment error). Fixed-threshold gate.
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET = ROOT / "evals" / "golden_set.jsonl"
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def env_error(message: str) -> None:
    print(f"::error title=Eval gate::{message}")
    sys.exit(2)


def load_cases() -> list[dict]:
    with GOLDEN_SET.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def ask(base_url: str, question: str) -> dict:
    r = httpx.post(f"{base_url}/ask", json={"question": question}, timeout=120)
    r.raise_for_status()
    return r.json()


def judge(
    client: OpenAI, model: str, prompt: str, temperature: float, case: dict, answer: str
) -> tuple[bool, str]:
    user = f"QUESTION: {case['question']}\nREFERENCE: {case['reference_answer']}\nANSWER: {answer}"
    effort = os.environ.get("MODEL_REASONING_EFFORT")
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user}],
        **({"reasoning_effort": effort} if effort else {}),
    )
    text = THINK_RE.sub("", response.choices[0].message.content or "").strip()
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    verdict = line.upper().startswith("PASS")
    reason = line.split(":", 1)[1].strip() if ":" in line else line
    return verdict, reason


def score_case(case: dict, response: dict, judge_result: tuple[bool, str] | None) -> dict:
    """Return pass/fail and the names of the failed checks for one case."""
    failed = []
    cited = set(response.get("citations", []))
    if case["must_refuse"]:
        if not response.get("refused"):
            failed.append("refusal")
    else:
        if not set(case["expected_sections"]) <= cited:
            failed.append("citation")
        if judge_result is not None and not judge_result[0]:
            failed.append("judge")
    return {"passed": not failed, "failed_checks": failed}


def decide(results: list[dict], threshold: float, critical_must_pass: bool) -> dict:
    total = len(results)
    passed = sum(r["passed"] for r in results)
    critical = [r for r in results if r["critical"]]
    critical_passed = sum(r["passed"] for r in critical)
    pass_rate = passed / total if total else 0.0
    ok = pass_rate >= threshold
    if critical_must_pass and critical_passed < len(critical):
        ok = False
    return {
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "threshold": threshold,
        "critical_passed": critical_passed,
        "critical_total": len(critical),
        "gate": "PASS" if ok else "FAIL",
    }


def summary_markdown(decision: dict, results: list[dict]) -> str:
    d = decision
    lines = [
        f"## Eval gate: {d['gate']}",
        "",
        "| Passed | Total | Pass rate | Threshold | Critical passed |",
        "|---|---|---|---|---|",
        f"| {d['passed']} | {d['total']} | {d['pass_rate']:.1%} | {d['threshold']:.1%} "
        f"| {d['critical_passed']}/{d['critical_total']} |",
        "",
    ]
    failed = [r for r in results if not r["passed"]]
    if failed:
        lines += ["### Failed cases", "", "| id | failed check | judge reason |", "|---|---|---|"]
        for r in failed:
            if "judge" in r["failed_checks"]:
                reason = (r.get("judge_reason") or "").replace("|", "/")
            else:
                reason = "(judge passed)"
            lines.append(f"| {r['id']} | {', '.join(r['failed_checks'])} | {reason} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", default="eval-results")
    parser.add_argument("--config", default="evals/eval_config.yaml")
    args = parser.parse_args()

    api_key = os.environ.get("MODEL_API_KEY", "")
    if not api_key:
        env_error("MODEL_API_KEY is not set")
    judge_model = os.environ.get("JUDGE_MODEL", "")
    if not judge_model:
        env_error("JUDGE_MODEL is not set")
    try:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        judge_prompt = (ROOT / config["judge_prompt"]).read_text(encoding="utf-8")
        threshold = float(config["threshold"])
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        env_error(f"bad eval config: {exc}")

    client = OpenAI(api_key=api_key, base_url=os.environ.get("MODEL_BASE_URL") or None)
    base_url = args.base_url.rstrip("/")
    cases = load_cases()

    def run_one(case: dict) -> dict:
        response = ask(base_url, case["question"])
        judge_result = None
        if not case["must_refuse"]:
            judge_result = judge(
                client,
                judge_model,
                judge_prompt,
                float(config.get("judge_temperature", 0)),
                case,
                response["answer"],
            )
        scored = score_case(case, response, judge_result)
        return {
            "id": case["id"],
            "critical": case["critical"],
            "question": case["question"],
            "expected_sections": case["expected_sections"],
            "must_refuse": case["must_refuse"],
            "answer": response["answer"],
            "citations": response["citations"],
            "refused": response["refused"],
            "judge_pass": None if judge_result is None else judge_result[0],
            "judge_reason": None if judge_result is None else judge_result[1],
            **scored,
        }

    try:
        with ThreadPoolExecutor(max_workers=int(config.get("concurrency", 4))) as pool:
            results = list(pool.map(run_one, cases))
    except (httpx.HTTPError, OpenAIError) as exc:
        # Service or judge unreachable: an environment error (exit 2), not a quality failure.
        env_error(f"service or judge call failed: {type(exc).__name__}")

    decision = decide(results, threshold, bool(config.get("critical_must_pass", True)))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(
        json.dumps({"decision": decision, "cases": results}, indent=2), encoding="utf-8"
    )
    summary = summary_markdown(decision, results)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary + "\n")

    for r in results:
        if not r["passed"]:
            show_reason = r["judge_reason"] and "judge" in r["failed_checks"]
            print(
                f"  failed {r['id']}: {', '.join(r['failed_checks'])}"
                f"{' - ' + r['judge_reason'] if show_reason else ''}"
            )
    d = decision
    print(
        f"{d['gate']} {d['passed']}/{d['total']} = {d['pass_rate']:.1%} "
        f"(threshold {d['threshold']:.1%}, critical {d['critical_passed']}/{d['critical_total']})"
    )
    return 0 if d["gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
