from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.export import local_pdf
from app.export.local_pdf_renderer import OfflinePdfRendererError
from app.storage.article_store import StoredArticle


def _article(
    article_id: str,
    archive_id: int,
    *,
    content: str = "正文 " * 100,
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": f"测试文章 {article_id}",
        "url": f"https://spaces.ac.cn/archives/{archive_id}",
        "content": content,
        "metadata": {
            "date": "2026-07-01",
            "category": "数学",
            "references": ["reference"],
            "images": ["https://example.invalid/image.png"],
        },
    }


def _write_store(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


@dataclass(frozen=True)
class _FakeRenderResult:
    pdf_size_bytes: int
    page_count: int = 2
    text_length: int = 500
    formula_count: int = 1
    formula_render_failure_count: int = 0
    delimiter_balanced: bool = True
    image_reference_count: int = 1
    local_image_embedded_count: int = 0
    remote_image_placeholder_count: int = 1
    broken_image_count: int = 0
    external_network_request_count: int = 0
    renderer_version: str = "chromium-test-1"
    template_version: str = "local-pdf-test-1"


class _FakeWorker:
    def __init__(
        self,
        owner: "_FakeWorkerFactory",
        worker_index: int,
        *,
        fail_ids: set[str],
    ) -> None:
        self.owner = owner
        self.worker_index = worker_index
        self.fail_ids = fail_ids

    def __enter__(self) -> "_FakeWorker":
        with self.owner.lock:
            self.owner.entered_workers.add(self.worker_index)
        return self

    def __exit__(self, *_: object) -> None:
        with self.owner.lock:
            self.owner.closed_workers.add(self.worker_index)

    def render(self, article: object, output_path: Path) -> _FakeRenderResult:
        article_id = str(getattr(article, "id"))
        with self.owner.lock:
            self.owner.active += 1
            self.owner.max_active = max(self.owner.max_active, self.owner.active)
            self.owner.rendered_ids.append(article_id)
        try:
            time.sleep(0.01)
            if article_id in self.fail_ids:
                raise RuntimeError(f"render failed for {article_id}")
            data = b"%PDF-1.7\n" + (article_id.encode("utf-8") * 1024) + b"\n%%EOF"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = output_path.with_suffix(".tmp")
            temporary.write_bytes(data)
            temporary.replace(output_path)
            return _FakeRenderResult(
                pdf_size_bytes=len(data),
                renderer_version=self.owner.renderer_version,
                template_version=self.owner.template_version,
            )
        finally:
            with self.owner.lock:
                self.owner.active -= 1


class _FakeWorkerFactory:
    def __init__(
        self,
        *,
        fail_ids: set[str] | None = None,
        renderer_version: str = "chromium-test-1",
        template_version: str = "local-pdf-test-1",
    ) -> None:
        self.fail_ids = fail_ids or set()
        self.renderer_version = renderer_version
        self.template_version = template_version
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.rendered_ids: list[str] = []
        self.entered_workers: set[int] = set()
        self.closed_workers: set[int] = set()

    def __call__(self, worker_index: int, cache_dir: Path) -> _FakeWorker:
        assert cache_dir.name == f"worker-{worker_index}"
        return _FakeWorker(self, worker_index, fail_ids=self.fail_ids)


def _config(store: Path, output: Path, **overrides: object) -> local_pdf.PdfExportConfig:
    values: dict[str, object] = {
        "article_store_path": store,
        "output_dir": output,
        "workers": 2,
        "resume": True,
        "template_version": "local-pdf-test-1",
        "renderer_version": "chromium-test-1",
    }
    values.update(overrides)
    return local_pdf.PdfExportConfig(**values)


def test_parallel_export_writes_relative_manifest_and_atomic_reports(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article(f"a{index}", 6500 + index) for index in range(4)])
    factory = _FakeWorkerFactory()

    summary = local_pdf.export_local_pdf_library(
        config=_config(store, output),
        worker_factory=factory,
    )

    assert summary.status == "PASS"
    assert summary.input_article_count == 4
    assert summary.selected_article_count == 4
    assert summary.exported_count == 4
    assert summary.unchanged_count == 0
    assert summary.failed_count == 0
    assert summary.validation_pass_count == 4
    assert summary.external_network_request_count == 0
    assert factory.max_active == 2
    assert factory.entered_workers == factory.closed_workers

    manifest_path = output / "manifest" / "pdf_manifest.json"
    csv_path = output / "manifest" / "pdf_manifest.csv"
    export_summary = output / "reports" / "export_summary.json"
    validation_summary = output / "reports" / "validation_summary.json"
    failures = output / "reports" / "failures.jsonl"
    assert all(path.is_file() for path in (manifest_path, csv_path, export_summary, validation_summary, failures))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["records"]) == 4
    assert manifest["output_root"] == "."
    for record in manifest["records"]:
        assert record["canonical_url"].startswith("https://spaces.ac.cn/archives/")
        assert record["output_relative_path"].startswith("articles/")
        assert not Path(record["output_relative_path"]).is_absolute()
        assert record["export_status"] == "PASS"
        assert record["validation_status"] == "PASS"
        assert len(record["pdf_sha256"]) == 64
        assert record["formula_count"] == 1
        assert record["remote_image_placeholder_count"] == 1
        assert record["external_network_request_count"] == 0
    assert not list(output.rglob("*.tmp"))


