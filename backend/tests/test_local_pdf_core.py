from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest
from dataclasses import replace

from app.export import local_pdf
from app.storage.article_store import StoredArticle


def _store_path(tmp_path: Path) -> Path:
    return tmp_path / "articles.json"


def _write_store(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _record(
    article_id: str,
    url: str,
    *,
    title: str = "测试文章",
    content: str = "正文正文。",
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": title,
        "url": url,
        "content": content,
        "metadata": metadata or {"date": "2026-07-01", "category": "数学"},
    }


def test_loader_enforces_schema_and_duplicate_constraints(tmp_path: Path) -> None:
    path = _store_path(tmp_path)
    _write_store(
        path,
        [
            {
                "id": "a1",
                "title": "title",
                "url": "https://spaces.ac.cn/archives/1",
                "content": "正文",
            },
        ],
    )
    with pytest.raises(Exception, match="metadata"):
        local_pdf.load_pdf_export_articles(path)

    _write_store(
        path,
        [
            _record("a1", "https://spaces.ac.cn/archives/1"),
            _record("a2", "https://spaces.ac.cn/archives/1"),
        ],
    )
    with pytest.raises(Exception, match="duplicate URL"):
        local_pdf.load_pdf_export_articles(path)


def test_loader_returns_empty_for_empty_store(tmp_path: Path) -> None:
    path = _store_path(tmp_path)
    _write_store(path, [])

    articles = local_pdf.load_pdf_export_articles(path)

    assert articles == []


def test_source_content_hash_is_deterministic_and_sensitive_to_source_content() -> None:
    article = StoredArticle(
        id="a1",
        title="测试",
        url="https://spaces.ac.cn/archives/100008",
        content="段落A。",
        metadata={"category": "数学"},
    )
    variant = StoredArticle(
        id="a1",
        title="测试",
        url="https://spaces.ac.cn/archives/100008",
        content="段落A。更新",
        metadata={"category": "数学"},
    )

    first = local_pdf.source_content_hash(article)
    second = local_pdf.source_content_hash(article)
    changed = local_pdf.source_content_hash(variant)

    assert first == second
    assert first != changed


def test_safe_pdf_filename_preserves_article_id_and_archive_id_and_chinese(tmp_path: Path) -> None:
    filename = local_pdf.safe_pdf_filename(
        article_id="art-1001",
        title="科学空间：测试文章 标题",
        url="https://spaces.ac.cn/archives/6508?ref=home",
    )
    assert filename.startswith("art-1001-006508-")
    assert filename.endswith(".pdf")
    assert "科学空间" in filename
    assert ".." not in filename
    assert ".local_data" not in filename


def test_safe_pdf_filename_rejects_path_traversal_characters_and_reserved_chars() -> None:
    filename = local_pdf.safe_pdf_filename(
        article_id="../../etc/passwd",
        title='a/b\\c:*?"<>|d',
        url="https://spaces.ac.cn/archives/42",
    )
    assert ".." not in filename
    assert "/" not in filename
    assert "\\" not in filename
    assert ":" not in filename
    assert "*" not in filename
    assert "?" not in filename
    assert "<" not in filename and ">" not in filename
    assert "|" not in filename
    assert filename.startswith("passwd-000042-") or filename.startswith("passwd-000042")


def test_safe_pdf_filename_uses_full_id_identity_after_component_sanitization() -> None:
    first = local_pdf.safe_pdf_filename(
        article_id="team/shared",
        title="same title",
        url="https://spaces.ac.cn/archives/6508",
    )
    second = local_pdf.safe_pdf_filename(
        article_id="other/shared",
        title="same title",
        url="https://spaces.ac.cn/archives/6508",
    )

    assert first != second


def test_safe_pdf_filename_limits_utf8_byte_length_for_long_chinese_title() -> None:
    filename = local_pdf.safe_pdf_filename(
        article_id="article-1",
        title="科学空间" * 100,
        url="https://spaces.ac.cn/archives/6508",
    )

    assert filename.endswith(".pdf")
    assert len(filename.encode("utf-8")) <= 224


def test_config_rejects_non_ignored_repo_runtime_path(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="output_dir must be under an ignored"):
        local_pdf.PdfExportConfig(
            article_store_path=_store_path(tmp_path),
            output_dir=repo_root / "not_ignored" / "pdf_library",
        )


def test_mode_b_requires_explicit_opt_in_and_boundaries(tmp_path: Path) -> None:
    article_store = _store_path(tmp_path)
    _write_store(article_store, [])
    source_output = tmp_path / "source_probe_pdf_library"
    with pytest.raises(ValueError, match="source-probe requires explicit"):
        local_pdf.PdfExportConfig(
            article_store_path=article_store,
            output_dir=source_output,
            mode="source-probe",
        )
    with pytest.raises(ValueError, match="source-probe"):
        local_pdf.PdfExportConfig(
            article_store_path=article_store,
            output_dir=source_output,
            mode="source-probe",
            allow_source_access=True,
            workers=2,
            limit=5,
            delay_seconds=8,
        )
    with pytest.raises(ValueError, match="source-probe"):
        local_pdf.PdfExportConfig(
            article_store_path=article_store,
            output_dir=source_output,
            mode="source-probe",
            allow_source_access=True,
            limit=12,
            workers=1,
            delay_seconds=8,
        )
    with pytest.raises(ValueError, match="source-probe"):
        local_pdf.PdfExportConfig(
            article_store_path=article_store,
            output_dir=source_output,
            mode="source-probe",
            allow_source_access=True,
            limit=5,
            workers=1,
            delay_seconds=5,
        )

    config = local_pdf.PdfExportConfig(
        article_store_path=article_store,
        output_dir=source_output,
        mode="source-probe",
        allow_source_access=True,
        limit=10,
        workers=1,
        delay_seconds=8,
    )
    assert config.source_probe is True
    assert config.limit == 10
    assert config.workers == 1
    assert config.delay_seconds >= 8


def test_workers_must_be_between_one_and_four(tmp_path: Path) -> None:
    article_store = _store_path(tmp_path)
    _write_store(article_store, [])
    with pytest.raises(ValueError, match="workers must be between 1 and 4"):
        local_pdf.PdfExportConfig(article_store_path=article_store, workers=0)
    with pytest.raises(ValueError, match="workers must be between 1 and 4"):
        local_pdf.PdfExportConfig(article_store_path=article_store, workers=5)
    assert local_pdf.PdfExportConfig(article_store_path=article_store).workers == 2


def test_representative_twenty_selection_is_deterministic() -> None:
    articles = [
        StoredArticle(
            id=article_id,
            title=article_id,
            url=f"https://spaces.ac.cn/archives/{index + 1}",
            content="body",
            metadata={},
        )
        for index, article_id in enumerate(reversed(local_pdf.REPRESENTATIVE_PILOT_ARTICLE_IDS))
    ]

    selected = local_pdf.select_pdf_export_articles(articles, limit=20)

    assert [article.id for article in selected] == list(local_pdf.REPRESENTATIVE_PILOT_ARTICLE_IDS)


def test_default_runtime_pdf_outputs_are_git_ignored() -> None:
    candidates = (
        ".local_data/scientific_spaces/corpus/pdf_library/articles/example.pdf",
        ".local_data/scientific_spaces/corpus/pdf_library/manifest/pdf_manifest.json",
        ".local_data/scientific_spaces/corpus/pdf_library/cache/rendered.article.html",
    )
    result = subprocess.run(
        ["git", "check-ignore", *candidates],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert set(result.stdout.splitlines()) == set(candidates)


def test_atomic_json_csv_writes_and_failures_append_without_loss(tmp_path: Path) -> None:
    target_json = tmp_path / "manifest.json"
    local_pdf._write_json_atomic(target_json, {"a": 1})

    target_csv = tmp_path / "manifest.csv"
    local_pdf._write_csv_atomic(
        target_csv,
        fieldnames=("article_id", "status"),
        rows=[{"article_id": "a1", "status": "PASS"}],
    )

    target_failures = tmp_path / "failures.jsonl"
    target_failures.write_text('{"first": true}\n', encoding="utf-8")
    local_pdf._append_failures_jsonl(target_failures, [{"article_id": "a1", "status": "FAIL", "reason": "x"}])

    assert json.loads(target_json.read_text(encoding="utf-8")) == {"a": 1}
    assert target_csv.is_file()
    with target_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"article_id": "a1", "status": "PASS"}]
    lines = [line for line in target_failures.read_text(encoding="utf-8").splitlines() if line]
    assert [json.loads(line) for line in lines] == [
        {"first": True},
        {"article_id": "a1", "status": "FAIL", "reason": "x"},
    ]
    assert not any(path.name.startswith(".manifest.json.tmp-") for path in tmp_path.iterdir())
    assert not any(path.name.startswith(".manifest.csv.tmp-") for path in tmp_path.iterdir())
    assert not any(path.name.startswith(".failures.jsonl.tmp-") for path in tmp_path.iterdir())


