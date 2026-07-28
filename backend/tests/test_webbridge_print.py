from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Any

import pytest

from app.export.browser_print import BrowserPrintConfig, NavigationRateLimiter
from app.export.printed_pdf import PrintedPdfInspection
from app.export.webbridge_print import (
    WebBridgeBrowserPrintSession,
    WebBridgeClient,
    WebBridgeCommandError,
)
from app.storage.article_store import StoredArticle


def _article() -> StoredArticle:
    return StoredArticle(
        id="article-webbridge",
        title="科学空间浏览指南（FAQ）",
        url="https://spaces.ac.cn/archives/6508",
        content=(
            "这是用于验证桌面浏览器打印正文完整性的中文段落，"
            "并包含公式 $x^2+y^2=z^2$。"
        ),
        metadata={
            "date": "2020-01-01",
            "category": "数学",
            "references": [],
            "images": [],
        },
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


class FakeWebBridgeClient:
    def __init__(self, *, http_status: int = 200) -> None:
        self.http_status = http_status
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def command(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((action, args))
        if action == "list_tabs":
            return {
                "tabs": [
                    {
                        "active": True,
                        "url": "https://spaces.ac.cn/archives/6508",
                    }
                ]
            }
        if action == "find_tab":
            return {"success": True}
        if action == "navigate":
            return {"success": True, "url": args["url"]}
        if action == "cdp":
            if args["method"] == "Runtime.evaluate":
                return {
                    "result": {
                        "type": "object",
                        "value": {
                            "url": "https://spaces.ac.cn/archives/6508",
                            "title": "科学空间浏览指南（FAQ） - 科学空间",
                            "responseStatus": self.http_status,
                            "bodySelectorCount": 3,
                            "maxBodyTextLength": 2_973,
                            "mathjaxAvailable": True,
                        },
                    }
                }
            assert args == {
                "method": "Page.navigate",
                "params": {
                    "url": "https://spaces.ac.cn/archives/6508",
                },
            }
            return {"frameId": "FRAME1", "loaderId": "LOADER1"}
        if action == "save_as_pdf":
            path = Path(args["path"])
            payload = b"%PDF-1.7\nwebbridge-print\n" * 100 + b"%%EOF\n"
            path.write_bytes(payload)
            return {
                "path": str(path),
                "sizeBytes": len(payload),
                "mimeType": "application/pdf",
            }
        raise AssertionError(f"Unexpected WebBridge action: {action}")


class RecoveringWebBridgeClient(FakeWebBridgeClient):
    def __init__(self) -> None:
        super().__init__()
        self.state_evaluation_count = 0

    def command(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if action == "cdp":
            method = args["method"]
            if method == "Runtime.evaluate":
                self.state_evaluation_count += 1
                if self.state_evaluation_count == 1:
                    self.calls.append((action, args))
                    raise WebBridgeCommandError(
                        "WebBridge Runtime.evaluate command failed: TimeoutError"
                    )
                return super().command(action, args)
            self.calls.append((action, args))
            url = args.get("params", {}).get("url")
            if method == "Page.stop":
                return {}
            if method == "Page.navigate" and url == "about:blank":
                return {"frameId": "FRAME1", "loaderId": "RESET1"}
            if (
                method == "Page.navigate"
                and url == "https://spaces.ac.cn/archives/6508"
            ):
                return {"frameId": "FRAME1", "loaderId": "LOADER2"}
        return super().command(action, args)


class NavigationWarningWebBridgeClient(FakeWebBridgeClient):
    def command(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if (
            action == "cdp"
            and args.get("method") == "Page.navigate"
        ):
            self.calls.append((action, args))
            return {"errorText": "net::ERR_TIMED_OUT"}
        return super().command(action, args)


class FakeLimiter:
    def __init__(self) -> None:
        self.backoffs: list[float] = []

    def acquire(self, stop_event: threading.Event) -> float:
        return 0.0

    def backoff(self, seconds: float) -> None:
        self.backoffs.append(seconds)


def test_webbridge_client_rejects_non_local_endpoint() -> None:
    with pytest.raises(ValueError, match="localhost"):
        WebBridgeClient(base_url="https://example.com")


def test_webbridge_session_rejects_parallel_workers() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        WebBridgeBrowserPrintSession(
            BrowserPrintConfig(workers=2, navigation_interval_seconds=4),
            client=FakeWebBridgeClient(),
        )


def test_webbridge_session_prints_and_validates_pdf(tmp_path: Path) -> None:
    client = FakeWebBridgeClient()
    output = tmp_path / "article.pdf"

    with WebBridgeBrowserPrintSession(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=1,
            settle_ms=0,
        ),
        client=client,
        pdf_inspector=lambda article, path, mathjax: _inspection(
            path.read_bytes()
        ),
    ) as session:
        result = session.render(
            _article(),
            output,
            NavigationRateLimiter(4),
            threading.Event(),
        )

    assert result.status == "success"
    assert result.http_status == 200
    assert result.mathjax_available is True
    assert result.inspection is not None
    assert output.is_file()
    assert [action for action, _ in client.calls] == [
        "list_tabs",
        "find_tab",
        "cdp",
        "cdp",
        "save_as_pdf",
    ]


def test_webbridge_session_stops_before_pdf_on_http_403(
    tmp_path: Path,
) -> None:
    client = FakeWebBridgeClient(http_status=403)

    with WebBridgeBrowserPrintSession(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=1,
            settle_ms=0,
        ),
        client=client,
    ) as session:
        result = session.render(
            _article(),
            tmp_path / "blocked.pdf",
            NavigationRateLimiter(4),
            threading.Event(),
        )

    assert result.status == "failed"
    assert result.failure_class == "http_403"
    assert result.http_status == 403
    assert "save_as_pdf" not in [action for action, _ in client.calls]


def test_webbridge_session_uses_content_gate_after_navigation_warning(
    tmp_path: Path,
) -> None:
    client = NavigationWarningWebBridgeClient()

    with WebBridgeBrowserPrintSession(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=1,
            settle_ms=0,
        ),
        client=client,
        pdf_inspector=lambda article, path, mathjax: _inspection(
            path.read_bytes()
        ),
    ) as session:
        result = session.render(
            _article(),
            tmp_path / "warning.pdf",
            NavigationRateLimiter(4),
            threading.Event(),
        )

    assert result.status == "success"
    assert result.attempts == 1


def test_webbridge_session_resets_error_page_before_retry(
    tmp_path: Path,
) -> None:
    client = RecoveringWebBridgeClient()
    limiter = FakeLimiter()

    with WebBridgeBrowserPrintSession(
        BrowserPrintConfig(
            workers=1,
            navigation_interval_seconds=4,
            retries=2,
            settle_ms=0,
        ),
        client=client,
        pdf_inspector=lambda article, path, mathjax: _inspection(
            path.read_bytes()
        ),
    ) as session:
        result = session.render(
            _article(),
            tmp_path / "recovered.pdf",
            limiter,  # type: ignore[arg-type]
            threading.Event(),
        )

    assert result.status == "success"
    assert result.attempts == 2
    assert limiter.backoffs == [30.0]
    cdp_calls = [
        args
        for action, args in client.calls
        if action == "cdp"
    ]
    assert [
        (call["method"], call.get("params", {}).get("url"))
        for call in cdp_calls
    ] == [
        ("Page.navigate", "https://spaces.ac.cn/archives/6508"),
        ("Runtime.evaluate", None),
        ("Page.stop", None),
        ("Page.navigate", "about:blank"),
        ("Page.navigate", "https://spaces.ac.cn/archives/6508"),
        ("Runtime.evaluate", None),
    ]
    assert cdp_calls[-1]["params"]["awaitPromise"] is True
    assert cdp_calls[-1]["params"]["returnByValue"] is True
