import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app import config

STOPWORDS = set(
    """
    the and for are was with that this from have has had can how
    what when who why does did our their they them you your any all
    not but into out its will would should could may must there which been
    were about after before than then also only each per get got one two
    many much long need needs still want wants let lets
    """.split()
)


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    text: str


def tokens(text: str) -> set[str]:
    out = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) < 3 or word in STOPWORDS:
            continue
        out.add(stem(word))
    return out


def stem(word: str) -> str:
    """Very small suffix stripper so 'batteries' matches 'battery' and 'declaring' 'declared'."""
    for suffix, repl in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)] + repl
    return word


@lru_cache(maxsize=1)
def load_sections(policy_dir: Path = config.POLICY_DIR) -> tuple[Section, ...]:
    sections = []
    for path in sorted(policy_dir.glob("S-*.md")):
        text = path.read_text(encoding="utf-8")
        first = text.splitlines()[0].lstrip("# ").strip()
        title = first.split(" ", 1)[1] if " " in first else first
        sections.append(Section(id=path.name[:4], title=title, text=text))
    return tuple(sections)


def score(question: str, section: Section) -> int:
    q = tokens(question)
    return len(q & tokens(section.text)) + 2 * len(q & tokens(section.title))


def retrieve(question: str, top_k: int | None = None) -> list[Section]:
    k = config.TOP_K if top_k is None else top_k
    ranked = sorted(load_sections(), key=lambda s: (-score(question, s), s.id))
    return ranked[:k]
