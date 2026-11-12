from typing import Protocol

from app import config


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIChatClient:
    """Calls any OpenAI-compatible chat endpoint. Created lazily on the first /ask call."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **self._extra,
        )
        return response.choices[0].message.content or ""


class FakeLLM:
    """Deterministic stand-in for unit tests. Needs no network and no key."""

    def __init__(self, refuse: bool = False) -> None:
        self.refuse = refuse
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.refuse:
            return config.REFUSAL
        ids = [line[1:5] for line in user.splitlines() if line.startswith("[S-")]
        return "Fake answer " + " ".join(f"[{i}]" for i in ids)
