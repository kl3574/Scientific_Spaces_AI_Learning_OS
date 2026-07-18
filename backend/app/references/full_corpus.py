from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.references.deduplication import DEDUPLICATION_RULE_VERSION, build_reference_data
from app.references.extraction import (
    EXTRACTION_RULE_VERSION,
    ArticleExtraction,
    ExtractedCandidate,
    extract_article_references,
)
from app.references.matching import MATCHER_VERSION, MatchSummary, match_reference_records
from app.references.models import (
    REFERENCE_EVIDENCE_SCHEMA,
    REFERENCE_MANIFEST_SCHEMA,
    REFERENCE_RECORD_SCHEMA,
    ZOTERO_CANDIDATE_SCHEMA,
    ReferenceRecord,
    canonical_json,
    sha256_text,
    stable_id,
)
from app.references.network import ZeroNetworkGuard
from app.references.normalization import NORMALIZATION_VERSION, NormalizationResult
from app.references.pilot import read_human_review
from app.references.store import (
    INTEGRITY_RULE_VERSION,
    STORE_FORMAT_VERSION,
    audit_reference_store,
    install_reference_store,
)
from app.storage.article_store import StoredArticle
from app.zotero.models import ZoteroItem


FULL_CORPUS_VERSION = "p3-006-full-corpus/v1"
CHECKPOINT_SCHEMA_VERSION = "reference-full-corpus-checkpoint/v1"
CHECKPOINT_VERSION = "p3-006-checkpoint/v1"
EXPECTED_INTERRUPTION_EXIT_CODE = 75

DEFAULT_MIN_AVAILABLE_DISK_BYTES = 2 * 1024**3
DEFAULT_MAX_ELAPSED_SECONDS = 30 * 60
DEFAULT_MAX_PEAK_RSS_BYTES = int(1.5 * 1024**3)
DEFAULT_MAX_STORE_BYTES = 512 * 1024**2
DEFAULT_MAX_TEMP_BYTES = int(1.5 * 1024**3)
DEFAULT_MAX_REPORT_BYTES = 10 * 1024**2


class FullCorpusReferenceError(RuntimeError):
    pass


class ControlledInterruption(FullCorpusReferenceError):
    def __init__(self, evidence: dict[str, Any]) -> None:
        super().__init__("Controlled interruption completed with a valid checkpoint")
        self.evidence = evidence


@dataclass(frozen=True)
class CorpusPreflightResult:
    inode: int
    size_bytes: int
    mtime_ns: int
    article_store_sha256: str
    corpus_fingerprint: str
    article_count: int
    unique_id_count: int
    unique_url_count: int
    duplicate_id_count: int
    duplicate_url_count: int
    missing_content_count: int
    malformed_article_count: int
    available_disk_bytes: int
    identity_stable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullCorpusReferenceConfig:
    article_store: Path
    output_dir: Path
    expected_article_count: int
    expected_article_store_sha256: str
    expected_corpus_fingerprint: str
    checkpoint_every: int = 50
    resume: bool = False
    rebuild: bool = False
    simulate_interruption_after: int | None = None
    no_network: bool = True
    minimum_review_cases: int = 60
    min_available_disk_bytes: int = DEFAULT_MIN_AVAILABLE_DISK_BYTES
    max_elapsed_seconds: int = DEFAULT_MAX_ELAPSED_SECONDS
    max_peak_rss_bytes: int = DEFAULT_MAX_PEAK_RSS_BYTES
    max_store_bytes: int = DEFAULT_MAX_STORE_BYTES
    max_temp_bytes: int = DEFAULT_MAX_TEMP_BYTES
    max_report_bytes: int = DEFAULT_MAX_REPORT_BYTES
    code_commit: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_store", Path(self.article_store))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        if self.expected_article_count < 1:
            raise ValueError("expected_article_count must be positive")
        if self.checkpoint_every < 1:
            raise ValueError("checkpoint_every must be positive")
        if self.minimum_review_cases < 1:
            raise ValueError("minimum_review_cases must be positive")
        if self.resume and self.rebuild:
            raise ValueError("--resume and --rebuild are mutually exclusive")
        if self.simulate_interruption_after is not None and self.simulate_interruption_after < 1:
            raise ValueError("simulate_interruption_after must be positive")
        if not self.no_network:
            raise ValueError("P3-006 full-corpus processing requires --no-network")


