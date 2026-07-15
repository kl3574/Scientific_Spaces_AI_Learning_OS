from __future__ import annotations

import json
from pathlib import Path

from app.references.normalization import normalize_arxiv, normalize_citation_text, normalize_doi, normalize_url


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "references" / "normalization_cases.json"


def test_normalization_fixture_matrix_has_at_least_sixty_unique_cases() -> None:
    cases = _cases()
    assert len(cases) >= 60
    assert len({case["id"] for case in cases}) == len(cases)


def test_all_normalization_fixtures_match_the_contract() -> None:
    for case in _cases():
        kind = case["kind"]
        raw = case["raw"]
        if kind == "doi":
            result = normalize_doi(raw)
        elif kind == "arxiv":
            result = normalize_arxiv(raw)
        elif kind == "url":
            result = normalize_url(raw, article_url=case.get("article_url", "https://spaces.ac.cn/archives/6508"))
        else:
            result = normalize_citation_text(raw)
        for key, expected in case["expected"].items():
            assert getattr(result, key) == expected, f"{case['id']} field {key}"


def _cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