def test_export_rejects_duplicate_resolved_output_paths_before_workers_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article("a1", 6508), _article("a2", 6509)])
    monkeypatch.setattr(local_pdf, "safe_pdf_filename", lambda **_: "collision.pdf")
    factory = _FakeWorkerFactory()

    with pytest.raises(local_pdf.CorpusValidationError, match="duplicate PDF output path"):
        local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=factory)

    assert factory.rendered_ids == []


def test_limited_export_rejects_collision_with_unselected_manifest_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article("a1", 6508), _article("a2", 6509)])
    local_pdf.export_local_pdf_library(
        config=_config(store, output),
        worker_factory=_FakeWorkerFactory(),
    )
    manifest = json.loads(
        (output / "manifest" / "pdf_manifest.json").read_text(encoding="utf-8")
    )
    a2_path = next(
        record["output_relative_path"]
        for record in manifest["records"]
        if record["article_id"] == "a2"
    )
    monkeypatch.setattr(local_pdf, "safe_pdf_filename", lambda **_: Path(a2_path).name)

    with pytest.raises(local_pdf.CorpusValidationError, match="duplicate PDF output path"):
        local_pdf.export_local_pdf_library(
            config=_config(store, output, article_id="a1", rebuild=True),
            worker_factory=_FakeWorkerFactory(),
        )


def test_resume_is_idempotent_and_does_not_start_workers(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article("a1", 6508), _article("a2", 6509)])
    first_factory = _FakeWorkerFactory()
    local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=first_factory)

    second_factory = _FakeWorkerFactory()
    summary = local_pdf.export_local_pdf_library(
        config=_config(store, output),
        worker_factory=second_factory,
    )

    assert summary.exported_count == 0
    assert summary.regenerated_count == 0
    assert summary.unchanged_count == 2
    assert summary.failed_count == 0
    assert second_factory.rendered_ids == []
    assert second_factory.entered_workers == set()

    retained = json.loads(
        (output / "reports" / "last_regeneration_summary.json").read_text(encoding="utf-8")
    )
    assert retained["exported_count"] == 2
    assert retained["unchanged_count"] == 0