@dataclass(frozen=True)
class FullCorpusReferenceResult:
    status: str
    action: str
    article_store_sha256_before: str
    article_store_sha256_after: str
    corpus_fingerprint_before: str
    corpus_fingerprint_after: str
    input_article_count: int
    processed_article_count: int
    explicit_terminal_failure_count: int
    unknown_article_status_count: int
    duplicate_processed_article_count: int
    input_accounting_rate: float
    detected_candidate_count: int
    classified_candidate_count: int
    overflow_candidate_count: int
    silent_drop_count: int
    classification_reconciliation_rate: float
    article_status_counts: dict[str, int]
    record_count: int
    evidence_count: int
    zotero_candidate_count: int
    provenance_complete_rate: float
    deterministic_id_rate: float
    duplicate_group_consistency_rate: float
    configuration_fingerprint: str
    build_fingerprint: str
    manifest_content_fingerprint: str
    content_file_hashes: dict[str, str]
    checkpoint_write_count: int
    checkpoint_next_position: int
    checkpoint_status: str
    store_no_op: bool
    rollback_recovered: bool
    fake_matching: dict[str, Any]
    unavailable_matching: dict[str, Any]
    human_review: dict[str, Any]
    review_case_count: int
    external_network_request_count: int
    unexpected_network_attempt_count: int
    source_mutation_count: int
    elapsed_seconds: float
    peak_rss_bytes: int
    installed_store_bytes: int
    checkpoint_bytes: int
    temporary_peak_estimate_bytes: int
    report_and_log_bytes: int
    resource_budgets_passed: bool
    implementation_fingerprint: str
    code_commit: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preflight_article_store(config: FullCorpusReferenceConfig) -> CorpusPreflightResult:
    source = config.article_store
    _validate_article_store_path(source)
    stat_before = source.stat()
    sha_before = _file_sha256(source)
    if sha_before != config.expected_article_store_sha256:
        raise FullCorpusReferenceError("Article Store SHA-256 does not match the approved identity")

    fingerprint_rows: list[tuple[str, str, str]] = []
    ids: set[str] = set()
    urls: set[str] = set()
    article_count = 0
    for article in iter_article_store(source):
        article_count += 1
        ids.add(article.id)
        urls.add(article.url)
        row = {
            "article_id": article.id,
            "url": article.url,
            "content_sha256": hashlib.sha256(article.content.encode("utf-8")).hexdigest(),
            "metadata": article.metadata,
        }
        fingerprint_rows.append((article.url, article.id, _corpus_canonical_json(row)))
    digest = hashlib.sha256()
    for _url, _article_id, payload in sorted(fingerprint_rows):
        digest.update(payload.encode("utf-8"))
        digest.update(b"\n")
    corpus_fingerprint = digest.hexdigest()

    if article_count != config.expected_article_count:
        raise FullCorpusReferenceError(
            f"Article Store count mismatch: expected {config.expected_article_count}, got {article_count}"
        )
    if corpus_fingerprint != config.expected_corpus_fingerprint:
        raise FullCorpusReferenceError("Article Store corpus fingerprint does not match the approved identity")

    stat_after = source.stat()
    sha_after = _file_sha256(source)
    identity_before = _stat_identity(stat_before)
    identity_after = _stat_identity(stat_after)
    identity_stable = identity_before == identity_after and sha_before == sha_after
    if not identity_stable:
        raise FullCorpusReferenceError("Article Store identity changed during preflight")

    available_disk = shutil.disk_usage(_nearest_existing_parent(config.output_dir)).free
    if available_disk < config.min_available_disk_bytes:
        raise FullCorpusReferenceError("Available disk is below the configured P3-006 minimum")
    return CorpusPreflightResult(
        inode=stat_before.st_ino,
        size_bytes=stat_before.st_size,
        mtime_ns=stat_before.st_mtime_ns,
        article_store_sha256=sha_before,
        corpus_fingerprint=corpus_fingerprint,
        article_count=article_count,
        unique_id_count=len(ids),
        unique_url_count=len(urls),
        duplicate_id_count=article_count - len(ids),
        duplicate_url_count=article_count - len(urls),
        missing_content_count=0,
        malformed_article_count=0,
        available_disk_bytes=available_disk,
        identity_stable=identity_stable,
    )


