import re

CITATION_RE = re.compile(r"\[(S-\d{2})\]")


def parse_citations(answer: str) -> list[str]:
    """Return section ids cited as [S-03], in first-seen order, without duplicates."""
    seen: list[str] = []
    for section_id in CITATION_RE.findall(answer):
        if section_id not in seen:
            seen.append(section_id)
    return seen
