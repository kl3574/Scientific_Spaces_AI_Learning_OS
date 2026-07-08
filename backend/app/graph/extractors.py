from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}")
_FORMULA_PATTERNS = [
    re.compile(r"\$\$\n?(.*?)\n?\$\$", re.DOTALL),
    re.compile(r"\\\[(.*?)\\\]", re.DOTALL),
    re.compile(r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", re.DOTALL),
]
_STOPWORDS = {
    "and",
    "are",
    "article",
    "can",
    "for",
    "from",
    "introduction",
    "the",
    "this",
    "using",
    "with",
}


def extract_concepts(*texts: str | None, limit: int = 12) -> list[str]:
    concepts: dict[str, str] = {}
    for text in texts:
        if not text:
            continue
        for match in _TOKEN_RE.findall(text):
            normalized = normalize_concept(match)
            if normalized and normalized not in _STOPWORDS:
                concepts.setdefault(normalized, display_concept(match))
            if len(concepts) >= limit:
                return list(concepts.values())
    return list(concepts.values())


def extract_formulas(markdown: str) -> list[str]:
    formulas: list[str] = []
    seen: set[str] = set()
    for pattern in _FORMULA_PATTERNS:
        for match in pattern.finditer(markdown):
            formula = match.group(1).strip()
            if formula and formula not in seen:
                formulas.append(formula)
                seen.add(formula)
    return formulas


def normalize_concept(value: str) -> str:
    return value.strip().lower()


def display_concept(value: str) -> str:
    stripped = value.strip()
    if stripped.isascii():
        return stripped.lower()
    return stripped
