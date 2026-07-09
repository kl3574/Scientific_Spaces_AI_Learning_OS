from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.corpus.materialization import LocalCorpusMaterializationConfig, materialize_local_corpus


REPO_ROOT = Path(__file__).resolve().parents[2]


def _article_store_path(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "pilot" / "article_store" / "articles.json"


def _local_library_dir(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "local_library"


def _write_store(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _record(
    article_id: str,
    url: str,
    *,
    title: str = "Audit 测试文章",
    content: str = "正文第一段。\n\n这里有足够的本地内容用于 audit。",
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": title,
        "url": url,
        "content": content,
        "metadata": {"date": "2026-07-01", "category": "数学研究", "references": [], "images": []},
    }


def test_local_corpus_audit_checks_store_library_indexes_and_samples(tmp_path: Path) -> None:
    from app.corpus.audit import LocalCorpusAuditConfig, audit_local_corpus

    article_store_path = _article_store_path(tmp_path)
    local_library_dir = _local_library_dir(tmp_path)
    _write_store(
        article_store_path,
        [
            _record("a1", "https://spaces.ac.cn/archives/1", title="First"),
            _record("a2", "https://spaces.ac.cn/archives/2", title="Second"),
        ],
    )
    materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=local_library_dir)
    )

    summary = audit_local_corpus(
        LocalCorpusAuditConfig(article_store_path=article_store_path, local_library_dir=local_library_dir, sample_size=2)
    )

    assert summary.article_store_count == 2
    assert summary.unique_url_count == 2
    assert summary.duplicate_count == 0
    assert summary.missing_content_count == 0
    assert summary.markdown_file_count == 2
    assert summary.index_json_count == 2
    assert summary.index_csv_count == 2
    assert summary.materialization_summary_count == 2
    assert summary.sample_frontmatter_valid is True
    assert summary.sample_content_non_empty is True
    assert summary.no_source_fetch is True
    assert summary.status == "PASS"


def test_local_corpus_audit_cli_prints_json(tmp_path: Path) -> None:
    article_store_path = _article_store_path(tmp_path)
    local_library_dir = _local_library_dir(tmp_path)
    _write_store(article_store_path, [_record("a1", "https://spaces.ac.cn/archives/1")])
    materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=article_store_path, output_dir=local_library_dir)
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "corpus" / "audit_local_library.py"),
            "--article-store-path",
            str(article_store_path),
            "--local-library-dir",
            str(local_library_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["article_store_count"] == 1
    assert payload["markdown_file_count"] == 1
