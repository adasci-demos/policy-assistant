from app.retrieval import load_sections, retrieve, score, tokens


def test_twelve_sections_loaded():
    ids = [s.id for s in load_sections()]
    assert ids == [f"S-{i:02d}" for i in range(1, 13)]


def test_tokens_drop_stopwords_and_short_words():
    assert tokens("What is the returns window?") == {"return", "window"}


def test_top_result_for_returns_question():
    assert retrieve("What is the returns window for a domestic shipment?", top_k=1)[0].id == "S-03"


def test_top_result_for_hazardous_question():
    top = retrieve("Can declared hazardous goods be sent by air?", top_k=1)[0]
    assert top.id == "S-06"


def test_top_k_limits_result_count():
    assert len(retrieve("refund", top_k=2)) == 2
    assert len(retrieve("refund", top_k=5)) == 5


def test_retrieval_is_deterministic():
    q = "How long does standard delivery take?"
    first = [s.id for s in retrieve(q, top_k=4)]
    assert first == [s.id for s in retrieve(q, top_k=4)]
    sections = load_sections()
    assert score(q, sections[1]) >= score(q, sections[11])
