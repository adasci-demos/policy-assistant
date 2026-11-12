import os
import re
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app import config
from app.citations import parse_citations
from app.llm import LLMClient, OpenAIChatClient
from app.retrieval import retrieve

app = FastAPI(title="Harbourline policy assistant")

SYSTEM_PROMPT = config.PROMPT_PATH.read_text(encoding="utf-8")
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

_llm: LLMClient | None = None


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    refused: bool


def get_llm() -> LLMClient:
    # Lazy: the client is built on the first /ask call, never at import or startup,
    # so the container starts and /healthz answers with no MODEL_API_KEY set.
    global _llm
    if _llm is None:
        _llm = OpenAIChatClient(
            api_key=os.environ.get("MODEL_API_KEY", ""),
            model=config.MODEL_NAME,
            base_url=config.MODEL_BASE_URL,
            reasoning_effort=config.MODEL_REASONING_EFFORT,
        )
    return _llm


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def build_user_message(question: str) -> str:
    parts = []
    for section in retrieve(question):
        parts.append(f"[{section.id}] {section.title}\n{section.text.strip()}\n")
    parts.append(f"Question: {question}")
    return "\n".join(parts)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, llm: Annotated[LLMClient, Depends(get_llm)]) -> AskResponse:
    raw = llm.complete(SYSTEM_PROMPT, build_user_message(req.question))
    answer = THINK_RE.sub("", raw).strip()
    return AskResponse(
        answer=answer,
        citations=parse_citations(answer),
        refused=answer == config.REFUSAL,
    )