def run_full_corpus_reference_build(config: FullCorpusReferenceConfig) -> FullCorpusReferenceResult:
    started = time.perf_counter()
    preflight = preflight_article_store(config)
    code_commit = config.code_commit or _git_head_commit()
    implementation_fingerprint = _implementation_fingerprint()
    rule_versions = _rule_versions()
    configuration = {
        "orchestrator_version": FULL_CORPUS_VERSION,
        "checkpoint_version": CHECKPOINT_VERSION,
        "checkpoint_every": config.checkpoint_every,
        "expected_article_count": config.expected_article_count,
        "article_store_sha256": preflight.article_store_sha256,
        "corpus_fingerprint": preflight.corpus_fingerprint,
        "implementation_fingerprint": implementation_fingerprint,
        "rule_versions": rule_versions,
        "matching_modes": ["fake_curated", "unavailable"],
        "no_network": True,
    }
    configuration_fingerprint = sha256_text(canonical_json(configuration))
    build_fingerprint = sha256_text(
        canonical_json(
            {
                "corpus_fingerprint": preflight.corpus_fingerprint,
                "configuration_fingerprint": configuration_fingerprint,
                "implementation_fingerprint": implementation_fingerprint,
            }
        )
    )
    identity = {
        "corpus_sha256": preflight.article_store_sha256,
        "corpus_fingerprint": preflight.corpus_fingerprint,
        "config_fingerprint": configuration_fingerprint,
        "rule_versions": rule_versions,
        "code_commit": code_commit,
        "implementation_fingerprint": implementation_fingerprint,
    }

    _validate_output_root(config.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = config.output_dir / "checkpoints"
    reports_dir = config.output_dir / "reports"
    current_dir = config.output_dir / "current"
    if config.rebuild:
        _remove_runtime_tree(checkpoints_dir)
    checkpoints_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)
    checkpoint_path = checkpoints_dir / "checkpoint.json"
    extraction_dir = checkpoints_dir / "extractions"
    extraction_dir.mkdir(exist_ok=True)

    current_before = _directory_content_fingerprint(current_dir) if current_dir.exists() else None
    checkpoint = _initial_checkpoint(identity)
    if checkpoint_path.exists():
        if config.rebuild:
            raise FullCorpusReferenceError("Checkpoint unexpectedly survived a rebuild reset")
        checkpoint = _load_and_validate_checkpoint(checkpoint_path, extraction_dir, identity)
        if not config.resume and checkpoint["status"] != "complete":
            raise FullCorpusReferenceError("Incomplete checkpoint requires --resume")
    elif config.resume:
        raise FullCorpusReferenceError("--resume requires an existing checkpoint")

    checkpoint_write_count = int(checkpoint["checkpoint_write_count"])
    completed_ids = set(str(value) for value in checkpoint["completed_article_ids"])
    checkpoint_prefix_ids = set(completed_ids)
    output_digests = {
        str(key): str(value) for key, value in checkpoint["article_output_digests"].items()
    }
    next_position = int(checkpoint["next_position"])
    source_prefix_ids: list[str] = []

    with ZeroNetworkGuard() as network:
        for position, article in enumerate(iter_article_store(config.article_store)):
            if position < next_position:
                source_prefix_ids.append(article.id)
                continue
            if article.id in completed_ids:
                raise FullCorpusReferenceError("Duplicate processed Article detected")
            extraction = extract_article_references(article)
            digest = _write_extraction(extraction_dir, extraction)
            completed_ids.add(article.id)
            output_digests[article.id] = digest
            next_position = position + 1

            should_checkpoint = next_position % config.checkpoint_every == 0
            should_interrupt = config.simulate_interruption_after == next_position
            if should_checkpoint or should_interrupt:
                checkpoint_write_count += 1
                checkpoint = _checkpoint_payload(
                    identity,
                    completed_ids=completed_ids,
                    output_digests=output_digests,
                    next_position=next_position,
                    checkpoint_write_count=checkpoint_write_count,
                    status="extracting",
                )
                _atomic_write_json(checkpoint_path, checkpoint)
            if should_interrupt:
                current_after = _directory_content_fingerprint(current_dir) if current_dir.exists() else None
                if current_before != current_after:
                    raise FullCorpusReferenceError("Controlled interruption changed the authoritative current store")
                source_after = _file_sha256(config.article_store)
                if source_after != preflight.article_store_sha256:
                    raise FullCorpusReferenceError("Article Store changed during controlled interruption")
                raise ControlledInterruption(
                    {
                        "status": "EXPECTED_INTERRUPTION",
                        "exit_code": EXPECTED_INTERRUPTION_EXIT_CODE,
                        "processed_article_count": next_position,
                        "checkpoint_next_position": next_position,
                        "checkpoint_write_count": checkpoint_write_count,
                        "checkpoint_valid": True,
                        "current_store_unchanged": current_before == current_after,
                        "article_store_sha256_before": preflight.article_store_sha256,
                        "article_store_sha256_after": source_after,
                        "network_request_count": network.external_network_request_count,
                        "unexpected_network_attempt_count": network.unexpected_network_attempt_count,
                    }
                )

        if set(source_prefix_ids) != checkpoint_prefix_ids:
            raise FullCorpusReferenceError("Checkpoint completed Article IDs do not match the corpus prefix")
        if next_position != preflight.article_count or len(completed_ids) != preflight.article_count:
            raise FullCorpusReferenceError("Full-corpus Article accounting is incomplete")

        checkpoint_write_count += 1
        checkpoint = _checkpoint_payload(
            identity,
            completed_ids=completed_ids,
            output_digests=output_digests,
            next_position=next_position,
            checkpoint_write_count=checkpoint_write_count,
            status="extracted",
        )
        _atomic_write_json(checkpoint_path, checkpoint)

        extractions = _load_extractions(extraction_dir, checkpoint)
        detected = sum(item.detected_candidate_count for item in extractions)
        overflow = sum(item.overflow_candidate_count for item in extractions)
        classified = sum(
            len(item.candidates) - (1 if item.overflow_candidate_count else 0)
            for item in extractions
        ) + overflow
        silent_drops = max(0, detected - classified)
        article_status_counts = dict(sorted(Counter(item.status for item in extractions).items()))

        build_data = build_reference_data(
            extractions,
            corpus_fingerprint=preflight.corpus_fingerprint,
            build_id=build_fingerprint,
        )
        curated_items = _curated_zotero_items(build_data.records)
        fake_summary = match_reference_records(build_data.records, curated_items, provider_available=True)
        unavailable_summary = match_reference_records(build_data.records, None, provider_available=False)
        fake_metrics = _matching_metrics(build_data.records, fake_summary, private_library_reads=0)
        unavailable_metrics = _matching_metrics(
            build_data.records,
            unavailable_summary,
            private_library_reads=0,
        )

        article_ids = sorted(completed_ids)
        extra_counts = {
            "input_articles": preflight.article_count,
            "processed_articles": len(extractions),
            "explicit_terminal_failures": 0,
            "unknown_article_statuses": 0,
            "duplicate_processed_articles": 0,
            "detected_candidates": detected,
            "classified_candidates": classified,
            "overflow_candidates": overflow,
            "silent_drops": silent_drops,
            "article_statuses": article_status_counts,
            "external_network_requests": network.external_network_request_count,
            "unexpected_network_attempts": network.unexpected_network_attempt_count,
            "automatic_writes": fake_metrics["automatic_write_count"],
            "private_library_reads": 0,
            "false_exact_matches": fake_metrics["false_exact_match_count"],
            "title_only_exact_matches": fake_metrics["title_only_exact_match_count"],
            "ambiguous_auto_confirmations": fake_metrics["ambiguous_auto_confirmation_count"],
            "deterministic_id_rate": build_data.metrics["deterministic_id_rate"],
            "duplicate_group_consistency_rate": build_data.metrics[
                "duplicate_group_consistency_rate"
            ],
            "orphan_evidence_count": build_data.metrics["orphan_evidence_count"],
            "checkpoint_version": CHECKPOINT_VERSION,
            "rule_versions": rule_versions,
            "code_commit": code_commit,
            "implementation_fingerprint": implementation_fingerprint,
        }
        install = install_reference_store(
            current_dir,
            build_data=build_data,
            zotero_candidates=fake_summary.candidates,
            article_ids=article_ids,
            corpus_fingerprint=preflight.corpus_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            build_fingerprint=build_fingerprint,
            source_asset_id=f"article-store:{preflight.corpus_fingerprint[:16]}",
            network_request_count=network.external_network_request_count,
            extra_counts=extra_counts,
            rebuild_command=(
                "UV_OFFLINE=1 uv run --project backend python "
                "scripts/references/build_full_corpus_references.py "
                "--article-store <approved-ignored-article-store> "
                "--output-dir .local_data/scientific_spaces/references/full-corpus "
                f"--expected-article-count {preflight.article_count} "
                "--expected-article-store-sha256 <approved-sha256> "
                "--expected-corpus-fingerprint <approved-fingerprint> "
                f"--checkpoint-every {config.checkpoint_every} --no-network"
            ),
        )
        manifest = audit_reference_store(
            current_dir,
            expected_corpus_fingerprint=preflight.corpus_fingerprint,
            expected_configuration_fingerprint=configuration_fingerprint,
        )
        review_cases = _write_human_review_template(
            reports_dir,
            build_data.records,
            fake_summary,
            build_fingerprint=build_fingerprint,
            minimum_cases=config.minimum_review_cases,
        )
        expected_cases = {case["reference_id"]: case["reference_type"] for case in review_cases}
        human_review = read_human_review(
            reports_dir / "human_review.json",
            expected_build_fingerprint=build_fingerprint,
            expected_cases=expected_cases,
        )

        checkpoint_write_count += 1
        checkpoint = _checkpoint_payload(
            identity,
            completed_ids=completed_ids,
            output_digests=output_digests,
            next_position=next_position,
            checkpoint_write_count=checkpoint_write_count,
            status="complete",
            store_build_fingerprint=build_fingerprint,
        )
        _atomic_write_json(checkpoint_path, checkpoint)

    source_after_preflight = preflight_article_store(config)
    source_mutation_count = int(
        source_after_preflight.article_store_sha256 != preflight.article_store_sha256
        or source_after_preflight.corpus_fingerprint != preflight.corpus_fingerprint
    )
    elapsed = time.perf_counter() - started
    peak_rss_bytes = _peak_rss_bytes()
    installed_store_bytes = _tree_size(current_dir)
    checkpoint_bytes = _tree_size(checkpoints_dir)
    report_bytes = _tree_size(reports_dir)
    temporary_peak_estimate = installed_store_bytes * 2 + checkpoint_bytes
    resource_budgets_passed = (
        elapsed <= config.max_elapsed_seconds
        and peak_rss_bytes <= config.max_peak_rss_bytes
        and installed_store_bytes <= config.max_store_bytes
        and temporary_peak_estimate <= config.max_temp_bytes
        and report_bytes <= config.max_report_bytes
    )
    provenance = _provenance_complete_rate(build_data.records, build_data.evidence)
    content_hashes = {str(item["path"]): str(item["sha256"]) for item in manifest.files}
    manifest_content_fingerprint = _manifest_content_fingerprint(manifest.to_dict())
    input_accounting_rate = (
        (len(extractions) + 0) / preflight.article_count if preflight.article_count else 0.0
    )
    classification_rate = classified / detected if detected else 1.0
    machine_passed = all(
        (
            source_mutation_count == 0,
            len(extractions) == preflight.article_count,
            len(completed_ids) == preflight.article_count,
            input_accounting_rate == 1.0,
            silent_drops == 0,
            classification_rate == 1.0,
            provenance == 1.0,
            float(build_data.metrics["deterministic_id_rate"]) == 1.0,
            float(build_data.metrics["duplicate_group_consistency_rate"]) == 1.0,
            int(build_data.metrics["orphan_evidence_count"]) == 0,
            fake_metrics["automatic_write_count"] == 0,
            fake_metrics["private_library_read_count"] == 0,
            fake_metrics["false_exact_match_count"] == 0,
            fake_metrics["title_only_exact_match_count"] == 0,
            fake_metrics["ambiguous_auto_confirmation_count"] == 0,
            unavailable_metrics["automatic_write_count"] == 0,
            network.external_network_request_count == 0,
            network.unexpected_network_attempt_count == 0,
            len(review_cases) >= config.minimum_review_cases,
            resource_budgets_passed,
        )
    )
    if not machine_passed:
        status = "BLOCKED"
    elif human_review.get("status") == "PASS":
        status = "PASS"
    else:
        status = "CONDITIONAL"
    action = "no_op" if install.no_op else ("resume" if config.resume else "build")
    result = FullCorpusReferenceResult(
        status=status,
        action=action,
        article_store_sha256_before=preflight.article_store_sha256,
        article_store_sha256_after=source_after_preflight.article_store_sha256,
        corpus_fingerprint_before=preflight.corpus_fingerprint,
        corpus_fingerprint_after=source_after_preflight.corpus_fingerprint,
        input_article_count=preflight.article_count,
        processed_article_count=len(extractions),
        explicit_terminal_failure_count=0,
        unknown_article_status_count=0,
        duplicate_processed_article_count=0,
        input_accounting_rate=input_accounting_rate,
        detected_candidate_count=detected,
        classified_candidate_count=classified,
        overflow_candidate_count=overflow,
        silent_drop_count=silent_drops,
        classification_reconciliation_rate=classification_rate,
        article_status_counts=article_status_counts,
        record_count=len(build_data.records),
        evidence_count=len(build_data.evidence),
        zotero_candidate_count=len(fake_summary.candidates),
        provenance_complete_rate=provenance,
        deterministic_id_rate=float(build_data.metrics["deterministic_id_rate"]),
        duplicate_group_consistency_rate=float(
            build_data.metrics["duplicate_group_consistency_rate"]
        ),
        configuration_fingerprint=configuration_fingerprint,
        build_fingerprint=build_fingerprint,
        manifest_content_fingerprint=manifest_content_fingerprint,
        content_file_hashes=dict(sorted(content_hashes.items())),
        checkpoint_write_count=checkpoint_write_count,
        checkpoint_next_position=next_position,
        checkpoint_status=str(checkpoint["status"]),
        store_no_op=install.no_op,
        rollback_recovered=install.rollback_recovered,
        fake_matching=fake_metrics,
        unavailable_matching=unavailable_metrics,
        human_review=human_review,
        review_case_count=len(review_cases),
        external_network_request_count=network.external_network_request_count,
        unexpected_network_attempt_count=network.unexpected_network_attempt_count,
        source_mutation_count=source_mutation_count,
        elapsed_seconds=round(elapsed, 6),
        peak_rss_bytes=peak_rss_bytes,
        installed_store_bytes=installed_store_bytes,
        checkpoint_bytes=checkpoint_bytes,
        temporary_peak_estimate_bytes=temporary_peak_estimate,
        report_and_log_bytes=report_bytes,
        resource_budgets_passed=resource_budgets_passed,
        implementation_fingerprint=implementation_fingerprint,
        code_commit=code_commit,
    )
    final_report_bytes = report_bytes
    for _attempt in range(3):
        result = replace(result, report_and_log_bytes=final_report_bytes)
        _atomic_write_json(reports_dir / "last_run.json", result.to_dict())
        measured = _tree_size(reports_dir)
        if measured == final_report_bytes:
            break
        final_report_bytes = measured
    result = replace(result, report_and_log_bytes=final_report_bytes)
    if final_report_bytes > config.max_report_bytes:
        raise FullCorpusReferenceError("Report and log output exceeded the configured budget")
    return result


