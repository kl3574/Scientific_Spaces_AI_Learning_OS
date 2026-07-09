from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.corpus.materialization import DEFAULT_ARTICLE_STORE_PATH, DEFAULT_LOCAL_LIBRARY_DIR


@dataclass(frozen=True)
class LocalCorpusAuditConfig:
    article_store_path: Path = DEFAULT_ARTICLE_STORE_PATH
    local_library_dir: Path = DEFAULT_LOCAL_LIBRARY_DIR
    sample_size: int = 5

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_store_path", Path(self.article_store_path))
        object.__setattr__(self, "local_library_dir", Path(self.local_library_dir))
        if self.sample_size < 1:
            raise ValueError("sample_size must be >= 1")


@dataclass(frozen=True)
class LocalCorpusAuditSummary:
    status: str
    article_store_path: str
    local_library_dir: str
    article_store_count: int
    unique_url_count: int
    duplicate_count: int
    missing_content_count: int
    markdown_file_count: int
    index_json_count: int
    index_csv_count: int
    materialization_summary_count: int
    sample_frontmatter_valid: bool
    sample_content_non_empty: bool
    no_source_fetch: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def audit_local_corpus(config: LocalCorpusAuditConfig | None = None) -> LocalCorpusAuditSummary:
    resolved = config or LocalCorpusAuditConfig()
    records = _read_article_records(resolved.article_store_path)
    urls = [_string_value(record.get("url")) for record in records]
    missing_content_count = sum(1 for record in records if not _string_value(record.get("content")).strip())

    local_library_dir = resolved.local_library_dir
    markdown_files = sorted((local_library_dir / "articles").glob("*.md"))
    index_json_count = _read_index_json_count(local_library_dir / "index" / "articles_index.json")
    index_csv_count = _read_index_csv_count(local_library_dir / "index" / "articles_index.csv")
    materialization_summary_count = _read_materialization_summary_count(
        local_library_dir / "reports" / "local_library_summary.json"
    )
    sampled_files = markdown_files[: resolved.sample_size]
    sample_frontmatter_valid = bool(sampled_files) and all(_frontmatter_valid(path) for path in sampled_files)
    sample_content_non_empty = bool(sampled_files) and all(_content_non_empty(path) for path in sampled_files)
    duplicate_count = len(urls) - len(set(urls))
    status = (
        "PASS"
        if duplicate_count == 0
        and missing_content_count == 0
        and len(records) == len(set(urls))
        and len(records) == len(markdown_files)
        and len(records) == index_json_count
        and len(records) == index_csv_count
        and len(records) == materialization_summary_count
        and sample_frontmatter_valid
        and sample_content_non_empty
        else "BLOCKED"
    )
    return LocalCorpusAuditSummary(
        status=status,
        article_store_path=str(resolved.article_store_path),
        local_library_dir=str(local_library_dir),
        article_store_count=len(records),
        unique_url_count=len(set(urls)),
        duplicate_count=duplicate_count,
        missing_content_count=missing_content_count,
        markdown_file_count=len(markdown_files),
        index_json_count=index_json_count,
        index_csv_count=index_csv_count,
        materialization_summary_count=materialization_summary_count,
        sample_frontmatter_valid=sample_frontmatter_valid,
        sample_content_non_empty=sample_content_non_empty,
        no_source_fetch=True,
    )


def _read_article_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _read_index_json_count(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else 0


def _read_index_csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        return len(list(csv.DictReader(handle)))


def _read_materialization_summary_count(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    exported_count = data.get("exported_markdown_count") if isinstance(data, dict) else None
    return int(exported_count) if isinstance(exported_count, int) else 0


def _frontmatter_valid(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return False
    frontmatter = parts[1]
    return all(f"{key}:" in frontmatter for key in ("id", "title", "url"))


def _content_non_empty(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return False
    return bool(parts[2].strip())


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
