from __future__ import annotations

import hashlib
import json
import time
import tracemalloc
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles
from app.references.deduplication import DEDUPLICATION_RULE_VERSION, build_reference_data
from app.references.extraction import EXTRACTION_RULE_VERSION, ArticleExtraction, extract_article_references
from app.references.matching import MATCHER_VERSION, match_reference_records
from app.references.models import (
    REFERENCE_EVIDENCE_SCHEMA,
    REFERENCE_MANIFEST_SCHEMA,
    REFERENCE_RECORD_SCHEMA,
    ZOTERO_CANDIDATE_SCHEMA,
    canonical_json,
    sha256_text,
)
from app.references.network import ZeroNetworkGuard
from app.references.normalization import NORMALIZATION_VERSION
from app.references.selection import SELECTION_RULE_VERSION, PilotSelection, select_pilot_articles
from app.references.store import (
    INTEGRITY_RULE_VERSION,
    STORE_FORMAT_VERSION,
    StoreInstallResult,
    install_reference_store,
)
from app.zotero.fake import FakeZoteroProvider


@dataclass(frozen=True)
class ReferencePilotConfig:
    article_store: Path
    output_dir: Path
    sample_size: int = 75
    no_network: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_store", Path(self.article_store))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        if not 50 <= self.sample_size <= 100:
            raise ValueError("sample_size must be between 50 and 100")
        if not self.no_network:
            raise ValueError("P3-003 pilot requires --no-network")