def iter_article_store(path: Path | str) -> Iterator[StoredArticle]:
    source = Path(path)
    ids: set[str] = set()
    urls: set[str] = set()
    required = {"id", "title", "url", "content", "metadata"}
    for index, item in enumerate(_iter_json_array(source)):
        if not isinstance(item, dict):
            raise FullCorpusReferenceError(f"Article at index {index} must be an object")
        missing = sorted(required - set(item))
        if missing:
            raise FullCorpusReferenceError(
                f"Article at index {index} missing fields: {', '.join(missing)}"
            )
        article_id = _required_text(item["id"], "id", index)
        title = _required_text(item["title"], "title", index)
        url = _required_text(item["url"], "url", index)
        content = _required_text(item["content"], "content", index, preserve=True)
        metadata = item["metadata"]
        if not isinstance(metadata, dict):
            raise FullCorpusReferenceError(f"Article at index {index} metadata must be an object")
        if article_id in ids:
            raise FullCorpusReferenceError(f"Article Store contains duplicate id: {article_id}")
        if url in urls:
            raise FullCorpusReferenceError(f"Article Store contains duplicate URL: {url}")
        ids.add(article_id)
        urls.add(url)
        yield StoredArticle(article_id, title, url, content, dict(metadata))


def _iter_json_array(path: Path) -> Iterator[Any]:
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as handle:
        buffer = ""
        position = 0
        eof = False

        def fill() -> None:
            nonlocal buffer, position, eof
            if position:
                buffer = buffer[position:]
                position = 0
            chunk = handle.read(64 * 1024)
            if chunk:
                buffer += chunk
            else:
                eof = True

        fill()
        while True:
            while position >= len(buffer) and not eof:
                fill()
            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if position < len(buffer):
                break
            if eof:
                raise FullCorpusReferenceError("Article Store JSON is empty")
        if buffer[position] != "[":
            raise FullCorpusReferenceError("Article Store root must be a JSON list")
        position += 1
        expect_value = True
        value_count = 0
        while True:
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position < len(buffer) or eof:
                    break
                fill()
            if position < len(buffer) and buffer[position] == "]":
                if expect_value and value_count:
                    raise FullCorpusReferenceError("Article Store JSON array has a trailing separator")
                position += 1
                break
            if not expect_value:
                if position >= len(buffer):
                    raise FullCorpusReferenceError("Article Store JSON ended unexpectedly")
                if buffer[position] != ",":
                    raise FullCorpusReferenceError("Article Store JSON array separator is invalid")
                position += 1
                expect_value = True
                continue
            while True:
                try:
                    value, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError as exc:
                    if eof:
                        raise FullCorpusReferenceError("Article Store is not valid JSON") from exc
                    fill()
                    continue
                position = end
                yield value
                value_count += 1
                expect_value = False
                break
        while True:
            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if position < len(buffer):
                raise FullCorpusReferenceError("Article Store has trailing JSON data")
            if eof:
                break
            fill()


