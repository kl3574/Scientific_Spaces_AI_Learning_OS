from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import math
import os
import queue
import re
import statistics
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

from app.storage.article_store import StoredArticle


DEFAULT_ARTICLE_STORE_PATH = Path(
    ".local_data/scientific_spaces/corpus/pilot/article_store/articles.json"
)
DEFAULT_OUTPUT_DIR = Path(".local_data/scientific_spaces/corpus/pdf_library")
DEFAULT_TEMPLATE_VERSION = "local-pdf-v5"
MIN_PDF_SIZE_BYTES = 1024
MIN_EXTRACTED_TEXT_LENGTH = 50
MAX_WORKERS = 4
MANIFEST_SCHEMA_VERSION = 2
MANIFEST_CHECKPOINT_INTERVAL = 10

REPRESENTATIVE_PILOT_ARTICLE_IDS = (
    "a96fb8c5192fc3ba",
    "f703785db4192f04",
    "54222327243755e4",
    "03dfe77de35ec4ec",
    "c10628495483e2c5",
    "314d4d677cdf8b6c",
    "e4539b3ee91ddf70",
    "1cdcdc963fbaf6bc",
    "8658cbea7ea7fa3d",
    "4368e79f44edce53",
    "9f65c292c4538f9e",
    "9adcdd2e80f9f4a6",
    "42ca3db9ef053ea5",
    "09260cccb8f0a9fe",
    "b6e4b373221c12f1",
    "c433711bdf659ac6",
    "e794b2ba77dad9f2",
    "b9cf3aa4d9aebf4d",
    "480d4ef5cc5be09e",
    "acaac952bd9e2de1",
)

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class CorpusValidationError(ValueError):
    pass


class ArticleRenderResult(Protocol):
    pdf_size_bytes: int
    page_count: int
    text_length: int
    formula_count: int
    formula_render_failure_count: int
    delimiter_balanced: bool
    image_reference_count: int
    local_image_embedded_count: int
    remote_image_placeholder_count: int
    broken_image_count: int
    external_network_request_count: int
    renderer_version: str
    template_version: str


class ArticleRenderer(Protocol):
    def __enter__(self) -> "ArticleRenderer": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None: ...

    def render(self, article: StoredArticle, output_path: Path) -> ArticleRenderResult: ...


