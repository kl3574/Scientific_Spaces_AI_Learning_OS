from __future__ import annotations

import socket

import pytest

from app.references.deduplication import build_reference_data
from app.references.extraction import extract_article_references
from app.references.network import NetworkAccessBlocked, ZeroNetworkGuard
from app.references.models import sha256_text
from tests.references.helpers import article


def test_markdown_extraction_preserves_sections_spans_and_classifications() -> None:
    item = article(
        "a1",
        """# Introduction
See DOI:10.1000/ABC and arXiv:1706.03762v2.

## Links
[paper](https://example.org/paper?utm_source=x&id=1)
[unsafe](javascript:alert(1))
[credential](https://user:secret@example.org/private)

```text
https://code.example/not-a-reference
```

## 参考文献
[1] 张三，科学计算方法，高等教育出版社，2020。
""",
    )

    result = extract_article_references(item)

    assert result.status == "classified"
    assert result.detected_candidate_count == len(result.candidates)
    by_type = {candidate.normalization.reference_type for candidate in result.candidates}
    assert {"doi", "arxiv", "http_url", "citation_text", "unsupported"} <= by_type
    assert all(candidate.source_section for candidate in result.candidates)
    assert all(candidate.source_span_start is not None for candidate in result.candidates)
    assert all(candidate.source_span_start < candidate.source_span_end for candidate in result.candidates)
    assert any(candidate.normalization.classification == "rejected" for candidate in result.candidates)
    assert all("secret" not in candidate.raw_reference for candidate in result.candidates)
    doi = next(candidate for candidate in result.candidates if candidate.normalization.reference_type == "doi")
    assert doi.source_section == "Introduction"
    assert doi.normalization.doi == "10.1000/abc"


def test_no_reference_article_receives_terminal_status() -> None:
    result = extract_article_references(article("none", "# Title\n\nA short paragraph with no references."))
    assert result.status == "no_reference"
    assert result.detected_candidate_count == 0
    assert result.candidates == []


def test_exact_duplicates_merge_but_cross_article_evidence_is_retained() -> None:
    first = article("a1", "# One\nDOI:10.1000/example\n\n## Again\nhttps://doi.org/10.1000/example")
    second = article("a2", "# Two\n10.1000/example")
    extractions = [extract_article_references(first), extract_article_references(second)]

    data = build_reference_data(extractions, corpus_fingerprint=sha256_text("corpus"), build_id="build")

    doi_records = [record for record in data.records if record.reference_type == "doi"]
    assert len(doi_records) == 1
    assert doi_records[0].classification == "duplicate"
    assert doi_records[0].source_count == 3
    assert len({item.source_article_id for item in data.evidence}) == 2
    assert doi_records[0].duplicate_group_id is not None


def test_arxiv_versions_do_not_exact_merge_but_share_possible_group() -> None:
    data = build_reference_data(
        [extract_article_references(article("a1", "arXiv:1706.03762v1 and arXiv:1706.03762v2"))],
        corpus_fingerprint=sha256_text("corpus"),
        build_id="build",
    )
    records = [record for record in data.records if record.reference_type == "arxiv"]
    assert len(records) == 2
    assert {record.arxiv_version for record in records} == {1, 2}
    assert len({record.duplicate_group_id for record in records}) == 1


def test_candidate_limit_is_terminally_classified() -> None:
    content = "\n".join(f"https://example.org/{index}" for index in range(10))
    result = extract_article_references(article("many", content), max_candidates=3)
    assert result.detected_candidate_count == 10
    assert result.overflow_candidate_count == 7
    assert len(result.candidates) == 4
    assert result.candidates[-1].normalization.classification == "unsupported"


def test_zero_network_guard_counts_and_blocks_attempts() -> None:
    with ZeroNetworkGuard() as counters:
        with pytest.raises(NetworkAccessBlocked):
            socket.create_connection(("example.com", 443))
    assert counters.external_network_request_count == 0
    assert counters.unexpected_network_attempt_count == 1


def test_doi_and_url_candidates_stop_at_markdown_and_cjk_boundaries() -> None:
    item = article(
        "boundary",
        """[Book](https://example.org/book/10.1201/9781420034813)。现在继续正文。
[Post](https://spaces.ac.cn/archives/1639 "optional title")
url={\\url{https://spaces.ac.cn/archives/407}},
""",
    )
    result = extract_article_references(item)
    doi = next(candidate for candidate in result.candidates if candidate.normalization.reference_type == "doi")
    assert doi.normalization.doi == "10.1201/9781420034813"
    urls = {
        candidate.normalization.normalized_url
        for candidate in result.candidates
        if candidate.normalization.normalized_url
    }
    assert "https://spaces.ac.cn/archives/1639" in urls
    assert "https://spaces.ac.cn/archives/407" in urls
    assert all("optional%20title" not in value and "%7D" not in value for value in urls)
