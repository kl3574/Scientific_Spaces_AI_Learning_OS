from __future__ import annotations

from app.references.matching import match_reference_records
from app.zotero.models import ZoteroItem
from tests.references.helpers import article, reference_data


def _item(*, key: str, title: str, doi: str | None = None, url: str | None = None) -> ZoteroItem:
    return ZoteroItem(
        item_key=key,
        bibtex_key=None,
        title=title,
        creators=[],
        year="2020",
        item_type="journalArticle",
        publication_title=None,
        doi=doi,
        url=url,
        abstract_note=None,
        tags=[],
        collections=[],
        updated_at=None,
    )


def test_doi_and_version_compatible_arxiv_are_exact_without_conflicts() -> None:
    data = reference_data(article("a1", "DOI:10.1000/example and arXiv:1706.03762v2"))
    summary = match_reference_records(
        data.records,
        [
            _item(key="D1", title="DOI item", doi="10.1000/example"),
            _item(key="A1", title="Attention", url="https://arxiv.org/abs/1706.03762v2"),
        ],
    )
    exact = [candidate for candidate in summary.candidates if candidate.decision == "exact"]
    assert {candidate.match_method for candidate in exact} == {"doi_exact", "arxiv_exact"}
    assert summary.automatic_write_count == 0


def test_title_only_match_remains_ambiguous() -> None:
    data = reference_data(article("a1", "# References\nAttention Is All You Need Transformer Architecture"))
    summary = match_reference_records(
        data.records,
        [_item(key="T1", title="Attention Is All You Need Transformer Architecture")],
    )
    assert all(candidate.decision != "exact" for candidate in summary.candidates)
    assert any(candidate.decision == "ambiguous" for candidate in summary.candidates)


def test_unavailable_provider_is_nonfatal_and_has_no_write() -> None:
    data = reference_data(article("a1", "DOI:10.1000/example"))
    summary = match_reference_records(data.records, None, provider_available=False)
    assert len(summary.candidates) == len(data.records)
    assert {candidate.decision for candidate in summary.candidates} == {"unmatched"}
    assert summary.automatic_write_count == 0


def test_conflicting_strong_identifier_never_becomes_exact() -> None:
    data = reference_data(article("a1", "DOI:10.1000/example"))
    summary = match_reference_records(
        data.records,
        [_item(key="D2", title="Other", doi="10.1000/different")],
    )
    assert all(candidate.decision != "exact" for candidate in summary.candidates)