WorkerFactory = Callable[[int, Path], ArticleRenderer]
ProgressCallback = Callable[[dict[str, Any]], None]


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _required_text(value: Any, *, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CorpusValidationError(f"Article at index {index} has empty or invalid {field}")
    return value if field == "content" else value.strip()


def load_pdf_export_articles(path: Path | str) -> list[StoredArticle]:
    source = Path(path)
    if not source.is_file():
        raise CorpusValidationError(f"Article store does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"Article store is not valid JSON: {source}") from exc
    if not isinstance(payload, list):
        raise CorpusValidationError("Article store root must be a JSON list")

    required = {"id", "title", "url", "content", "metadata"}
    articles: list[StoredArticle] = []
    article_ids: set[str] = set()
    urls: set[str] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise CorpusValidationError(f"Article at index {index} must be an object")
        missing = sorted(required - item.keys())
        if missing:
            raise CorpusValidationError(
                f"Article at index {index} missing fields: {', '.join(missing)}"
            )
        article_id = _required_text(item["id"], field="id", index=index)
        title = _required_text(item["title"], field="title", index=index)
        url = _required_text(item["url"], field="url", index=index)
        content = _required_text(item["content"], field="content", index=index)
        metadata = item["metadata"]
        if not isinstance(metadata, dict):
            raise CorpusValidationError(f"Article at index {index} metadata must be an object")
        if article_id in article_ids:
            raise CorpusValidationError(f"Article store contains duplicate id: {article_id}")
        if url in urls:
            raise CorpusValidationError(f"Article store contains duplicate URL: {url}")
        article_ids.add(article_id)
        urls.add(url)
        articles.append(
            StoredArticle(
                id=article_id,
                title=title,
                url=url,
                content=content,
                metadata=dict(metadata),
            )
        )
    return sorted(articles, key=lambda article: (article.url, article.id))


def compute_source_corpus_fingerprint(articles: list[StoredArticle]) -> str:
    digest = hashlib.sha256()
    for article in sorted(articles, key=lambda item: (item.url, item.id)):
        record = {
            "article_id": article.id,
            "url": article.url,
            "content_sha256": hashlib.sha256(article.content.encode("utf-8")).hexdigest(),
            "metadata": article.metadata,
        }
        digest.update(_canonical_json(record).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def source_content_hash(article: StoredArticle) -> str:
    payload = {
        "article_id": article.id,
        "title": article.title,
        "url": article.url,
        "content": article.content,
        "metadata": article.metadata,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _extract_archive_id(url: str) -> str:
    for part in urlsplit(url).path.rstrip("/").split("/"):
        if part.isdigit():
            return part.zfill(6)[-6:]
    return "000000"


def _sanitize_component(value: str) -> str:
    normalized = value.replace("..", "-").replace("/", "-").replace("\\", "-")
    normalized = re.sub(r"[<>:\"/\\|?*]", "-", normalized)
    normalized = re.sub(r"[\x00-\x1f\x7f]", "", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    cleaned = [
        character
        if character.isalnum() or character in {"-", "_", "."} or "\u4e00" <= character <= "\u9fff"
        else "-"
        for character in normalized
    ]
    return re.sub(r"-+", "-", "".join(cleaned)).strip(".-_ ")


def _truncate_utf8(value: str, *, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip(".-_ ")


def safe_pdf_filename(
    *,
    article_id: str,
    title: str,
    url: str,
    max_stem_length: int = 140,
) -> str:
    safe_id_source = article_id.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe_id = _truncate_utf8(_sanitize_component(safe_id_source) or "article", max_bytes=48)
    id_digest = hashlib.sha256(article_id.encode("utf-8")).hexdigest()[:16]
    archive_id = _extract_archive_id(url)
    safe_title = _sanitize_component(title)
    stem = f"{safe_id}-{archive_id}-{id_digest}"
    if safe_title:
        stem = f"{stem}-{safe_title}"
    stem = stem[:max_stem_length].strip(".-_ ")
    stem = _truncate_utf8(stem, max_bytes=220)
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return f"{stem or 'article'}.pdf"


def _validate_output_directory(path: Path) -> None:
    resolved = path.expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[3]
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return
    if ".local_data" not in resolved.parts:
        raise ValueError("output_dir must be under an ignored .local_data runtime directory")


@contextmanager
def _exclusive_output_lock(output_dir: Path | str) -> Iterable[None]:
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".export.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"PDF export already in progress for {root}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@dataclass(frozen=True)
class PdfExportConfig:
    article_store_path: Path = DEFAULT_ARTICLE_STORE_PATH
    markdown_dir: Path | None = None
    output_dir: Path = DEFAULT_OUTPUT_DIR
    mode: str = "offline"
    article_id: str | None = None
    limit: int | None = None
    resume: bool = True
    rebuild: bool = False
    workers: int = 2
    allow_source_access: bool = False
    delay_seconds: float = 0.0
    template_version: str = DEFAULT_TEMPLATE_VERSION
    renderer_version: str | None = None
    min_pdf_size_bytes: int = MIN_PDF_SIZE_BYTES
    minimum_text_length: int = MIN_EXTRACTED_TEXT_LENGTH

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_store_path", Path(self.article_store_path))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        if self.markdown_dir is not None:
            object.__setattr__(self, "markdown_dir", Path(self.markdown_dir))
        if self.mode not in {"offline", "source-probe"}:
            raise ValueError("mode must be offline or source-probe")
        if self.workers < 1 or self.workers > MAX_WORKERS:
            raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be positive")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        if self.min_pdf_size_bytes < 1:
            raise ValueError("min_pdf_size_bytes must be positive")
        if self.minimum_text_length < 1:
            raise ValueError("minimum_text_length must be positive")
        if not self.template_version.strip():
            raise ValueError("template_version must not be empty")
        if self.mode == "source-probe":
            if not self.allow_source_access:
                raise ValueError("source-probe requires explicit --allow-source-access")
            if self.workers != 1:
                raise ValueError("source-probe requires workers=1")
            if self.limit is None or self.limit > 10:
                raise ValueError("source-probe requires a limit between 1 and 10")
            if self.delay_seconds < 8:
                raise ValueError("source-probe requires delay_seconds>=8")
            if "source_probe" not in self.output_dir.name:
                raise ValueError("source-probe requires a separate source_probe output directory")
        _validate_output_directory(self.output_dir)

    @property
    def source_probe(self) -> bool:
        return self.mode == "source-probe"


@dataclass(frozen=True)
class PdfExportRecord:
    article_id: str
    archive_id: str
    title: str
    canonical_url: str
    source_content_hash: str
    output_relative_path: str
    pdf_size_bytes: int
    pdf_sha256: str
    page_count: int
    export_status: str
    validation_status: str
    formula_count: int
    image_reference_count: int
    local_image_embedded_count: int
    remote_image_placeholder_count: int
    exported_at: str
    renderer_version: str
    template_version: str
    error_category: str | None
    action: str
    text_length: int
    formula_render_failure_count: int
    delimiter_balanced: bool
    broken_image_count: int
    external_network_request_count: int
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PdfExportSummary:
    status: str
    corpus_fingerprint: str
    input_article_count: int
    selected_article_count: int
    exported_count: int
    unchanged_count: int
    regenerated_count: int
    failed_count: int
    validation_pass_count: int
    validation_fail_count: int
    total_pdf_size_bytes: int
    pdf_size_min: int
    pdf_size_mean: float
    pdf_size_median: float
    pdf_size_p95: int
    pdf_size_max: int
    total_page_count: int
    page_count_min: int
    page_count_mean: float
    page_count_median: float
    page_count_p95: int
    page_count_max: int
    formula_article_count: int
    formula_render_failure_count: int
    image_reference_count: int
    local_image_embedded_count: int
    remote_image_placeholder_count: int
    broken_image_count: int
    empty_pdf_count: int
    corrupt_pdf_count: int
    stale_pdf_count: int
    export_elapsed_seconds: float
    files_per_second: float
    worker_count: int
    external_network_request_count: int
    completed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def total_count(self) -> int:
        return self.selected_article_count

    @property
    def pass_count(self) -> int:
        return self.validation_pass_count

    @property
    def fail_count(self) -> int:
        return self.failed_count


@dataclass(frozen=True)
class PdfExportManifest:
    mode: str
    corpus_fingerprint: str
    records: list[PdfExportRecord]
    summary: PdfExportSummary | None = None
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "generated_at": self.generated_at or _utc_now(),
            "output_root": ".",
            "mode": self.mode,
            "corpus_fingerprint": self.corpus_fingerprint,
            "records": [record.to_dict() for record in self.records],
        }
        if self.summary is not None:
            payload["summary"] = self.summary.to_dict()
        return payload


def _write_json_atomic(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        temporary.write_text(_canonical_json(payload), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_csv_atomic(
    path: Path,
    *,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    try:
        temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append_failures_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    existing: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))
    _write_jsonl_atomic(path, [*existing, *rows])


def _validate_pdf_file(path: Path, *, min_size_bytes: int = MIN_PDF_SIZE_BYTES) -> bool:
    if not path.is_file() or path.stat().st_size < min_size_bytes:
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_relative_output(output_dir: Path, relative_path: str) -> Path | None:
    candidate = (output_dir / relative_path).resolve()
    try:
        candidate.relative_to(output_dir.resolve())
    except ValueError:
        return None
    return candidate


def should_resume(
    record: PdfExportRecord,
    article: StoredArticle,
    *,
    config: PdfExportConfig,
) -> bool:
    if config.rebuild or not config.resume:
        return False
    if record.export_status != "PASS" or record.validation_status != "PASS":
        return False
    if record.source_content_hash != source_content_hash(article):
        return False
    if record.template_version != config.template_version:
        return False
    if config.renderer_version is None or record.renderer_version != config.renderer_version:
        return False
    output_path = _resolve_relative_output(config.output_dir.resolve(), record.output_relative_path)
    if output_path is None or not output_path.is_file():
        return False
    if output_path.stat().st_size != record.pdf_size_bytes:
        return False
    if not _validate_pdf_file(output_path, min_size_bytes=config.min_pdf_size_bytes):
        return False
    return bool(record.pdf_sha256) and file_sha256(output_path) == record.pdf_sha256


def _record_from_dict(payload: dict[str, Any]) -> PdfExportRecord | None:
    names = {field.name for field in fields(PdfExportRecord)}
    if not names.issubset(payload):
        return None
    try:
        return PdfExportRecord(**{name: payload[name] for name in names})
    except (TypeError, ValueError):
        return None


def _read_manifest_records(path: Path) -> dict[str, PdfExportRecord]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(raw_records, list):
        return {}
    result: dict[str, PdfExportRecord] = {}
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        record = _record_from_dict(raw)
        if record is not None:
            result[record.article_id] = record
    return result


def select_pdf_export_articles(
    articles: list[StoredArticle],
    *,
    article_id: str | None = None,
    limit: int | None = None,
) -> list[StoredArticle]:
    if article_id is not None:
        selected = [article for article in articles if article.id == article_id]
        if not selected:
            raise CorpusValidationError(f"Article id not found: {article_id}")
        return selected
    if limit is None:
        return list(articles)
    if limit == len(REPRESENTATIVE_PILOT_ARTICLE_IDS):
        by_id = {article.id: article for article in articles}
        if all(article_id in by_id for article_id in REPRESENTATIVE_PILOT_ARTICLE_IDS):
            return [by_id[article_id] for article_id in REPRESENTATIVE_PILOT_ARTICLE_IDS]
    if limit >= len(articles):
        return list(articles)
    return list(articles[:limit])


def _validate_markdown_library(articles: list[StoredArticle], markdown_dir: Path) -> None:
    root = markdown_dir.resolve()
    library_root = root.parent if root.name == "articles" else root
    index_path = library_root / "index" / "articles_index.json"
    if not index_path.is_file():
        raise CorpusValidationError(f"Markdown library index does not exist: {index_path}")
    try:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusValidationError(f"Markdown library index is invalid: {index_path}") from exc
    if not isinstance(entries, list):
        raise CorpusValidationError("Markdown library index must be a JSON list")
    by_id = {
        str(entry.get("id")): str(entry.get("markdown_path"))
        for entry in entries
        if isinstance(entry, dict) and entry.get("id") and entry.get("markdown_path")
    }
    expected_ids = {article.id for article in articles}
    if set(by_id) != expected_ids:
        raise CorpusValidationError("Markdown library count or Article ids do not match Article store")
    for article_id, relative_path in by_id.items():
        candidate = (library_root / relative_path).resolve()
        if not candidate.is_relative_to(library_root) or not candidate.is_file():
            raise CorpusValidationError(f"Markdown file missing or outside library: {article_id}")


def detect_local_renderer_version() -> str:
    from app.export.local_pdf_renderer import sync_playwright

    if sync_playwright is None:
        raise RuntimeError("Playwright is required for offline PDF export")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            return f"chromium-{browser.version}"
        finally:
            browser.close()


def _default_worker_factory(config: PdfExportConfig) -> WorkerFactory:
    from app.export.local_pdf_worker import LocalPdfArticleRenderer

    allowed_roots: tuple[Path, ...] = ()
    content_root: Path | None = None
    if config.markdown_dir is not None:
        root = config.markdown_dir.resolve()
        allowed_roots = (root,)
        content_root = root

    def factory(worker_index: int, cache_dir: Path) -> ArticleRenderer:
        return LocalPdfArticleRenderer(
            cache_dir=cache_dir,
            allowed_image_roots=allowed_roots,
            content_root=content_root,
            minimum_pdf_size_bytes=config.min_pdf_size_bytes,
            minimum_text_length=config.minimum_text_length,
            template_version=config.template_version,
        )

    return factory


@dataclass(frozen=True)
class _RenderJob:
    article: StoredArticle
    output_path: Path
    output_relative_path: str
    previous: PdfExportRecord | None


@dataclass(frozen=True)
class _JobResult:
    job: _RenderJob
    result: ArticleRenderResult | None
    error: BaseException | None


def _render_jobs(
    jobs: list[_RenderJob],
    *,
    worker_count: int,
    cache_dir: Path,
    worker_factory: WorkerFactory,
) -> Iterable[_JobResult]:
    task_queue: queue.Queue[_RenderJob | None] = queue.Queue()
    result_queue: queue.Queue[_JobResult | tuple[str, BaseException]] = queue.Queue()
    for job in jobs:
        task_queue.put(job)
    for _ in range(worker_count):
        task_queue.put(None)

    def runner(worker_index: int) -> None:
        try:
            context = worker_factory(worker_index, cache_dir / f"worker-{worker_index}")
            with context as worker:
                while True:
                    job = task_queue.get()
                    if job is None:
                        return
                    try:
                        rendered = worker.render(job.article, job.output_path)
                    except BaseException as exc:
                        result_queue.put(_JobResult(job=job, result=None, error=exc))
                    else:
                        result_queue.put(_JobResult(job=job, result=rendered, error=None))
        except BaseException as exc:
            result_queue.put(("worker-init", exc))

    threads = [
        threading.Thread(
            target=runner,
            args=(index,),
            name=f"local-pdf-worker-{index}",
            daemon=False,
        )
        for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()

    received_ids: set[str] = set()
    worker_errors: list[BaseException] = []
    while len(received_ids) < len(jobs):
        try:
            item = result_queue.get(timeout=0.2)
        except queue.Empty:
            if not any(thread.is_alive() for thread in threads):
                break
            continue
        if isinstance(item, tuple):
            worker_errors.append(item[1])
            continue
        received_ids.add(item.job.article.id)
        yield item

    for thread in threads:
        thread.join()

    missing_jobs = [job for job in jobs if job.article.id not in received_ids]
    if missing_jobs:
        detail = "; ".join(str(error) for error in worker_errors) or "all workers stopped"
        for job in missing_jobs:
            yield _JobResult(
                job=job,
                result=None,
                error=RuntimeError(f"worker initialization failed: {detail}"),
            )


def _error_category(error: BaseException) -> str:
    message = str(error).lower()
    if "formula" in message or "delimiter" in message:
        return "formula"
    if "network" in message or "external request" in message:
        return "network"
    if "validation" in message or "pdfinfo" in message or "pdftotext" in message:
        return "validation"
    if "worker initialization" in message:
        return "worker_init"
    return "render"


def _failure_record(job: _RenderJob, error: BaseException, config: PdfExportConfig) -> PdfExportRecord:
    previous_size = job.output_path.stat().st_size if job.output_path.is_file() else 0
    return PdfExportRecord(
        article_id=job.article.id,
        archive_id=_extract_archive_id(job.article.url),
        title=job.article.title,
        canonical_url=job.article.url,
        source_content_hash=source_content_hash(job.article),
        output_relative_path=job.output_relative_path,
        pdf_size_bytes=previous_size,
        pdf_sha256=file_sha256(job.output_path) if job.output_path.is_file() else "",
        page_count=0,
        export_status="FAIL",
        validation_status="FAIL",
        formula_count=0,
        image_reference_count=0,
        local_image_embedded_count=0,
        remote_image_placeholder_count=0,
        exported_at=_utc_now(),
        renderer_version=config.renderer_version or "unknown",
        template_version=config.template_version,
        error_category=_error_category(error),
        action="FAILED",
        text_length=0,
        formula_render_failure_count=0,
        delimiter_balanced=False,
        broken_image_count=0,
        external_network_request_count=max(
            int(getattr(error, "blocked_request_count", 0) or 0),
            0,
        ),
        error_message=str(error),
    )


def _success_record(
    job: _RenderJob,
    result: ArticleRenderResult,
    config: PdfExportConfig,
) -> PdfExportRecord:
    if result.template_version != config.template_version:
        raise RuntimeError(
            f"template version mismatch: {result.template_version} != {config.template_version}"
        )
    if result.renderer_version != config.renderer_version:
        raise RuntimeError(
            f"renderer version mismatch: {result.renderer_version} != {config.renderer_version}"
        )
    if result.formula_render_failure_count:
        raise RuntimeError(
            f"formula render failures: {result.formula_render_failure_count}"
        )
    if not result.delimiter_balanced:
        raise RuntimeError("formula delimiter validation failed")
    if result.external_network_request_count:
        raise RuntimeError(
            f"external network requests: {result.external_network_request_count}"
        )
    if not _validate_pdf_file(job.output_path, min_size_bytes=config.min_pdf_size_bytes):
        raise RuntimeError("PDF validation failed after renderer completion")
    if result.pdf_size_bytes != job.output_path.stat().st_size:
        raise RuntimeError("PDF size differs from renderer validation result")
    return PdfExportRecord(
        article_id=job.article.id,
        archive_id=_extract_archive_id(job.article.url),
        title=job.article.title,
        canonical_url=job.article.url,
        source_content_hash=source_content_hash(job.article),
        output_relative_path=job.output_relative_path,
        pdf_size_bytes=result.pdf_size_bytes,
        pdf_sha256=file_sha256(job.output_path),
        page_count=result.page_count,
        export_status="PASS",
        validation_status="PASS",
        formula_count=result.formula_count,
        image_reference_count=result.image_reference_count,
        local_image_embedded_count=result.local_image_embedded_count,
        remote_image_placeholder_count=result.remote_image_placeholder_count,
        exported_at=_utc_now(),
        renderer_version=result.renderer_version,
        template_version=result.template_version,
        error_category=None,
        action="REGENERATED" if job.previous is not None else "CREATED",
        text_length=result.text_length,
        formula_render_failure_count=result.formula_render_failure_count,
        delimiter_balanced=result.delimiter_balanced,
        broken_image_count=result.broken_image_count,
        external_network_request_count=result.external_network_request_count,
        error_message=None,
    )


def _number_stats(values: list[int]) -> tuple[int, float, float, int, int]:
    if not values:
        return 0, 0.0, 0.0, 0, 0
    ordered = sorted(values)
    p95 = ordered[max(math.ceil(len(ordered) * 0.95) - 1, 0)]
    return (
        ordered[0],
        statistics.fmean(ordered),
        statistics.median(ordered),
        p95,
        ordered[-1],
    )


def _build_summary(
    *,
    all_articles: list[StoredArticle],
    selected: list[StoredArticle],
    records: dict[str, PdfExportRecord],
    corpus_fingerprint: str,
    exported_count: int,
    unchanged_count: int,
    regenerated_count: int,
    failed_count: int,
    stale_pdf_count: int,
    elapsed_seconds: float,
    worker_count: int,
) -> PdfExportSummary:
    selected_records = [records[article.id] for article in selected if article.id in records]
    pass_records = [
        record
        for record in selected_records
        if record.export_status == "PASS" and record.validation_status == "PASS"
    ]
    validation_fail_count = len(selected) - len(pass_records)
    sizes = [record.pdf_size_bytes for record in pass_records]
    pages = [record.page_count for record in pass_records]
    size_min, size_mean, size_median, size_p95, size_max = _number_stats(sizes)
    page_min, page_mean, page_median, page_p95, page_max = _number_stats(pages)
    formula_failures = sum(record.formula_render_failure_count for record in selected_records)
    external_requests = sum(record.external_network_request_count for record in selected_records)
    empty_count = len(
        [
            record
            for record in pass_records
            if record.pdf_size_bytes <= 0 or record.page_count < 1 or record.text_length <= 0
        ]
    )
    corrupt_count = len(
        [
            record
            for record in selected_records
            if record.validation_status == "FAIL" and record.error_category == "validation"
        ]
    )
    status = (
        "PASS"
        if failed_count == 0
        and validation_fail_count == 0
        and formula_failures == 0
        and external_requests == 0
        and empty_count == 0
        and corrupt_count == 0
        else "BLOCKED"
    )
    rendered_count = exported_count + regenerated_count
    return PdfExportSummary(
        status=status,
        corpus_fingerprint=corpus_fingerprint,
        input_article_count=len(all_articles),
        selected_article_count=len(selected),
        exported_count=exported_count,
        unchanged_count=unchanged_count,
        regenerated_count=regenerated_count,
        failed_count=failed_count,
        validation_pass_count=len(pass_records),
        validation_fail_count=validation_fail_count,
        total_pdf_size_bytes=sum(sizes),
        pdf_size_min=size_min,
        pdf_size_mean=size_mean,
        pdf_size_median=size_median,
        pdf_size_p95=size_p95,
        pdf_size_max=size_max,
        total_page_count=sum(pages),
        page_count_min=page_min,
        page_count_mean=page_mean,
        page_count_median=page_median,
        page_count_p95=page_p95,
        page_count_max=page_max,
        formula_article_count=len([record for record in pass_records if record.formula_count > 0]),
        formula_render_failure_count=formula_failures,
        image_reference_count=sum(record.image_reference_count for record in selected_records),
        local_image_embedded_count=sum(
            record.local_image_embedded_count for record in selected_records
        ),
        remote_image_placeholder_count=sum(
            record.remote_image_placeholder_count for record in selected_records
        ),
        broken_image_count=sum(record.broken_image_count for record in selected_records),
        empty_pdf_count=empty_count,
        corrupt_pdf_count=corrupt_count,
        stale_pdf_count=stale_pdf_count,
        export_elapsed_seconds=round(elapsed_seconds, 6),
        files_per_second=round(rendered_count / elapsed_seconds, 6)
        if rendered_count and elapsed_seconds
        else 0.0,
        worker_count=worker_count,
        external_network_request_count=external_requests,
        completed_at=_utc_now(),
    )


def _persist_manifest(
    *,
    output_dir: Path,
    mode: str,
    corpus_fingerprint: str,
    records: dict[str, PdfExportRecord],
    summary: PdfExportSummary | None,
) -> None:
    ordered = sorted(records.values(), key=lambda record: (record.canonical_url, record.article_id))
    manifest = PdfExportManifest(
        mode=mode,
        corpus_fingerprint=corpus_fingerprint,
        records=ordered,
        summary=summary,
    )
    manifest_dir = output_dir / "manifest"
    _write_json_atomic(manifest_dir / "pdf_manifest.json", manifest.to_dict())
    fieldnames = [field.name for field in fields(PdfExportRecord)]
    _write_csv_atomic(
        manifest_dir / "pdf_manifest.csv",
        fieldnames=fieldnames,
        rows=[record.to_dict() for record in ordered],
    )


def _persist_reports(
    output_dir: Path,
    summary: PdfExportSummary,
    records: dict[str, PdfExportRecord],
) -> None:
    reports_dir = output_dir / "reports"
    _write_json_atomic(reports_dir / "export_summary.json", summary.to_dict())
    if (
        summary.exported_count + summary.regenerated_count > 0
        and summary.selected_article_count == summary.input_article_count
    ):
        _write_json_atomic(
            reports_dir / "last_regeneration_summary.json",
            summary.to_dict(),
        )
    _write_json_atomic(
        reports_dir / "validation_summary.json",
        {
            "status": summary.status,
            "validation_pass_count": summary.validation_pass_count,
            "validation_fail_count": summary.validation_fail_count,
            "formula_render_failure_count": summary.formula_render_failure_count,
            "empty_pdf_count": summary.empty_pdf_count,
            "corrupt_pdf_count": summary.corrupt_pdf_count,
            "external_network_request_count": summary.external_network_request_count,
            "completed_at": summary.completed_at,
        },
    )
    failures = [
        record.to_dict()
        for record in records.values()
        if record.export_status == "FAIL" or record.validation_status == "FAIL"
    ]
    _write_jsonl_atomic(reports_dir / "failures.jsonl", failures)


def _cleanup_unreferenced_pdfs(
    output_dir: Path,
    records: dict[str, PdfExportRecord],
) -> None:
    articles_dir = (output_dir / "articles").resolve()
    if not articles_dir.is_dir():
        return
    referenced: set[Path] = set()
    for record in records.values():
        candidate = _resolve_relative_output(output_dir, record.output_relative_path)
        if candidate is not None and candidate.is_relative_to(articles_dir):
            referenced.add(candidate)
    for candidate in articles_dir.rglob("*.pdf"):
        if candidate.resolve() not in referenced:
            candidate.unlink()


def export_local_pdf_library(
    *,
    config: PdfExportConfig | None = None,
    worker_factory: WorkerFactory | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PdfExportSummary:
    resolved_config = config or PdfExportConfig()
    if resolved_config.mode != "offline":
        raise NotImplementedError(
            "source-probe is bounded and optional; offline export is the P2-005 batch workflow"
        )

    output_dir = resolved_config.output_dir.expanduser().resolve()
    _validate_output_directory(output_dir)
    with _exclusive_output_lock(output_dir):
        return _export_local_pdf_library_locked(
            config=resolved_config,
            worker_factory=worker_factory,
            progress_callback=progress_callback,
        )


def _export_local_pdf_library_locked(
    *,
    config: PdfExportConfig,
    worker_factory: WorkerFactory | None,
    progress_callback: ProgressCallback | None,
) -> PdfExportSummary:
    resolved_config = config

    started = time.perf_counter()
    all_articles = load_pdf_export_articles(resolved_config.article_store_path)
    if resolved_config.markdown_dir is not None:
        _validate_markdown_library(all_articles, resolved_config.markdown_dir)
    corpus_fingerprint = compute_source_corpus_fingerprint(all_articles)
    selected = select_pdf_export_articles(
        all_articles,
        article_id=resolved_config.article_id,
        limit=resolved_config.limit,
    )

    renderer_version = resolved_config.renderer_version or detect_local_renderer_version()
    resolved_config = replace(resolved_config, renderer_version=renderer_version)
    output_dir = resolved_config.output_dir.expanduser().resolve()
    _validate_output_directory(output_dir)
    articles_dir = output_dir / "articles"
    cache_dir = output_dir / "cache"
    articles_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest" / "pdf_manifest.json"
    existing = _read_manifest_records(manifest_path)
    valid_article_ids = {article.id for article in all_articles}
    records = {
        article_id: record
        for article_id, record in existing.items()
        if article_id in valid_article_ids
    }

    jobs: list[_RenderJob] = []
    output_path_owners: dict[str, str] = {}
    for record in records.values():
        normalized_relative_path = record.output_relative_path.casefold()
        owner = output_path_owners.get(normalized_relative_path)
        if owner is not None and owner != record.article_id:
            raise CorpusValidationError(
                "duplicate PDF output path in existing manifest for Article ids "
                f"{owner} and {record.article_id}: {record.output_relative_path}"
            )
        output_path_owners[normalized_relative_path] = record.article_id
    unchanged_count = 0
    stale_pdf_count = 0
    for article in selected:
        relative_path = (
            Path("articles")
            / safe_pdf_filename(article_id=article.id, title=article.title, url=article.url)
        )
        normalized_relative_path = relative_path.as_posix().casefold()
        owner = output_path_owners.get(normalized_relative_path)
        if owner is not None and owner != article.id:
            raise CorpusValidationError(
                f"duplicate PDF output path for Article ids {owner} and {article.id}: {relative_path}"
            )
        output_path_owners[normalized_relative_path] = article.id
        output_path = output_dir / relative_path
        previous = records.get(article.id)
        if previous is not None and should_resume(previous, article, config=resolved_config):
            records[article.id] = replace(previous, action="UNCHANGED")
            unchanged_count += 1
            continue
        if previous is not None:
            stale_pdf_count += 1
        jobs.append(
            _RenderJob(
                article=article,
                output_path=output_path,
                output_relative_path=relative_path.as_posix(),
                previous=previous,
            )
        )

    exported_count = 0
    regenerated_count = 0
    failed_count = 0
    completed = unchanged_count
    factory = worker_factory or _default_worker_factory(resolved_config)
    active_worker_count = min(resolved_config.workers, len(jobs)) if jobs else 0
    for job_result in _render_jobs(
        jobs,
        worker_count=active_worker_count,
        cache_dir=cache_dir,
        worker_factory=factory,
    ) if jobs else ():
        job = job_result.job
        if job_result.error is not None:
            record = _failure_record(job, job_result.error, resolved_config)
            failed_count += 1
        else:
            assert job_result.result is not None
            try:
                record = _success_record(job, job_result.result, resolved_config)
            except BaseException as exc:
                record = _failure_record(job, exc, resolved_config)
                failed_count += 1
            else:
                if job.previous is None:
                    exported_count += 1
                else:
                    regenerated_count += 1
        records[job.article.id] = record
        completed += 1
        if completed % MANIFEST_CHECKPOINT_INTERVAL == 0 or completed == len(selected):
            _persist_manifest(
                output_dir=output_dir,
                mode=resolved_config.mode,
                corpus_fingerprint=corpus_fingerprint,
                records=records,
                summary=None,
            )
        if progress_callback is not None:
            progress_callback(
                {
                    "completed": completed,
                    "selected": len(selected),
                    "article_id": job.article.id,
                    "status": record.export_status,
                    "exported": exported_count,
                    "regenerated": regenerated_count,
                    "unchanged": unchanged_count,
                    "failed": failed_count,
                }
            )

    elapsed = time.perf_counter() - started
    summary = _build_summary(
        all_articles=all_articles,
        selected=selected,
        records=records,
        corpus_fingerprint=corpus_fingerprint,
        exported_count=exported_count,
        unchanged_count=unchanged_count,
        regenerated_count=regenerated_count,
        failed_count=failed_count,
        stale_pdf_count=stale_pdf_count,
        elapsed_seconds=elapsed,
        worker_count=resolved_config.workers,
    )
    if summary.status == "PASS" and len(selected) == len(all_articles):
        _cleanup_unreferenced_pdfs(output_dir, records)
    _persist_manifest(
        output_dir=output_dir,
        mode=resolved_config.mode,
        corpus_fingerprint=corpus_fingerprint,
        records=records,
        summary=summary,
    )
    _persist_reports(output_dir, summary, records)
    return summary