@dataclass(frozen=True)
class ReferencePilotResult:
    status: str
    article_store_sha256_before: str
    article_store_sha256_after: str
    corpus_fingerprint_before: str
    corpus_fingerprint_after: str
    selection_only_inventory_article_count: int
    pilot_article_count: int
    unselected_article_count: int
    unselected_reference_output_count: int
    selection_fingerprint: str
    selected_article_ids: list[str]
    selected_strata: list[dict[str, Any]]
    tag_counts: dict[str, int]
    article_status_counts: dict[str, int]
    detected_candidate_count: int
    classified_candidate_count: int
    overflow_candidate_count: int
    silent_drop_count: int
    record_count: int
    evidence_count: int
    zotero_candidate_count: int
    articles_classified_rate: float
    provenance_complete_rate: float
    deterministic_id_rate: float
    duplicate_group_consistency_rate: float
    external_network_request_count: int
    unexpected_network_attempt_count: int
    automatic_write_count: int
    false_exact_zotero_fixture_matches: int
    store_no_op_rerun: bool
    store_build_fingerprint: str
    configuration_fingerprint: str
    elapsed_seconds: float
    peak_memory_bytes: int
    output_bytes: int
    human_review: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reference_pilot(config: ReferencePilotConfig) -> ReferencePilotResult:
    started = time.perf_counter()
    tracemalloc.start()
    article_sha_before = _file_sha256(config.article_store)
    with ZeroNetworkGuard() as network:
        articles = load_full_corpus_articles(config.article_store)
        corpus_before = compute_corpus_fingerprint(articles)
        selection = select_pilot_articles(articles, sample_size=config.sample_size)
        extractions = [extract_article_references(article) for article in selection.selected_articles]
        configuration = {
            "sample_size": config.sample_size,
            "selection_rule_version": SELECTION_RULE_VERSION,
            "extractor_version": EXTRACTION_RULE_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "deduplication_version": DEDUPLICATION_RULE_VERSION,
            "matcher_version": MATCHER_VERSION,
            "store_format_version": STORE_FORMAT_VERSION,
            "integrity_rule_version": INTEGRITY_RULE_VERSION,
            "manifest_schema_version": REFERENCE_MANIFEST_SCHEMA,
            "record_schema_version": REFERENCE_RECORD_SCHEMA,
            "evidence_schema_version": REFERENCE_EVIDENCE_SCHEMA,
            "candidate_schema_version": ZOTERO_CANDIDATE_SCHEMA,
            "no_network": True,
        }
        configuration_fingerprint = sha256_text(canonical_json(configuration))
        build_fingerprint = sha256_text(
            canonical_json(
                {
                    "corpus_fingerprint": corpus_before,
                    "selection_fingerprint": selection.selection_fingerprint,
                    "configuration_fingerprint": configuration_fingerprint,
                }
            )
        )
        build_data = build_reference_data(
            extractions,
            corpus_fingerprint=corpus_before,
            build_id=build_fingerprint,
        )
        fake_provider = FakeZoteroProvider()
        match_summary = match_reference_records(build_data.records, fake_provider.items, provider_available=True)
        detected = sum(item.detected_candidate_count for item in extractions)
        overflow = sum(item.overflow_candidate_count for item in extractions)
        classified = sum(
            len(item.candidates) - (1 if item.overflow_candidate_count else 0)
            for item in extractions
        ) + overflow
        silent_drop = max(0, detected - classified)
        article_status_counts = dict(sorted(Counter(item.status for item in extractions).items()))
        extra_counts = {
            "selection_only_inventory_articles": selection.inventory_article_count,
            "selected_articles": len(selection.selected_articles),
            "unselected_reference_output_count": 0,
            "detected_candidates": detected,
            "classified_candidates": classified,
            "overflow_candidates": overflow,
            "silent_drops": silent_drop,
            "article_statuses": article_status_counts,
            "external_network_requests": network.external_network_request_count,
            "unexpected_network_attempts": network.unexpected_network_attempt_count,
            "automatic_writes": match_summary.automatic_write_count,
        }
        install = install_reference_store(
            config.output_dir,
            build_data=build_data,
            zotero_candidates=match_summary.candidates,
            article_ids=[article.id for article in selection.selected_articles],
            corpus_fingerprint=corpus_before,
            configuration_fingerprint=configuration_fingerprint,
            build_fingerprint=build_fingerprint,
            source_asset_id=f"article-store:{corpus_before[:16]}",
            network_request_count=network.external_network_request_count,
            extra_counts=extra_counts,
        )
        rerun = install_reference_store(
            config.output_dir,
            build_data=build_data,
            zotero_candidates=match_summary.candidates,
            article_ids=[article.id for article in selection.selected_articles],
            corpus_fingerprint=corpus_before,
            configuration_fingerprint=configuration_fingerprint,
            build_fingerprint=build_fingerprint,
            source_asset_id=f"article-store:{corpus_before[:16]}",
            network_request_count=network.external_network_request_count,
            extra_counts=extra_counts,
        )
        review_cases = _write_runtime_reports(
            config.output_dir,
            selection,
            build_data.records,
            match_summary.candidates,
            build_fingerprint=build_fingerprint,
        )
        human_review = read_human_review(
            config.output_dir / "reports" / "human_review.json",
            expected_build_fingerprint=build_fingerprint,
            expected_cases={case["reference_id"]: case["reference_type"] for case in review_cases},
        )
        articles_after = load_full_corpus_articles(config.article_store)
        corpus_after = compute_corpus_fingerprint(articles_after)

    article_sha_after = _file_sha256(config.article_store)
    current, peak = tracemalloc.get_traced_memory()
    del current
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    output_bytes = sum(path.stat().st_size for path in config.output_dir.rglob("*") if path.is_file())
    article_count = len(selection.selected_articles)
    provenance_complete = _provenance_complete_rate(build_data.records, build_data.evidence)
    machine_blocked = False
    if (
        article_sha_before != article_sha_after
        or corpus_before != corpus_after
        or silent_drop != 0
        or network.external_network_request_count != 0
        or network.unexpected_network_attempt_count != 0
        or not rerun.no_op
        or match_summary.automatic_write_count != 0
    ):
        machine_blocked = True
    if machine_blocked:
        status = "BLOCKED"
    elif human_review.get("status") == "PASS":
        status = "PASS"
    else:
        status = "PENDING_REVIEW"
    return ReferencePilotResult(
        status=status,
        article_store_sha256_before=article_sha_before,
        article_store_sha256_after=article_sha_after,
        corpus_fingerprint_before=corpus_before,
        corpus_fingerprint_after=corpus_after,
        selection_only_inventory_article_count=selection.inventory_article_count,
        pilot_article_count=article_count,
        unselected_article_count=selection.inventory_article_count - article_count,
        unselected_reference_output_count=0,
        selection_fingerprint=selection.selection_fingerprint,
        selected_article_ids=[article.id for article in selection.selected_articles],
        selected_strata=[item.to_report_dict() for item in selection.selected_inventory],
        tag_counts=selection.tag_counts,
        article_status_counts=article_status_counts,
        detected_candidate_count=detected,
        classified_candidate_count=classified,
        overflow_candidate_count=overflow,
        silent_drop_count=silent_drop,
        record_count=len(build_data.records),
        evidence_count=len(build_data.evidence),
        zotero_candidate_count=len(match_summary.candidates),
        articles_classified_rate=article_count / article_count if article_count else 0.0,
        provenance_complete_rate=provenance_complete,
        deterministic_id_rate=float(build_data.metrics["deterministic_id_rate"]),
        duplicate_group_consistency_rate=float(build_data.metrics["duplicate_group_consistency_rate"]),
        external_network_request_count=network.external_network_request_count,
        unexpected_network_attempt_count=network.unexpected_network_attempt_count,
        automatic_write_count=match_summary.automatic_write_count,
        false_exact_zotero_fixture_matches=match_summary.false_exact_fixture_count,
        store_no_op_rerun=rerun.no_op,
        store_build_fingerprint=install.manifest.build_fingerprint,
        configuration_fingerprint=configuration_fingerprint,
        elapsed_seconds=round(elapsed, 6),
        peak_memory_bytes=peak,
        output_bytes=output_bytes,
        human_review=human_review,
    )


