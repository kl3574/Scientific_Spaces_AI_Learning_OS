from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Any

import pytest

from app.export.browser_print import (
    BrowserPrintConfig,
    BrowserPrintResult,
    NavigationRateLimiter,
)
from app.export.printed_pdf import PrintedPdfInspection
from app.storage.article_store import StoredArticle
from app.zotero.bulk_pdf import (
    BulkZoteroPdfSync,
    CheckpointJournal,
    run_throughput_probe,
)
from app.zotero.sync import ZoteroSyncError, render_article_item


def _article(index: int) -> StoredArticle:
    return StoredArticle(
        id=f"article-{index:04d}",
        title=f"科学空间文章 {index}",
        url=f"https://spaces.ac.cn/archives/{10_000 + index}",
        content=(
            "这是用于验证浏览器打印正文完整性的中文段落，"
            f"文章编号为 {index}，并包含公式 $x_{index}^2+y^2=z^2$。"
        ),
        metadata={
            "date": "2026-07-28",
            "category": "数学",
            "references": [],
            "images": [],
        },
    )


def _pdf_bytes(index: int = 0) -> bytes:
    return (
        b"%PDF-1.7\n"
        + f"printed-article-{index}\n".encode() * 100
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


class FakeBrowserSession:
    def __init__(
        self,
        config: BrowserPrintConfig,
        fetches: list[str],
        lock: threading.Lock,
    ) -> None:
        self.config = config
        self.fetches = fetches
        self.lock = lock

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
        payload = _pdf_bytes(int(article.id.rsplit("-", 1)[-1]))
        output_path.write_bytes(payload)
        with self.lock:
            self.fetches.append(article.id)
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


class FakeSessionFactory:
    def __init__(self) -> None:
        self.fetches: list[str] = []
        self.lock = threading.Lock()

    def __call__(self, config: BrowserPrintConfig) -> FakeBrowserSession:
        return FakeBrowserSession(config, self.fetches, self.lock)


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
        self.selected_count = 0

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
        self.selected_count += 1

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


def test_browser_config_enforces_probe_safety_floor() -> None:
    with pytest.raises(ValueError, match="workers"):
        BrowserPrintConfig(workers=5).validate()
    with pytest.raises(ValueError, match="interval"):
        BrowserPrintConfig(navigation_interval_seconds=3.9).validate()


def test_navigation_rate_limiter_spaces_global_starts() -> None:
    now = [100.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = NavigationRateLimiter(4.0, clock=clock, sleeper=sleeper)

    waits = [limiter.acquire() for _ in range(3)]

    assert waits == [0.0, 4.0, 4.0]
    assert sum(sleeps) == pytest.approx(8.0)


def test_bounded_probe_selects_fastest_stable_tier(tmp_path: Path) -> None:
    factory = FakeSessionFactory()

    outcome = run_throughput_probe(
        [_article(index) for index in range(24)],
        tmp_path / "probe",
        session_factory=factory,
    )

    assert outcome.status == "PASS"
    assert outcome.selected_tier is not None
    assert outcome.selected_tier.workers == 4
    assert outcome.selected_tier.navigation_interval_seconds == 4.0
    assert outcome.tested_url_count == 24
    assert len(factory.fetches) == 24
    assert not (tmp_path / "probe").exists()


def test_bulk_sync_is_resumable_and_idempotent(tmp_path: Path) -> None:
    articles = [_article(index) for index in range(3)]
    transport = FakeZoteroTransport()
    factory = FakeSessionFactory()
    checkpoint = CheckpointJournal(tmp_path / "checkpoint.jsonl")
    runner = BulkZoteroPdfSync(
        transport,
        browser_config=BrowserPrintConfig(
            workers=2,
            navigation_interval_seconds=4,
        ),
        checkpoint=checkpoint,
        staging_dir=tmp_path / "staging",
        readback_batch_size=2,
        readback_attempts=1,
        readback_delay_seconds=0,
        session_factory=factory,
    )

    first = runner.run(articles, write=True)
    second = runner.run(articles, write=True)

    assert first.status == "PASS"
    assert first.created_count == 3
    assert first.final_parent_count == 3
    assert first.final_pdf_count == 3
    assert first.final_html_count == 0
    assert first.duplicate_count == 0
    assert transport.write_count == 3
    assert len(factory.fetches) == 3

    assert second.status == "PASS"
    assert second.preexisting_count == 3
    assert second.pending_count == 0
    assert second.network_navigation_count == 0
    assert second.zotero_write_count == 0
    assert transport.write_count == 3
    assert len(factory.fetches) == 3
    assert list((tmp_path / "staging").glob("*.pdf")) == []


def test_snapshot_inspection_rejects_duplicate_zotero_parents(
    tmp_path: Path,
) -> None:
    article = _article(1)
    transport = FakeZoteroTransport()
    item = render_article_item(article)
    transport.items = [
        {"key": "A", "data": {**item, "key": "A"}},
        {"key": "B", "data": {**item, "key": "B"}},
    ]
    runner = BulkZoteroPdfSync(
        transport,
        browser_config=BrowserPrintConfig(),
        checkpoint=CheckpointJournal(tmp_path / "checkpoint.jsonl"),
        staging_dir=tmp_path / "staging",
        session_factory=FakeSessionFactory(),
    )

    with pytest.raises(ZoteroSyncError, match="Multiple Zotero items"):
        runner.run([article], write=False)
