#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.storage.article_store import ArticleStore  # noqa: E402
from app.zotero.sync import (  # noqa: E402
    DEFAULT_COLLECTION_NAME,
    LocalZoteroSyncTransport,
    ZoteroArticleSync,
    ZoteroSyncError,
)

DEFAULT_ARTICLE_STORE = (
    REPO_ROOT
    / ".local_data"
    / "scientific_spaces"
    / "corpus"
    / "pilot"
    / "article_store"
    / "articles.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Idempotently sync one Scientific Spaces article into a private Zotero collection."
    )
    parser.add_argument("--article-store", type=Path, default=DEFAULT_ARTICLE_STORE)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Perform the Zotero write. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()

    articles = [
        article
        for article in ArticleStore(args.article_store).list_articles()
        if article.id == args.article_id
    ]
    if len(articles) != 1:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Expected exactly one article with id {args.article_id}",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    try:
        result = ZoteroArticleSync(
            LocalZoteroSyncTransport(),
            collection_name=args.collection_name,
        ).sync(articles[0], write=args.write)
    except ZoteroSyncError as exc:
        print(
            json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
