from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.crawler.canonical import canonicalize_article_urls


def load_seed_urls(path: Path | str) -> list[str]:
    seed_path = Path(path)
    text = seed_path.read_text(encoding="utf-8")
    if seed_path.suffix == ".json":
        raw_urls = _urls_from_json(json.loads(text))
    else:
        raw_urls = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return canonicalize_article_urls(raw_urls).canonical_urls


def _urls_from_json(data: Any) -> list[str]:
    if isinstance(data, dict):
        articles = data.get("articles")
        if not isinstance(articles, list):
            raise ValueError("--seed-file JSON object must contain an articles list")
        return [_url_from_item(item) for item in articles if _url_from_item(item)]
    if isinstance(data, list):
        return [_url_from_item(item) for item in data if _url_from_item(item)]
    raise ValueError("--seed-file JSON must contain a URL list or an object with articles")


def _url_from_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict) and isinstance(item.get("url"), str):
        return item["url"]
    return ""
