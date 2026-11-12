import pytest
from fastapi.testclient import TestClient

from app.llm import FakeLLM
from app.main import app, get_llm


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def client(fake_llm):
    app.dependency_overrides[get_llm] = lambda: fake_llm
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
