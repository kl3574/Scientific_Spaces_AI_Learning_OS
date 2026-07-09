from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DEFAULT_ARTICLE_STORE_PATH = Path(".local_data/scientific_spaces/corpus/pilot/article_store/articles.json")
DEFAULT_LOCAL_LIBRARY_DIR = Path(".local_data/scientific_spaces/corpus/local_library")


@dataclass(frozen=True)
class LocalCorpusMaterializationConfig:
    article_store_path: Path = DEFAULT_ARTICLE_STORE_PATH
    output_dir: Path = DEFAULT_LOCAL_LIBRARY_DIR

    def __post_init__(self) -> None:
        article_store_path = Path(self.article_store_path)
        output_dir = Path(self.output_dir)
        object.__setattr__(self, "article_store_path", article_store_path)
        object.__setattr__(self, "output_dir", output_dir)
        if ".local_data" not in output_dir.parts:
            raise ValueError("output_dir must be under an ignored .local_data runtime directory")


@dataclass(frozen=True)
class LocalCorpusMaterializationSummary:
    input_article_store_path: str
    article_count: int
    exported_markdown_count: int
    missing_content_count: int
    output_path: str
    index_json_path: str
    index_csv_path: str
    summary_path: str
    no_source_fetch: bool
    rejected_article_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def materialize_local_corpus(config: LocalCorpusMaterializationConfig | None = None) -> LocalCorpusMaterializationSummary:
    resolved_config = config or LocalCorpusMaterializationConfig()
    records = _read_article_records(resolved_config.article_store_path)
    output_dir = resolved_config.output_dir
    articles_dir = output_dir / "articles"
    index_dir = output_dir / "index"
    reports_dir = output_dir / "reports"
    articles_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    _clear_markdown_outputs(articles_dir)

    index_entries: list[dict[str, str]] = []
    rejected_article_ids: list[str] = []
    for record in records:
        article_id = _string_value(record.get("id"))
        title = _string_value(record.get("title"))
        url = _string_value(record.get("url"))
        content = record.get("content")
        if not isinstance(content, str) or not content.strip():
            rejected_article_ids.append(article_id or url or "unknown")
            continue

        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        date = _string_value(metadata.get("date"))
        category = _string_value(metadata.get("category"))
        filename = safe_markdown_filename(article_id=article_id, title=title, url=url)
        relative_path = f"articles/{filename}"
        markdown_path = output_dir / relative_path
        markdown_path.write_text(
            _markdown_document(
                article_id=article_id,
                title=title,
                url=url,
                date=date,
                category=category,
                content=content.strip(),
            ),
            encoding="utf-8",
        )
        index_entries.append(
            {
                "id": article_id,
                "title": title,
                "url": url,
                "date": date,
                "category": category,
                "markdown_path": relative_path,
            }
        )

    index_json_path = index_dir / "articles_index.json"
    index_csv_path = index_dir / "articles_index.csv"
    summary_path = reports_dir / "local_library_summary.json"
    _write_index_json(index_json_path, index_entries)
    _write_index_csv(index_csv_path, index_entries)
    summary = LocalCorpusMaterializationSummary(
        input_article_store_path=str(resolved_config.article_store_path),
        article_count=len(records),
        exported_markdown_count=len(index_entries),
        missing_content_count=len(rejected_article_ids),
        output_path=str(output_dir),
        index_json_path=str(index_json_path),
        index_csv_path=str(index_csv_path),
        summary_path=str(summary_path),
        no_source_fetch=True,
        rejected_article_ids=rejected_article_ids,
    )
    summary_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def safe_markdown_filename(*, article_id: str, title: str, url: str) -> str:
    archive_id = _archive_id(url)
    prefix = archive_id or article_id or "article"
    slug = _slug(title)
    stem = f"{prefix}-{slug}" if slug else prefix
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("._-").lower()
    if not safe_stem:
        safe_stem = "article"
    return f"{safe_stem[:120]}.md"


def _read_article_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Article store must contain a JSON list")
    return [item for item in data if isinstance(item, dict)]


def _clear_markdown_outputs(articles_dir: Path) -> None:
    for path in articles_dir.glob("*.md"):
        path.unlink()


def _write_index_json(path: Path, entries: list[dict[str, str]]) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_index_csv(path: Path, entries: list[dict[str, str]]) -> None:
    fieldnames = ["id", "title", "url", "date", "category", "markdown_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)


def _markdown_document(
    *,
    article_id: str,
    title: str,
    url: str,
    date: str,
    category: str,
    content: str,
) -> str:
    safe_title = title or article_id or url
    return (
        "---\n"
        f"id: {_frontmatter_value(article_id)}\n"
        f"title: {_frontmatter_value(safe_title)}\n"
        f"url: {_frontmatter_value(url)}\n"
        f"date: {_frontmatter_value(date)}\n"
        f"category: {_frontmatter_value(category)}\n"
        "---\n\n"
        f"# {safe_title}\n\n"
        f"{content}\n"
    )


def _frontmatter_value(value: str) -> str:
    cleaned = " ".join(str(value).splitlines()).strip()
    if not cleaned:
        return ""
    if any(marker in cleaned for marker in (": ", "#", '"', "'", "[", "]", "{", "}")):
        return json.dumps(cleaned, ensure_ascii=False)
    return cleaned


def _archive_id(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    if "/archives/" not in path:
        return ""
    candidate = path.rsplit("/", 1)[-1]
    return candidate if candidate.isdigit() else ""


def _slug(value: str) -> str:
    normalized = value.lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
