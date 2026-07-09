from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.corpus.materialization import (
    LocalCorpusMaterializationConfig,
    materialize_local_corpus,
    safe_markdown_filename,
)


def _runtime_output_dir(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "local_library"


def _article_store_path(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "pilot" / "article_store" / "articles.json"


def _write_store(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _article_record(
    *,
    article_id: str = "article-6508",
    title: str = "Attention 测试文章",
    url: str = "https://spaces.ac.cn/archives/6508",
    content: str | None = "正文第一段。\n\n公式 $qk^T$ 保持不变。",
    date: str | None = "2026-07-01",
    category: str | None = "数学研究",
) -> dict[str, object]:
    record: dict[str, object] = {
        "id": article_id,
        "title": title,
        "url": url,
        "metadata": {"date": date, "category": category, "references": [], "images": []},
    }
    if content is not None:
        record["content"] = content
    return record


def test_materialization_reads_article_store_and_writes_markdown_with_frontmatter(tmp_path: Path) -> None:
    article_store_path = _article_store_path(tmp_path)
    output_dir = _runtime_output_dir(tmp_path)
    _write_store(article_store_path, [_article_record()])

    summary = materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=output_dir)
    )

    assert summary.input_article_store_path == str(article_store_path)
    assert summary.article_count == 1
    assert summary.exported_markdown_count == 1
    assert summary.missing_content_count == 0
    assert summary.no_source_fetch is True

    markdown_path = output_dir / "articles" / "6508-attention.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    assert markdown.startswith(
        "---\n"
        "id: article-6508\n"
        "title: Attention 测试文章\n"
        "url: https://spaces.ac.cn/archives/6508\n"
        "date: 2026-07-01\n"
        "category: 数学研究\n"
        "---\n\n"
        "# Attention 测试文章\n\n"
    )
    assert "正文第一段。" in markdown
    assert "$qk^T$" in markdown


def test_safe_markdown_filename_removes_unsafe_path_characters() -> None:
    filename = safe_markdown_filename(
        article_id="hash-id",
        title="Attention: A/B? <测试>",
        url="https://spaces.ac.cn/archives/6508?x=1",
    )

    assert filename == "6508-attention-a-b.md"
    assert all(char not in filename for char in ' /\\:?*"<>|')


def test_materialization_writes_json_and_csv_indexes(tmp_path: Path) -> None:
    article_store_path = _article_store_path(tmp_path)
    output_dir = _runtime_output_dir(tmp_path)
    _write_store(
        article_store_path,
        [
            _article_record(article_id="a1", title="First", url="https://spaces.ac.cn/archives/1"),
            _article_record(article_id="a2", title="Second", url="https://spaces.ac.cn/archives/2", category="AI"),
        ],
    )

    materialize_local_corpus(LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=output_dir))

    index_json = json.loads((output_dir / "index" / "articles_index.json").read_text(encoding="utf-8"))
    assert [entry["id"] for entry in index_json] == ["a1", "a2"]
    assert index_json[0]["markdown_path"] == "articles/1-first.md"
    assert index_json[1]["category"] == "AI"

    with (output_dir / "index" / "articles_index.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["id"] for row in rows] == ["a1", "a2"]
    assert rows[0]["markdown_path"] == "articles/1-first.md"


def test_empty_or_missing_content_articles_are_rejected(tmp_path: Path) -> None:
    article_store_path = _article_store_path(tmp_path)
    output_dir = _runtime_output_dir(tmp_path)
    _write_store(
        article_store_path,
        [
            _article_record(article_id="valid", title="Valid", url="https://spaces.ac.cn/archives/1"),
            _article_record(article_id="empty", title="Empty", url="https://spaces.ac.cn/archives/2", content="   "),
            _article_record(article_id="missing", title="Missing", url="https://spaces.ac.cn/archives/3", content=None),
        ],
    )

    summary = materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=output_dir)
    )

    assert summary.article_count == 3
    assert summary.exported_markdown_count == 1
    assert summary.missing_content_count == 2
    assert summary.rejected_article_ids == ["empty", "missing"]
    assert (output_dir / "articles" / "1-valid.md").exists()
    assert not (output_dir / "articles" / "2-empty.md").exists()
    assert not (output_dir / "articles" / "3-missing.md").exists()


def test_output_directory_must_be_ignored_runtime_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output_dir must be under an ignored .local_data runtime directory"):
        LocalCorpusMaterializationConfig(
            article_store_path=_article_store_path(tmp_path),
            output_dir=tmp_path / "docs" / "local_library",
        )


def test_materialization_does_not_access_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_source_access(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("source access is forbidden for local materialization")

    monkeypatch.setattr("urllib.request.urlopen", fail_source_access)
    article_store_path = _article_store_path(tmp_path)
    output_dir = _runtime_output_dir(tmp_path)
    _write_store(article_store_path, [_article_record()])

    summary = materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=output_dir)
    )

    assert summary.exported_markdown_count == 1