def test_content_or_template_change_regenerates_only_stale_articles(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    records = [_article("a1", 6508), _article("a2", 6509)]
    _write_store(store, records)
    local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=_FakeWorkerFactory())

    records[0]["content"] = "更新后的正文 " * 100
    _write_store(store, records)
    content_factory = _FakeWorkerFactory()
    content_summary = local_pdf.export_local_pdf_library(
        config=_config(store, output),
        worker_factory=content_factory,
    )
    assert content_summary.regenerated_count == 1
    assert content_summary.unchanged_count == 1
    assert content_factory.rendered_ids == ["a1"]
    assert content_summary.stale_pdf_count == 1

    template_factory = _FakeWorkerFactory(template_version="local-pdf-test-2")
    template_summary = local_pdf.export_local_pdf_library(
        config=_config(store, output, template_version="local-pdf-test-2"),
        worker_factory=template_factory,
    )
    assert template_summary.regenerated_count == 2
    assert template_summary.unchanged_count == 0
    assert sorted(template_factory.rendered_ids) == ["a1", "a2"]


def test_failed_regeneration_preserves_previous_pdf_and_records_failure(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article("a1", 6508)])
    local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=_FakeWorkerFactory())
    manifest = json.loads((output / "manifest" / "pdf_manifest.json").read_text(encoding="utf-8"))
    pdf_path = output / manifest["records"][0]["output_relative_path"]
    original = pdf_path.read_bytes()

    failing = _FakeWorkerFactory(fail_ids={"a1"})
    summary = local_pdf.export_local_pdf_library(
        config=_config(store, output, rebuild=True),
        worker_factory=failing,
    )

    assert summary.failed_count == 1
    assert summary.validation_fail_count == 1
    assert pdf_path.read_bytes() == original
    record = json.loads((output / "manifest" / "pdf_manifest.json").read_text(encoding="utf-8"))["records"][0]
    assert record["export_status"] == "FAIL"
    assert record["error_category"] == "render"
    assert "render failed" in record["error_message"]


def test_limited_run_preserves_unselected_manifest_records(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    _write_store(store, [_article(f"a{index}", 6500 + index) for index in range(3)])
    local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=_FakeWorkerFactory())
    retained_before = json.loads(
        (output / "reports" / "last_regeneration_summary.json").read_text(encoding="utf-8")
    )

    summary = local_pdf.export_local_pdf_library(
        config=_config(store, output, limit=1, rebuild=True),
        worker_factory=_FakeWorkerFactory(),
    )

    manifest = json.loads((output / "manifest" / "pdf_manifest.json").read_text(encoding="utf-8"))
    assert summary.selected_article_count == 1
    assert len(manifest["records"]) == 3
    assert len(list((output / "articles").glob("*.pdf"))) == 3
    retained_after = json.loads(
        (output / "reports" / "last_regeneration_summary.json").read_text(encoding="utf-8")
    )
    assert retained_after == retained_before


def test_successful_export_removes_unreferenced_and_renamed_pdf_files(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "pdf-library"
    records = [_article("a1", 6508), _article("a2", 6509)]
    _write_store(store, records)
    local_pdf.export_local_pdf_library(config=_config(store, output), worker_factory=_FakeWorkerFactory())
    first_manifest = json.loads(
        (output / "manifest" / "pdf_manifest.json").read_text(encoding="utf-8")
    )
    old_paths = {
        record["article_id"]: output / record["output_relative_path"]
        for record in first_manifest["records"]
    }

    records[0]["title"] = "renamed article"
    _write_store(store, [records[0]])
    summary = local_pdf.export_local_pdf_library(
        config=_config(store, output),
        worker_factory=_FakeWorkerFactory(),
    )

    assert summary.status == "PASS"
    assert not old_paths["a1"].exists()
    assert not old_paths["a2"].exists()
    assert len(list((output / "articles").glob("*.pdf"))) == 1


def test_failure_record_preserves_blocked_network_attempt_count(tmp_path: Path) -> None:
    article = StoredArticle(
        id="a1",
        title="Article",
        url="https://spaces.ac.cn/archives/6508",
        content="body",
        metadata={},
    )
    job = local_pdf._RenderJob(
        article=article,
        output_path=tmp_path / "article.pdf",
        output_relative_path="articles/article.pdf",
        previous=None,
    )
    error = OfflinePdfRendererError("blocked requests", blocked_request_count=2)

    record = local_pdf._failure_record(job, error, _config(tmp_path / "store.json", tmp_path))

    assert record.external_network_request_count == 2
