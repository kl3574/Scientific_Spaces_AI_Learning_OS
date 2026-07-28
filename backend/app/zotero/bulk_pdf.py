from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.export.browser_print import (
    BrowserPrintConfig,
    BrowserPrintError,
    BrowserPrintPool,
    BrowserPrintResult,
    SessionFactory,
    SystemResourceSnapshot,
    duration_summary,
    system_resource_snapshot,
)
from app.export.printed_pdf import (
    PrintedPdfInspection,
    PrintedPdfValidationError,
    formula_expected,
    inspect_printed_article_pdf,
)
from app.storage.article_store import StoredArticle
from app.zotero.sync import (
    ARTICLE_ID_PREFIX,
    DEFAULT_COLLECTION_NAME,
    ZoteroArticleSync,
    ZoteroSyncError,
    ZoteroSyncResult,
    ZoteroSyncTransport,
    canonicalize_article_url,
    inspect_pdf_bytes,
    render_article_item,
)

MAX_PROBE_URLS = 25


@dataclass(frozen=True)
class ProbeTier:
    workers: int
    navigation_interval_seconds: float
    article_count: int = 4

    def to_dict(self) -> dict[str, int | float]:
        return {
            "workers": self.workers,
            "navigation_interval_seconds": self.navigation_interval_seconds,
            "article_count": self.article_count,
        }


DEFAULT_PROBE_TIERS = (
    ProbeTier(1, 8.0),
    ProbeTier(2, 8.0),
    ProbeTier(3, 8.0),
    ProbeTier(4, 8.0),
    ProbeTier(4, 6.0),
    ProbeTier(4, 4.0),
)


@dataclass(frozen=True)
class ProbeTierEvidence:
    tier: ProbeTier
    status: str
    stable: bool
    result_count: int
    success_count: int
    navigation_attempt_count: int
    retry_count: int
    latency_degraded: bool
    memory_degraded: bool
    before: SystemResourceSnapshot
    after: SystemResourceSnapshot
    durations: dict[str, float | None]
    results: tuple[BrowserPrintResult, ...]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.to_dict(),
            "status": self.status,
            "stable": self.stable,
            "result_count": self.result_count,
            "success_count": self.success_count,
            "navigation_attempt_count": self.navigation_attempt_count,
            "retry_count": self.retry_count,
            "latency_degraded": self.latency_degraded,
            "memory_degraded": self.memory_degraded,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "durations": self.durations,
            "results": [result.to_dict() for result in self.results],
            "error": self.error,
        }


@dataclass(frozen=True)
class ThroughputProbeOutcome:
    status: str
    selected_tier: ProbeTier | None
    tested_url_count: int
    tiers: tuple[ProbeTierEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_tier": (
                self.selected_tier.to_dict() if self.selected_tier else None
            ),
            "tested_url_count": self.tested_url_count,
            "tiers": [tier.to_dict() for tier in self.tiers],
        }


@dataclass(frozen=True)
class PendingReadback:
    article: StoredArticle
    path: Path
    inspection: PrintedPdfInspection


@dataclass
class BulkSyncSummary:
    status: str
    total_article_count: int
    preexisting_count: int = 0
    pending_count: int = 0
    resumed_pdf_count: int = 0
    rendered_count: int = 0
    created_count: int = 0
    failed_count: int = 0
    deferred_count: int = 0
    network_navigation_count: int = 0
    zotero_write_count: int = 0
    final_parent_count: int = 0
    final_pdf_count: int = 0
    final_html_count: int = 0
    duplicate_count: int = 0
    failure_classes: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_article_count": self.total_article_count,
            "preexisting_count": self.preexisting_count,
            "pending_count": self.pending_count,
            "resumed_pdf_count": self.resumed_pdf_count,
            "rendered_count": self.rendered_count,
            "created_count": self.created_count,
            "failed_count": self.failed_count,
            "deferred_count": self.deferred_count,
            "network_navigation_count": self.network_navigation_count,
            "zotero_write_count": self.zotero_write_count,
            "final_parent_count": self.final_parent_count,
            "final_pdf_count": self.final_pdf_count,
            "final_html_count": self.final_html_count,
            "duplicate_count": self.duplicate_count,
            "failure_classes": dict(sorted(self.failure_classes.items())),
            "errors": self.errors,
        }


