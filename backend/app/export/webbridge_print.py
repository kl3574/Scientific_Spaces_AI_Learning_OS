from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.export.browser_print import (
    BrowserPrintConfig,
    BrowserPrintResult,
    NavigationRateLimiter,
    SessionFactory,
)
from app.export.printed_pdf import (
    PrintedPdfInspection,
    PrintedPdfValidationError,
    inspect_printed_article_pdf,
)
from app.storage.article_store import StoredArticle

DEFAULT_WEBBRIDGE_URL = "http://127.0.0.1:10086"
DEFAULT_WEBBRIDGE_SESSION = "p3-009-corpus-sync"
DEFAULT_WEBBRIDGE_GROUP = "P3-009 抓取基线核验"

PdfInspector = Callable[
    [StoredArticle, Path, bool],
    PrintedPdfInspection,
]


class WebBridgeCommandError(RuntimeError):
    pass


class WebBridgeClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_WEBBRIDGE_URL,
        session_name: str = DEFAULT_WEBBRIDGE_SESSION,
        timeout_seconds: float = 90,
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
        ):
            raise ValueError("WebBridge must use a localhost HTTP endpoint")
        if not session_name.strip():
            raise ValueError("WebBridge session name is required")
        self.base_url = base_url.rstrip("/")
        self.session_name = session_name
        self.timeout_seconds = timeout_seconds

    def command(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(
            {
                "action": action,
                "args": args,
                "session": self.session_name,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/command",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise WebBridgeCommandError(
                f"WebBridge command failed with HTTP {exc.code}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalize local bridge failures.
            raise WebBridgeCommandError(
                f"WebBridge {action} command failed: "
                f"{type(exc).__name__}"
            ) from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WebBridgeCommandError(
                "WebBridge returned invalid JSON"
            ) from exc
        if not isinstance(result, dict) or result.get("ok") is not True:
            error = result.get("error", {}) if isinstance(result, dict) else {}
            message = (
                str(error.get("message") or "WebBridge command was rejected")
                if isinstance(error, dict)
                else "WebBridge command was rejected"
            )
            raise WebBridgeCommandError(message)
        data = result.get("data")
        if not isinstance(data, dict):
            raise WebBridgeCommandError("WebBridge response has no data object")
        return data


class WebBridgeBrowserPrintSession:
    def __init__(
        self,
        config: BrowserPrintConfig,
        *,
        client: WebBridgeClient | None = None,
        group_title: str = DEFAULT_WEBBRIDGE_GROUP,
        pdf_inspector: PdfInspector | None = None,
    ) -> None:
        config.validate()
        if config.workers != 1:
            raise ValueError(
                "WebBridge browser printing supports exactly one controlled tab"
            )
        self.config = config
        self.client = client or WebBridgeClient()
        self.group_title = group_title
        self.pdf_inspector = pdf_inspector or _inspect_pdf
        self._has_tab = False

    def __enter__(self) -> WebBridgeBrowserPrintSession:
        tabs = self.client.command("list_tabs", {}).get("tabs")
        if not isinstance(tabs, list):
            raise WebBridgeCommandError("WebBridge tab list is invalid")
        if tabs:
            active = next(
                (tab for tab in tabs if isinstance(tab, dict) and tab.get("active")),
                tabs[-1],
            )
            if not isinstance(active, dict) or not active.get("url"):
                raise WebBridgeCommandError("WebBridge tab identity is invalid")
            self.client.command(
                "find_tab",
                {"url": str(active["url"])},
            )
            self._has_tab = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        # Tabs opened for the task remain in their visible group. The bridge
        # contract requires explicit user authorization before closing them.
        return None

    def render(
        self,
        article: StoredArticle,
        output_path: Path,
        limiter: NavigationRateLimiter,
        stop_event: threading.Event,
    ) -> BrowserPrintResult:
        started_at = time.monotonic()
        total_navigation_wait = 0.0
        last_error = "unknown WebBridge browser print error"
        last_failure_class = "browser"
        last_http_status: int | None = None

        for attempt in range(1, self.config.retries + 1):
            try:
                output_path.unlink(missing_ok=True)
                total_navigation_wait += limiter.acquire(stop_event)
                self._navigate(article.url)
                state = self._wait_for_article_state()
                status = state.get("responseStatus")
                last_http_status = status if isinstance(status, int) else None
                if status == 403:
                    raise _WebBridgeAttemptError(
                        "http_403",
                        "HTTP status 403",
                        http_status=403,
                    )
                if status == 429:
                    raise _WebBridgeAttemptError(
                        "http_429",
                        "HTTP status 429",
                        http_status=429,
                    )
                if not isinstance(status, int) or not 200 <= status < 300:
                    raise _WebBridgeAttemptError(
                        "http_status",
                        f"HTTP status {status}",
                        http_status=last_http_status,
                    )
                if _canonical_url(str(state.get("url") or "")) != _canonical_url(
                    article.url
                ):
                    raise _WebBridgeAttemptError(
                        "content_quality",
                        "WebBridge landed on the wrong Article URL",
                    )
                title = str(state.get("title") or "").strip()
                if not title:
                    raise _WebBridgeAttemptError(
                        "content_quality",
                        "source page title is empty",
                    )
                body_length = state.get("maxBodyTextLength")
                if not isinstance(body_length, int) or body_length < 100:
                    raise _WebBridgeAttemptError(
                        "content_quality",
                        "source Article body is unavailable",
                    )
                mathjax_available = bool(state.get("mathjaxAvailable"))
                save_result = self.client.command(
                    "save_as_pdf",
                    {
                        "paper_format": "a4",
                        "landscape": False,
                        "scale": 1.0,
                        "print_background": True,
                        "path": str(output_path.resolve()),
                    },
                )
                if (
                    save_result.get("mimeType") != "application/pdf"
                    or int(save_result.get("sizeBytes") or 0) <= 0
                ):
                    raise _WebBridgeAttemptError(
                        "pdf_quality",
                        "WebBridge did not create a PDF",
                    )
                inspection = self.pdf_inspector(
                    article,
                    output_path,
                    mathjax_available,
                )
                return BrowserPrintResult(
                    article_id=article.id,
                    url=article.url,
                    status="success",
                    output_path=output_path,
                    title=title,
                    http_status=status,
                    duration_seconds=time.monotonic() - started_at,
                    navigation_wait_seconds=total_navigation_wait,
                    attempts=attempt,
                    mathjax_available=mathjax_available,
                    inspection=inspection,
                )
            except _WebBridgeAttemptError as exc:
                last_error = str(exc)
                last_failure_class = exc.failure_class
                last_http_status = exc.http_status or last_http_status
                if exc.failure_class == "browser":
                    self._reset_tab_after_failure()
            except PrintedPdfValidationError as exc:
                last_error = str(exc)
                last_failure_class = "pdf_quality"
            except WebBridgeCommandError as exc:
                last_error = str(exc)
                last_failure_class = "browser"
                self._reset_tab_after_failure()
            except OSError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                last_failure_class = "pdf_quality"

            output_path.unlink(missing_ok=True)
            if last_failure_class in {"http_403", "http_429"}:
                limiter.backoff(60.0)
                break
            if attempt < self.config.retries:
                limiter.backoff(
                    (
                        max(30.0, self.config.navigation_interval_seconds * 2)
                        if last_failure_class == "browser"
                        else max(
                            8.0,
                            self.config.navigation_interval_seconds * 2,
                        )
                    )
                )

        return BrowserPrintResult(
            article_id=article.id,
            url=article.url,
            status="failed",
            output_path=output_path,
            http_status=last_http_status,
            duration_seconds=time.monotonic() - started_at,
            navigation_wait_seconds=total_navigation_wait,
            attempts=attempt,
            failure_class=last_failure_class,
            error=last_error,
        )

    def _reset_tab_after_failure(self) -> None:
        if not self._has_tab:
            return
        try:
            self.client.command(
                "cdp",
                {"method": "Page.stop", "params": {}},
            )
            self.client.command(
                "cdp",
                {
                    "method": "Page.navigate",
                    "params": {"url": "about:blank"},
                },
            )
        except WebBridgeCommandError:
            return

    def _navigate(self, url: str) -> None:
        if not self._has_tab:
            navigation = self.client.command(
                "navigate",
                {
                    "url": url,
                    "newTab": True,
                    "group_title": self.group_title,
                },
            )
            if navigation.get("success") is not True:
                raise _WebBridgeAttemptError(
                    "browser",
                    "WebBridge navigation did not succeed",
                )
            self._has_tab = True
            return

        self.client.command(
            "cdp",
            {
                "method": "Page.navigate",
                "params": {"url": url},
            },
        )
        # CDP may report a subresource timeout even after the Article body has
        # committed. URL, HTTP, body, and PDF gates below remain authoritative.

    def _wait_for_article_state(self) -> dict[str, Any]:
        data = self.client.command(
            "cdp",
            {
                "method": "Runtime.evaluate",
                "params": {
                    "expression": _article_state_script(
                        settle_ms=self.config.settle_ms,
                        article_ready_timeout_ms=(
                            self.config.article_ready_timeout_ms
                        ),
                        mathjax_timeout_ms=self.config.mathjax_timeout_ms,
                    ),
                    "awaitPromise": True,
                    "returnByValue": True,
                },
            },
        )
        result = data.get("result")
        value = result.get("value") if isinstance(result, dict) else None
        if (
            not isinstance(result, dict)
            or result.get("type") != "object"
            or not isinstance(value, dict)
        ):
            raise WebBridgeCommandError(
                "WebBridge Article state response is invalid"
            )
        return value


class _WebBridgeAttemptError(RuntimeError):
    def __init__(
        self,
        failure_class: str,
        message: str,
        *,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.http_status = http_status


def webbridge_session_factory(
    *,
    base_url: str = DEFAULT_WEBBRIDGE_URL,
    session_name: str = DEFAULT_WEBBRIDGE_SESSION,
    group_title: str = DEFAULT_WEBBRIDGE_GROUP,
) -> SessionFactory:
    def factory(config: BrowserPrintConfig) -> WebBridgeBrowserPrintSession:
        return WebBridgeBrowserPrintSession(
            config,
            client=WebBridgeClient(
                base_url=base_url,
                session_name=session_name,
            ),
            group_title=group_title,
        )

    return factory


def _inspect_pdf(
    article: StoredArticle,
    path: Path,
    mathjax_rendered: bool,
) -> PrintedPdfInspection:
    return inspect_printed_article_pdf(
        article,
        path,
        mathjax_rendered=mathjax_rendered,
    )


def _canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {
        "spaces.ac.cn",
        "www.spaces.ac.cn",
    }:
        raise _WebBridgeAttemptError(
            "content_quality",
            "WebBridge returned a non-Scientific-Spaces URL",
        )
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(("https", host, path, parsed.query, ""))


def _article_state_script(
    *,
    settle_ms: int,
    article_ready_timeout_ms: int,
    mathjax_timeout_ms: int,
) -> str:
    return f"""
(async () => {{
  const selectors = [
    "#content > .Post",
    "#content .Post",
    ".Post",
    "article",
    ".post",
    ".entry",
    "#article"
  ];
  const sleep = (milliseconds) =>
    new Promise((resolve) => setTimeout(resolve, milliseconds));
  const deadline = Date.now() + {article_ready_timeout_ms};
  let maxBodyTextLength = 0;
  let bodySelectorCount = 0;
  while (Date.now() < deadline) {{
    const nodes = selectors.flatMap(
      (selector) => Array.from(document.querySelectorAll(selector))
    );
    const lengths = nodes.map(
      (node) => String(node.innerText || "").trim().length
    );
    bodySelectorCount = nodes.length;
    maxBodyTextLength = lengths.length ? Math.max(...lengths) : 0;
    if (maxBodyTextLength >= 100) {{
      break;
    }}
    await sleep(250);
  }}
  await sleep({settle_ms});
  const mathJax = window.MathJax;
  const mathjaxAvailable = Boolean(
    mathJax ||
    document.querySelector(
      'script[src*="MathJax"], script[src*="mathjax"], .MathJax, mjx-container, .katex'
    )
  );
  if (mathJax && mathJax.startup && mathJax.startup.promise) {{
    await Promise.race([
      mathJax.startup.promise.catch(() => true),
      sleep({mathjax_timeout_ms})
    ]);
  }} else if (mathJax && typeof mathJax.typesetPromise === "function") {{
    await Promise.race([
      mathJax.typesetPromise().catch(() => true),
      sleep({mathjax_timeout_ms})
    ]);
  }} else if (mathJax && mathJax.Hub && mathJax.Hub.Queue) {{
    await Promise.race([
      new Promise((resolve) => mathJax.Hub.Queue(() => resolve(true))),
      sleep({mathjax_timeout_ms})
    ]);
  }}
  const navigation = performance.getEntriesByType("navigation")[0];
  return {{
    url: location.href,
    title: document.title,
    responseStatus:
      navigation && "responseStatus" in navigation
        ? navigation.responseStatus
        : null,
    bodySelectorCount,
    maxBodyTextLength,
    mathjaxAvailable
  }};
}})()
""".strip()
