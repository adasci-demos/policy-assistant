from app.citations import parse_citations


def test_single_citation():
    assert parse_citations("Returns take 30 days [S-03].") == ["S-03"]


def test_multiple_citations_in_order():
    assert parse_citations("Report in 7 days [S-04]; 45 days [S-03].") == ["S-04", "S-03"]


def test_duplicates_removed():
    assert parse_citations("[S-07] and again [S-07]") == ["S-07"]


def test_no_citations_or_malformed():
    assert parse_citations("No sources. (S-03) [S3] [s-03]") == []