class CheckpointJournal:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._latest: dict[str, dict[str, Any]] = {}
        self._load()

    def get(self, article_id: str) -> dict[str, Any] | None:
        return self._latest.get(article_id)

    def record(
        self,
        article: StoredArticle,
        status: str,
        **evidence: Any,
    ) -> None:
        payload = {
            "record_type": "article",
            "recorded_at": _utc_now(),
            "article_id": article.id,
            "url": article.url,
            "status": status,
            **evidence,
        }
        self._append(payload)
        self._latest[article.id] = payload

    def record_run(self, event: str, **evidence: Any) -> None:
        self._append(
            {
                "record_type": "run",
                "recorded_at": _utc_now(),
                "event": event,
                **evidence,
            }
        )

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ZoteroSyncError("Unable to read the bulk sync checkpoint") from exc
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ZoteroSyncError(
                    f"Checkpoint JSON is invalid at line {line_number}"
                ) from exc
            if (
                isinstance(payload, dict)
                and payload.get("record_type") == "article"
                and isinstance(payload.get("article_id"), str)
            ):
                self._latest[payload["article_id"]] = payload

    def _append(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(encoded + "\n")
                file.flush()
                os.fsync(file.fileno())
        except OSError as exc:
            raise ZoteroSyncError("Unable to persist the bulk sync checkpoint") from exc


class ExclusiveRunLock:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file: Any = None

    def __enter__(self) -> ExclusiveRunLock:
        self._file = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._file.close()
            raise ZoteroSyncError(
                "Another full-corpus Zotero PDF sync is already running"
            ) from exc
        self._file.seek(0)
        self._file.truncate()
        self._file.write(f"{os.getpid()}\n")
        self._file.flush()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        if self._file is None:
            return
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()


class ZoteroParentIndex:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self._by_article_id: dict[str, list[dict[str, Any]]] = {}
        self._by_url: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            data = _item_data(item)
            if data.get("itemType") != "webpage":
                continue
            for article_id in _article_ids(data):
                self._by_article_id.setdefault(article_id, []).append(item)
            raw_url = str(data.get("url") or "")
            try:
                url = canonicalize_article_url(raw_url)
            except ZoteroSyncError:
                continue
            self._by_url.setdefault(url, []).append(item)

    def candidates(self, article: StoredArticle) -> list[dict[str, Any]]:
        url = canonicalize_article_url(article.url)
        candidates = [
            *self._by_article_id.get(article.id, []),
            *self._by_url.get(url, []),
        ]
        unique: dict[str, dict[str, Any]] = {}
        for item in candidates:
            key = _item_key(item) or f"object:{id(item)}"
            unique[key] = item
        return list(unique.values())


class BulkZoteroPdfSync:
    def __init__(
        self,
        transport: ZoteroSyncTransport,
        *,
        browser_config: BrowserPrintConfig,
        checkpoint: CheckpointJournal,
        staging_dir: Path | str,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        readback_batch_size: int = 8,
        readback_attempts: int = 30,
        readback_delay_seconds: float = 0.5,
        session_factory: SessionFactory | None = None,
    ) -> None:
        browser_config.validate()
        if readback_batch_size < 1 or readback_batch_size > 25:
            raise ValueError("readback batch size must be between 1 and 25")
        self.transport = transport
        self.browser_config = browser_config
        self.checkpoint = checkpoint
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.readback_batch_size = readback_batch_size
        self.readback_attempts = readback_attempts
        self.readback_delay_seconds = readback_delay_seconds
        self.session_factory = session_factory
        self.sync = ZoteroArticleSync(
            transport,
            collection_name=collection_name,
        )

    def run(
        self,
        articles: list[StoredArticle],
        *,
        write: bool,
    ) -> BulkSyncSummary:
        _validate_article_inventory(articles)
        summary = BulkSyncSummary(
            status="DRY_RUN" if not write else "IN_PROGRESS",
            total_article_count=len(articles),
        )
        collection_key = self.sync.resolve_collection_key()
        items = self.transport.list_collection_items(collection_key)
        index = ZoteroParentIndex(items)
        pending: list[StoredArticle] = []
        blockers: list[tuple[StoredArticle, str]] = []

        self.checkpoint.record_run(
            "preflight_started",
            total_article_count=len(articles),
            collection_name=self.collection_name,
            browser_config={
                "workers": self.browser_config.workers,
                "navigation_interval_seconds": (
                    self.browser_config.navigation_interval_seconds
                ),
            },
        )

        for article in articles:
            result = self.sync.inspect_snapshot(
                article,
                collection_key=collection_key,
                items=index.candidates(article),
                require_pdf=True,
            )
            if result.pdf_status == "existing":
                if result.html_attachment_count:
                    blockers.append(
                        (article, "existing parent retains an HTML attachment")
                    )
                    continue
                summary.preexisting_count += 1
                self.checkpoint.record(
                    article,
                    "existing",
                    zotero=result.to_dict(),
                )
                _unlink_if_exists(self._staging_path(article))
                continue
            if result.status == "migration_required":
                blockers.append(
                    (article, "existing parent requires PDF migration")
                )
                continue
            pending.append(article)

        summary.pending_count = len(pending)
        if blockers:
            for article, reason in blockers:
                self._record_failure(summary, article, "zotero_state", reason)
            summary.status = "BLOCKED"
            return summary
        if not write:
            return summary
        if not pending:
            return self._finalize_audit(articles, collection_key, summary)

        self.transport.select_collection(collection_key, self.collection_name)
        readback_batch: list[PendingReadback] = []
        render_required: list[StoredArticle] = []
        render_required_by_id: dict[str, StoredArticle] = {}
        processed_ids: set[str] = set()

        for article in pending:
            resumed = self._load_resumable_pdf(article)
            if resumed is None:
                render_required.append(article)
                render_required_by_id[article.id] = article
                continue
            summary.resumed_pdf_count += 1
            processed_ids.add(article.id)
            try:
                self._submit_pdf(article, resumed, summary)
                readback_batch.append(resumed)
                if len(readback_batch) >= self.readback_batch_size:
                    self._reconcile_batch(
                        readback_batch,
                        collection_key,
                        summary,
                    )
                    readback_batch.clear()
            except ZoteroSyncError as exc:
                self._record_failure(
                    summary,
                    article,
                    "zotero_write",
                    str(exc),
                )
                break

        if not summary.failed_count:
            pool = BrowserPrintPool(
                self.browser_config,
                session_factory=self.session_factory,
            )
            rendered = pool.iter_render(render_required, self.staging_dir)
            browser_error: str | None = None
            try:
                for result in rendered:
                    processed_ids.add(result.article_id)
                    summary.network_navigation_count += result.attempts
                    article = render_required_by_id.get(result.article_id)
                    if article is None:
                        raise ZoteroSyncError(
                            "Browser result has an unknown Article ID"
                        )
                    if result.status != "success" or result.inspection is None:
                        self._record_failure(
                            summary,
                            article,
                            result.failure_class or "browser",
                            result.error or result.status,
                        )
                        continue
                    summary.rendered_count += 1
                    self.checkpoint.record(
                        article,
                        "rendered",
                        browser=result.to_dict(),
                        staging_path=result.output_path.name,
                    )
                    pending_pdf = PendingReadback(
                        article=article,
                        path=result.output_path,
                        inspection=result.inspection,
                    )
                    try:
                        self._submit_pdf(article, pending_pdf, summary)
                    except ZoteroSyncError as exc:
                        self._record_failure(
                            summary,
                            article,
                            "zotero_write",
                            str(exc),
                        )
                        break
                    readback_batch.append(pending_pdf)
                    if len(readback_batch) >= self.readback_batch_size:
                        self._reconcile_batch(
                            readback_batch,
                            collection_key,
                            summary,
                        )
                        readback_batch.clear()
            except BrowserPrintError as exc:
                browser_error = str(exc)
            finally:
                try:
                    rendered.close()
                except BrowserPrintError as exc:
                    browser_error = browser_error or str(exc)
            if browser_error:
                first_unprocessed = next(
                    (
                        article
                        for article in render_required
                        if article.id not in processed_ids
                    ),
                    None,
                )
                if first_unprocessed is not None:
                    processed_ids.add(first_unprocessed.id)
                    self._record_failure(
                        summary,
                        first_unprocessed,
                        "browser_provider",
                        browser_error,
                    )

        if readback_batch:
            try:
                self._reconcile_batch(
                    readback_batch,
                    collection_key,
                    summary,
                )
                readback_batch.clear()
            except ZoteroSyncError as exc:
                for pending_pdf in readback_batch:
                    self._record_failure(
                        summary,
                        pending_pdf.article,
                        "zotero_readback",
                        str(exc),
                    )

        unprocessed = [
            article
            for article in pending
            if article.id not in processed_ids
        ]
        summary.deferred_count = len(unprocessed)
        for article in unprocessed:
            self.checkpoint.record(
                article,
                "deferred",
                reason="run stopped before browser navigation",
            )

        if summary.failed_count or summary.deferred_count:
            summary.status = "BLOCKED"
            self.checkpoint.record_run(
                "run_blocked",
                summary=summary.to_dict(),
            )
            return summary
        return self._finalize_audit(articles, collection_key, summary)

    def _load_resumable_pdf(
        self,
        article: StoredArticle,
    ) -> PendingReadback | None:
        checkpoint = self.checkpoint.get(article.id)
        if checkpoint is None or checkpoint.get("status") not in {
            "rendered",
            "write_submitted",
        }:
            return None
        path = self._staging_path(article)
        if not path.exists():
            return None
        browser = checkpoint.get("browser")
        mathjax_rendered = bool(
            isinstance(browser, dict) and browser.get("mathjax_available")
        )
        try:
            inspection = inspect_printed_article_pdf(
                article,
                path,
                mathjax_rendered=mathjax_rendered,
            )
        except PrintedPdfValidationError:
            _unlink_if_exists(path)
            return None
        return PendingReadback(
            article=article,
            path=path,
            inspection=inspection,
        )

    def _submit_pdf(
        self,
        article: StoredArticle,
        pending_pdf: PendingReadback,
        summary: BulkSyncSummary,
    ) -> None:
        try:
            payload = pending_pdf.path.read_bytes()
        except OSError as exc:
            raise ZoteroSyncError("Staged PDF is unavailable") from exc
        inspection = inspect_pdf_bytes(payload)
        if inspection.sha256 != pending_pdf.inspection.sha256:
            raise ZoteroSyncError("Staged PDF changed after validation")
        self.transport.save_item_with_pdf(
            render_article_item(article),
            payload,
        )
        summary.zotero_write_count += 1
        self.checkpoint.record(
            article,
            "write_submitted",
            pdf_sha256=inspection.sha256,
            file_size_bytes=inspection.file_size_bytes,
            browser={
                "mathjax_available": pending_pdf.inspection.mathjax_rendered,
            },
            staging_path=pending_pdf.path.name,
        )

    def _reconcile_batch(
        self,
        pending: list[PendingReadback],
        collection_key: str,
        summary: BulkSyncSummary,
    ) -> None:
        last_pending = [item.article.id for item in pending]
        verified: dict[str, ZoteroSyncResult] = {}
        for attempt in range(self.readback_attempts):
            items = self.transport.list_collection_items(collection_key)
            index = ZoteroParentIndex(items)
            verified.clear()
            last_pending = []
            for pending_pdf in pending:
                result = self.sync.inspect_snapshot(
                    pending_pdf.article,
                    collection_key=collection_key,
                    items=index.candidates(pending_pdf.article),
                    require_pdf=True,
                )
                if (
                    result.pdf_status != "existing"
                    or result.html_attachment_count != 0
                ):
                    last_pending.append(pending_pdf.article.id)
                    continue
                if result.pdf_sha256 != pending_pdf.inspection.sha256:
                    raise ZoteroSyncError(
                        "Zotero PDF readback hash differs from the staged PDF"
                    )
                verified[pending_pdf.article.id] = result
            if not last_pending:
                break
            if attempt + 1 < self.readback_attempts:
                time.sleep(self.readback_delay_seconds)
        if last_pending:
            raise ZoteroSyncError(
                "Zotero batch readback did not complete for "
                f"{len(last_pending)} Article(s)"
            )

        for pending_pdf in pending:
            result = verified[pending_pdf.article.id]
            summary.created_count += 1
            self.checkpoint.record(
                pending_pdf.article,
                "created",
                zotero=result.to_dict(),
                pdf_validation=pending_pdf.inspection.to_dict(),
            )
            _unlink_if_exists(pending_pdf.path)

    def _finalize_audit(
        self,
        articles: list[StoredArticle],
        collection_key: str,
        summary: BulkSyncSummary,
    ) -> BulkSyncSummary:
        items = self.transport.list_collection_items(collection_key)
        index = ZoteroParentIndex(items)
        for article in articles:
            try:
                result = self.sync.inspect_snapshot(
                    article,
                    collection_key=collection_key,
                    items=index.candidates(article),
                    require_pdf=True,
                )
            except ZoteroSyncError as exc:
                summary.duplicate_count += 1
                self._record_failure(
                    summary,
                    article,
                    "zotero_audit",
                    str(exc),
                )
                continue
            if result.pdf_status != "existing":
                self._record_failure(
                    summary,
                    article,
                    "zotero_audit",
                    "required PDF attachment is missing",
                )
                continue
            summary.final_parent_count += 1
            summary.final_pdf_count += 1
            summary.final_html_count += result.html_attachment_count
            if result.html_attachment_count:
                self._record_failure(
                    summary,
                    article,
                    "zotero_audit",
                    "HTML attachment remains after PDF synchronization",
                )
                continue
            self.checkpoint.record(
                article,
                "audited",
                zotero=result.to_dict(),
            )

        if (
            summary.failed_count
            or summary.duplicate_count
            or summary.final_html_count
            or summary.final_parent_count != len(articles)
            or summary.final_pdf_count != len(articles)
        ):
            summary.status = "BLOCKED"
            self.checkpoint.record_run(
                "audit_blocked",
                summary=summary.to_dict(),
            )
            return summary

        summary.status = "PASS"
        self.checkpoint.record_run(
            "run_completed",
            summary=summary.to_dict(),
        )
        return summary

    def _staging_path(self, article: StoredArticle) -> Path:
        return self.staging_dir / f"{article.id}.pdf"

    def _record_failure(
        self,
        summary: BulkSyncSummary,
        article: StoredArticle,
        failure_class: str,
        error: str,
    ) -> None:
        summary.failed_count += 1
        summary.failure_classes[failure_class] = (
            summary.failure_classes.get(failure_class, 0) + 1
        )
        summary.errors.append(
            {
                "article_id": article.id,
                "url": article.url,
                "failure_class": failure_class,
                "error": error,
            }
        )
        self.checkpoint.record(
            article,
            "failed",
            failure_class=failure_class,
            error=error,
        )


def run_throughput_probe(
    articles: list[StoredArticle],
    output_dir: Path | str,
    *,
    tiers: tuple[ProbeTier, ...] = DEFAULT_PROBE_TIERS,
    session_factory: SessionFactory | None = None,
    settle_ms: int = 10_000,
) -> ThroughputProbeOutcome:
    requested = sum(tier.article_count for tier in tiers)
    if requested > MAX_PROBE_URLS:
        raise ValueError(f"probe may use at most {MAX_PROBE_URLS} URLs")
    if len(articles) < requested:
        raise ValueError(
            f"probe requires {requested} distinct known Articles"
        )

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    evidence: list[ProbeTierEvidence] = []
    selected: ProbeTier | None = None
    baseline_median: float | None = None
    cursor = 0

    for tier in tiers:
        tier_articles = articles[cursor : cursor + tier.article_count]
        cursor += tier.article_count
        tier_dir = directory / (
            f"w{tier.workers}-i{tier.navigation_interval_seconds:g}"
        )
        before = system_resource_snapshot()
        results: list[BrowserPrintResult] = []
        error: str | None = None
        try:
            pool = BrowserPrintPool(
                BrowserPrintConfig(
                    workers=tier.workers,
                    navigation_interval_seconds=(
                        tier.navigation_interval_seconds
                    ),
                    retries=2,
                    settle_ms=settle_ms,
                    stop_failure_classes=frozenset(
                        {
                            "http_403",
                            "http_429",
                            "http_status",
                            "timeout",
                            "content_quality",
                            "pdf_quality",
                            "browser",
                        }
                    ),
                ),
                session_factory=session_factory,
            )
            results = list(pool.iter_render(tier_articles, tier_dir))
        except Exception as exc:  # noqa: BLE001 - persist bounded probe evidence.
            error = f"{type(exc).__name__}: {exc}"
        finally:
            shutil.rmtree(tier_dir, ignore_errors=True)
        after = system_resource_snapshot()
        success_count = sum(result.status == "success" for result in results)
        navigation_attempts = sum(result.attempts for result in results)
        retry_count = sum(max(0, result.attempts - 1) for result in results)
        durations = duration_summary(results)
        median = durations["median_seconds"]
        latency_degraded = bool(
            baseline_median is not None
            and isinstance(median, float)
            and median > max(60.0, baseline_median * 2.5)
        )
        memory_degraded = _memory_degraded(before, after)
        stable = bool(
            error is None
            and len(results) == tier.article_count
            and success_count == tier.article_count
            and retry_count == 0
            and not latency_degraded
            and not memory_degraded
        )
        tier_evidence = ProbeTierEvidence(
            tier=tier,
            status="PASS" if stable else "FAIL",
            stable=stable,
            result_count=len(results),
            success_count=success_count,
            navigation_attempt_count=navigation_attempts,
            retry_count=retry_count,
            latency_degraded=latency_degraded,
            memory_degraded=memory_degraded,
            before=before,
            after=after,
            durations=durations,
            results=tuple(results),
            error=error,
        )
        evidence.append(tier_evidence)
        if not stable:
            break
        selected = tier
        if baseline_median is None and isinstance(median, float):
            baseline_median = median

    try:
        directory.rmdir()
    except OSError:
        pass
    return ThroughputProbeOutcome(
        status="PASS" if selected is not None else "BLOCKED",
        selected_tier=selected,
        tested_url_count=sum(
            sum(result.attempts > 0 for result in item.results)
            for item in evidence
        ),
        tiers=tuple(evidence),
    )


def select_probe_articles(
    articles: list[StoredArticle],
    *,
    count: int = 24,
) -> list[StoredArticle]:
    if count < 1 or count > MAX_PROBE_URLS:
        raise ValueError(f"probe count must be between 1 and {MAX_PROBE_URLS}")
    formula_articles = [
        article
        for article in articles
        if len(article.content) >= 300 and formula_expected(article.content)
    ]
    eligible = formula_articles or [
        article for article in articles if len(article.content) >= 300
    ]
    if len(eligible) < count:
        raise ValueError("Article Store has too few valid probe candidates")
    ordered = sorted(eligible, key=lambda article: (len(article.content), article.url))
    if count == 1:
        return [ordered[len(ordered) // 2]]
    indexes = [
        round(index * (len(ordered) - 1) / (count - 1))
        for index in range(count)
    ]
    selected = [ordered[index] for index in indexes]
    if len({article.id for article in selected}) != count:
        raise ValueError("Unable to select distinct probe Articles")
    return selected


def write_json_atomic(path: Path | str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    try:
        temporary.write_text(encoded + "\n", encoding="utf-8")
        os.replace(temporary, target)
    except OSError as exc:
        _unlink_if_exists(temporary)
        raise ZoteroSyncError("Unable to persist runtime evidence") from exc


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _memory_degraded(
    before: SystemResourceSnapshot,
    after: SystemResourceSnapshot,
) -> bool:
    if (
        before.available_memory_bytes is None
        or after.available_memory_bytes is None
    ):
        return False
    drop = before.available_memory_bytes - after.available_memory_bytes
    return drop > max(4 * 1024**3, before.available_memory_bytes // 4)


def _validate_article_inventory(articles: list[StoredArticle]) -> None:
    if not articles:
        raise ZoteroSyncError("Article inventory is empty")
    ids = [article.id for article in articles]
    urls = [canonicalize_article_url(article.url) for article in articles]
    if len(set(ids)) != len(ids):
        raise ZoteroSyncError("Article inventory contains duplicate IDs")
    if len(set(urls)) != len(urls):
        raise ZoteroSyncError("Article inventory contains duplicate URLs")
    for article in articles:
        if not article.title.strip() or len(article.content) < 32:
            raise ZoteroSyncError(
                f"Article inventory contains invalid content: {article.id}"
            )


def _article_ids(data: dict[str, Any]) -> set[str]:
    extra = str(data.get("extra") or "")
    return {
        line[len(ARTICLE_ID_PREFIX) :].strip()
        for line in extra.splitlines()
        if line.startswith(ARTICLE_ID_PREFIX)
        and line[len(ARTICLE_ID_PREFIX) :].strip()
    }


def _item_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _item_key(payload: dict[str, Any]) -> str:
    data = _item_data(payload)
    return str(payload.get("key") or data.get("key") or "")


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise ZoteroSyncError(f"Unable to remove runtime artifact: {path.name}") from exc


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