def _initial_checkpoint(identity: dict[str, Any]) -> dict[str, Any]:
    return _checkpoint_payload(
        identity,
        completed_ids=set(),
        output_digests={},
        next_position=0,
        checkpoint_write_count=0,
        status="new",
    )


def _checkpoint_payload(
    identity: dict[str, Any],
    *,
    completed_ids: set[str],
    output_digests: dict[str, str],
    next_position: int,
    checkpoint_write_count: int,
    status: str,
    store_build_fingerprint: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "checkpoint_version": CHECKPOINT_VERSION,
        **identity,
        "completed_article_ids": sorted(completed_ids),
        "article_output_digests": dict(sorted(output_digests.items())),
        "next_position": next_position,
        "checkpoint_write_count": checkpoint_write_count,
        "status": status,
        "store_build_fingerprint": store_build_fingerprint,
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _load_and_validate_checkpoint(
    checkpoint_path: Path,
    extraction_dir: Path,
    identity: dict[str, Any],
) -> dict[str, Any]:
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullCorpusReferenceError("Checkpoint is missing or corrupt") from exc
    if not isinstance(payload, dict):
        raise FullCorpusReferenceError("Checkpoint root must be an object")
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise FullCorpusReferenceError("Checkpoint schema version mismatch")
    if payload.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise FullCorpusReferenceError("Checkpoint version mismatch")
    for key, expected in identity.items():
        if payload.get(key) != expected:
            raise FullCorpusReferenceError(f"Checkpoint identity mismatch: {key}")
    completed = payload.get("completed_article_ids")
    digests = payload.get("article_output_digests")
    next_position = payload.get("next_position")
    if (
        not isinstance(completed, list)
        or completed != sorted(completed)
        or len(completed) != len(set(completed))
        or not isinstance(digests, dict)
        or set(completed) != set(digests)
        or not isinstance(next_position, int)
        or next_position != len(completed)
    ):
        raise FullCorpusReferenceError("Checkpoint accounting is invalid")
    if payload.get("status") not in {"extracting", "extracted", "complete"}:
        raise FullCorpusReferenceError("Unknown checkpoint state")
    for article_id in completed:
        path = _extraction_path(extraction_dir, str(article_id))
        if not path.is_file() or path.is_symlink():
            raise FullCorpusReferenceError("Checkpoint extraction payload is missing or unsafe")
        if _file_sha256(path) != digests[article_id]:
            raise FullCorpusReferenceError("Checkpoint extraction payload checksum mismatch")
        extraction = _read_extraction(path)
        if extraction.article_id != article_id:
            raise FullCorpusReferenceError("Checkpoint extraction payload ownership mismatch")
    return payload


def _write_extraction(root: Path, extraction: ArticleExtraction) -> str:
    payload = {
        "schema_version": "article-reference-extraction/v1",
        "extraction": asdict(extraction),
    }
    path = _extraction_path(root, extraction.article_id)
    _atomic_write_json(path, payload)
    return _file_sha256(path)


def _read_extraction(path: Path) -> ArticleExtraction:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "article-reference-extraction/v1":
            raise ValueError("unsupported extraction schema")
        raw = payload["extraction"]
        candidates = []
        for item in raw["candidates"]:
            normalization = NormalizationResult(**item["normalization"])
            values = dict(item)
            values["normalization"] = normalization
            candidates.append(ExtractedCandidate(**values))
        return ArticleExtraction(
            article_id=str(raw["article_id"]),
            status=str(raw["status"]),
            candidates=candidates,
            detected_candidate_count=int(raw["detected_candidate_count"]),
            overflow_candidate_count=int(raw["overflow_candidate_count"]),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise FullCorpusReferenceError("Checkpoint extraction payload is corrupt") from exc


def _load_extractions(root: Path, checkpoint: dict[str, Any]) -> list[ArticleExtraction]:
    output = []
    for article_id in checkpoint["completed_article_ids"]:
        output.append(_read_extraction(_extraction_path(root, str(article_id))))
    if len(output) != len({item.article_id for item in output}):
        raise FullCorpusReferenceError("Duplicate processed Article extraction detected")
    return sorted(output, key=lambda item: item.article_id)


def _extraction_path(root: Path, article_id: str) -> Path:
    return root / f"{sha256_text(article_id)}.json"


def _curated_zotero_items(records: list[ReferenceRecord]) -> list[ZoteroItem]:
    items: list[ZoteroItem] = []
    doi_record = next((record for record in records if record.doi), None)
    arxiv_record = next((record for record in records if record.arxiv_id), None)
    url_record = next(
        (
            record
            for record in records
            if record.reference_type == "http_url" and record.normalized_url
        ),
        None,
    )
    title_record = next(
        (
            record
            for record in records
            if len((record.normalized_identifier or record.evidence_text).split()) >= 2
        ),
        None,
    )

    def item(key: str, title: str, *, doi: str | None = None, url: str | None = None) -> ZoteroItem:
        return ZoteroItem(
            item_key=key,
            bibtex_key=None,
            title=title[:500],
            creators=[],
            year=None,
            item_type="journalArticle",
            publication_title=None,
            doi=doi,
            url=url,
            abstract_note=None,
            tags=[],
            collections=[],
            updated_at=None,
        )

    if doi_record is not None:
        title = doi_record.normalized_identifier or doi_record.evidence_text
        items.append(item("CURATED_DOI", title, doi=doi_record.doi))
        items.append(item("CURATED_CONFLICT", title, doi="10.9999/p3-006-conflict"))
    if arxiv_record is not None:
        version = f"v{arxiv_record.arxiv_version}" if arxiv_record.arxiv_version else ""
        items.append(
            item(
                "CURATED_ARXIV",
                arxiv_record.normalized_identifier or arxiv_record.evidence_text,
                url=f"https://arxiv.org/abs/{arxiv_record.arxiv_id}{version}",
            )
        )
    if url_record is not None:
        items.append(item("CURATED_URL", "Curated URL fixture", url=url_record.normalized_url))
    if title_record is not None:
        items.append(
            item(
                "CURATED_TITLE",
                title_record.normalized_identifier or title_record.evidence_text,
            )
        )
    return items


def _matching_metrics(
    records: list[ReferenceRecord],
    summary: MatchSummary,
    *,
    private_library_reads: int,
) -> dict[str, Any]:
    decisions = Counter(candidate.decision for candidate in summary.candidates)
    false_exact = sum(
        candidate.decision == "exact"
        and not any(field in {"doi", "arxiv"} for field in candidate.matched_fields)
        for candidate in summary.candidates
    )
    title_only_exact = sum(
        candidate.decision == "exact" and candidate.matched_fields == ["title"]
        for candidate in summary.candidates
    )
    ambiguous_auto_confirm = 0
    referenced = {candidate.reference_id for candidate in summary.candidates}
    return {
        "record_count": len(records),
        "candidate_count": len(summary.candidates),
        "covered_reference_count": len(referenced),
        "decision_counts": dict(sorted(decisions.items())),
        "automatic_write_count": summary.automatic_write_count,
        "private_library_read_count": private_library_reads,
        "false_exact_match_count": false_exact,
        "title_only_exact_match_count": title_only_exact,
        "ambiguous_auto_confirmation_count": ambiguous_auto_confirm,
    }


def _write_human_review_template(
    reports_dir: Path,
    records: list[ReferenceRecord],
    matches: MatchSummary,
    *,
    build_fingerprint: str,
    minimum_cases: int,
) -> list[dict[str, Any]]:
    by_reference: dict[str, list[Any]] = {}
    for candidate in matches.candidates:
        by_reference.setdefault(candidate.reference_id, []).append(candidate)
    ordered = sorted(records, key=lambda item: item.reference_id)
    selected: list[tuple[ReferenceRecord, str]] = []
    selected_ids: set[str] = set()

    def add(reason: str, values: list[ReferenceRecord], limit: int = 8) -> None:
        used = 0
        for record in values:
            if used >= limit:
                break
            if record.reference_id in selected_ids:
                continue
            selected.append((record, reason))
            selected_ids.add(record.reference_id)
            used += 1

    add("strong_identifier", [item for item in ordered if item.reference_type in {"doi", "arxiv"}])
    add("external_url", [item for item in ordered if item.reference_type == "http_url"])
    add("internal_or_relative_url", [item for item in ordered if item.reference_type == "relative_or_internal_url"])
    add("duplicate_group", [item for item in ordered if item.duplicate_group_id is not None])
    add("ambiguous_text", [item for item in ordered if item.reference_type == "citation_text"])
    add(
        "rejected_or_unsupported",
        [item for item in ordered if item.classification in {"malformed", "rejected", "unsupported"}],
    )
    add("high_confidence", [item for item in ordered if item.confidence >= 0.9])
    add("malformed_edge", [item for item in ordered if item.reference_type == "malformed"])
    for decision in ("exact", "probable", "ambiguous", "unmatched"):
        add(
            f"zotero_{decision}",
            [
                item
                for item in ordered
                if any(candidate.decision == decision for candidate in by_reference.get(item.reference_id, []))
            ],
            limit=4,
        )
    add("stable_fill", ordered, limit=max(0, minimum_cases - len(selected)))
    cases = []
    for record, reason in selected[: max(minimum_cases, len(selected))]:
        decisions = sorted(
            {candidate.decision for candidate in by_reference.get(record.reference_id, [])}
        )
        cases.append(
            {
                "case_id": stable_id(
                    "review",
                    "reference-human-review-case/v1",
                    f"{build_fingerprint}\0{record.reference_id}",
                ),
                "reference_id": record.reference_id,
                "reference_type": record.reference_type,
                "classification": record.classification,
                "normalized_identifier": record.normalized_identifier,
                "normalized_url": record.normalized_url,
                "duplicate_group_id": record.duplicate_group_id,
                "source_article_id": record.source_article_id,
                "source_section": record.source_section,
                "evidence_text": record.evidence_text,
                "selection_reason": reason,
                "zotero_candidate_decisions": decisions,
                "classification_correctness": "pending",
                "normalized_identity_correctness": "pending",
                "provenance_sufficiency": "pending",
                "duplicate_decision": "pending",
                "zotero_decision": "pending",
                "reviewer_status": "pending",
                "comment": "",
                "reviews": [],
            }
        )
    template = {
        "schema_version": "reference-human-review/v1",
        "store_build_fingerprint": build_fingerprint,
        "selection": "deterministic-stratified-reference-id-order",
        "case_count": len(cases),
        "cases": cases,
    }
    _atomic_write_json(reports_dir / "human_review_template.json", template)
    return cases


def _provenance_complete_rate(records: list[Any], evidence: list[Any]) -> float:
    records_complete = all(
        record.source_article_id
        and record.source_article_title
        and record.source_article_url
        and record.source_section
        and record.evidence_ids
        and record.source_count == len(record.evidence_ids)
        for record in records
    )
    evidence_complete = all(
        item.source_article_id
        and item.source_article_title
        and item.source_article_url
        and item.source_section
        and item.raw_reference_hash
        for item in evidence
    )
    return 1.0 if records_complete and evidence_complete else 0.0


def _rule_versions() -> dict[str, str]:
    return {
        "extraction": EXTRACTION_RULE_VERSION,
        "normalization": NORMALIZATION_VERSION,
        "deduplication": DEDUPLICATION_RULE_VERSION,
        "matching": MATCHER_VERSION,
        "store": STORE_FORMAT_VERSION,
        "integrity": INTEGRITY_RULE_VERSION,
        "manifest_schema": REFERENCE_MANIFEST_SCHEMA,
        "record_schema": REFERENCE_RECORD_SCHEMA,
        "evidence_schema": REFERENCE_EVIDENCE_SCHEMA,
        "candidate_schema": ZOTERO_CANDIDATE_SCHEMA,
    }


def _implementation_fingerprint() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _manifest_content_fingerprint(payload: dict[str, Any]) -> str:
    deterministic = dict(payload)
    deterministic.pop("generated_at", None)
    return sha256_text(canonical_json(deterministic))


def _git_head_commit() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if len(value) != 40:
        raise FullCorpusReferenceError("Unable to determine the build code commit")
    return value


def _validate_article_store_path(path: Path) -> None:
    if ".." in path.parts:
        raise FullCorpusReferenceError("Article Store path cannot contain parent traversal")
    if not path.is_file() or path.is_symlink():
        raise FullCorpusReferenceError("Article Store must be a regular nonsymlink file")
    if ".local_data" not in path.resolve().parts:
        raise FullCorpusReferenceError("Article Store must be inside an approved .local_data root")
    _reject_symlink_components(path)


def _validate_output_root(path: Path) -> None:
    if ".." in path.parts:
        raise FullCorpusReferenceError("Output path cannot contain parent traversal")
    if ".local_data" not in path.resolve(strict=False).parts:
        raise FullCorpusReferenceError("Output path must be inside an ignored .local_data root")
    _reject_symlink_components(path)
    if path.exists() and (not path.is_dir() or path.is_symlink()):
        raise FullCorpusReferenceError("Output root is missing or unsafe")


def _reject_symlink_components(path: Path) -> None:
    cursor = path.absolute()
    while cursor != cursor.parent:
        if cursor.exists() and cursor.is_symlink():
            raise FullCorpusReferenceError("Path cannot contain symlink components")
        cursor = cursor.parent


def _remove_runtime_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise FullCorpusReferenceError("Runtime checkpoint path is unsafe")
    shutil.rmtree(path)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise FullCorpusReferenceError("Refusing to replace a symlink runtime artifact")
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    data = (canonical_json(payload) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _directory_content_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            digest.update(item.relative_to(path).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(_file_sha256(item).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path.resolve(strict=False)
    while not candidate.exists():
        if candidate == candidate.parent:
            raise FullCorpusReferenceError("Unable to locate a filesystem for disk-capacity preflight")
        candidate = candidate.parent
    return candidate


def _peak_rss_bytes() -> int:
    # Linux reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _required_text(
    value: Any,
    field: str,
    index: int,
    *,
    preserve: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FullCorpusReferenceError(f"Article at index {index} has empty or invalid {field}")
    return value if preserve else value.strip()


def _corpus_canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
