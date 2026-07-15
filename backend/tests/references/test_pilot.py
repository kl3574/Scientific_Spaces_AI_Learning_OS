from __future__ import annotations

import json
from pathlib import Path

from app.references.pilot import ReferencePilotConfig, read_human_review, run_reference_pilot


def test_bounded_pilot_uses_selection_only_inventory_and_emits_only_selected_articles(tmp_path: Path) -> None:
    article_store = tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "articles.json"
    output_dir = tmp_path / ".local_data" / "scientific_spaces" / "references" / "pilot"
    _write_article_store(article_store, count=55)

    result = run_reference_pilot(
        ReferencePilotConfig(
            article_store=article_store,
            output_dir=output_dir,
            sample_size=50,
            no_network=True,
        )
    )

    assert result.status == "PENDING_REVIEW"
    assert result.selection_only_inventory_article_count == 55
    assert result.pilot_article_count == 50
    assert result.unselected_article_count == 5
    assert result.unselected_reference_output_count == 0
    assert result.articles_classified_rate == 1.0
    assert result.silent_drop_count == 0
    assert result.external_network_request_count == 0
    assert result.unexpected_network_attempt_count == 0
    assert result.article_store_sha256_before == result.article_store_sha256_after
    assert result.corpus_fingerprint_before == result.corpus_fingerprint_after
    assert result.store_no_op_rerun is True
    article_index = json.loads((output_dir / "article_index.json").read_text(encoding="utf-8"))
    assert set(article_index) == set(result.selected_article_ids)
    review_cases = json.loads(
        (output_dir / "reports" / "human_review_template.json").read_text(encoding="utf-8")
    )["cases"]
    assert len(review_cases) >= 30
    assert any(case["selection_reason"] == "strong_identifier" for case in review_cases)
    assert any(case["selection_reason"] == "rejected_or_malformed" for case in review_cases)
    assert all("classification" in case and "normalized_url" in case for case in review_cases)


def test_human_review_precision_keeps_disagreement_in_denominator(tmp_path: Path) -> None:
    path = tmp_path / "human_review.json"
    cases = []
    for index in range(30):
        reviews = [
            {
                "reviewer_id": "reviewer-1",
                "reviewer_status": "complete",
                "extraction_validity": "valid",
                "normalized_identity": "correct",
                "evidence_sufficiency": "sufficient",
                "duplicate_decision": "correct",
                "zotero_decision": "correct",
                "comment": "reviewed",
            }
        ]
        if index == 0:
            reviews.append(
                {
                    "reviewer_id": "reviewer-2",
                    "reviewer_status": "complete",
                    "extraction_validity": "invalid",
                    "normalized_identity": "incorrect",
                    "evidence_sufficiency": "insufficient",
                    "duplicate_decision": "incorrect",
                    "zotero_decision": "incorrect",
                    "comment": "independent disagreement",
                }
            )
        cases.append({"reference_id": f"r{index}", "reference_type": "doi", "reviews": reviews})
    path.write_text(json.dumps({"cases": cases}), encoding="utf-8")

    result = read_human_review(path)

    assert result["reviewed_case_count"] == 30
    assert result["reviewer_count"] == 2
    assert result["disagreement_count"] == 1
    assert result["strong_identifier_numerator"] == 29
    assert result["strong_identifier_denominator"] == 30
    assert result["strong_identifier_precision"] == 29 / 30
    assert result["status"] == "PASS"


def test_human_review_rejects_a_stale_store_build(tmp_path: Path) -> None:
    path = tmp_path / "human_review.json"
    path.write_text(
        json.dumps(
            {
                "store_build_fingerprint": "old-build",
                "cases": [
                    {
                        "reference_id": "ref-1",
                        "reference_type": "doi",
                        "reviews": [{"reviewer_id": "reviewer-1", "reviewer_status": "complete"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = read_human_review(
        path,
        expected_build_fingerprint="new-build",
        expected_cases={"ref-1": "doi"},
    )

    assert result["status"] == "STALE"
    assert result["reviewed_case_count"] == 0
    assert result["stale_reason"] == "store_build_fingerprint_mismatch"


def _write_article_store(path: Path, *, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(count):
        marker = index % 10
        content = (
            f"# Article {index}\n\n"
            f"Synthetic citation DOI:10.1000/example-{index}.\n\n"
            + ("## References\n[1] Example Author, Example Work, 2020.\n" if marker % 2 == 0 else "")
            + ("Formula $x^2 + y^2$ and [link](https://example.org/paper).\n" if marker % 3 == 0 else "")
            + ("```text\nhttps://code.example/ignored\n```\n" if marker % 5 == 0 else "")
        )
        records.append(
            {
                "id": f"article-{index:03d}",
                "title": f"Synthetic Article {index}",
                "url": f"https://spaces.ac.cn/archives/{1000 + index}",
                "content": content,
                "metadata": {
                    "date": f"{2010 + index % 15}-01-01",
                    "category": "fixture",
                    "references": [],
                    "images": [],
                },
            }
        )
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
