from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path
from typing import Any

import pytest

from app.crawler.browser import BrowserFetchResult
from app.export.browser_print import (
    BrowserPrintConfig,
    BrowserPrintResult,
    NavigationRateLimiter,
)
from app.export.printed_pdf import PrintedPdfInspection
from app.parser.article import ParsedArticle
from app.storage.article_store import ArticleStore, StoredArticle
from app.zotero.bulk_pdf import (
    BulkZoteroPdfSync,
    CheckpointJournal,
)
from app.zotero.incremental_sync import (
    IncrementalBlogZoteroSync,
    IncrementalCheckpointJournal,
    IncrementalSyncError,
    WebBridgeArticleHtmlFetcher,
    append_articles_atomically,
)
from app.export.webbridge_print import WebBridgeCommandError


RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>new</title>
      <link>https://spaces.ac.cn/archives/20002</link>
    </item>
    <item>
      <title>existing</title>
      <link>https://spaces.ac.cn/archives/20001</link>
    </item>
  </channel>
</rss>
"""


def _parsed(index: int) -> ParsedArticle:
    return ParsedArticle(
        title=f"科学空间增量文章 {index}",
        url=f"https://spaces.ac.cn/archives/{20_000 + index}",
        date="2026-07-29",
        category="数学研究",
        content=(
            "这是用于验证增量更新的完整中文正文，包含足够的内容和标点。"
            "第二段用于确认现有记录不会在增量写入过程中发生改变。"
            "公式为 $x^2+y^2=z^2$，并且公式定界符保持平衡。"
        )
        * 4,
        images=["https://spaces.ac.cn/usr/uploads/example.png"],
        references=[
            {
                "title": "Reference",
                "url": "https://example.com/reference",
            }
        ],
    )


def _article_html() -> str:
    return """
    <html>
      <head><title>科学空间增量文章 2 - 科学空间</title></head>
      <body>
        <div id="content">
          <article class="Post">
            <h1>科学空间增量文章 2</h1>
            <div>日期：2026-07-29 分类：<a href="/category/math">数学研究</a></div>
            <div id="PostContent">
              <p>这是用于验证增量更新的完整中文正文，包含足够的内容和标点。</p>
              <p>第二段用于确认现有记录不会在增量写入过程中发生改变。</p>
              <script type="math/tex">x^2+y^2=z^2</script>
              <p>这里继续补充正文，确保内容质量验证不会把页面误判为抽取失败。</p>
              <p>这里继续补充正文，确保内容质量验证不会把页面误判为抽取失败。</p>
              <p>这里继续补充正文，确保内容质量验证不会把页面误判为抽取失败。</p>
              <img src="/usr/uploads/example.png" />
              <h2>参考资料</h2>
              <ol><li><a href="https://example.com/reference">Reference</a></li></ol>
            </div>
          </article>
        </div>
      </body>
    </html>
    """


def _pdf_bytes(index: int) -> bytes:
    return (
        b"%PDF-1.7\n"
        + f"incremental-{index}\n".encode() * 100
        + b"%%EOF\n"
    )


def _inspection(payload: bytes) -> PrintedPdfInspection:
    return PrintedPdfInspection(
        file_size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        page_count=1,
        a4_page=True,
        extracted_text_chars=500,
        sample_count=1,
        matched_sample_count=1,
        chinese_present=True,
        title_present=True,
        formula_expected=True,
        mathjax_rendered=True,
    )


class FakeSourceFetcher:
    def __init__(self, html: str) -> None:
        self.html = html
        self.fetches: list[str] = []
        self.navigation_attempt_count = 0
        self.enter_count = 0

    def __enter__(self) -> FakeSourceFetcher:
        self.enter_count += 1
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def fetch(self, url: str) -> BrowserFetchResult:
        self.fetches.append(url)
        self.navigation_attempt_count += 1
        return BrowserFetchResult(
            url=url,
            html=self.html,
            title="科学空间增量文章 2 - 科学空间",
            status=200,
            mathjax_available=True,
        )


class FakeBrowserSession:
    def __init__(
        self,
        config: BrowserPrintConfig,
        fetches: list[str],
    ) -> None:
        self.config = config
        self.fetches = fetches

    def __enter__(self) -> FakeBrowserSession:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def render(
        self,
        article: StoredArticle,
        output_path: Path,
        limiter: NavigationRateLimiter,
        stop_event: threading.Event,
    ) -> BrowserPrintResult:
        del limiter, stop_event
        payload = _pdf_bytes(len(self.fetches) + 1)
        output_path.write_bytes(payload)
        self.fetches.append(article.url)
        return BrowserPrintResult(
            article_id=article.id,
            url=article.url,
            status="success",
            output_path=output_path,
            title=article.title,
            http_status=200,
            duration_seconds=0.1,
            attempts=1,
            mathjax_available=True,
            inspection=_inspection(payload),
        )


class FakeBrowserFactory:
    def __init__(self) -> None:
        self.fetches: list[str] = []

    def __call__(self, config: BrowserPrintConfig) -> FakeBrowserSession:
        return FakeBrowserSession(config, self.fetches)


class FakeZoteroTransport:
    def __init__(self) -> None:
        self.collections = [
            {
                "key": "COLLECTION1",
                "data": {
                    "name": "苏剑林博客",
                    "parentCollection": False,
                },
            }
        ]
        self.items: list[dict[str, Any]] = []
        self.children: dict[str, list[dict[str, Any]]] = {}
        self.payloads: dict[str, bytes] = {}
        self.write_count = 0

    def find_collections(self, name: str) -> list[dict[str, Any]]:
        assert name == "苏剑林博客"
        return self.collections

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]:
        assert collection_key == "COLLECTION1"
        return list(self.items)

    def list_item_children(self, item_key: str) -> list[dict[str, Any]]:
        return list(self.children.get(item_key, []))

    def select_collection(self, collection_key: str, collection_name: str) -> None:
        assert collection_key == "COLLECTION1"
        assert collection_name == "苏剑林博客"

    def import_ris(self, ris: str) -> None:
        raise AssertionError(f"RIS import is not expected: {ris}")

    def save_item_with_pdf(
        self,
        item: dict[str, Any],
        pdf_bytes: bytes,
    ) -> None:
        self.write_count += 1
        parent_key = f"ITEM{self.write_count}"
        attachment_key = f"PDF{self.write_count}"
        self.items.append(
            {
                "key": parent_key,
                "data": {
                    **item,
                    "key": parent_key,
                    "collections": ["COLLECTION1"],
                },
            }
        )
        self.children[parent_key] = [
            {
                "key": attachment_key,
                "data": {
                    "key": attachment_key,
                    "itemType": "attachment",
                    "parentItem": parent_key,
                    "contentType": "application/pdf",
                    "url": item["url"],
                },
            }
        ]
        self.payloads[attachment_key] = pdf_bytes

    def read_attachment_bytes(self, attachment_key: str) -> bytes:
        return self.payloads[attachment_key]


def _runner(
    tmp_path: Path,
    *,
    source: FakeSourceFetcher,
) -> tuple[
    IncrementalBlogZoteroSync,
    ArticleStore,
    FakeZoteroTransport,
    FakeBrowserFactory,
]:
    store = ArticleStore(tmp_path / "articles.json")
    store.upsert(_parsed(1))
    transport = FakeZoteroTransport()
    browser = FakeBrowserFactory()

    def bulk_factory() -> BulkZoteroPdfSync:
        return BulkZoteroPdfSync(
            transport,
            browser_config=BrowserPrintConfig(
                workers=1,
                navigation_interval_seconds=4,
            ),
            checkpoint=CheckpointJournal(tmp_path / "pdf-checkpoint.jsonl"),
            staging_dir=tmp_path / "staging",
            readback_attempts=1,
            readback_delay_seconds=0,
            session_factory=browser,
        )

    runner = IncrementalBlogZoteroSync(
        store=store,
        bulk_sync_factory=bulk_factory,
        checkpoint=IncrementalCheckpointJournal(
            tmp_path / "incremental-checkpoint.jsonl"
        ),
        source_fetcher_factory=lambda: source,
        rss_fetch_xml=lambda _url: RSS_FIXTURE,
        backup_path=tmp_path / "backups" / "articles.json",
    )
    return runner, store, transport, browser


def test_incremental_sync_adds_only_missing_article_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source = FakeSourceFetcher(_article_html())
    runner, store, transport, browser = _runner(
        tmp_path,
        source=source,
    )
    original = store.list_articles()[0].to_dict()

    first = runner.run(write=True)
    second = runner.run(write=True)

    assert first.status == "PASS"
    assert first.feed_article_count == 2
    assert first.missing_before_count == 1
    assert first.acquired_count == 1
    assert first.stored_count == 1
    assert first.source_navigation_count == 1
    assert first.existing_records_unchanged is True
    assert first.backup_created is True
    assert first.zotero is not None
    assert first.zotero["final_parent_count"] == 2
    assert first.zotero["final_pdf_count"] == 2
    assert first.zotero["final_html_count"] == 0
    assert source.fetches == ["https://spaces.ac.cn/archives/20002"]
    assert store.count() == 2
    assert (tmp_path / "backups" / "articles.json").exists()
    assert next(
        article
        for article in store.list_articles()
        if article.url == original["url"]
    ).to_dict() == original

    assert second.status == "PASS"
    assert second.missing_before_count == 0
    assert second.acquired_count == 0
    assert second.stored_count == 0
    assert second.source_navigation_count == 0
    assert second.backup_created is False
    assert second.zotero is not None
    assert second.zotero["network_navigation_count"] == 0
    assert second.zotero["zotero_write_count"] == 0
    assert source.enter_count == 1
    assert transport.write_count == 2
    assert len(browser.fetches) == 2
    assert list((tmp_path / "staging").glob("*.pdf")) == []


def test_read_only_preview_does_not_fetch_or_mutate(
    tmp_path: Path,
) -> None:
    source = FakeSourceFetcher(_article_html())
    runner, store, transport, browser = _runner(
        tmp_path,
        source=source,
    )
    before = store.path.read_bytes()

    result = runner.run(write=False)

    assert result.status == "DRY_RUN"
    assert result.missing_before_count == 1
    assert result.acquired_count == 0
    assert result.stored_count == 0
    assert result.source_navigation_count == 0
    assert source.enter_count == 0
    assert source.fetches == []
    assert browser.fetches == []
    assert transport.write_count == 0
    assert store.path.read_bytes() == before


def test_source_quality_failure_does_not_change_store_or_zotero(
    tmp_path: Path,
) -> None:
    source = FakeSourceFetcher(
        "<html><head><title>broken</title></head><body>navigation</body></html>"
    )
    runner, store, transport, browser = _runner(
        tmp_path,
        source=source,
    )
    before = store.path.read_bytes()

    result = runner.run(write=True)

    assert result.status == "BLOCKED"
    assert result.stored_count == 0
    assert result.zotero is None
    assert result.failures
    assert store.path.read_bytes() == before
    assert transport.write_count == 0
    assert browser.fetches == []


def test_atomic_append_rejects_existing_url_without_mutation(
    tmp_path: Path,
) -> None:
    store = ArticleStore(tmp_path / "articles.json")
    store.upsert(_parsed(1))
    before = store.path.read_bytes()

    with pytest.raises(IncrementalSyncError, match="overlaps"):
        append_articles_atomically(store, [_parsed(1)])

    assert store.path.read_bytes() == before


class NavigationRaceClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.evaluate_count = 0

    def command(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((action, args))
        if action == "list_tabs":
            return {
                "tabs": [
                    {
                        "active": True,
                        "url": "about:blank",
                    }
                ]
            }
        if action == "find_tab":
            return {"success": True}
        if action == "cdp" and args.get("method") == "Page.navigate":
            return {"frameId": "FRAME1"}
        if action == "cdp" and args.get("method") == "Runtime.evaluate":
            self.evaluate_count += 1
            if self.evaluate_count == 1:
                raise WebBridgeCommandError(
                    "Inspected target navigated or closed"
                )
            return {
                "result": {
                    "type": "object",
                    "value": {
                        "url": "https://spaces.ac.cn/archives/20002",
                        "title": "科学空间增量文章 2",
                        "responseStatus": 200,
                        "maxBodyTextLength": 500,
                        "mathjaxAvailable": True,
                        "html": _article_html(),
                    },
                }
            }
        raise AssertionError(f"Unexpected command: {action} {args}")


def test_webbridge_fetcher_recovers_from_navigation_context_race() -> None:
    client = NavigationRaceClient()
    sleeps: list[float] = []

    with WebBridgeArticleHtmlFetcher(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=1,
            settle_ms=0,
        ),
        client=client,  # type: ignore[arg-type]
        sleeper=sleeps.append,
    ) as fetcher:
        result = fetcher.fetch(
            "https://spaces.ac.cn/archives/20002"
        )

    assert result.status == 200
    assert result.mathjax_available is True
    assert fetcher.navigation_attempt_count == 1
    assert client.evaluate_count == 2
    assert sleeps == [0.5]


@pytest.mark.browser_live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to enable browser live tests",
)
def test_incremental_webbridge_live_html_acquisition() -> None:
    with WebBridgeArticleHtmlFetcher(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=1,
            settle_ms=2_500,
        )
    ) as fetcher:
        result = fetcher.fetch(
            "https://spaces.ac.cn/archives/11823"
        )

    assert result.status == 200
    assert result.mathjax_available is True
    assert result.title
    assert len(result.html) > 1_000
