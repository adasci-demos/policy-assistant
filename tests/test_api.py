from app import config
from app.llm import FakeLLM
from app.main import app, get_llm


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ask_returns_answer_and_citations(client):
    r = client.post("/ask", json={"question": "What is the returns window?"})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is False
    assert "S-03" in body["citations"]


def test_ask_sends_sections_to_model(client, fake_llm):
    client.post("/ask", json={"question": "Can hazardous goods go by air?"})
    system, user = fake_llm.calls[0]
    assert "only the policy sections" in system
    assert "[S-06]" in user
    assert user.rstrip().endswith("Question: Can hazardous goods go by air?")


def test_refusal_flag(client):
    app.dependency_overrides[get_llm] = lambda: FakeLLM(refuse=True)
    r = client.post("/ask", json={"question": "Can you ship a live dog?"})
    body = r.json()
    assert body["refused"] is True
    assert body["answer"] == config.REFUSAL
    assert body["citations"] == []