def test_output_directory_lock_rejects_overlapping_export_processes(tmp_path: Path) -> None:
    output = tmp_path / "pdf-library"

    with local_pdf._exclusive_output_lock(output):
        with pytest.raises(RuntimeError, match="already in progress"):
            with local_pdf._exclusive_output_lock(output):
                pass


def test_resume_requires_pass_status_hash_template_renderer_and_valid_pdf_header(tmp_path: Path) -> None:
    article = StoredArticle(
        id="a1",
        title="标题",
        url="https://spaces.ac.cn/archives/6508",
        content="body",
        metadata={},
    )
    source_hash = local_pdf.source_content_hash(article)
    output_path = tmp_path / "articles" / "a1-006508.pdf"
    output_path.parent.mkdir()
    output_path.write_bytes(b"%PDF-1.7\n" + (b"0" * 2048) + b"\n%%EOF")
    record = local_pdf.PdfExportRecord(
        article_id=article.id,
        archive_id="006508",
        title=article.title,
        canonical_url=article.url,
        source_content_hash=source_hash,
        output_relative_path="articles/a1-006508.pdf",
        pdf_size_bytes=output_path.stat().st_size,
        pdf_sha256=local_pdf.file_sha256(output_path),
        page_count=1,
        export_status="PASS",
        validation_status="PASS",
        formula_count=0,
        image_reference_count=0,
        local_image_embedded_count=0,
        remote_image_placeholder_count=0,
        exported_at="2026-07-01T00:00:00Z",
        renderer_version="chromium-test-1",
        template_version=local_pdf.DEFAULT_TEMPLATE_VERSION,
        error_category=None,
        action="CREATED",
        text_length=100,
        formula_render_failure_count=0,
        delimiter_balanced=True,
        broken_image_count=0,
        external_network_request_count=0,
        error_message=None,
    )

    config = local_pdf.PdfExportConfig(
        article_store_path=_store_path(tmp_path),
        output_dir=tmp_path,
        renderer_version="chromium-test-1",
    )
    assert local_pdf.should_resume(record, article, config=config) is True

    original_size = output_path.stat().st_size
    output_path.write_bytes(b"%PDF-1.7\n" + (b"1" * (original_size - 14)) + b"%%EOF")
    assert output_path.stat().st_size == original_size
    assert local_pdf.should_resume(record, article, config=config) is False

    output_path.write_bytes(b"%PDF-1.7\n" + (b"0" * 2048) + b"\n%%EOF")

    bad_status = replace(record, export_status="FAIL", action="FAILED")
    assert local_pdf.should_resume(bad_status, article, config=config) is False

    short = replace(record, source_content_hash=source_hash + "0")
    assert local_pdf.should_resume(short, article, config=config) is False

    output_path.write_bytes(b"not a pdf")
    assert local_pdf.should_resume(record, article, config=config) is False


def test_compute_corpus_fingerprint_reused_in_manifest(tmp_path: Path) -> None:
    store = _store_path(tmp_path)
    records = [
        _record("a1", "https://spaces.ac.cn/archives/6508"),
        _record("a2", "https://spaces.ac.cn/archives/6509"),
    ]
    _write_store(store, records)
    loaded = local_pdf.load_pdf_export_articles(store)
    fingerprint = local_pdf.compute_source_corpus_fingerprint(loaded)
    manifest = local_pdf.PdfExportManifest(
        mode="offline",
        corpus_fingerprint=fingerprint,
        records=[],
        summary=None,
    )

    assert manifest.corpus_fingerprint == fingerprint
    assert isinstance(manifest.to_dict()["generated_at"], str)
    assert manifest.to_dict()["output_root"] == "."
