import os
from pathlib import Path

import pytest

from app.storage.article_store import ArticleStore
from app.sync import SyncRunner


pytestmark = pytest.mark.live


@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="live source check is opt-in")
def test_live_rss_browser_source_syncs_articles(tmp_path: Path) -> None:
    store = ArticleStore(tmp_path / "articles.json")
    result = SyncRunner(
        source_strategy="rss-browser",
        max_articles=3,
        store=store,
        report_path=tmp_path / "validation_report.json",
    )

    first = result.run()
    first_count = store.count()
    second = result.run()

    assert first.discovered_count >= 3
    assert first.imported_count >= 1
    assert second.imported_count >= 1
    assert first_count >= 1
    assert store.count() == first_count