def read_human_review(
    path: Path,
    *,
    expected_build_fingerprint: str | None = None,
    expected_cases: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "PENDING",
            "reviewed_case_count": 0,
            "reviewer_count": 0,
            "single_review_limitation": False,
            "strong_identifier_numerator": 0,
            "strong_identifier_denominator": 0,
            "disagreement_count": 0,
            "strong_identifier_precision": None,
            "invalid_case_count": 0,
            "stale_reason": None,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if expected_build_fingerprint is not None and payload.get("store_build_fingerprint") != expected_build_fingerprint:
        return {
            "status": "STALE",
            "reviewed_case_count": 0,
            "reviewer_count": 0,
            "single_review_limitation": False,
            "strong_identifier_numerator": 0,
            "strong_identifier_denominator": 0,
            "disagreement_count": 0,
            "strong_identifier_precision": None,
            "invalid_case_count": 0,
            "stale_reason": "store_build_fingerprint_mismatch",
        }
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    completed = []
    reviewers: set[str] = set()
    seen_reference_ids: set[str] = set()
    invalid_cases = 0
    disagreements = 0
    strong_numerator = 0
    strong_denominator = 0
    for case in cases:
        reference_id = str(case.get("reference_id", ""))
        if not reference_id or reference_id in seen_reference_ids:
            invalid_cases += 1
            continue
        if expected_cases is not None and (
            reference_id not in expected_cases or case.get("reference_type") != expected_cases[reference_id]
        ):
            invalid_cases += 1
            continue
        seen_reference_ids.add(reference_id)
        submitted_reviews = [
            review for review in case.get("reviews", []) if review.get("reviewer_status") == "complete"
        ]
        reviews = [review for review in submitted_reviews if _valid_completed_review(review)]
        if len(reviews) != len(submitted_reviews):
            invalid_cases += 1
            continue
        if not reviews:
            continue
        completed.append(case)
        reviewers.update(str(review.get("reviewer_id")) for review in reviews if review.get("reviewer_id"))
        judgement_keys = (
            "extraction_validity",
            "normalized_identity",
            "evidence_sufficiency",
            "duplicate_decision",
            "zotero_decision",
        )
        disagreement = any(len({str(review.get(key)) for review in reviews}) > 1 for key in judgement_keys)
        if disagreement:
            disagreements += 1
        if case.get("reference_type") in {"doi", "arxiv"}:
            strong_denominator += 1
            valid = all(
                review.get("extraction_validity") == "valid"
                and review.get("normalized_identity") == "correct"
                and review.get("evidence_sufficiency") == "sufficient"
                for review in reviews
            )
            if valid and not disagreement:
                strong_numerator += 1
    precision = strong_numerator / strong_denominator if strong_denominator else None
    status = (
        "PASS"
        if len(completed) >= 30 and precision is not None and precision >= 0.95 and invalid_cases == 0
        else "PENDING"
    )
    return {
        "status": status,
        "reviewed_case_count": len(completed),
        "reviewer_count": len(reviewers),
        "single_review_limitation": len(reviewers) == 1,
        "strong_identifier_numerator": strong_numerator,
        "strong_identifier_denominator": strong_denominator,
        "disagreement_count": disagreements,
        "strong_identifier_precision": precision,
        "invalid_case_count": invalid_cases,
        "stale_reason": None,
    }


def _valid_completed_review(review: dict[str, Any]) -> bool:
    return (
        bool(review.get("reviewer_id"))
        and review.get("extraction_validity") in {"valid", "invalid"}
        and review.get("normalized_identity") in {"correct", "incorrect", "not_applicable"}
        and review.get("evidence_sufficiency") in {"sufficient", "insufficient"}
        and review.get("duplicate_decision") in {"correct", "incorrect", "not_applicable"}
        and review.get("zotero_decision") in {"correct", "incorrect", "not_applicable"}
        and isinstance(review.get("comment"), str)
        and bool(review["comment"].strip())
    )


def _write_runtime_reports(
    output_dir: Path,
    selection: PilotSelection,
    records: list[Any],
    zotero_candidates: list[Any],
    *,
    build_fingerprint: str,
) -> list[dict[str, Any]]:
    reports = output_dir / "reports"
    reports.mkdir(exist_ok=True)
    selection_payload = {
        "selection_rule_version": SELECTION_RULE_VERSION,
        "inventory_article_count": selection.inventory_article_count,
        "selected_article_count": len(selection.selected_articles),
        "unselected_reference_output_count": 0,
        "selection_fingerprint": selection.selection_fingerprint,
        "tag_counts": selection.tag_counts,
        "selected": [item.to_report_dict() for item in selection.selected_inventory],
    }
    _write_json(reports / "selection.json", selection_payload)
    review_path = reports / "human_review_template.json"
    by_reference = {candidate.reference_id: candidate for candidate in zotero_candidates}
    ordered = _select_human_review_records(records, by_reference)
    template = {
        "schema_version": "reference-human-review/v1",
        "store_build_fingerprint": build_fingerprint,
        "selection_fingerprint": selection.selection_fingerprint,
        "selection": (
            "exact-and-probable-then-strong-identifiers-rejected-suspicious-"
            "then-stable-reference-id"
        ),
        "cases": [
            {
                "reference_id": record.reference_id,
                "reference_type": record.reference_type,
                "classification": record.classification,
                "normalized_identifier": record.normalized_identifier,
                "normalized_url": record.normalized_url,
                "raw_reference": record.raw_reference,
                "confidence": record.confidence,
                "duplicate_group_id": record.duplicate_group_id,
                "source_count": record.source_count,
                "source_article_id": record.source_article_id,
                "source_section": record.source_section,
                "evidence_text": record.evidence_text,
                "candidate_decision": by_reference.get(record.reference_id).decision
                if by_reference.get(record.reference_id)
                else "unmatched",
                "selection_reason": selection_reason,
                "reviews": [],
            }
            for record, selection_reason in ordered
        ],
    }
    _write_json(review_path, template)
    return template["cases"]


def _select_human_review_records(
    records: list[Any],
    by_reference: dict[str, Any],
) -> list[tuple[Any, str]]:
    stable = sorted(records, key=lambda item: item.reference_id)
    selected: list[tuple[Any, str]] = []
    selected_ids: set[str] = set()

    def add_group(reason: str, candidates: list[Any], limit: int) -> None:
        for record in candidates:
            if len([item for item in selected if item[1] == reason]) >= limit:
                break
            if record.reference_id in selected_ids:
                continue
            selected.append((record, reason))
            selected_ids.add(record.reference_id)

    add_group(
        "zotero_exact",
        [item for item in stable if getattr(by_reference.get(item.reference_id), "decision", None) == "exact"],
        20,
    )
    add_group(
        "zotero_probable",
        [item for item in stable if getattr(by_reference.get(item.reference_id), "decision", None) == "probable"],
        20,
    )
    add_group("strong_identifier", [item for item in stable if item.reference_type in {"doi", "arxiv"}], 20)
    add_group(
        "rejected_or_malformed",
        [
            item
            for item in stable
            if item.classification in {"malformed", "rejected", "unsupported"}
            or item.reference_type in {"malformed", "unsupported"}
        ],
        10,
    )
    add_group("suspicious_high_confidence", [item for item in stable if _is_suspicious_url(item)], 10)
    add_group("stable_sample", stable, max(0, 40 - len(selected)))
    return selected


def _is_suspicious_url(record: Any) -> bool:
    if record.reference_type not in {"http_url", "relative_or_internal_url"} or record.confidence < 0.8:
        return False
    url = (record.normalized_url or "").lower()
    return any(
        marker in url
        for marker in (
            "/usr/uploads/",
            "/payment/",
            "#share",
            "#pay",
        )
    )


def _provenance_complete_rate(records: list[Any], evidence: list[Any]) -> float:
    required_records = all(
        record.source_article_id
        and record.source_article_title
        and record.source_article_url
        and record.source_section
        and record.evidence_ids
        and record.source_count == len(record.evidence_ids)
        for record in records
    )
    required_evidence = all(
        item.source_article_id
        and item.source_article_title
        and item.source_article_url
        and item.source_section
        and item.raw_reference_hash
        for item in evidence
    )
    return 1.0 if required_records and required_evidence else 0.0


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
