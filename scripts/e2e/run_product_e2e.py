#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Iterator
from urllib.error import URLError
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
FRONTEND_ROOT = ROOT / "frontend"
ARTICLE_FIXTURE = BACKEND_ROOT / "tests" / "fixtures" / "evaluation" / "articles.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.graph.builder import KnowledgeGraphBuilder
from app.graph.store import GraphStore
from app.rag.full_corpus import compute_corpus_fingerprint
from app.references.deduplication import build_reference_data
from app.references.extraction import extract_article_references
from app.references.matching import match_reference_records
from app.references.store import install_reference_store
from app.storage.article_store import StoredArticle


API_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:3000"
CRB_ARTICLE_ID = "crb-formula"
CRB_TITLE = "CRB公式与估计下界"
ATTENTION_ARTICLE_ID = "attention-basics"
ATTENTION_TITLE = "Attention机制入门"
RESEARCH_ARTICLE_ID = "local-research-map"
RESEARCH_TITLE = "本地研究路径与来源边界"
ATTENTION_CONCEPT_ID = "concept:attention"
ATTENTION_CONCEPT_RETURN = "/graph?node_id=concept%3Aattention"
ATTENTION_CONCEPT_QUERY_RETURN = f"{ATTENTION_CONCEPT_RETURN}&q=Attention"
EXPECTED_ARTICLE_COUNT = 3


class E2EFailure(AssertionError):
    """Raised when an end-to-end product assertion fails."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local-only Scientific Spaces product E2E suite.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of complete desktop/mobile passes.")
    parser.add_argument(
        "--frontend-mode",
        choices=("start", "dev"),
        default="start",
        help="Use the built Next.js server or the development server.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON result path; temporary output is preferred.")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.frontend_mode == "start" and not (FRONTEND_ROOT / ".next").is_dir():
        parser.error("frontend/.next is absent; run npm run build before --frontend-mode start")

    result: dict[str, object]
    with tempfile.TemporaryDirectory(prefix="scientific-spaces-p3-011-e2e-") as temporary:
        runtime_root = Path(temporary)
        try:
            runtime = prepare_runtime(runtime_root)
            with product_servers(runtime, frontend_mode=args.frontend_mode) as logs:
                result = run_browser_suite(runtime, repeat=args.repeat)
            restart_result = verify_backend_restart_persistence(runtime)
            result["restart_persistence"] = restart_result
            if restart_result["status"] != "PASS":
                result["status"] = "BLOCKED"
            result["server_logs"] = {
                "backend": _bounded_log_summary(logs["backend"]),
                "frontend": _bounded_log_summary(logs["frontend"]),
                "restart_backend": _bounded_log_summary(Path(runtime["root"]) / "restart-backend.log"),
            }
        except Exception as exc:
            result = {
                "status": "BLOCKED",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=12),
            }
            backend_log = runtime_root / "backend.log"
            frontend_log = runtime_root / "frontend.log"
            result["server_logs"] = {
                "backend": _bounded_log_summary(backend_log),
                "frontend": _bounded_log_summary(frontend_log),
            }

    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    return 0 if result.get("status") == "PASS" else 1


def prepare_runtime(runtime_root: Path) -> dict[str, Path | dict[str, str]]:
    data_root = runtime_root / ".local_data" / "scientific_spaces"
    articles_path = data_root / "articles.json"
    graph_path = data_root / "knowledge_graph.json"
    learning_path = data_root / "learning.json"
    tutor_path = data_root / "tutor_sessions.json"
    zotero_path = data_root / "zotero_links.json"
    reference_store = data_root / "references" / "full-corpus" / "current"
    data_root.mkdir(parents=True, exist_ok=True)

    articles = _load_fixture_articles()
    articles_path.write_text(
        json.dumps([article.to_dict() for article in articles], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    environment = {
        "SCIENTIFIC_SPACES_DATA_DIR": str(data_root),
        "SCIENTIFIC_SPACES_ARTICLES_FILE": str(articles_path),
        "SCIENTIFIC_SPACES_ARTICLE_STORE": str(articles_path),
        "SCIENTIFIC_SPACES_GRAPH_FILE": str(graph_path),
        "SCIENTIFIC_SPACES_LEARNING_FILE": str(learning_path),
        "SCIENTIFIC_SPACES_TUTOR_FILE": str(tutor_path),
        "SCIENTIFIC_SPACES_ZOTERO_FILE": str(zotero_path),
        "SCIENTIFIC_SPACES_REFERENCE_STORE": str(reference_store),
        "SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake",
        "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": "fake",
        "NEXT_PUBLIC_API_BASE_URL": API_URL,
    }

    with temporary_environment(environment):
        GraphStore(graph_path).save(
            KnowledgeGraphBuilder(articles=articles, include_personalization=False).build()
        )
        corpus_fingerprint = compute_corpus_fingerprint(articles)
        build_data = build_reference_data(
            [extract_article_references(article) for article in articles],
            corpus_fingerprint=corpus_fingerprint,
            build_id="p3-011-product-e2e",
        )
        match_summary = match_reference_records(build_data.records, [])
        install_reference_store(
            reference_store,
            build_data=build_data,
            zotero_candidates=match_summary.candidates,
            article_ids=[article.id for article in articles],
            corpus_fingerprint=corpus_fingerprint,
            configuration_fingerprint="p3-011-product-e2e-config",
            build_fingerprint="p3-011-product-e2e-build",
            source_asset_id="article-store:p3-011-e2e-fixture",
            network_request_count=0,
            extra_counts={"silent_drops": 0},
        )

    return {
        "root": runtime_root,
        "articles": articles_path,
        "graph": graph_path,
        "learning": learning_path,
        "tutor": tutor_path,
        "zotero": zotero_path,
        "references": reference_store,
        "environment": environment,
    }


def _load_fixture_articles() -> list[StoredArticle]:
    payload = json.loads(ARTICLE_FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != EXPECTED_ARTICLE_COUNT:
        raise E2EFailure(f"expected {EXPECTED_ARTICLE_COUNT} fixture Articles")
    articles: list[StoredArticle] = []
    for raw in payload:
        item = dict(raw)
        metadata = dict(item["metadata"])
        if item["id"] == CRB_ARTICLE_ID:
            item["content"] = (
                f"{item['content']}\n\n"
                "## 推导步骤\n\n"
                "在正则条件下，信息矩阵给出参数不确定性的局部尺度。\n\n"
                "### 正则条件\n\n"
                "分数函数的期望为零，且 Fisher 信息有限。\n\n"
                "## 数值检查\n\n"
                "| quantity | value |\n| --- | ---: |\n| dimension | 1 |\n\n"
                "```python\nvariance_bound = 1 / fisher_information\n```\n\n"
                "## 数值检查\n\n重复标题用于验证唯一锚点。\n\n"
                "## References\n\n"
                "DOI: 10.1000/example\n\n"
                "https://arxiv.org/abs/1706.03762\n\n"
                "![External payment image](https://spaces.ac.cn/usr/themes/geekg/payment/wx.png)\n"
            )
            metadata["references"] = [
                *list(metadata.get("references") or []),
                "DOI: 10.1000/example",
                "arXiv:1706.03762",
            ]
        item["metadata"] = metadata
        articles.append(
            StoredArticle(
                id=str(item["id"]),
                title=str(item["title"]),
                url=str(item["url"]),
                content=str(item["content"]),
                metadata=dict(item["metadata"]),
            )
        )
    return articles


@contextmanager
def temporary_environment(updates: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def product_servers(
    runtime: dict[str, Path | dict[str, str]],
    *,
    frontend_mode: str,
) -> Iterator[dict[str, Path]]:
    environment = os.environ.copy()
    environment.update(runtime["environment"])
    backend_log = Path(runtime["root"]) / "backend.log"
    frontend_log = Path(runtime["root"]) / "frontend.log"
    backend_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None
    _require_port_free(8000)
    _require_port_free(3000)
    try:
        with backend_log.open("w", encoding="utf-8") as backend_handle:
            backend_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(BACKEND_ROOT),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env=environment,
                stdout=backend_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            _wait_for_url(f"{API_URL}/health", backend_process, backend_log)

        frontend_script = "start" if frontend_mode == "start" else "dev"
        with frontend_log.open("w", encoding="utf-8") as frontend_handle:
            frontend_process = subprocess.Popen(
                [
                    "npm",
                    "run",
                    frontend_script,
                    "--",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    "3000",
                ],
                cwd=FRONTEND_ROOT,
                env=environment,
                stdout=frontend_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
            _wait_for_url(FRONTEND_URL, frontend_process, frontend_log, timeout=60)

        yield {"backend": backend_log, "frontend": frontend_log}
    finally:
        _stop_process(frontend_process)
        _stop_process(backend_process)


def run_browser_suite(
    runtime: dict[str, Path | dict[str, str]],
    *,
    repeat: int,
) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    runs: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        browser_version = browser.version
        for iteration in range(1, repeat + 1):
            _reset_mutable_runtime(runtime)
            run_result = _run_single_iteration(browser, iteration=iteration)
            runs.append(run_result)
        browser.close()

    all_checks = [
        check
        for run in runs
        for check in dict(run["checks"]).values()
    ]
    return {
        "status": "PASS" if all(all_checks) else "BLOCKED",
        "browser": "Chromium",
        "browser_version": browser_version,
        "repeat_count": repeat,
        "successful_repeat_count": sum(1 for run in runs if run["status"] == "PASS"),
        "external_network_request_count": sum(
            int(run["external_network_request_count"]) for run in runs
        ),
        "runs": runs,
    }


def _run_single_iteration(browser, *, iteration: int) -> dict[str, object]:
    from playwright.sync_api import expect

    checks: dict[str, bool] = {}
    blocked_external: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: _capture_page_error(page_errors, "primary", page, error))
    page.add_init_script(
        """
        (() => {
          window.__p3030HydrationFocusEvents = [];
          window.__p3030HydrationFocusObserver = event => {
            if (event.target instanceof HTMLElement) {
              window.__p3030HydrationFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }
          };
          document.addEventListener('focusin', window.__p3030HydrationFocusObserver, true);
        })();
        """
    )

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    _wait_for_animation_frames(page, 5)
    hydration_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030HydrationFocusObserver, true);
          return window.__p3030HydrationFocusEvents;
        }
        """
    )
    _require(
        not hydration_focus_events and page.evaluate("document.activeElement === document.body"),
        f"initial Shell hydration moved focus without user input: {hydration_focus_events}",
    )
    checks["shell_initial_hydration_focus_stable"] = True
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_text(str(EXPECTED_ARTICLE_COUNT), exact=True).first).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-command-center")).to_be_visible()
    expect(page.get_by_role("heading", name="Learning Overview", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Focused Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    expect(
        page.get_by_test_id("dashboard-study-session").get_by_role(
            "link", name="Build from saved learning", exact=True
        )
    ).to_be_visible()
    dashboard_sync_payload = json.dumps(
        {
            "version": 1,
            "active_article_id": CRB_ARTICLE_ID,
            "updated_at": "2026-08-31T01:00:00.000Z",
            "items": [
                {
                    "article_id": CRB_ARTICLE_ID,
                    "title": CRB_TITLE,
                    "section_id": "regularity",
                    "added_at": "2026-08-31T01:00:00.000Z",
                }
            ],
        },
        ensure_ascii=False,
    )
    page.evaluate(
        """
        ([key, eventName, payload]) => {
          localStorage.setItem(key, payload);
          window.dispatchEvent(new Event(eventName));
        }
        """,
        [
            "scientific-spaces-study-session-v1",
            "scientific-spaces-study-session-change",
            dashboard_sync_payload,
        ],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "ready"
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_contain_text(CRB_TITLE)
    page.evaluate(
        """
        ([key, eventName]) => {
          localStorage.removeItem(key);
          window.dispatchEvent(new Event(eventName));
        }
        """,
        ["scientific-spaces-study-session-v1", "scientific-spaces-study-session-change"],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    checks["dashboard_session_same_tab_sync"] = True

    sync_page = context.new_page()
    sync_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    sync_page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "dashboard-cross-tab", sync_page, error),
    )
    sync_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(sync_page)
    sync_page.evaluate(
        "([key, payload]) => localStorage.setItem(key, payload)",
        ["scientific-spaces-study-session-v1", dashboard_sync_payload],
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "ready"
    )
    sync_page.evaluate(
        "key => localStorage.removeItem(key)", "scientific-spaces-study-session-v1"
    )
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    sync_page.close()
    checks["dashboard_session_cross_tab_sync"] = True
    expect(page.get_by_role("heading", name="Next Actions", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "dashboard")
    expect(page.get_by_test_id("workspace-context").locator('[aria-current="page"]')).to_have_text(
        "Dashboard"
    )
    _require(
        page.locator('nav[aria-label="Primary"] a').count() == 7,
        "desktop Application Shell does not expose seven primary workspaces",
    )
    next_actions = page.get_by_test_id("dashboard-next-actions")
    for action in ("Open saved learning", "Ask tutor", "Explore graph", "Review sources"):
        expect(next_actions.get_by_role("link", name=re.compile(rf"^{re.escape(action)}"))).to_be_visible()
    _require(
        page.locator('nav[aria-label="Primary"] [aria-current="page"]').get_attribute("href") == "/",
        "Dashboard navigation item is not marked as current",
    )
    checks["dashboard"] = True
    checks["dashboard_command_center"] = True
    checks["desktop_application_shell"] = True
    _verify_overlapping_shell_route_cancellation(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["shell_overlapping_route_cancellation"] = True
    _verify_shell_reader_focus_ownership(
        browser,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["shell_reader_destination_focus_ownership"] = True

    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    expect(search_trigger).to_be_visible()
    _require(
        search_trigger.inner_text().strip() == "Search",
        "desktop search trigger exposes shortcut instructions",
    )
    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    expect(search_dialog).to_be_visible()
    search_input = search_dialog.get_by_label("Search library")
    expect(search_input).to_be_focused()
    _require(
        search_dialog.locator('[data-testid="global-search-result-workspace"]').count() == 7,
        "global quick navigation does not expose seven stable workspaces",
    )
    last_workspace_result = search_dialog.locator(
        '[data-testid="global-search-result-workspace"]'
    ).last
    search_input.press("Shift+Tab")
    expect(last_workspace_result).to_be_focused()
    last_workspace_result.press("Tab")
    expect(search_input).to_be_focused()
    search_input.press("Escape")
    expect(search_dialog).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["global_search_entry_focus_and_quick_navigation"] = True

    page.evaluate("window.scrollTo(0, 300)")
    page.wait_for_function("() => window.scrollY > 0")
    search_trigger.click()
    same_url_dialog = page.get_by_test_id("global-search-dialog")
    same_url_dashboard = same_url_dialog.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Dashboard"))
    same_url_history = page.evaluate("history.length")
    same_url_location = page.url
    same_url_scroll = page.evaluate("window.scrollY")
    page.evaluate(
        """
        () => {
          const originalFetch = window.fetch;
          const originalPushState = history.pushState;
          const originalReplaceState = history.replaceState;
          window.__p3030SameUrlActivity = { fetches: [], pushes: 0, replaces: 0 };
          window.__p3030SameUrlOriginals = {
            fetch: originalFetch,
            pushState: originalPushState,
            replaceState: originalReplaceState,
          };
          window.fetch = function (...args) {
            window.__p3030SameUrlActivity.fetches.push(String(args[0]));
            return originalFetch.apply(this, args);
          };
          history.pushState = function (...args) {
            window.__p3030SameUrlActivity.pushes += 1;
            return originalPushState.apply(this, args);
          };
          history.replaceState = function (...args) {
            window.__p3030SameUrlActivity.replaces += 1;
            return originalReplaceState.apply(this, args);
          };
        }
        """
    )
    same_url_dashboard.focus()
    same_url_dashboard.press("Enter")
    expect(same_url_dialog).to_have_count(0)
    shell_main = page.get_by_test_id("shell-main-content")
    expect(shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(shell_main, "same-URL Shell main")
    _require(page.evaluate("history.length") == same_url_history, "same-URL Search added history")
    _require(page.url == same_url_location, "same-URL Search changed the current URL")
    _require(page.evaluate("window.scrollY") == same_url_scroll, "same-URL Search changed scroll")
    _wait_for_animation_frames(page, 5)
    same_url_activity = page.evaluate(
        """
        () => {
          const activity = window.__p3030SameUrlActivity;
          const originals = window.__p3030SameUrlOriginals;
          window.fetch = originals.fetch;
          history.pushState = originals.pushState;
          history.replaceState = originals.replaceState;
          delete window.__p3030SameUrlActivity;
          delete window.__p3030SameUrlOriginals;
          return activity;
        }
        """
    )
    _require(
        same_url_activity == {"fetches": [], "pushes": 0, "replaces": 0},
        f"same-URL Search reached the Router despite preventDefault: {same_url_activity}",
    )
    page.evaluate("window.scrollTo(0, 0)")
    checks["shell_search_same_url_focus"] = True

    search_trigger.click()
    event_identity_search = page.get_by_test_id("global-search-dialog")
    expect(event_identity_search.get_by_label("Search library")).to_be_focused()
    page.evaluate(
        """
        () => {
          history.replaceState(history.state, '', '/session');
          const dashboardLink = document.querySelector(
            '[data-testid="global-search-dialog"] '
              + '[data-testid="global-search-result-workspace"][href="/"]'
          );
          if (!(dashboardLink instanceof HTMLElement)) {
            throw new Error('Search Dashboard link is unavailable');
          }
          dashboardLink.click();
        }
        """
    )
    expect(event_identity_search).to_have_count(0)
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    checks["shell_event_time_route_identity"] = True

    search_trigger.click()
    backdrop_search = page.get_by_test_id("global-search-dialog")
    expect(backdrop_search.get_by_label("Search library")).to_be_focused()
    page.mouse.click(10, 500)
    expect(backdrop_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_search_backdrop_dismissal"] = True

    search_trigger.click()
    close_button_search = page.get_by_test_id("global-search-dialog")
    expect(close_button_search.get_by_label("Search library")).to_be_focused()
    close_button_search.get_by_role("button", name="Close", exact=True).click()
    expect(close_button_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_search_close_button_dismissal"] = True

    search_trigger.click()
    breakpoint_search = page.get_by_test_id("global-search-dialog")
    breakpoint_input = breakpoint_search.get_by_label("Search library")
    expect(breakpoint_input).to_be_focused()
    page.set_viewport_size({"width": 800, "height": 1000})
    breakpoint_input.press("Escape")
    expect(breakpoint_search).to_have_count(0)
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "hidden-opener main fallback")
    page.set_viewport_size({"width": 1440, "height": 1000})
    expect(search_trigger).to_be_visible()
    checks["shell_hidden_opener_fallback"] = True

    search_trigger.click()
    reopened_search = page.get_by_test_id("global-search-dialog")
    reopened_search_input = reopened_search.get_by_label("Search library")
    expect(reopened_search_input).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030ReopenFocusBehindModal = [];
          window.__p3030ReopenFocusObserver = event => {
            const activeDialog = document.querySelector('[data-testid="global-search-dialog"]');
            if (activeDialog && event.target instanceof Node && !activeDialog.contains(event.target)) {
              window.__p3030ReopenFocusBehindModal.push(
                event.target instanceof Element
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ReopenFocusObserver, true);
          const dialog = document.querySelector('[data-testid="global-search-dialog"]');
          const close = Array.from(dialog?.querySelectorAll('button') || [])
            .find(button => button.textContent?.trim() === 'Close');
          const trigger = document.querySelector('[data-testid="global-search-trigger-desktop"]');
          close?.click();
          trigger?.click();
        }
        """
    )
    expect(reopened_search).to_be_visible()
    expect(reopened_search_input).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    reopen_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ReopenFocusObserver, true);
          return window.__p3030ReopenFocusBehindModal;
        }
        """
    )
    _require(
        reopen_focus_events == [],
        f"stale dismissal focused behind the reopened Search modal: {reopen_focus_events}",
    )
    reopened_search_input.press("Escape")
    expect(reopened_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_stale_dismiss_focus_cancelled"] = True

    search_trigger.click()
    superseded_search = page.get_by_test_id("global-search-dialog")
    expect(superseded_search.get_by_label("Search library")).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030OriginalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
          window.__p3030HeldFocusFrames = [];
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 900000 + window.__p3030HeldFocusFrames.length;
          };
        }
        """
    )
    superseded_search.get_by_test_id("global-search-result-workspace").filter(
        has_text=re.compile(r"^Dashboard")
    ).click()
    expect(superseded_search).to_have_count(0)
    page.evaluate(
        """
        () => {
          if (window.__p3030HeldFocusFrames.length !== 1) {
            throw new Error(
              `expected one first-generation main-focus frame, got ${window.__p3030HeldFocusFrames.length}`
            );
          }
          const firstGeneration = window.__p3030HeldFocusFrames.shift();
          firstGeneration(performance.now());
          if (window.__p3030HeldFocusFrames.length !== 1) {
            throw new Error(
              `first-generation frame did not schedule exactly one nested frame: ${window.__p3030HeldFocusFrames.length}`
            );
          }
        }
        """
    )
    page.evaluate(
        "() => { window.requestAnimationFrame = window.__p3030OriginalRequestAnimationFrame; }"
    )
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.wait_for_timeout(50)
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.focus()
    page.evaluate(
        """
        () => {
          const originalRequestAnimationFrame = window.__p3030OriginalRequestAnimationFrame;
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 920000 + window.__p3030HeldFocusFrames.length;
          };
          try {
            for (let generation = 0; generation < 4; generation += 1) {
              const callbacks = window.__p3030HeldFocusFrames.splice(0);
              if (callbacks.length === 0) break;
              callbacks.forEach(callback => callback(performance.now()));
            }
            if (window.__p3030HeldFocusFrames.length > 0) {
              throw new Error('stale main-focus RAF chain exceeded its bound');
            }
          } finally {
            window.requestAnimationFrame = originalRequestAnimationFrame;
          }
        }
        """
    )
    expect(session_navigation).to_be_focused()
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_new_route_invalidates_stale_focus"] = True

    search_trigger.click()
    stale_opener_search = page.get_by_test_id("global-search-dialog")
    stale_opener_input = stale_opener_search.get_by_label("Search library")
    expect(stale_opener_input).to_be_focused()
    page.evaluate(
        """
        () => {
          window.__p3030OriginalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
          window.__p3030HeldFocusFrames = [];
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 910000 + window.__p3030HeldFocusFrames.length;
          };
        }
        """
    )
    stale_opener_input.press("Escape")
    expect(stale_opener_search).to_have_count(0)
    page.evaluate(
        "() => { window.requestAnimationFrame = window.__p3030OriginalRequestAnimationFrame; }"
    )
    page.go_back()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.wait_for_timeout(50)
    session_navigation = page.get_by_test_id("primary-nav-session")
    session_navigation.focus()
    page.evaluate(
        """
        () => {
          const originalRequestAnimationFrame = window.__p3030OriginalRequestAnimationFrame;
          window.requestAnimationFrame = callback => {
            window.__p3030HeldFocusFrames.push(callback);
            return 930000 + window.__p3030HeldFocusFrames.length;
          };
          try {
            for (let generation = 0; generation < 4; generation += 1) {
              const callbacks = window.__p3030HeldFocusFrames.splice(0);
              if (callbacks.length === 0) break;
              callbacks.forEach(callback => callback(performance.now()));
            }
            if (window.__p3030HeldFocusFrames.length > 0) {
              throw new Error('stale opener RAF chain exceeded its bound');
            }
          } finally {
            window.requestAnimationFrame = originalRequestAnimationFrame;
          }
        }
        """
    )
    expect(session_navigation).to_be_focused()
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_new_route_invalidates_stale_opener"] = True

    search_trigger.click()
    modified_search = page.get_by_test_id("global-search-dialog")
    modified_session = modified_search.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Session"))
    modified_location = page.url
    page.evaluate(
        """
        () => {
          window.__p3030ModifiedFocusBehindModal = [];
          window.__p3030ModifiedFocusObserver = event => {
            const dialog = document.querySelector('[data-testid="global-search-dialog"]');
            if (dialog && event.target instanceof Node && !dialog.contains(event.target)) {
              window.__p3030ModifiedFocusBehindModal.push(
                event.target instanceof Element
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ModifiedFocusObserver, true);
        }
        """
    )

    def attach_modified_page_observers(candidate) -> None:
        candidate.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        candidate.on(
            "pageerror",
            lambda error: _capture_page_error(page_errors, "modified-search", candidate, error),
        )

    context.on("page", attach_modified_page_observers)
    with context.expect_page(timeout=10_000) as modified_page_info:
        modified_session.click(modifiers=["Control"])
    modified_page = modified_page_info.value
    context.remove_listener("page", attach_modified_page_observers)
    modified_page.wait_for_load_state("domcontentloaded")
    _wait_for_application_shell(modified_page)
    expect(modified_page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    _require(modified_page.url.endswith("/session"), f"modified Search opened wrong URL: {modified_page.url}")
    modified_page.close()
    page.bring_to_front()
    expect(modified_search).to_be_visible()
    _require(page.url == modified_location, "modified Search navigation changed the current page")
    _wait_for_animation_frames(page, 5)
    _require(
        page.evaluate(
            """
            () => document.querySelector('[data-testid="global-search-dialog"]')
              ?.contains(document.activeElement) === true
            """
        ),
        "modified Search activation moved focus behind the open modal",
    )
    modified_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ModifiedFocusObserver, true);
          return window.__p3030ModifiedFocusBehindModal;
        }
        """
    )
    _require(
        modified_focus_events == [],
        f"modified Search activation armed focus behind the modal: {modified_focus_events}",
    )
    page.keyboard.press("Escape")
    expect(modified_search).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["shell_modified_navigation_preserves_modal"] = True

    search_trigger.click()
    slow_route_search = page.get_by_test_id("global-search-dialog")
    slow_route_search.get_by_label("Search library").fill("CRB")
    slow_graph_result = slow_route_search.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(slow_graph_result).to_be_visible(timeout=30_000)
    slow_graph_href = str(slow_graph_result.get_attribute("href") or "")
    _require(slow_graph_href.startswith("/graph?"), f"slow Graph target is invalid: {slow_graph_href}")
    page.evaluate(
        """
        targetHref => {
          const originalFetch = window.fetch;
          const target = new URL(targetHref, location.href);
          window.__p3030SlowRouteActivity = {
            delayedRequests: [],
            frameCount: 0,
            prematureMainFocus: false,
            originalFetch,
            targetRoute: `${target.pathname}${target.search}`,
          };
          window.__p3030SlowRouteFocusObserver = event => {
            const activity = window.__p3030SlowRouteActivity;
            if (
              `${location.pathname}${location.search}` !== activity.targetRoute
              && event.target instanceof Element
              && event.target.getAttribute('data-testid') === 'shell-main-content'
            ) {
              activity.prematureMainFocus = true;
            }
          };
          document.addEventListener('focusin', window.__p3030SlowRouteFocusObserver, true);
          window.fetch = async function (...args) {
            const input = args[0];
            const url = input instanceof Request ? input.url : String(input);
            const activity = window.__p3030SlowRouteActivity;
            if (
              url.includes('/graph?')
              && url.includes('_rsc=')
              && activity.delayedRequests.length === 0
            ) {
              activity.delayedRequests.push(url);
              await new Promise(resolve => {
                const nextFrame = () => {
                  activity.frameCount += 1;
                  if (activity.frameCount > 120) {
                    resolve();
                    return;
                  }
                  requestAnimationFrame(nextFrame);
                };
                requestAnimationFrame(nextFrame);
              });
            }
            return originalFetch.apply(this, args);
          };
        }
        """,
        slow_graph_href,
    )
    slow_graph_result.click()
    expect(slow_route_search).to_have_count(0)
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    slow_route_main = page.get_by_test_id("shell-main-content")
    expect(slow_route_main).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    expect(slow_route_main).to_be_focused()
    _require_visible_focus(slow_route_main, "slow Search route destination")
    slow_route_activity = page.evaluate(
        """
        () => {
          const activity = window.__p3030SlowRouteActivity;
          document.removeEventListener('focusin', window.__p3030SlowRouteFocusObserver, true);
          window.fetch = activity.originalFetch;
          delete window.__p3030SlowRouteActivity;
          delete window.__p3030SlowRouteFocusObserver;
          return {
            delayedRequests: activity.delayedRequests,
            frameCount: activity.frameCount,
            prematureMainFocus: activity.prematureMainFocus,
          };
        }
        """
    )
    _require(
        len(slow_route_activity["delayedRequests"]) == 1,
        "slow Shell route probe did not delay one RSC request: "
        f"{slow_route_activity['delayedRequests']}",
    )
    _require(
        slow_route_activity["frameCount"] > 120,
        f"slow Shell route probe observed too few frames: {slow_route_activity['frameCount']}",
    )
    _require(
        slow_route_activity["prematureMainFocus"] is False,
        "Shell focused main before the delayed route committed",
    )
    checks["shell_slow_route_focus_ownership"] = True
    page.get_by_test_id("primary-nav-dashboard").click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    search_dialog.get_by_label("Search library").fill("")
    session_workspace_result = search_dialog.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Session"))
    expect(session_workspace_result).to_be_visible()
    session_workspace_result.click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("study-session-empty")).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search workspace destination")
    checks["shell_search_workspace_route_focus"] = True
    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["study_session_empty_and_quick_navigation"] = True

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    saved_workspace_result = search_dialog.get_by_test_id("global-search-result-workspace").filter(
        has_text=re.compile(r"^Saved")
    )
    expect(saved_workspace_result).to_be_visible()
    saved_workspace_result.click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("saved-library-empty")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "library")
    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    search_trigger.focus()
    checks["saved_library_empty_and_quick_navigation"] = True

    page.route(
        re.compile(r".*/v1\.2/references(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-019 partial Reference failure"}',
        ),
        times=1,
    )
    page.keyboard.press("Control+K")
    search_dialog = page.get_by_test_id("global-search-dialog")
    expect(search_dialog).to_be_visible()
    search_input = search_dialog.get_by_label("Search library")
    expect(search_input).to_be_focused()
    page.keyboard.press("Control+K")
    expect(search_input).to_be_focused()
    search_input.fill("Attention")
    article_search_result = search_dialog.get_by_test_id("global-search-result-article").first
    graph_search_result = search_dialog.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(article_search_result).to_be_visible(timeout=30_000)
    expect(graph_search_result).to_be_visible(timeout=30_000)
    expect(search_dialog.get_by_text("Some sources are unavailable", exact=True)).to_be_visible()
    _require(
        "q%3DAttention%26sort%3Drelevance" in (article_search_result.get_attribute("href") or ""),
        "global Article result does not preserve its relevance-search return path",
    )
    visible_search_text = search_dialog.inner_text()
    _require(
        "attention-basics" not in visible_search_text and "concept:attention" not in visible_search_text,
        "global search exposes raw internal identifiers",
    )
    search_input.press("ArrowDown")
    expect(article_search_result).to_be_focused()
    article_search_result.press("Escape")
    expect(search_dialog).to_have_count(0)
    expect(search_trigger).to_be_focused()
    checks["global_search_partial_failure_and_keyboard"] = True

    search_trigger.click()
    article_route_search = page.get_by_test_id("global-search-dialog")
    article_route_search.get_by_label("Search library").fill("CRB")
    article_route_result = article_route_search.get_by_test_id("global-search-result-article").first
    expect(article_route_result).to_be_visible(timeout=30_000)
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-030-shell-focus-probe",
                    "article_id": CRB_ARTICLE_ID,
                    "started_at": "2026-09-05T01:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    article_route_result.click()
    expect(article_route_search).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search Article destination")
    page.go_back()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()
    search_trigger = page.get_by_test_id("global-search-trigger-desktop")
    checks["shell_search_article_route_focus"] = True

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    search_input = search_dialog.get_by_label("Search library")
    page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (!delayed && url.includes('/v1.1/articles') && url.includes('q=CRB')) {
              delayed = true;
              const response = originalFetch(...args);
              return new Promise((resolve, reject) => {
                window.setTimeout(() => response.then(resolve, reject), 1000);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    search_input.fill("CRB")
    page.wait_for_timeout(350)
    search_input.fill("Attention")
    current_article_result = search_dialog.get_by_test_id("global-search-result-article").first
    expect(current_article_result).to_contain_text("Attention机制入门", timeout=30_000)
    page.wait_for_timeout(1100)
    expect(current_article_result).to_contain_text("Attention机制入门")
    expect(search_input).to_have_value("Attention")
    checks["global_search_stale_response_guard"] = True

    search_input.fill("1706.03762")
    expect(search_dialog.get_by_test_id("global-search-result-reference").first).to_be_visible(
        timeout=30_000
    )
    search_input.fill("Attention")
    graph_search_result = search_dialog.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(graph_search_result).to_be_visible(timeout=30_000)
    graph_search_result.click()
    expect(search_dialog).to_have_count(0)
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_placeholder("Title, concept, or formula")).to_have_value("Attention")
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("shell-main-content")).to_be_focused(timeout=30_000)
    _require_visible_focus(page.get_by_test_id("shell-main-content"), "Search Graph destination")
    _require("node_id=concept%3Aattention" in page.url, f"Graph deep link was not preserved: {page.url}")
    checks["global_search_reference_and_graph_deep_link"] = True

    page.get_by_test_id("global-search-trigger-desktop").click()
    same_route_search = page.get_by_test_id("global-search-dialog")
    same_route_search.get_by_label("Search library").fill("CRB")
    same_route_graph_result = same_route_search.get_by_role(
        "link", name=re.compile(r"^crb\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(same_route_graph_result).to_be_visible(timeout=30_000)
    same_route_graph_result.focus()
    same_route_graph_result.press("Enter")
    expect(same_route_search).to_have_count(0)
    same_route_selected = page.get_by_test_id("graph-selected-region")
    expect(same_route_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(same_route_selected, "same-route global-search Graph detail")
    expect(same_route_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    _require(
        "node_id=concept%3Acrb" in page.url and "q=CRB" in page.url,
        f"same-route Graph navigation diverged from its URL: {page.url}",
    )
    checks["global_search_same_route_graph_navigation"] = True

    same_route_selected.press("Control+k")
    shortcut_search = page.get_by_test_id("global-search-dialog")
    shortcut_input = shortcut_search.get_by_label("Search library")
    expect(shortcut_input).to_be_focused()
    shortcut_input.fill("Attention")
    shortcut_graph_result = shortcut_search.get_by_role(
        "link", name=re.compile(r"^attention\s+Concept\s+·\s+Knowledge Graph$", re.I)
    )
    expect(shortcut_graph_result).to_be_visible(timeout=30_000)
    page.evaluate(
        """
        () => {
          window.__p3030ShortcutRouteFocusEvents = [];
          window.__p3030ShortcutRouteFocusObserver = event => {
            if (event.target instanceof HTMLElement) {
              window.__p3030ShortcutRouteFocusEvents.push(
                event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
              );
            }
          };
          document.addEventListener('focusin', window.__p3030ShortcutRouteFocusObserver, true);
        }
        """
    )
    shortcut_graph_result.focus()
    shortcut_graph_result.press("Enter")
    expect(shortcut_search).to_have_count(0)
    shortcut_selected = page.get_by_test_id("graph-selected-region")
    expect(shortcut_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(shortcut_selected).to_be_focused(timeout=30_000)
    _wait_for_animation_frames(page, 5)
    shortcut_focus_events = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030ShortcutRouteFocusObserver, true);
          return window.__p3030ShortcutRouteFocusEvents;
        }
        """
    )
    expect(shortcut_selected).to_be_focused()
    _require(
        "shell-main-content" not in shortcut_focus_events,
        f"Shell stole shortcut-origin Graph focus: {shortcut_focus_events}",
    )
    page.go_back()
    same_route_selected = page.get_by_test_id("graph-selected-region")
    expect(same_route_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(same_route_selected).to_be_focused(timeout=30_000)
    checks["shell_shortcut_destination_focus_ownership"] = True

    page.evaluate(
        """
        () => {
          window.__p3030FocusBehindModal = [];
          window.__p3030FocusObserver = event => {
            const modal = document.querySelector('[aria-modal="true"]');
            if (modal && event.target instanceof Node && !modal.contains(event.target)) {
              window.__p3030FocusBehindModal.push(
                event.target instanceof HTMLElement
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030FocusObserver, true);
        }
        """
    )
    page.get_by_test_id("global-search-trigger-desktop").click()
    history_search = page.get_by_test_id("global-search-dialog")
    expect(history_search).to_be_visible()
    page.go_back()
    expect(history_search).to_have_count(0)
    history_selected = page.get_by_test_id("graph-selected-region")
    expect(history_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(history_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(history_selected, "Graph Back destination")
    _wait_for_animation_frames(page, 5)
    expect(history_selected).to_be_focused()

    page.get_by_test_id("global-search-trigger-desktop").click()
    history_search = page.get_by_test_id("global-search-dialog")
    expect(history_search).to_be_visible()
    page.go_forward()
    expect(history_search).to_have_count(0)
    history_selected = page.get_by_test_id("graph-selected-region")
    expect(history_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    expect(history_selected).to_be_focused(timeout=30_000)
    _require_visible_focus(history_selected, "Graph Forward destination")
    _wait_for_animation_frames(page, 5)
    expect(history_selected).to_be_focused()
    focus_behind_modal = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030FocusObserver, true);
          return window.__p3030FocusBehindModal;
        }
        """
    )
    _require(not focus_behind_modal, f"route focus escaped a mounted Shell modal: {focus_behind_modal}")
    checks["shell_query_history_modal_focus"] = True

    page.get_by_test_id("primary-nav-session").click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    page.evaluate(
        """
        () => {
          window.__p3030PathFocusBehindModal = [];
          window.__p3030PathFocusObserver = event => {
            const modal = document.querySelector('[aria-modal="true"]');
            if (modal && event.target instanceof Node && !modal.contains(event.target)) {
              window.__p3030PathFocusBehindModal.push(
                event.target instanceof HTMLElement
                  ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  : 'non-element'
              );
            }
          };
          document.addEventListener('focusin', window.__p3030PathFocusObserver, true);
        }
        """
    )
    page.get_by_test_id("global-search-trigger-desktop").click()
    pathname_history_search = page.get_by_test_id("global-search-dialog")
    expect(pathname_history_search.get_by_label("Search library")).to_be_focused()
    page.go_back()
    expect(pathname_history_search).to_have_count(0)
    pathname_history_selected = page.get_by_test_id("graph-selected-region")
    expect(pathname_history_selected.get_by_role("heading", name=re.compile(r"^crb$", re.I))).to_be_visible(
        timeout=30_000
    )
    pathname_history_main = page.get_by_test_id("shell-main-content")
    expect(pathname_history_main).to_be_focused(timeout=30_000)
    _require_visible_focus(pathname_history_main, "pathname Back destination")
    _wait_for_animation_frames(page, 5)
    expect(pathname_history_main).to_be_focused()

    page.get_by_test_id("global-search-trigger-desktop").click()
    pathname_history_search = page.get_by_test_id("global-search-dialog")
    expect(pathname_history_search.get_by_label("Search library")).to_be_focused()
    page.go_forward()
    expect(pathname_history_search).to_have_count(0)
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    pathname_history_main = page.get_by_test_id("shell-main-content")
    expect(pathname_history_main).to_be_focused(timeout=30_000)
    _require_visible_focus(pathname_history_main, "pathname Forward destination")
    _wait_for_animation_frames(page, 5)
    expect(pathname_history_main).to_be_focused()
    pathname_focus_behind_modal = page.evaluate(
        """
        () => {
          document.removeEventListener('focusin', window.__p3030PathFocusObserver, true);
          return window.__p3030PathFocusBehindModal;
        }
        """
    )
    _require(
        not pathname_focus_behind_modal,
        f"pathname history focus escaped a mounted Shell modal: {pathname_focus_behind_modal}",
    )
    checks["shell_pathname_history_modal_focus"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)).to_be_visible()

    page.get_by_role("link", name="Articles", exact=True).click()
    expect(page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(page.locator('nav[aria-label="Primary"] [aria-current="page"]')).to_have_text("Articles")
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "articles")
    page.get_by_placeholder("Search title or keyword").fill("CRB")
    page.get_by_role("button", name="Search", exact=True).click()
    article_link = page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(article_link).to_be_visible(timeout=30_000)
    preview_text = article_link.locator("xpath=ancestor::article[1]").get_by_test_id("article-preview").inner_text()
    _require("# " not in preview_text and "](" not in preview_text, "article preview exposes Markdown syntax")
    checks["title_and_keyword_search"] = True

    capture_url = page.url
    page.evaluate(
        """
        () => {
          window.__p3026LearningWrites = 0;
          window.__p3026SessionWrites = 0;
          const originalFetch = window.fetch.bind(window);
          const originalSetItem = Storage.prototype.setItem;
          window.fetch = (...args) => {
            const url = String(args[0]);
            const method = String(args[1]?.method || "GET").toUpperCase();
            if (url.includes("/learning/") && method !== "GET") {
              window.__p3026LearningWrites += 1;
            }
            return originalFetch(...args);
          };
          Storage.prototype.setItem = function (key, value) {
            if (key === "scientific-spaces-study-session-v1") {
              window.__p3026SessionWrites += 1;
            }
            return originalSetItem.call(this, key, value);
          };
        }
        """
    )
    capture_checkbox = page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    _focus_via_tab(page, capture_checkbox)
    capture_checkbox.press("Space")
    expect(capture_checkbox).to_be_checked()
    capture_action = page.get_by_role("button", name="Add selected to session", exact=True)
    _focus_via_tab(page, capture_action)
    capture_action.press("Enter")
    capture_feedback = page.get_by_test_id("article-session-capture-feedback")
    expect(capture_feedback).to_be_focused()
    expect(capture_feedback).to_have_attribute("aria-live", "polite")
    expect(capture_feedback).to_have_attribute("aria-atomic", "true")
    expect(capture_feedback).to_contain_text(
        "1 added; 0 already present; 0 invalid; 0 omitted by capacity."
    )
    _require_visible_focus(capture_feedback, "Article capture feedback")
    capture_feedback_box = capture_feedback.bounding_box()
    _require(
        capture_feedback_box is not None
        and capture_feedback_box["y"] < page.viewport_size["height"]
        and capture_feedback_box["y"] + capture_feedback_box["height"] > 0,
        f"Article capture feedback does not intersect the viewport: {capture_feedback_box}",
    )
    captured_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in captured_session["items"]] == [CRB_ARTICLE_ID]
        and captured_session["active_article_id"] == CRB_ARTICLE_ID,
        f"Article capture persisted the wrong Session: {captured_session}",
    )
    _require(page.url == capture_url, "Article capture navigated or changed list URL state")
    _require(
        page.evaluate("window.__p3026LearningWrites") == 0,
        "Article capture mutated Learning State or Bookmark data",
    )
    _require(
        page.evaluate("window.__p3026SessionWrites") == 1,
        "Article capture did not use exactly one Session storage write",
    )
    expect(article_link.locator("xpath=ancestor::article[1]")).to_contain_text("In session")
    page.evaluate(
        """
        () => {
          localStorage.removeItem("scientific-spaces-study-session-v1");
          window.dispatchEvent(new Event("scientific-spaces-study-session-change"));
        }
        """
    )
    expect(article_link.locator("xpath=ancestor::article[1]")).not_to_contain_text("In session")
    checks["article_session_capture_keyboard_and_truthful_write"] = True
    checks["article_session_capture_no_server_mutation_or_navigation"] = True

    page.get_by_placeholder("Search title or keyword").fill("__p3_011_no_matching_article__")
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_text("No articles found.", exact=True)).to_be_visible(timeout=30_000)
    page.get_by_placeholder("Search title or keyword").fill("CRB")
    page.get_by_role("button", name="Search", exact=True).click()
    article_link = page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(article_link).to_be_visible(timeout=30_000)
    checks["empty_search_state"] = True

    article_link.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    article_trail = page.get_by_test_id("workspace-context")
    expect(article_trail).to_contain_text("Articles")
    expect(article_trail).to_contain_text("Article")
    expect(article_trail).not_to_contain_text(CRB_ARTICLE_ID)
    expect(page.locator(".reader-markdown")).to_contain_text("Fisher")
    expect(page.locator(".reader-markdown .katex").first).to_be_visible()
    expect(page.get_by_text("External image not loaded automatically.", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Structured References", exact=True)).to_be_visible()
    expect(page.get_by_text("10.1000/example", exact=False).first).to_be_visible(timeout=30_000)
    checks["article_markdown_formula_and_reference"] = True

    outline = page.get_by_test_id("article-outline")
    expect(outline).to_be_visible()
    heading_ids = page.locator(".reader-markdown h2, .reader-markdown h3, .reader-markdown h4").evaluate_all(
        "nodes => nodes.map(node => node.id)"
    )
    _require(heading_ids and all(heading_ids), "reader headings are missing anchors")
    _require(len(heading_ids) == len(set(heading_ids)), "reader heading anchors are not unique")
    target_outline_link = outline.get_by_role("link", name="数值检查", exact=True).first
    target_section_id = unquote((target_outline_link.get_attribute("href") or "").lstrip("#"))
    target_outline_link.click()
    _require(
        page.evaluate("() => document.activeElement?.id") == target_section_id,
        "outline navigation did not move focus to the target heading",
    )
    page.wait_for_function("() => window.scrollY > 0")
    page.wait_for_function(
        "() => Number(document.querySelector('[data-testid=reading-progress]')?.getAttribute('aria-valuenow') || 0) > 0"
    )
    expect(outline.locator('[aria-current="location"]')).to_have_text("数值检查")
    progress_value = int(page.get_by_test_id("reading-progress").get_attribute("aria-valuenow") or "0")
    _require(0 < progress_value <= 100, f"reader progress is out of bounds: {progress_value}")
    page.get_by_role("button", name="Large text", exact=True).click()
    page.get_by_role("button", name="Wide", exact=True).click()
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-size", "large")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-width", "wide")
    checks["reader_outline_progress_and_preferences"] = True

    end_session_button = page.get_by_role("button", name="End session", exact=True)
    expect(end_session_button).to_be_enabled(timeout=30_000)
    sessions = _api_json(context, "GET", "/learning/sessions")
    _require(sessions["total"] == 1, f"expected one reader session, got {sessions['total']}")
    checks["single_reader_session"] = True

    completed_button = page.get_by_role("button", name="completed", exact=True)
    completed_button.click()
    expect(completed_button).to_have_class(re.compile(r"\bbg-slate-950\b"), timeout=30_000)
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("button", name="Remove", exact=True)).to_be_visible(timeout=30_000)
    note_text = f"P3-011 iteration {iteration}"
    page.get_by_placeholder("Write a learning note").fill(note_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    expect(page.get_by_text(note_text, exact=True)).to_be_visible()
    end_session_button.click()
    expect(end_session_button).to_be_disabled()

    stats = _api_json(context, "GET", "/learning/stats")
    _require(stats["completed_count"] == 1, "completed learning state was not persisted")
    _require(stats["bookmark_count"] == 1, "bookmark was not persisted")
    _require(stats["note_count"] == 1, "note was not persisted")
    ended_sessions = _api_json(context, "GET", "/learning/sessions")
    _require(
        ended_sessions["items"][0]["ended_at"] is not None,
        "reader session did not end",
    )
    checks["learning_state_bookmark_note_and_session"] = True

    persisted_reader_state = page.evaluate(
        "() => JSON.parse(localStorage.getItem('scientific-spaces-reader-progress-v1') || '{\"items\":[]}').items[0] || null"
    )
    _require(
        persisted_reader_state is not None
        and persisted_reader_state.get("section_id") == target_section_id,
        f"reader state lost the last meaningful section: {persisted_reader_state}",
    )

    tutor_action = page.get_by_role("link", name="Ask tutor", exact=True)
    expect(tutor_action).to_be_visible()
    tutor_action.click()
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    _require(page.get_by_label("Article ID").count() == 0, "Tutor still exposes a raw Article ID input")
    tutor_return = page.get_by_role("link", name="Return to article", exact=True)
    tutor_return_href = tutor_return.get_attribute("href") or ""
    _require(
        tutor_return_href.startswith(f"/articles/{CRB_ARTICLE_ID}")
        and "from=" in tutor_return_href
        and "#" in tutor_return_href,
        f"Tutor return context is incomplete: {tutor_return_href}",
    )
    tutor_return.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    tutor_return_session = page.get_by_role("button", name="End session", exact=True)
    expect(tutor_return_session).to_be_enabled(timeout=30_000)
    tutor_return_session.click()
    expect(tutor_return_session).to_be_disabled()

    graph_action = page.get_by_role("link", name="Explore graph", exact=True)
    expect(graph_action).to_be_visible()
    graph_action.click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    graph_workspace_modes = page.get_by_role("group", name="Graph workspace view")
    expect(graph_workspace_modes.get_by_role("button", name="Explore", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    graph_workspace_modes.get_by_role("button", name="Knowledge context", exact=True).click()
    desktop_context_region = page.locator("#graph-context-workspace")
    expect(desktop_context_region).to_be_focused()
    _require_visible_focus(desktop_context_region, "desktop Knowledge Context region")
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    selected_article_map_node = page.get_by_role(
        "button", name=f"Selected Article: {CRB_TITLE}", exact=True
    )
    expect(selected_article_map_node).to_be_visible(timeout=30_000)
    desktop_canvas_box = page.locator(".knowledge-graph-canvas").bounding_box()
    desktop_map_node_box = selected_article_map_node.bounding_box()
    _require_box_inside(
        desktop_canvas_box,
        desktop_map_node_box,
        "desktop selected Graph node",
        minimum_width=80,
        minimum_height=30,
    )
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    filter_history_length = page.evaluate("history.length")
    page.get_by_role("button", name="Apply", exact=True).click()
    page.wait_for_function("() => new URLSearchParams(location.search).get('q') === 'Attention'")
    _require(
        "node_id=article%3Acrb-formula" in page.url,
        f"Graph filter replacement lost the selected Article: {page.url}",
    )
    _require(
        page.evaluate("history.length") == filter_history_length,
        "applying Graph filters created a browser history entry",
    )
    page.get_by_role("button", name="Clear", exact=True).click()
    page.wait_for_function("() => !new URLSearchParams(location.search).has('q')")
    _require(
        "node_id=article%3Acrb-formula" in page.url,
        f"clearing Graph filters lost the selected Article: {page.url}",
    )
    _require(
        page.evaluate("history.length") == filter_history_length,
        "clearing Graph filters created a browser history entry",
    )
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    graph_workspace_modes.get_by_role("button", name="Explore", exact=True).click()
    context_graph_node = (
        page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(context_graph_node).to_be_visible(timeout=30_000)
    context_graph_node.focus()
    expect(context_graph_node).to_be_focused()
    history_before_selection = page.evaluate("history.length")
    context_graph_node.press("Enter")
    expect(page.get_by_test_id("graph-selected-region")).to_be_focused()
    _require_visible_focus(page.get_by_test_id("graph-selected-region"), "desktop selected Graph region")
    _require(
        "node_id=concept%3Aattention" in page.url
        and "q=Attention" in page.url
        and "article_id=crb-formula" in page.url,
        f"Graph selection URL is incomplete: {page.url}",
    )
    _require(
        page.evaluate("history.length") == history_before_selection + 1,
        "different-node selection did not create exactly one history entry",
    )
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    desktop_detail_region = page.get_by_test_id("graph-selected-region")
    _require(
        desktop_detail_region.evaluate("node => getComputedStyle(node).overflowY") == "auto",
        "desktop selected-node inspector is not independently scrollable",
    )
    _require(
        desktop_detail_region.evaluate("node => getComputedStyle(node).position") == "sticky",
        "desktop selected-node inspector is not sticky at runtime",
    )
    desktop_detail_first_control = desktop_detail_region.get_by_role(
        "button", name="Knowledge context", exact=True
    )
    page.keyboard.press("Tab")
    expect(desktop_detail_first_control).to_be_focused()
    desktop_detail_last_control = desktop_detail_region.get_by_role(
        "link", name="Open concept quiz", exact=True
    )
    _focus_via_tab(page, desktop_detail_last_control, max_steps=40)
    expect(desktop_detail_last_control).to_be_focused()
    _require(
        desktop_detail_region.evaluate("node => node.scrollTop") > 0,
        "keyboard focus did not reveal the final control in the sticky inspector",
    )
    checks["graph_sticky_detail_keyboard_reach"] = True
    selected_history_length = page.evaluate("history.length")
    context_graph_node.click()
    _require(
        page.evaluate("history.length") == selected_history_length,
        "same-node selection created another history entry",
    )
    page.go_back()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    _require("node_id=article%3Acrb-formula" in page.url, f"Graph Back state diverged: {page.url}")
    page.go_forward()
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    _require("node_id=concept%3Aattention" in page.url, f"Graph Forward state diverged: {page.url}")

    graph_reload_url = page.url
    page.close()
    page = _new_observed_page(context, console_errors, page_errors, label="graph-reload")
    page.goto(graph_reload_url, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    page.wait_for_load_state("networkidle")
    _require(not page_errors, f"Graph deep-link reopen emitted page errors: {page_errors}")
    page.reload(wait_until="networkidle")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Graph hard reload emitted page errors: {page_errors}")
    expect(page.get_by_placeholder("Title, concept, or formula")).to_have_value("Attention")
    expect(page.get_by_test_id("learning-workflow-context")).to_contain_text(CRB_TITLE)
    checks["graph_canonical_history_and_focus"] = True
    graph_workspace_modes = page.get_by_role("group", name="Graph workspace view")
    graph_workspace_modes.get_by_role("button", name="Knowledge context", exact=True).click()
    expect(
        page.get_by_role("button", name=re.compile(r"^Selected Concept: Attention", re.I))
    ).to_be_visible(timeout=30_000)
    page.get_by_test_id("graph-view-list").click()
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    page.get_by_test_id("graph-view-map").click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible()
    graph_return = page.get_by_role("link", name="Return to article", exact=True)
    graph_return_href = graph_return.get_attribute("href") or ""
    _require(
        graph_return_href.startswith(f"/articles/{CRB_ARTICLE_ID}")
        and "from=" in graph_return_href
        and "#" in graph_return_href,
        f"Graph return context is incomplete: {graph_return_href}",
    )
    graph_return.click()
    page.wait_for_function(
        "expected => location.pathname + location.search + location.hash === expected",
        arg=graph_return_href,
        timeout=30_000,
    )
    returned_reader = page.locator("article#article-start")
    expect(returned_reader.locator(":scope > h1")).to_have_text(
        CRB_TITLE,
        timeout=30_000
    )
    expect(page.get_by_role("status").filter(has_text="Loading article")).to_have_count(0)
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    graph_return_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_return_session).to_be_enabled(timeout=30_000)
    graph_return_session.click()
    expect(graph_return_session).to_be_disabled()

    back_to_results = page.get_by_role("link", name="Back to articles", exact=True)
    back_to_results_href = back_to_results.get_attribute("href") or ""
    _require(
        back_to_results_href == "/articles?q=CRB",
        f"Article search return context is missing: {back_to_results_href}",
    )
    back_to_results.click()
    expect(page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(page.get_by_placeholder("Search title or keyword")).to_have_value("CRB")
    expect(page.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    _require("q=CRB" in page.url, f"Article search URL state was not restored: {page.url}")
    checks["integrated_learning_workflow"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    _require(
        page.get_by_role("link", name=re.compile(r"^Continue learning CRB")).count() == 0,
        "Dashboard Continue still includes a confirmed completed Article",
    )
    continue_href = f"/articles/{CRB_ARTICLE_ID}#{target_section_id}"
    expect(page.get_by_role("heading", name="Learning Activity", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="New in Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-activity")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("dashboard-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["dashboard_history"] = True
    checks["dashboard_excludes_completed_continue"] = True

    attention_state_response = context.request.put(
        f"{API_URL}/learning/state/{ATTENTION_ARTICLE_ID}",
        data={"status": "reading"},
    )
    _require(
        attention_state_response.ok,
        f"failed to prepare an in-progress Library fixture: {attention_state_response.status}",
    )
    page.get_by_role("link", name="Saved", exact=True).click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "library")
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("heading", name="Bookmarked", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Recently Read", exact=True)).to_be_visible()
    expect(page.get_by_test_id("saved-library-section-continue")).to_contain_text(ATTENTION_TITLE)
    expect(page.get_by_test_id("saved-library-section-bookmarked")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("saved-library-section-recent")).to_contain_text(CRB_TITLE)

    attention_library_item = page.get_by_test_id("saved-library-section-continue").locator(
        '[data-testid="saved-library-item"]'
    ).filter(has_text=ATTENTION_TITLE).first
    attention_library_item.get_by_role(
        "button", name=f"Add {ATTENTION_TITLE} to study session", exact=True
    ).click()
    expect(
        attention_library_item.get_by_role(
            "button", name=f"{ATTENTION_TITLE} is in study session", exact=True
        )
    ).to_be_disabled()

    page.get_by_role("button", name=re.compile(r"^Saved \(1\)$")).click()
    page.get_by_label("Sort saved learning", exact=True).select_option("progress")
    page.get_by_label("Filter saved learning", exact=True).fill("CRB")
    page.get_by_role("button", name="Filter", exact=True).click()
    expect(page).to_have_url(re.compile(r"/library\?q=CRB&view=bookmarked&sort=progress$"))
    saved_crb_link = page.get_by_test_id("saved-library-section-bookmarked").get_by_role(
        "link", name=CRB_TITLE, exact=True
    )
    expect(saved_crb_link).to_be_visible()
    saved_crb_href = saved_crb_link.get_attribute("href") or ""
    _require(
        "from=%2Flibrary%3Fq%3DCRB%26view%3Dbookmarked%26sort%3Dprogress" in saved_crb_href
        and "#" in saved_crb_href,
        f"Saved Library Reader destination is incomplete: {saved_crb_href}",
    )
    saved_crb_link.click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    saved_return = page.get_by_role("link", name="Back to saved library", exact=True)
    expect(saved_return).to_have_attribute(
        "href", "/library?q=CRB&view=bookmarked&sort=progress"
    )
    saved_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(saved_reader_session).to_be_enabled(timeout=30_000)
    saved_reader_session.click()
    expect(saved_reader_session).to_be_disabled()
    saved_return.click()
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_label("Filter saved learning", exact=True)).to_have_value("CRB")
    expect(page.get_by_label("Sort saved learning", exact=True)).to_have_value("progress")
    expect(page.get_by_role("button", name=re.compile(r"^Saved \(1\)$"))).to_have_attribute(
        "aria-pressed", "true"
    )
    session_url_before_add = page.url
    saved_crb_item = page.get_by_test_id("saved-library-section-bookmarked").locator(
        '[data-testid="saved-library-item"]'
    ).filter(has_text=CRB_TITLE).first
    saved_crb_item.get_by_role(
        "button", name=f"Add {CRB_TITLE} to study session", exact=True
    ).click()
    _require(page.url == session_url_before_add, "adding to Session discarded Saved Library URL state")
    expect(page.get_by_role("link", name="Open study session (2)", exact=True)).to_be_visible()
    page.get_by_role("link", name="Dashboard", exact=True).click()
    dashboard_session = page.get_by_test_id("dashboard-study-session")
    expect(dashboard_session).to_have_attribute("data-state", "ready")
    expect(dashboard_session).to_contain_text("2 Articles")
    expect(dashboard_session).to_contain_text(ATTENTION_TITLE)
    expect(dashboard_session).to_contain_text("1 completed · 1 remaining")
    expect(dashboard_session.get_by_role("link", name="Open session", exact=True)).to_have_attribute(
        "href", "/session"
    )
    expect(page.get_by_role("link", name="Resume focused session", exact=True)).to_be_visible()
    checks["saved_learning_library"] = True

    page.get_by_role("link", name="Resume focused session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("2 Articles")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("Completed")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("Remaining")
    expect(page.get_by_test_id("study-session-item").filter(has_text=ATTENTION_TITLE).first).to_contain_text(
        "Current · Reading"
    )
    crb_queue_item = page.get_by_test_id("study-session-item").filter(has_text=CRB_TITLE).first
    crb_queue_item.get_by_role("button", name=f"Move {CRB_TITLE} up", exact=True).click()
    crb_queue_item.get_by_role("button", name=f"Set {CRB_TITLE} as current", exact=True).click()
    expect(crb_queue_item).to_contain_text("Current · Completed")
    page.wait_for_load_state("networkidle")
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )
    _require(not page_errors, f"Study Session state update emitted page errors: {page_errors}")
    page.reload(wait_until="networkidle")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    crb_queue_item = page.get_by_test_id("study-session-item").first
    expect(crb_queue_item).to_contain_text(CRB_TITLE)
    expect(crb_queue_item).to_contain_text("Current · Completed")
    _require(not page_errors, f"Study Session hard reload emitted page errors: {page_errors}")
    page.get_by_role(
        "link", name=f"Review current Article: {CRB_TITLE}", exact=True
    ).click()
    crb_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
    expect(crb_heading).to_be_visible(timeout=30_000)
    expect(crb_heading).to_be_focused(timeout=30_000)
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 1 of 2")
    expect(session_reader_navigation.get_by_role(
        "link", name=f"Next in session: {ATTENTION_TITLE}", exact=True
    )).to_be_visible()
    completion_region = page.get_by_test_id("focused-session-completion")
    expect(completion_region).to_be_visible()
    completion_status = page.get_by_test_id("focused-session-completion-status")
    expect(completion_status).to_have_attribute("aria-live", "polite")
    expect(completion_status).to_have_attribute("aria-atomic", "true")
    crb_state_before = _api_json(context, "GET", f"/learning/state/{CRB_ARTICLE_ID}")
    mark_complete = completion_region.get_by_role("button", name="Mark Article complete", exact=True)
    expect(mark_complete).to_be_enabled(timeout=30_000)
    page.keyboard.press("Tab")
    expect(mark_complete).to_be_focused()
    mark_complete.press("Enter")
    expect(completion_region).to_have_attribute("data-state", "ready-to-advance", timeout=30_000)
    expect(completion_region).to_be_focused(timeout=30_000)
    expect(completion_status).to_contain_text("Article completion is confirmed")
    expect(completion_region.get_by_role("button", name="Article completion confirmed", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="End session", exact=True)).to_be_disabled(timeout=30_000)
    crb_state_after = _api_json(context, "GET", f"/learning/state/{CRB_ARTICLE_ID}")
    _require(
        crb_state_after["read_count"] == crb_state_before["read_count"],
        "confirming an already completed Article duplicated its completion write",
    )
    open_next = completion_region.get_by_role("button", name="Open next unfinished Article", exact=True)
    page.keyboard.press("Tab")
    expect(open_next).to_be_focused()
    open_next.press("Enter")
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 2 of 2")
    expect(
        session_reader_navigation.get_by_role(
            "link", name=f"Previous in session: {CRB_TITLE}", exact=True
        )
    ).to_be_visible()
    persisted_guided_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        persisted_guided_session["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"guided advance did not persist the next active Article: {persisted_guided_session}",
    )
    attention_state_before = _api_json(context, "GET", f"/learning/state/{ATTENTION_ARTICLE_ID}")
    completion_region = page.get_by_test_id("focused-session-completion")
    attention_mark_complete = completion_region.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(attention_mark_complete).to_be_enabled(timeout=30_000)
    completion_region.focus()
    page.keyboard.press("Tab")
    expect(attention_mark_complete).to_be_focused()
    attention_mark_complete.press("Enter")
    expect(completion_region).to_have_attribute("data-state", "ready-to-advance", timeout=30_000)
    expect(completion_region).to_be_focused(timeout=30_000)
    attention_state_after = _api_json(context, "GET", f"/learning/state/{ATTENTION_ARTICLE_ID}")
    _require(
        attention_state_after["status"] == "completed"
        and attention_state_after["read_count"] == attention_state_before["read_count"] + 1,
        f"Attention completion was not persisted exactly once: {attention_state_after}",
    )
    terminal_url = page.url
    terminal_action = completion_region.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    page.keyboard.press("Tab")
    expect(terminal_action).to_be_focused()
    terminal_action.press("Enter")
    expect(completion_region).to_have_attribute("data-state", "complete", timeout=30_000)
    expect(completion_region).to_be_focused(timeout=30_000)
    expect(completion_region).to_contain_text("Every queued Article is confirmed complete")
    _require(page.url == terminal_url, "terminal completion navigated without an unfinished Article")
    completion_region.get_by_role("link", name="Review completed session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("2")
    expect(page.get_by_test_id("study-session-complete")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("study-session-item")).to_have_count(2)
    checks["focused_session_completion_and_guided_advance"] = True
    checks["focused_session_duplicate_safe_completion"] = True
    checks["focused_session_retained_terminal_queue"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    dashboard_session = page.get_by_test_id("dashboard-study-session")
    expect(dashboard_session).to_contain_text("2 completed · 0 remaining", timeout=30_000)
    expect(dashboard_session).to_contain_text("Session complete")
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    dashboard_session.get_by_role("link", name="Review completed session", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    crb_queue_item = page.get_by_test_id("study-session-item").filter(has_text=CRB_TITLE).first
    crb_queue_item.get_by_role(
        "button", name=f"Remove {CRB_TITLE} from session", exact=True
    ).click()
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("1 Article")
    page.get_by_role("button", name="Clear queue", exact=True).click()
    page.get_by_role("button", name="Confirm clear queue", exact=True).click()
    expect(page.get_by_test_id("study-session-empty")).to_be_visible()
    checks["focused_study_session_workflow"] = True

    page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "empty"
    )
    checks["dashboard_focused_session"] = True
    page.goto(f"{FRONTEND_URL}{continue_href}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    page.wait_for_function("() => window.scrollY > 0")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-size", "large")
    expect(page.locator("article.reader-workspace")).to_have_attribute("data-reader-width", "wide")
    expect(page.get_by_test_id("article-outline").locator('[aria-current="location"]')).to_be_visible()
    resumed_end_session = page.get_by_role("button", name="End session", exact=True)
    expect(resumed_end_session).to_be_enabled(timeout=30_000)
    resumed_end_session.click()
    expect(resumed_end_session).to_be_disabled()
    checks["continue_reading_resume"] = True

    page.get_by_role("link", name="Graph", exact=True).click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    expect(page.get_by_text(re.compile(r"^Showing \d+-\d+ of \d+$"))).to_be_visible(timeout=30_000)
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Showing 1-\d+ of \d+$"))).to_be_visible(timeout=30_000)
    graph_node = (
        page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(graph_node).to_be_visible()
    graph_node.click()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    concept_study_set = page.get_by_test_id("concept-study-set")
    expect(concept_study_set).to_have_attribute("data-state", "ready")
    expect(concept_study_set.get_by_role("heading", name="Concept Study Set", exact=True)).to_be_visible()
    expect(concept_study_set).to_contain_text("not a complete or recommended learning sequence")
    expect(concept_study_set.get_by_test_id("concept-study-article")).to_have_count(1)
    expect(concept_study_set.get_by_test_id("concept-study-article").first).to_contain_text(
        ATTENTION_TITLE
    )
    for fact_label in ("Source records", "Returned", "Eligible", "Duplicates", "Invalid", "Omitted"):
        expect(concept_study_set.locator("dt").filter(has_text=fact_label)).to_be_visible()
    _require(
        ATTENTION_CONCEPT_ID not in concept_study_set.inner_text(),
        "Concept Study Set exposes a raw Graph node identifier",
    )
    concept_study_set.get_by_role("button", name="Go to Knowledge Context", exact=True).click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Inspect selected", exact=True).click()
    expect(page.get_by_test_id("concept-study-set")).to_be_visible()
    checks["graph_context_mode_and_inspect_selected"] = True

    concept_article_link = concept_study_set.get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    expect(concept_article_link).to_have_attribute(
        "href",
        f"/articles/{ATTENTION_ARTICLE_ID}?"
        + urlencode({"from": ATTENTION_CONCEPT_QUERY_RETURN}),
    )
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-023-isolated-concept-reader",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-08-31T04:00:00+00:00",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    _focus_via_tab(page, concept_article_link)
    concept_article_href = str(concept_article_link.get_attribute("href") or "")
    concept_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=concept_article_href,
        timeout=30_000,
    )
    concept_reader_heading = page.locator("article#article-start > h1")
    expect(concept_reader_heading).to_have_text(ATTENTION_TITLE, timeout=30_000)
    expect(concept_reader_heading).to_be_focused()
    _require_visible_focus(concept_reader_heading, "Concept Study Set Reader heading")
    reader_concept_return = page.get_by_role("link", name="Back to concept", exact=True).first
    expect(reader_concept_return).to_have_attribute("href", ATTENTION_CONCEPT_QUERY_RETURN)
    _focus_via_tab(page, reader_concept_return)
    reader_concept_return.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=ATTENTION_CONCEPT_QUERY_RETURN,
        timeout=30_000,
    )
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    returned_concept_study_set = page.get_by_test_id("concept-study-set")
    expect(returned_concept_study_set).to_be_visible(timeout=30_000)
    returned_concept_article_link = returned_concept_study_set.get_by_role(
        "link", name=ATTENTION_TITLE, exact=True
    )
    expect(returned_concept_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(
        returned_concept_article_link,
        "returned Concept Study Set Article action",
    )

    concept_ask_payloads: list[dict[str, object]] = []

    def fulfill_concept_explain(route) -> None:
        concept_ask_payloads.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "answer": "## Attention\n\nLocal Article evidence explains the selected Concept.",
                    "mode": "explain",
                    "sources": [
                        {
                            "source_type": "article_chunk",
                            "source_id": f"{ATTENTION_ARTICLE_ID}:0",
                            "title": ATTENTION_TITLE,
                            "url": "https://spaces.ac.cn/archives/12345",
                            "section_title": "Attention",
                            "chunk_index": 0,
                            "evidence": None,
                            "metadata": {"article_id": ATTENTION_ARTICLE_ID},
                        }
                    ],
                    "graph_context": {"nodes": [], "edges": []},
                    "zotero_context": [],
                    "follow_up_questions": [],
                    "refusal_reason": None,
                    "selection_summary": None,
                    "evidence_summary": None,
                },
                ensure_ascii=False,
            ),
        )

    page.route(re.compile(r".*/tutor/ask$"), fulfill_concept_explain, times=1)
    concept_explain_link = page.get_by_test_id("concept-study-set").get_by_role(
        "link", name="Explain concept", exact=True
    )
    _focus_via_tab(page, concept_explain_link)
    concept_explain_link.press("Enter")
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text("attention")
    expect(page.get_by_role("button", name="Explain", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_label("Question")).to_have_value(
        "Explain attention using intuition, mathematics, and cited local evidence."
    )
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    concept_return = page.get_by_role("link", name="Return to concept", exact=True)
    expect(concept_return).to_have_attribute("href", ATTENTION_CONCEPT_RETURN)
    _require(not concept_ask_payloads, "Concept Explain auto-submitted before user action")
    page.get_by_role("button", name="Quiz", exact=True).click()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text(
        "Quiz uses the selected local Article and concept topic."
    )
    expect(page.get_by_text("Concept topic", exact=True)).to_be_visible()
    page.get_by_role("button", name="Explain", exact=True).click()
    expect(page.get_by_test_id("concept-learning-context")).to_contain_text(
        "Graph context supplements the selected local Article evidence."
    )
    concept_submit = page.get_by_role("button", name="Ask tutor", exact=True)
    _focus_via_tab(page, concept_submit)
    concept_submit.press("Enter")
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    _require(
        concept_ask_payloads
        == [
            {
                "question": "Explain attention using intuition, mathematics, and cited local evidence.",
                "mode": "explain",
                "article_id": ATTENTION_ARTICLE_ID,
                "node_id": ATTENTION_CONCEPT_ID,
                "top_k": 5,
                "include_graph_context": True,
                "include_zotero_context": True,
            }
        ],
        f"Concept Explain payload is incorrect: {concept_ask_payloads}",
    )
    _focus_via_tab(page, concept_return)
    concept_return.press("Enter")
    expect(page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)

    concept_quiz_payloads: list[dict[str, object]] = []

    def fulfill_concept_quiz(route) -> None:
        concept_quiz_payloads.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "questions": [
                        {
                            "question": "What does Attention select?",
                            "options": ["Relevant local evidence", "Unbounded external data"],
                            "correct_answer": "Relevant local evidence",
                            "explanation": "The local Article describes evidence-weighted selection.",
                            "sources": [
                                {
                                    "source_type": "article_chunk",
                                    "source_id": f"{ATTENTION_ARTICLE_ID}:0",
                                    "title": ATTENTION_TITLE,
                                    "url": "https://spaces.ac.cn/archives/12345",
                                    "section_title": "Attention",
                                    "chunk_index": 0,
                                    "evidence": None,
                                    "metadata": {"article_id": ATTENTION_ARTICLE_ID},
                                }
                            ],
                        }
                    ],
                    "total": 1,
                },
                ensure_ascii=False,
            ),
        )

    page.route(re.compile(r".*/tutor/quiz$"), fulfill_concept_quiz, times=1)
    concept_quiz_link = page.get_by_test_id("concept-study-set").get_by_role(
        "link", name="Open concept quiz", exact=True
    )
    _focus_via_tab(page, concept_quiz_link)
    concept_quiz_link.press("Enter")
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Quiz", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_label("Prompt")).to_have_value("attention")
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    concept_return = page.get_by_role("link", name="Return to concept", exact=True)
    expect(concept_return).to_have_attribute("href", ATTENTION_CONCEPT_RETURN)
    _require(not concept_quiz_payloads, "Concept Quiz auto-submitted before user action")
    concept_quiz_submit = page.get_by_role("button", name="Generate quiz", exact=True)
    _focus_via_tab(page, concept_quiz_submit)
    concept_quiz_submit.press("Enter")
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    _require(
        concept_quiz_payloads
        == [
            {
                "article_id": ATTENTION_ARTICLE_ID,
                "node_id": ATTENTION_CONCEPT_ID,
                "num_questions": 3,
                "topic": "attention",
            }
        ],
        f"Concept Quiz payload is incorrect: {concept_quiz_payloads}",
    )
    _focus_via_tab(page, concept_return)
    concept_return.press("Enter")
    expect(page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)

    page.evaluate(
        """
        () => {
          window.__p3023SessionWrites = 0;
          const originalSetItem = Storage.prototype.setItem;
          Storage.prototype.setItem = function (key, value) {
            if (key === "scientific-spaces-study-session-v1") {
              window.__p3023SessionWrites += 1;
            }
            return originalSetItem.call(this, key, value);
          };
        }
        """
    )
    study_set = page.get_by_test_id("concept-study-set")
    bulk_add = study_set.get_by_role("button", name="Add eligible Articles", exact=True)
    _focus_via_tab(page, bulk_add)
    bulk_add.press("Enter")
    expect(study_set.get_by_role("status").last).to_contain_text(
        "1 added; 0 already present; 0 invalid; 0 omitted by capacity."
    )
    _require(
        page.evaluate("window.__p3023SessionWrites") == 1,
        "Concept Study Set bulk append did not use exactly one storage write",
    )
    persisted_concept_session = page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in persisted_concept_session["items"]]
        == [ATTENTION_ARTICLE_ID]
        and persisted_concept_session["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"Concept Study Set saved the wrong Session state: {persisted_concept_session}",
    )
    bulk_add.press("Enter")
    expect(study_set.get_by_role("status").last).to_contain_text(
        "0 added; 1 already present; 0 invalid; 0 omitted by capacity."
    )
    _require(
        page.evaluate("window.__p3023SessionWrites") == 1,
        "idempotent Concept Study Set append performed an extra storage write",
    )
    page.evaluate(
        """
        () => {
          localStorage.removeItem("scientific-spaces-study-session-v1");
          window.dispatchEvent(new Event("scientific-spaces-study-session-change"));
        }
        """
    )
    checks["concept_study_set_workflow"] = True
    checks["concept_reader_and_tutor_round_trip"] = True
    checks["concept_tutor_explicit_payloads"] = True
    checks["concept_study_set_session_append"] = True
    checks["concept_study_set_keyboard_focus"] = True

    concept_graph_return = page.evaluate(
        """
        () => {
          const source = new URLSearchParams(location.search);
          const target = new URLSearchParams();
          const nodeId = source.get("node_id");
          const query = source.get("q");
          if (nodeId) target.set("node_id", nodeId);
          if (query) target.set("q", query);
          return `/graph?${target.toString()}`;
        }
        """
    )
    provenance_article_links = page.get_by_role("link", name="Open article", exact=True)
    _require(
        provenance_article_links.count() > 0,
        "Concept provenance did not expose an Article link",
    )
    for index in range(provenance_article_links.count()):
        provenance_href = provenance_article_links.nth(index).get_attribute("href") or ""
        provenance_from = parse_qs(urlparse(provenance_href).query).get("from", [])
        _require(
            provenance_from == [concept_graph_return],
            f"Concept provenance Article link lost Graph context: {provenance_href}",
        )
    provenance_article_link = provenance_article_links.first
    provenance_article_href = str(provenance_article_link.get_attribute("href") or "")
    _focus_via_tab(page, provenance_article_link)
    provenance_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=provenance_article_href,
        timeout=30_000,
    )
    provenance_reader = page.locator("article#article-start")
    provenance_reader_heading = provenance_reader.locator(":scope > h1")
    expect(provenance_reader_heading).to_be_visible(timeout=30_000)
    expect(provenance_reader_heading).to_be_focused()
    _require_visible_focus(provenance_reader_heading, "provenance-origin Reader heading")
    provenance_return = page.get_by_role("link", name="Back to concept", exact=True).first
    expect(provenance_return).to_have_attribute("href", concept_graph_return)
    provenance_session = page.get_by_role("button", name="End session", exact=True)
    expect(provenance_session).to_be_enabled(timeout=30_000)
    provenance_session.click()
    expect(provenance_session).to_be_disabled()
    _focus_via_tab(page, provenance_return)
    provenance_return.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=concept_graph_return,
        timeout=30_000,
    )
    returned_provenance_link = page.locator(
        '[data-graph-article-focus="provenance-0"]'
    )
    expect(returned_provenance_link).to_be_focused(timeout=30_000)
    _require_visible_focus(returned_provenance_link, "returned provenance Article action")
    checks["graph_provenance_article_return_context"] = True

    page.evaluate(
        """
        ([key, value]) => sessionStorage.setItem(key, JSON.stringify(value))
        """,
        [
            "scientific-spaces:graph-article-return-focus:v1",
            {
                "articleId": ATTENTION_ARTICLE_ID,
                "focusTarget": "provenance-9",
                "returnTo": concept_graph_return,
            },
        ],
    )
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    missing_origin_region = page.get_by_test_id("graph-selected-region")
    expect(missing_origin_region).to_be_visible(timeout=30_000)
    expect(missing_origin_region).to_be_focused(timeout=30_000)
    _require_visible_focus(missing_origin_region, "missing provenance origin fallback")
    checks["graph_missing_exact_origin_focus_fallback"] = True

    page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    concept_context_region = page.locator("#graph-context-workspace")
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("graph-map-counts")).to_contain_text("relationships")
    graph_edge = page.locator('.react-flow__edge[tabindex="0"]').first
    expect(graph_edge).to_be_visible(timeout=30_000)
    graph_edge.focus()
    expect(graph_edge).to_be_focused()
    graph_edge.press("Control+k")
    svg_opener_search = page.get_by_test_id("global-search-dialog")
    expect(svg_opener_search.get_by_label("Search library")).to_be_focused()
    svg_opener_search.get_by_label("Search library").press("Escape")
    expect(svg_opener_search).to_have_count(0)
    expect(graph_edge).to_be_focused()
    checks["shell_svg_opener_focus_restoration"] = True
    graph_article_node = page.get_by_role("button", name=re.compile(r"^Article: ")).first
    expect(graph_article_node).to_be_visible()
    graph_article_node.press("Enter")
    page.wait_for_function("() => new URL(location.href).searchParams.get('node_id')?.startsWith('article:')")
    _require_visible_focus(concept_context_region, "desktop Context region after map selection")
    expect(page.get_by_role("button", name=re.compile(r"^Selected Article: ")).first).to_be_visible(
        timeout=30_000
    )
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name="Inspect selected", exact=True).click()
    graph_article_link = page.get_by_role("link", name="Open article").first
    expect(graph_article_link).to_be_visible()
    graph_article_return = page.evaluate(
        """
        () => {
          const source = new URLSearchParams(location.search);
          const target = new URLSearchParams();
          const nodeId = source.get("node_id");
          const query = source.get("q");
          if (nodeId) target.set("node_id", nodeId);
          if (query) target.set("q", query);
          return target.size ? `/graph?${target.toString()}` : "/graph";
        }
        """
    )
    graph_article_href = str(graph_article_link.get_attribute("href") or "")
    parsed_graph_article_href = urlparse(graph_article_href)
    _require(
        parsed_graph_article_href.path.startswith("/articles/")
        and parse_qs(parsed_graph_article_href.query).get("from") == [graph_article_return],
        "Graph Article deep link is invalid",
    )
    graph_browser_origin = page.evaluate("location.pathname + location.search")
    graph_history_before_article = page.evaluate("history.length")
    graph_article_link.focus()
    expect(graph_article_link).to_be_focused()
    graph_article_link.press("Enter")
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    graph_reader = page.locator("article#article-start")
    graph_reader_heading = graph_reader.locator(":scope > h1")
    expect(graph_reader_heading).to_be_visible(timeout=30_000)
    expect(graph_reader_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(graph_reader_heading, "Graph-origin Reader heading")
    _require(
        page.evaluate("history.length") == graph_history_before_article + 1,
        "Graph Article navigation did not create exactly one history entry",
    )
    expect(page.get_by_role("status").filter(has_text="Loading article")).to_have_count(0)
    graph_reader_return = page.get_by_role("link", name="Return to graph", exact=True)
    expect(graph_reader_return).to_have_attribute("href", graph_article_return)
    graph_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_reader_session).to_be_enabled(timeout=30_000)
    graph_reader_session.click()
    expect(graph_reader_session).to_be_disabled()
    page.go_back()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_browser_origin,
        timeout=30_000,
    )
    browser_back_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(browser_back_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(browser_back_article_link, "browser-Back Graph Article action")
    _require(
        page.evaluate("history.length") == graph_history_before_article + 1,
        "browser Back changed Graph-Reader history length",
    )
    page.go_forward()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    forward_reader_heading = page.locator("article#article-start > h1")
    expect(forward_reader_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(forward_reader_heading, "browser-Forward Reader heading")
    forward_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(forward_reader_session).to_be_enabled(timeout=30_000)
    forward_reader_session.click()
    expect(forward_reader_session).to_be_disabled()
    page.go_back()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_browser_origin,
        timeout=30_000,
    )
    repeated_back_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(repeated_back_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(repeated_back_article_link, "repeated browser-Back Graph Article action")
    page.go_forward()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_href,
        timeout=30_000,
    )
    repeated_forward_heading = page.locator("article#article-start > h1")
    expect(repeated_forward_heading).to_be_focused(timeout=30_000)
    _require_visible_focus(repeated_forward_heading, "repeated browser-Forward Reader heading")
    repeated_forward_session = page.get_by_role("button", name="End session", exact=True)
    expect(repeated_forward_session).to_be_enabled(timeout=30_000)
    repeated_forward_session.click()
    expect(repeated_forward_session).to_be_disabled()
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.locator("article#article-start > h1")).to_be_visible(timeout=30_000)
    graph_reader_return = page.get_by_role("link", name="Return to graph", exact=True)
    expect(graph_reader_return).to_have_attribute("href", graph_article_return)
    graph_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(graph_reader_session).to_be_enabled(timeout=30_000)
    graph_reader_session.click()
    expect(graph_reader_session).to_be_disabled()
    graph_reader_return.click()
    page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_article_return,
        timeout=30_000,
    )
    returned_graph_article_link = page.locator(
        '[data-graph-article-focus="selected-node"]'
    )
    expect(returned_graph_article_link).to_be_visible(timeout=30_000)
    expect(returned_graph_article_link).to_be_focused(timeout=30_000)
    _require_visible_focus(returned_graph_article_link, "restored Graph Article action")
    checks["graph_reader_exact_round_trip"] = True
    checks["graph_reader_keyboard_focus"] = True
    checks["graph_reader_reload_return"] = True
    page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    page.get_by_test_id("graph-view-list").click()
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    list_selection_url = page.url
    related_context_node = page.get_by_test_id("graph-context-list").locator("button").first
    expect(related_context_node).to_be_visible(timeout=30_000)
    related_context_node.press("Enter")
    page.wait_for_function("previous => location.href !== previous", arg=list_selection_url)
    _require_visible_focus(concept_context_region, "desktop Context region after list selection")
    expect(
        page.get_by_role("group", name="Graph workspace view").get_by_role(
            "button", name="Knowledge context", exact=True
        )
    ).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible(
        timeout=30_000
    )
    page.get_by_test_id("graph-view-map").click()
    expect(page.get_by_test_id("graph-visualization")).to_be_visible()
    checks["knowledge_graph"] = True
    checks["visual_knowledge_explorer"] = True

    page.get_by_role("link", name="Tutor", exact=True).click()
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    page.get_by_label("Search articles").fill("CRB")
    page.get_by_role("button", name="Search library", exact=True).click()
    page.get_by_role("button", name=f"Select {CRB_TITLE}", exact=True).click()
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    _require(page.get_by_label("Article ID").count() == 0, "Tutor primary flow exposes Article ID")

    markdown_response = {
        "answer": (
            "## Core idea\n\n"
            "**Fisher information** controls the local variance scale $I(\\theta)$.\n\n"
            "$$\\operatorname{Var}(\\hat\\theta) \\ge I(\\theta)^{-1}$$\n\n"
            "```python\nbound = 1 / fisher_information\n```"
        ),
        "mode": "explain",
        "sources": [
            {
                "source_type": "article_chunk",
                "source_id": f"{CRB_ARTICLE_ID}:0",
                "title": CRB_TITLE,
                "url": "https://spaces.ac.cn/archives/6508",
                "section_title": "推导步骤",
                "chunk_index": 0,
                "evidence": None,
                "metadata": {"article_id": CRB_ARTICLE_ID},
            }
        ],
        "graph_context": {"nodes": [], "edges": []},
        "zotero_context": [],
        "follow_up_questions": ["How is the lower bound derived?"],
        "refusal_reason": None,
        "selection_summary": {
            "candidate_count": 1,
            "selected_article_count": 1,
            "selected_chunk_count": 1,
            "graph_node_count": 0,
            "graph_edge_count": 0,
            "graph_latency_ms": None,
            "graph_error_code": None,
            "context_character_count": 320,
            "estimated_token_count": 80,
            "truncated": False,
            "supplement_omitted_count": 0,
        },
        "evidence_summary": {
            "source_count": 1,
            "article_count": 1,
            "has_formula_evidence": True,
            "has_definition_evidence": True,
            "has_answerable_evidence": True,
            "source_schema_valid": True,
            "unsupported_or_out_of_scope": False,
            "refusal_reason": None,
        },
    }
    tutor_workflow_query = urlencode(
        {
            "article_id": CRB_ARTICLE_ID,
            "article_title": CRB_TITLE,
            "return_to": f"/articles/{CRB_ARTICLE_ID}",
        }
    )
    stale_markdown_response = {
        **markdown_response,
        "answer": "P3-027 stale Article response must never be displayed.",
    }
    stale_activity_posts: list[str] = []

    def track_stale_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            stale_activity_posts.append(request.url)

    page.on("request", track_stale_activity)
    _install_fetch_response_gate(page, "/tutor/ask")
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(stale_markdown_response, ensure_ascii=False),
        ),
        times=1,
    )
    page.get_by_label("Question").fill("Stale Article request that must not publish")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_test_id("tutor-request-status")).to_have_text(
        "Tutor request in progress."
    )
    page.get_by_label("Search articles").fill("Attention")
    page.get_by_role("button", name="Search library", exact=True).click()
    page.get_by_role("button", name=f"Select {ATTENTION_TITLE}", exact=True).click()
    expect(page.get_by_test_id("tutor-selected-article")).to_contain_text(ATTENTION_TITLE)
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-result").count() == 0
        and page.get_by_text("P3-027 stale Article response must never be displayed.").count() == 0,
        "stale Tutor response published after the selected Article changed",
    )
    _require(
        not stale_activity_posts,
        f"stale Tutor response wrote recent activity: {stale_activity_posts}",
    )
    _restore_fetch_response_gate(page)
    page.get_by_label("Search articles").fill("CRB")
    page.get_by_role("button", name="Search library", exact=True).click()
    page.get_by_role("button", name=f"Select {CRB_TITLE}", exact=True).click()
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    checks["tutor_article_request_and_activity_ownership"] = True

    page.get_by_text("Advanced context", exact=True).click()
    page.get_by_label("Graph concept key").fill("concept:crb")
    stale_failure_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/ask")
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional stale Tutor failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    page.get_by_label("Question").fill("Updated prompt after stale failure submission")
    page.get_by_label("Graph concept key").fill("concept:attention")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-error").count() == 0,
        "stale Tutor failure published after prompt and Graph context changed",
    )
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    stale_failure_console = console_errors[stale_failure_console_start:]
    _require(
        len(stale_failure_console) == 1 and "status of 503" in stale_failure_console[0],
        f"unexpected stale Tutor failure console output: {stale_failure_console}",
    )
    del console_errors[stale_failure_console_start:]
    _restore_fetch_response_gate(page)
    page.get_by_label("Graph concept key").fill("")

    stale_quiz_response = {
        "questions": [
            {
                "question": "P3-027 stale Quiz must never be displayed",
                "options": ["Stale", "Current"],
                "correct_answer": "Current",
                "explanation": "This delayed Quiz belongs to an invalidated mode.",
                "sources": [],
            }
        ],
        "total": 1,
    }
    page.get_by_role("button", name="Quiz", exact=True).click()
    page.get_by_label("Prompt").fill("stale quiz")
    _install_fetch_response_gate(page, "/tutor/quiz")
    page.route(
        re.compile(r".*/tutor/quiz$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(stale_quiz_response),
        ),
        times=1,
    )
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    page.get_by_role("button", name="Explain", exact=True).click()
    _release_fetch_response_gate(page)
    _require(
        page.get_by_test_id("tutor-quiz-workspace").count() == 0
        and page.get_by_text("P3-027 stale Quiz must never be displayed").count() == 0,
        "stale Quiz published after the Tutor mode changed",
    )
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    _restore_fetch_response_gate(page)
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    checks["tutor_prompt_node_failure_and_mode_quiz_ownership"] = True

    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(markdown_response, ensure_ascii=False),
        ),
        times=1,
    )
    tutor_follow_up_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/sessions", method="POST")
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional delayed Tutor activity failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-result")).to_be_focused()
    expect(page.get_by_test_id("tutor-request-status")).to_have_text("Tutor answer ready.")
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("tutor-answer").locator("strong")).to_contain_text("Fisher information")
    expect(page.get_by_test_id("tutor-answer").locator(".katex").first).to_be_visible()
    expect(page.get_by_test_id("tutor-answer").locator("code")).to_contain_text("fisher_information")
    tutor_article_link = page.get_by_role("link", name="Open local article").first
    expect(tutor_article_link).to_be_visible()
    _require(
        tutor_article_link.get_attribute("href") == f"/articles/{CRB_ARTICLE_ID}",
        "Tutor Article deep link is invalid",
    )
    page.get_by_role("button", name="How is the lower bound derived?", exact=True).click()
    expect(page.get_by_label("Question")).to_have_value("How is the lower bound derived?")
    expect(page.get_by_label("Question")).to_be_focused()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible()
    _release_fetch_response_gate(page)
    expect(
        page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    tutor_follow_up_console = console_errors[tutor_follow_up_console_start:]
    _require(
        len(tutor_follow_up_console) == 1
        and "status of 503" in tutor_follow_up_console[0],
        f"unexpected delayed Tutor activity failure console output: {tutor_follow_up_console}",
    )
    del console_errors[tutor_follow_up_console_start:]
    _restore_fetch_response_gate(page)
    checks["tutor_explain"] = True
    checks["guided_tutor_article_markdown_and_follow_up"] = True
    checks["tutor_follow_up_preserves_activity_failure"] = True
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-activity").get_by_role("alert")).to_have_count(0)
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    checks["tutor_follow_up_submission_clears_previous_activity_failure"] = True

    page.get_by_role("button", name="Derive", exact=True).click()
    page.get_by_label("Question").fill("Activity completion that will become stale")
    stale_activity_console_start = len(console_errors)
    _install_fetch_response_gate(page, "/tutor/sessions", method="POST")
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional stale Tutor activity failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    page.get_by_label("Question").fill("Superseding ordinary prompt edit")
    _release_fetch_response_gate(page)
    _require(
        page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        ).count()
        == 0,
        "superseded Tutor activity failure published after an ordinary prompt edit",
    )
    stale_activity_console = console_errors[stale_activity_console_start:]
    _require(
        len(stale_activity_console) == 1
        and "status of 503" in stale_activity_console[0],
        f"unexpected stale Tutor activity console output: {stale_activity_console}",
    )
    del console_errors[stale_activity_console_start:]
    _restore_fetch_response_gate(page)
    checks["tutor_superseded_activity_completion_is_silent"] = True

    page.get_by_label("Question").fill("根据文章公式推导 CRB 下界")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-activity")).to_contain_text(CRB_TITLE, timeout=30_000)
    expect(page.get_by_test_id("tutor-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["tutor_derive"] = True

    page.get_by_role("button", name="Quiz", exact=True).click()
    page.get_by_label("Prompt").fill("CRB")
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-quiz-workspace")).to_be_focused()
    expect(page.get_by_test_id("tutor-request-status")).to_contain_text("Quiz ready with")
    tutor_mode_group = page.get_by_test_id("tutor-mode-group")
    expect(tutor_mode_group.locator("legend")).to_have_text("Study mode")
    _require(
        tutor_mode_group.locator('button[aria-pressed]').count() == 5,
        "Tutor mode group does not expose five pressed buttons",
    )
    _require(
        tutor_mode_group.locator('button[aria-pressed="true"]').count() == 1,
        "Tutor mode group does not expose exactly one active mode",
    )
    _require(page.get_by_role("tablist").count() == 0, "Tutor mode exposes a partial tab pattern")
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz disclosed answers before submission")
    quiz_articles = page.get_by_test_id("tutor-quiz-workspace").locator("article")
    _require(quiz_articles.count() >= 2, "Quiz did not return enough grounded questions for choices")
    for quiz_index in range(quiz_articles.count()):
        quiz_articles.nth(quiz_index).locator('input[type="radio"]').first.check()
    page.get_by_role("button", name="Check answers", exact=True).click()
    expect(page.get_by_test_id("tutor-quiz-score")).to_be_visible()
    expect(page.get_by_test_id("tutor-quiz-score")).to_be_focused()
    expect(page.get_by_test_id("tutor-quiz-score")).to_have_attribute("role", "status")
    expect(page.get_by_test_id("tutor-quiz-score")).to_have_attribute("aria-live", "polite")
    expect(page.get_by_text(re.compile(r"^Correct answer:")).first).to_be_visible()
    expect(page.get_by_role("heading", name="题目来源", exact=True).first).to_be_visible()
    page.get_by_role("button", name="Try again", exact=True).click()
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz retry retained answer disclosure")
    expect(quiz_articles.first.locator('input[type="radio"]').first).to_be_focused()
    checks["tutor_quiz"] = True
    checks["tutor_quiz_hidden_review_and_score"] = True
    checks["tutor_accessible_result_and_quiz_focus"] = True

    page.get_by_role("button", name="Research", exact=True).click()
    page.get_by_label("Question").fill("基于本地资料给出 CRB 研究方向")
    page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-017 session write failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name=re.compile(r"^(Answer|Refusal)$"))).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_role("heading", name="Research 模式范围", exact=True)).to_be_visible()
    expect(page.get_by_text("The answer is ready, but recent activity could not be updated.", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("heading", name=re.compile(r"^(Answer|Refusal)$"))).to_be_visible()
    checks["tutor_research"] = True
    checks["tutor_session_failure_isolation"] = True

    page.get_by_role("button", name="Q&A", exact=True).click()
    expect(page.get_by_test_id("tutor-activity").get_by_role("alert")).to_have_count(0)
    checks["tutor_context_change_clears_previous_activity_failure"] = True
    page.get_by_label("Question").fill("Trigger one controlled Tutor failure")
    tutor_error_console_start = len(console_errors)
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional Tutor request failure"}',
        ),
        times=1,
    )
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_test_id("tutor-error")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("tutor-error")).to_be_focused()
    expect(page.get_by_test_id("guided-tutor-workspace")).to_have_attribute("aria-busy", "false")
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({**markdown_response, "mode": "qa"}, ensure_ascii=False),
        ),
        times=1,
    )
    page.get_by_role("button", name="Retry request", exact=True).press("Enter")
    expect(page.get_by_test_id("tutor-result")).to_be_focused(timeout=30_000)
    tutor_error_console = console_errors[tutor_error_console_start:]
    _require(
        len(tutor_error_console) == 1 and "status of 503" in tutor_error_console[0],
        f"unexpected controlled Tutor failure console output: {tutor_error_console}",
    )
    del console_errors[tutor_error_console_start:]
    checks["tutor_accessible_error_and_retry_focus"] = True

    _require(not page_errors, f"primary workflow emitted page errors: {page_errors}")
    page.close()

    activity_order_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-activity-read-order"
    )
    activity_order_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(activity_order_page)
    _install_fetch_response_gate(activity_order_page, "/tutor/sessions", method="GET")
    activity_order_page.get_by_role("link", name="Tutor", exact=True).click()
    expect(
        activity_order_page.get_by_role(
            "heading", name="AI Research Tutor", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _wait_for_fetch_response_gate_pending(activity_order_page)
    activity_order_console_start = len(console_errors)
    activity_order_page.route(
        re.compile(r".*/tutor/sessions$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional activity ordering failure"}',
        ),
        times=1,
    )
    activity_order_page.get_by_label("Question").fill(
        "Keep the newer activity failure after an older read completes"
    )
    activity_order_page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(
        activity_order_page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible(timeout=30_000)
    _release_fetch_response_gate(activity_order_page)
    expect(
        activity_order_page.get_by_text(
            "The answer is ready, but recent activity could not be updated.", exact=True
        )
    ).to_be_visible()
    activity_order_console = console_errors[activity_order_console_start:]
    _require(
        len(activity_order_console) == 1
        and "status of 503" in activity_order_console[0],
        f"unexpected Tutor activity ordering console output: {activity_order_console}",
    )
    del console_errors[activity_order_console_start:]
    _restore_fetch_response_gate(activity_order_page)
    checks["tutor_newer_activity_failure_supersedes_older_read"] = True
    activity_order_page.close()

    route_context_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-route-context-removal"
    )
    route_context_page.goto(
        f"{FRONTEND_URL}/tutor?{tutor_workflow_query}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(route_context_page)
    expect(route_context_page.get_by_test_id("tutor-selected-article")).to_contain_text(
        CRB_TITLE
    )
    same_route_activity_posts: list[str] = []

    def track_same_route_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            same_route_activity_posts.append(request.url)

    route_context_page.on("request", track_same_route_activity)
    _install_fetch_response_gate(route_context_page, "/tutor/ask")
    route_context_page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **markdown_response,
                    "answer": "P3-027 stale same-route response must not publish.",
                },
                ensure_ascii=False,
            ),
        ),
        times=1,
    )
    route_context_page.get_by_label("Question").fill(
        "Pending response before same-route context removal"
    )
    route_context_page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(route_context_page.get_by_test_id("guided-tutor-workspace")).to_have_attribute(
        "aria-busy", "true"
    )
    route_context_page.get_by_role("link", name="Tutor", exact=True).click()
    expect(route_context_page).to_have_url(f"{FRONTEND_URL}/tutor")
    expect(route_context_page.get_by_test_id("tutor-selected-article")).to_have_count(0)
    expect(route_context_page.get_by_label("Question")).to_have_value("")
    _release_fetch_response_gate(route_context_page)
    expect(route_context_page.get_by_test_id("tutor-result")).to_have_count(0)
    expect(route_context_page.get_by_test_id("tutor-error")).to_have_count(0)
    _require(
        route_context_page.get_by_text(
            "P3-027 stale same-route response must not publish.", exact=True
        ).count()
        == 0,
        "same-route context removal published a stale Tutor response",
    )
    _require(
        not same_route_activity_posts,
        f"same-route context removal wrote stale Tutor activity: {same_route_activity_posts}",
    )
    _restore_fetch_response_gate(route_context_page)
    checks["tutor_route_context_removal"] = True
    route_context_page.close()

    unmount_page = _new_observed_page(
        context, console_errors, page_errors, label="tutor-pending-navigation"
    )
    pending_navigation_activity: list[str] = []

    def track_pending_navigation_activity(request) -> None:
        if request.method == "POST" and urlparse(request.url).path == "/tutor/sessions":
            pending_navigation_activity.append(request.url)

    unmount_page.on("request", track_pending_navigation_activity)
    unmount_page.goto(
        f"{FRONTEND_URL}/tutor?{tutor_workflow_query}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(unmount_page)
    _install_fetch_response_gate(unmount_page, "/tutor/ask")
    unmount_page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **markdown_response,
                    "answer": "P3-027 pending navigation response must not persist.",
                },
                ensure_ascii=False,
            ),
        ),
        times=1,
    )
    unmount_page.get_by_label("Question").fill("Navigate away before this completes")
    unmount_page.get_by_role("button", name="Ask tutor", exact=True).click()
    unmount_page.get_by_role("link", name="Articles", exact=True).click()
    expect(
        unmount_page.get_by_role("heading", name="Article List", exact=True)
    ).to_be_visible(timeout=30_000)
    _release_fetch_response_gate(unmount_page)
    _require(
        not pending_navigation_activity,
        f"unmounted Tutor request persisted activity: {pending_navigation_activity}",
    )
    checks["tutor_pending_navigation_has_no_activity"] = True
    _restore_fetch_response_gate(unmount_page)
    unmount_page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="graph-route-boundary")
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    page.get_by_role("link", name="Graph", exact=True).click()
    expect(page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    page.go_back()
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    _require(
        page.url.rstrip("/") == FRONTEND_URL,
        f"Graph popstate handler replaced a non-Graph destination: {page.url}",
    )
    _require(not page_errors, f"Graph route-boundary Back emitted page errors: {page_errors}")
    checks["graph_route_boundary_back"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="article-not-found")

    page.goto(f"{FRONTEND_URL}/articles/not-a-real-article", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_text("Article not found", exact=True)).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Article not-found route emitted page errors: {page_errors}")
    checks["article_not_found_state"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="route-not-found")
    not_found_console_start = len(console_errors)
    page.goto(f"{FRONTEND_URL}/not-a-product-route", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(
        page.get_by_test_id("route-not-found-state").get_by_text("Page not found", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "unknown")
    expected_not_found_console = console_errors[not_found_console_start:]
    _require(
        all("status of 404" in message for message in expected_not_found_console),
        f"unexpected console output during intentional route 404: {expected_not_found_console}",
    )
    del console_errors[not_found_console_start:]
    _require(not page_errors, f"route not-found state emitted page errors: {page_errors}")
    checks["route_not_found_state"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="article-controlled-error")
    page.route(
        re.compile(r".*/v1\.1/articles(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-011 E2E failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_text("Failed to load articles: 503", exact=True)).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Article error state emitted page errors: {page_errors}")
    checks["controlled_backend_error_state"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="graph-controlled-error")
    graph_error_console_start = len(console_errors)
    page.add_init_script(
        script=f"""
        sessionStorage.setItem(
          "scientific-spaces:graph-article-return-focus:v1",
          {json.dumps(json.dumps({
              "articleId": ATTENTION_ARTICLE_ID,
              "focusTarget": "provenance-0",
              "returnTo": ATTENTION_CONCEPT_RETURN,
          }))}
        );
        """
    )
    page.route(
        re.compile(r".*/graph/nodes/concept%3Aattention$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-024 Graph detail failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    graph_error_region = page.get_by_test_id("graph-selected-region")
    expect(graph_error_region.get_by_role("alert")).to_contain_text(
        "Graph request failed: 503", timeout=30_000
    )
    expect(graph_error_region).to_be_focused()
    _require_visible_focus(graph_error_region, "returned Graph detail error region")
    graph_error_region.get_by_role("button", name="Retry", exact=True).click()
    expect(graph_error_region).to_be_focused()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("graph-selection-status")).to_contain_text("Details ready.")
    expected_graph_console = console_errors[graph_error_console_start:]
    _require(
        expected_graph_console
        and all("status of 503" in message for message in expected_graph_console),
        f"unexpected Graph failure console output: {expected_graph_console}",
    )
    del console_errors[graph_error_console_start:]
    _require(not page_errors, f"Graph detail recovery emitted page errors: {page_errors}")
    checks["graph_detail_error_focus_and_retry"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="dashboard-partial")
    page.route(
        re.compile(r".*/learning/stats$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-016 partial dashboard failure"}',
        ),
        times=1,
    )
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_attribute("data-state", "partial")
    expect(page.get_by_role("heading", name="New in Library", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name=CRB_TITLE, exact=True).first).to_be_visible()
    page.get_by_role("button", name="Retry", exact=True).click()
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_count(0, timeout=30_000)
    expect(page.get_by_role("heading", name="Learning Activity", exact=True)).to_be_visible()
    _require(not page_errors, f"Dashboard partial state emitted page errors: {page_errors}")
    checks["dashboard_partial_failure"] = True
    page.close()

    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="dashboard-completion-status-unavailable",
    )
    dashboard_completion_console_start = len(console_errors)
    page.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-025 completion-state list failure"}',
        ),
        times=1,
    )
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_attribute(
        "data-state", "partial"
    )
    continue_region = page.get_by_test_id("continue-reading")
    expect(continue_region).to_contain_text("Completion status is unavailable")
    expect(
        continue_region.get_by_role("link", name=re.compile(r"^Continue learning "))
    ).to_be_visible()
    page.get_by_role("button", name="Retry", exact=True).click()
    expect(page.get_by_test_id("dashboard-remote-state")).to_have_count(0, timeout=30_000)
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    expected_dashboard_completion_console = console_errors[
        dashboard_completion_console_start:
    ]
    _require(
        len(expected_dashboard_completion_console) == 1
        and "status of 503" in expected_dashboard_completion_console[0],
        "unexpected Dashboard completion-state fallback console output: "
        f"{expected_dashboard_completion_console}",
    )
    del console_errors[dashboard_completion_console_start:]
    _require(
        not page_errors,
        f"Dashboard completion-state fallback emitted page errors: {page_errors}",
    )
    checks["dashboard_completion_status_fallback"] = True
    page.close()

    page = _new_observed_page(context, console_errors, page_errors, label="library-partial")
    page.route(
        re.compile(r".*/learning/bookmarks$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional P3-020 partial Bookmark failure"}',
        ),
        times=1,
    )
    page.goto(f"{FRONTEND_URL}/library", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_test_id("saved-library-remote-state")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("saved-library-remote-state")).to_contain_text(
        "Some saved-learning data is unavailable"
    )
    expect(page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(page.get_by_text(CRB_TITLE, exact=True).first).to_be_visible()
    page.get_by_test_id("saved-library-remote-state").get_by_role(
        "button", name="Retry", exact=True
    ).click()
    expect(page.get_by_test_id("saved-library-remote-state")).to_have_count(0, timeout=30_000)
    _require(not page_errors, f"Saved Library partial state emitted page errors: {page_errors}")
    checks["saved_library_partial_failure"] = True
    page.close()
    context.close()

    article_race_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    article_race_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let delayedCrb = false;
          let delayedSuccess = false;
          let delayedSort = false;
          let delayedPage = false;
          let retryRaceCount = 0;
          const articleResponse = (id, title, query, sort, page, hasNext = false) =>
            new Response(JSON.stringify({
              items: [{
                id,
                title,
                url: `https://spaces.ac.cn/archives/${id}`,
                metadata: {},
                content_preview: `${title} preview`,
              }],
              total: hasNext ? 40 : 1,
              query,
              category: null,
              sort,
              page,
              page_size: 20,
              total_pages: hasNext ? 2 : 1,
              has_next: hasNext && page === 1,
              has_previous: page > 1,
            }), { status: 200, headers: { "Content-Type": "application/json" } });
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (!delayedCrb && url.includes('/v1.1/articles') && url.includes('q=CRB')) {
              delayedCrb = true;
              return new Promise((_, reject) => {
                window.setTimeout(() => reject(new Error('intentional stale Article failure')), 900);
              });
            }
            if (!delayedSuccess && url.includes('/v1.1/articles') && url.includes('q=slow-success')) {
              delayedSuccess = true;
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-success', 'Stale success result', 'slow-success', 'date_desc', 1)),
                  900,
                );
              });
            }
            if (!delayedSort && url.includes('/v1.1/articles') && url.includes('q=CRB') && url.includes('sort=title_asc')) {
              delayedSort = true;
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-sort', 'Stale sort result', 'CRB', 'title_asc', 1)),
                  900,
                );
              });
            }
            if (url.includes('/v1.1/articles') && url.includes('q=page-fixture')) {
              const page = Number(new URL(url).searchParams.get('page') || '1');
              if (page === 2 && !delayedPage) {
                delayedPage = true;
                return new Promise((resolve) => {
                  window.setTimeout(
                    () => resolve(articleResponse('stale-page', 'Stale page 2 result', 'page-fixture', 'archive_desc', 2, true)),
                    900,
                  );
                });
              }
              return Promise.resolve(articleResponse('page-one', 'Page fixture 1', 'page-fixture', 'date_desc', 1, true));
            }
            if (url.includes('/v1.1/articles') && url.includes('q=retry-race')) {
              retryRaceCount += 1;
              if (retryRaceCount === 1) {
                return Promise.resolve(new Response('{', {
                  status: 200,
                  headers: { "Content-Type": "application/json" },
                }));
              }
              return new Promise((resolve) => {
                window.setTimeout(
                  () => resolve(articleResponse('stale-retry', 'Stale retry result', 'retry-race', 'date_desc', 1)),
                  900,
                );
              });
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(article_race_context, blocked_external)
    article_race_page = _new_observed_page(
        article_race_context,
        console_errors,
        page_errors,
        label="article-result-race",
    )
    article_race_page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(article_race_page)
    expect(article_race_page.get_by_text(re.compile(r"^Page 1 / "))).to_be_visible(
        timeout=30_000
    )
    race_search = article_race_page.get_by_placeholder("Search title or keyword")
    race_submit = article_race_page.get_by_role("button", name="Search", exact=True)
    race_search.fill("CRB")
    race_submit.click()
    expect(article_race_page.get_by_text("Loading articles", exact=True)).to_be_visible()
    _require(
        article_race_page.get_by_role("link", name=CRB_TITLE, exact=True).count() == 0,
        "pending Article request left stale rows actionable",
    )
    race_search.fill("Attention")
    race_submit.click()
    race_search.fill("CRB")
    race_submit.click()
    race_crb_link = article_race_page.get_by_role("link", name=CRB_TITLE, exact=True)
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_have_count(0)

    race_search.fill("slow-success")
    race_submit.click()
    race_search.fill("CRB")
    race_submit.click()
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale success result", exact=True)).to_have_count(0)

    race_sort = article_race_page.get_by_test_id(
        "article-discovery-workspace"
    ).locator("select")
    race_sort.select_option("title_asc")
    race_sort.select_option("archive_desc")
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale sort result", exact=True)).to_have_count(0)

    race_search.fill("page-fixture")
    race_submit.click()
    expect(article_race_page.get_by_text("Page fixture 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.get_by_role("button", name="Next", exact=True).click()
    race_sort.select_option("date_desc")
    expect(article_race_page.get_by_text("Page fixture 1", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.wait_for_timeout(1_000)
    expect(article_race_page.get_by_text("Stale page 2 result", exact=True)).to_have_count(0)
    expect(article_race_page.get_by_text("Page 1 / 2", exact=True)).to_be_visible()

    race_search.fill("retry-race")
    race_submit.click()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_be_visible(
        timeout=30_000
    )
    article_race_page.get_by_role("button", name="Retry articles", exact=True).click()
    race_search.fill("CRB")
    race_submit.click()
    expect(race_crb_link).to_be_visible(timeout=30_000)
    article_race_page.wait_for_timeout(1_000)
    expect(race_crb_link).to_be_visible()
    expect(article_race_page.get_by_text("Stale retry result", exact=True)).to_have_count(0)

    race_checkbox = article_race_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    race_checkbox.check()
    expect(race_checkbox).to_be_checked()
    race_search.fill("Attention")
    race_submit.click()
    expect(
        article_race_page.get_by_role("link", name=ATTENTION_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    expect(article_race_page.get_by_test_id("article-session-capture")).to_contain_text(
        "0 selected on this page"
    )

    article_race_page.route(
        re.compile(r".*/v1\.1/articles\?.*q=__p3026_error__.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    race_search.fill("__p3026_error__")
    race_submit.click()
    expect(article_race_page.get_by_text("Article library unavailable", exact=True)).to_be_visible(
        timeout=30_000
    )
    _require(
        article_race_page.locator('[data-testid="article-discovery-workspace"] article').count() == 0,
        "failed Article request exposed actionable stale rows",
    )
    article_race_page.get_by_role("button", name="Retry articles", exact=True).click()
    expect(article_race_page.get_by_text("No articles found.", exact=True)).to_be_visible(
        timeout=30_000
    )
    checks["article_result_generation_and_stale_failure_guard"] = True
    checks["article_result_stale_success_sort_page_retry_guard"] = True
    checks["article_result_failure_retry_and_selection_reset"] = True
    article_race_context.close()

    article_recovery_context = browser.new_context(
        viewport={"width": 320, "height": 844}, locale="zh-CN", is_mobile=True
    )
    article_recovery_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let deferOnce = true;
          window.__p3028LateArticleResolved = false;
          window.fetch = async (...args) => {
            const input = args[0];
            const target = new URL(
              typeof input === "string" || input instanceof URL ? input : input.url,
              window.location.href
            );
            if (deferOnce && target.pathname === "/articles/crb-formula") {
              deferOnce = false;
              return new Promise((resolve) => {
                window.setTimeout(() => {
                  window.__p3028LateArticleResolved = true;
                  resolve(new Response(JSON.stringify({
                    id: "crb-formula",
                    title: "STALE ARTICLE RESPONSE",
                    url: "https://spaces.ac.cn/archives/stale",
                    content: "# Stale response",
                    metadata: { date: null, category: null, references: [], images: [] },
                  }), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                  }));
                }, 12_000);
              });
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(article_recovery_context, blocked_external)
    article_recovery_page = _new_observed_page(
        article_recovery_context,
        console_errors,
        page_errors,
        label="graph-reader-recovery",
    )
    graph_recovery_return = "/graph?node_id=article%3Acrb-formula&q=CRB"
    graph_recovery_reader = (
        f"/articles/{CRB_ARTICLE_ID}?"
        + urlencode({"from": graph_recovery_return})
    )
    recovery_session_posts: list[str] = []
    recovery_learning_gets: list[str] = []

    def track_recovery_session(request) -> None:
        request_path = urlparse(request.url).path
        if request.method == "POST" and request_path == "/learning/sessions":
            recovery_session_posts.append(request.url)
        if request.method == "GET" and request_path in {
            f"/learning/state/{CRB_ARTICLE_ID}",
            "/learning/bookmarks",
            f"/learning/notes/{CRB_ARTICLE_ID}",
        }:
            recovery_learning_gets.append(request_path)

    article_recovery_page.on("request", track_recovery_session)
    article_recovery_page.goto(
        f"{FRONTEND_URL}{graph_recovery_reader}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(article_recovery_page)
    recovery_loading = article_recovery_page.get_by_role("status").filter(
        has_text="Loading article"
    )
    expect(recovery_loading).to_have_count(1)
    expect(recovery_loading.locator("xpath=parent::section")).to_have_attribute(
        "aria-busy", "true"
    )
    expect(
        recovery_loading.get_by_role("link", name="Return to graph", exact=True)
    ).to_have_attribute("href", graph_recovery_return)
    _require(
        not recovery_session_posts,
        "pending Article request created a learning session before Article acceptance",
    )
    expect(
        article_recovery_page.get_by_text("Article unavailable", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(article_recovery_page.get_by_text("Article loading timed out. Try again.")).to_be_visible()
    recovery_retry = article_recovery_page.get_by_role(
        "button", name="Retry article", exact=True
    )
    recovery_return = article_recovery_page.get_by_role(
        "link", name="Return to graph", exact=True
    )
    expect(recovery_retry).to_be_visible()
    expect(recovery_retry).to_be_focused()
    _require_visible_focus(recovery_retry, "narrow Article retry action")
    expect(recovery_return).to_have_attribute("href", graph_recovery_return)
    recovery_retry.scroll_into_view_if_needed()
    recovery_return.scroll_into_view_if_needed()
    _require_viewport_containment(
        recovery_retry.bounding_box(), 320, 844, "narrow Article retry action"
    )
    _require_viewport_containment(
        recovery_return.bounding_box(), 320, 844, "narrow Article return action"
    )
    _require(
        _document_width(article_recovery_page) <= 320,
        "narrow Article recovery surface overflows horizontally",
    )
    recovery_retry.press("Enter")
    recovery_heading = article_recovery_page.locator("article#article-start > h1")
    expect(recovery_heading).to_have_text(CRB_TITLE, timeout=30_000)
    expect(recovery_heading).to_be_focused()
    _require_visible_focus(recovery_heading, "retried Graph-origin Reader heading")
    _require(
        len(recovery_session_posts) == 1,
        f"Article retry created an unexpected number of learning sessions: {recovery_session_posts}",
    )
    history_before_late_response = article_recovery_page.evaluate(
        "localStorage.getItem('scientific-spaces-reading-history-v1')"
    )
    learning_gets_before_late_response = list(recovery_learning_gets)
    article_recovery_page.wait_for_function(
        "() => window.__p3028LateArticleResolved === true",
        timeout=30_000,
    )
    expect(recovery_heading).to_have_text(CRB_TITLE)
    expect(article_recovery_page.get_by_text("STALE ARTICLE RESPONSE", exact=True)).to_have_count(0)
    _require(
        len(recovery_session_posts) == 1,
        "late stale Article success created a second learning session",
    )
    _require(
        article_recovery_page.evaluate(
            "localStorage.getItem('scientific-spaces-reading-history-v1')"
        )
        == history_before_late_response,
        "late stale Article success changed reading history",
    )
    _require(
        recovery_learning_gets == learning_gets_before_late_response,
        "late stale Article success started learning-context reads",
    )
    recovery_end_session = article_recovery_page.get_by_role(
        "button", name="End session", exact=True
    )
    expect(recovery_end_session).to_be_enabled(timeout=30_000)
    recovery_end_session.click()
    expect(recovery_end_session).to_be_disabled()
    checks["graph_reader_loading_and_recovery"] = True
    checks["graph_reader_latest_generation_side_effects"] = True
    article_recovery_context.close()

    stale_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    stale_session_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          let deferSessionOnce = true;
          window.__p3028StaleSessionId = null;
          window.fetch = async (...args) => {
            const input = args[0];
            const target = new URL(
              typeof input === "string" || input instanceof URL ? input : input.url,
              window.location.href
            );
            const method = (
              input instanceof Request ? input.method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (deferSessionOnce && method === "POST" && target.pathname === "/learning/sessions") {
              deferSessionOnce = false;
              const response = await originalFetch(...args);
              const payload = await response.clone().json();
              window.__p3028StaleSessionId = payload.session_id;
              await new Promise((resolve) => window.setTimeout(resolve, 1_500));
              return response;
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    _install_network_guard(stale_session_context, blocked_external)
    stale_session_page = _new_observed_page(
        stale_session_context,
        console_errors,
        page_errors,
        label="graph-reader-stale-session",
    )
    stale_session_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(stale_session_page)
    expect(stale_session_page.locator("article#article-start > h1")).to_have_text(
        CRB_TITLE, timeout=30_000
    )
    stale_session_page.wait_for_function(
        "() => typeof window.__p3028StaleSessionId === 'string'",
        timeout=30_000,
    )
    stale_session_id = str(stale_session_page.evaluate("window.__p3028StaleSessionId"))

    def is_stale_session_end(response) -> bool:
        return (
            response.request.method == "PUT"
            and urlparse(response.url).path == f"/learning/sessions/{stale_session_id}/end"
        )

    with stale_session_page.expect_response(is_stale_session_end, timeout=30_000) as stale_end_info:
        stale_session_page.get_by_role("link", name="Back to articles", exact=True).first.click()
    stale_end_response = stale_end_info.value
    _require(stale_end_response.ok, "stale Reader session reconciliation failed")
    stale_session_page.wait_for_function(
        "() => location.pathname === '/articles'", timeout=30_000
    )
    persisted_sessions = _api_json(stale_session_context, "GET", "/learning/sessions")
    reconciled_session = next(
        (
            item
            for item in persisted_sessions.get("items", [])
            if item.get("session_id") == stale_session_id
        ),
        None,
    )
    _require(
        reconciled_session is not None and reconciled_session.get("ended_at"),
        "stale Reader session remained open after navigation",
    )
    checks["graph_reader_stale_session_reconciled"] = True
    stale_session_context.close()

    learning_partial_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(learning_partial_context, blocked_external)
    learning_partial_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    learning_partial_page = _new_observed_page(
        learning_partial_context,
        console_errors,
        page_errors,
        label="article-learning-partial",
    )
    learning_partial_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(learning_partial_page)
    learning_partial_row = learning_partial_page.get_by_role(
        "link", name=CRB_TITLE, exact=True
    ).locator("xpath=ancestor::article[1]")
    expect(learning_partial_row).to_contain_text("Status unavailable", timeout=30_000)
    expect(learning_partial_row).to_contain_text("Bookmarked")
    learning_partial_page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const input = args[0];
            const url = typeof input === "string" ? input : input.url;
            if (!delayed && new URL(url, window.location.href).pathname === "/learning/state") {
              delayed = true;
              return new Promise((resolve, reject) => {
                window.setTimeout(() => originalFetch(...args).then(resolve, reject), 900);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    learning_retry = learning_partial_page.get_by_role(
        "button", name="Retry learning status", exact=True
    )
    learning_retry.click()
    learning_availability = learning_partial_page.get_by_test_id(
        "article-badge-availability"
    )
    expect(learning_retry).to_be_disabled()
    expect(learning_availability).to_have_attribute("aria-busy", "true")
    expect(learning_availability).to_contain_text(
        "Learning status retry in progress. Article rows remain unavailable."
    )
    expect(learning_availability).to_be_focused()
    _require_visible_focus(learning_availability, "Learning badge retry progress")
    learning_search = learning_partial_page.get_by_placeholder("Search title or keyword")
    learning_search.focus()
    expect(learning_search).to_be_focused()
    expect(learning_partial_row).to_contain_text("completed", timeout=30_000)
    expect(learning_availability).to_contain_text("Learning status is available.")
    expect(learning_search).to_be_focused()
    checks["article_learning_failure_preserves_bookmarks"] = True
    learning_partial_context.close()

    bookmark_partial_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(bookmark_partial_context, blocked_external)
    bookmark_partial_context.route(
        re.compile(r".*/learning/bookmarks$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="{",
        ),
        times=1,
    )
    bookmark_partial_page = _new_observed_page(
        bookmark_partial_context,
        console_errors,
        page_errors,
        label="article-bookmark-partial",
    )
    bookmark_partial_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(bookmark_partial_page)
    bookmark_partial_row = bookmark_partial_page.get_by_role(
        "link", name=CRB_TITLE, exact=True
    ).locator("xpath=ancestor::article[1]")
    expect(bookmark_partial_row).to_contain_text("completed", timeout=30_000)
    expect(bookmark_partial_row).not_to_contain_text("Bookmarked")
    bookmark_partial_page.evaluate(
        """
        () => {
          const originalFetch = window.fetch.bind(window);
          let delayed = false;
          window.fetch = (...args) => {
            const input = args[0];
            const url = typeof input === "string" ? input : input.url;
            if (!delayed && new URL(url, window.location.href).pathname === "/learning/bookmarks") {
              delayed = true;
              return new Promise((resolve, reject) => {
                window.setTimeout(() => originalFetch(...args).then(resolve, reject), 900);
              });
            }
            return originalFetch(...args);
          };
        }
        """
    )
    bookmark_retry = bookmark_partial_page.get_by_role(
        "button", name="Retry saved status", exact=True
    )
    bookmark_retry.click()
    bookmark_availability = bookmark_partial_page.get_by_test_id(
        "article-badge-availability"
    )
    expect(bookmark_retry).to_be_disabled()
    expect(bookmark_availability).to_have_attribute("aria-busy", "true")
    expect(bookmark_availability).to_contain_text(
        "Saved status retry in progress. Article rows remain unavailable."
    )
    expect(bookmark_availability).to_be_focused()
    _require_visible_focus(bookmark_availability, "Saved badge retry progress")
    expect(bookmark_partial_row).to_contain_text("Bookmarked", timeout=30_000)
    expect(bookmark_availability).to_contain_text("Saved status is available.")
    expect(bookmark_availability).to_be_focused()
    _require_visible_focus(bookmark_availability, "Saved badge retry result")
    checks["article_bookmark_failure_preserves_learning_state"] = True
    bookmark_partial_context.close()

    capture_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    _install_network_guard(capture_context, blocked_external)
    capture_page = _new_observed_page(
        capture_context, console_errors, page_errors, label="article-capture-reload"
    )
    capture_observer = _new_observed_page(
        capture_context, console_errors, page_errors, label="article-capture-observer"
    )
    for capture_target in (capture_page, capture_observer):
        capture_target.goto(f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded")
        _wait_for_application_shell(capture_target)
        expect(capture_target.get_by_role("link", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
    capture_page.evaluate(
        """
        ([attentionId, attentionTitle, researchId, researchTitle]) => {
          localStorage.setItem("scientific-spaces-study-session-v1", JSON.stringify({
            version: 1,
            active_article_id: attentionId,
            updated_at: "2026-09-05T01:00:00.000Z",
            items: [
              {
                article_id: attentionId,
                title: attentionTitle,
                section_id: null,
                added_at: "2026-09-05T01:00:00.000Z",
              },
              {
                article_id: researchId,
                title: researchTitle,
                section_id: null,
                added_at: "2026-09-05T01:01:00.000Z",
              },
            ],
          }));
        }
        """,
        [ATTENTION_ARTICLE_ID, ATTENTION_TITLE, RESEARCH_ARTICLE_ID, RESEARCH_TITLE],
    )
    expect(capture_observer.get_by_test_id("article-session-capture")).to_contain_text(
        "2/20 in session", timeout=30_000
    )
    capture_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    ).check()
    capture_page_url = capture_page.url
    capture_page.get_by_role("button", name="Add selected to session", exact=True).click()
    capture_payload = capture_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        [item["article_id"] for item in capture_payload["items"]]
        == [ATTENTION_ARTICLE_ID, RESEARCH_ARTICLE_ID, CRB_ARTICLE_ID]
        and capture_payload["active_article_id"] == ATTENTION_ARTICLE_ID,
        f"Article capture did not reload or preserve the current Session: {capture_payload}",
    )
    _require(capture_page.url == capture_page_url, "Article capture auto-navigated")
    expect(
        capture_page.get_by_role("link", name=CRB_TITLE, exact=True).locator(
            "xpath=ancestor::article[1]"
        )
    ).to_contain_text("In session")
    expect(
        capture_observer.get_by_role("link", name=CRB_TITLE, exact=True).locator(
            "xpath=ancestor::article[1]"
        )
    ).to_contain_text("In session", timeout=30_000)
    capture_feedback = capture_page.get_by_test_id("article-session-capture-feedback")
    expect(capture_feedback).to_be_focused()
    expect(capture_feedback).to_contain_text("Focused Session contains 3 of 20 Articles.")
    capture_observer.evaluate(
        "localStorage.removeItem('scientific-spaces-study-session-v1')"
    )
    capture_region = capture_page.get_by_test_id("article-session-capture")
    expect(capture_region).to_contain_text("0/20 in session", timeout=30_000)
    expect(capture_feedback).to_have_text("")
    expect(capture_region).to_be_focused()
    _require_visible_focus(capture_region, "Article capture region after external queue change")
    checks["article_capture_reloads_queue_and_preserves_active"] = True
    checks["article_capture_same_and_cross_tab_refresh"] = True
    checks["article_capture_external_change_invalidates_feedback"] = True
    capture_context.close()

    write_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    write_failure_context.add_init_script(
        script="""
        const originalSetItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function (key, value) {
          if (key === "scientific-spaces-study-session-v1") {
            throw new Error("intentional Article capture write failure");
          }
          return originalSetItem.call(this, key, value);
        };
        """
    )
    _install_network_guard(write_failure_context, blocked_external)
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="article-capture-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_checkbox = write_failure_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    write_failure_checkbox.check()
    write_failure_page.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    write_failure_feedback = write_failure_page.get_by_test_id(
        "article-session-capture-feedback"
    )
    expect(write_failure_feedback).to_be_focused()
    expect(write_failure_feedback).to_contain_text(
        "Focused Session storage failed. No changes were saved. Selection is ready to retry."
    )
    expect(write_failure_checkbox).to_be_checked()
    _require(
        write_failure_page.evaluate(
            "localStorage.getItem('scientific-spaces-study-session-v1')"
        )
        is None,
        "failed Article capture persisted a Session",
    )
    checks["article_capture_write_failure_preserves_selection"] = True
    write_failure_context.close()

    full_capture_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    full_capture_items = [
        {
            "article_id": CRB_ARTICLE_ID,
            "title": CRB_TITLE,
            "section_id": None,
            "added_at": "2026-09-05T02:00:00.000Z",
        },
        *[
            {
                "article_id": f"article-capture-capacity-{index}",
                "title": f"Article capture capacity fixture {index}",
                "section_id": None,
                "added_at": f"2026-09-05T02:{index + 1:02d}:00.000Z",
            }
            for index in range(19)
        ],
    ]
    full_capture_payload = json.dumps(
        {
            "version": 1,
            "active_article_id": CRB_ARTICLE_ID,
            "updated_at": "2026-09-05T02:20:00.000Z",
            "items": full_capture_items,
        },
        ensure_ascii=False,
    )
    full_capture_context.add_init_script(
        script=f"localStorage.setItem('scientific-spaces-study-session-v1', {json.dumps(full_capture_payload)});"
    )
    _install_network_guard(full_capture_context, blocked_external)
    full_capture_page = _new_observed_page(
        full_capture_context,
        console_errors,
        page_errors,
        label="article-capture-full",
    )
    full_capture_page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    _wait_for_application_shell(full_capture_page)
    expect(full_capture_page.get_by_text(re.compile(r"^Page 1 / "))).to_be_visible(
        timeout=30_000
    )
    full_capture_page.get_by_role("button", name="Select page", exact=True).click()
    expect(full_capture_page.get_by_test_id("article-session-capture")).to_contain_text(
        "3 selected on this page"
    )
    full_capture_page.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    full_feedback = full_capture_page.get_by_test_id("article-session-capture-feedback")
    expect(full_feedback).to_be_focused()
    expect(full_feedback).to_contain_text(
        "0 added; 1 already present; 0 invalid; 2 omitted by capacity."
    )
    expect(full_capture_page.get_by_test_id("article-session-capture")).to_contain_text(
        "2 selected on this page"
    )
    persisted_full_capture = full_capture_page.evaluate(
        "localStorage.getItem('scientific-spaces-study-session-v1')"
    )
    _require(
        persisted_full_capture == full_capture_payload,
        "duplicate/full Article capture rewrote the unchanged queue",
    )
    checks["article_capture_duplicate_and_capacity_truth"] = True
    full_capture_context.close()

    unavailable_context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(unavailable_context, blocked_external)
    for endpoint in ("state", "bookmarks", "stats"):
        unavailable_context.route(
            re.compile(rf".*/learning/{endpoint}$"),
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional P3-020 unavailable state"}',
            ),
        )
    unavailable_page = unavailable_context.new_page()
    unavailable_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    unavailable_page.on(
        "pageerror",
        lambda error: _capture_page_error(
            page_errors, "session-storage-unavailable", unavailable_page, error
        ),
    )
    unavailable_page.goto(f"{FRONTEND_URL}/library", wait_until="domcontentloaded")
    _wait_for_application_shell(unavailable_page)
    expect(unavailable_page.get_by_test_id("saved-library-unavailable")).to_be_visible(
        timeout=30_000
    )
    expect(unavailable_page.get_by_test_id("saved-library-unavailable")).not_to_contain_text(
        CRB_ARTICLE_ID
    )
    checks["saved_library_unavailable_state"] = True
    unavailable_context.close()

    recovered_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    recovered_session_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": "missing-article",
              "updated_at": "invalid timestamp",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
                  {
                      "article_id": "raw-title-id",
                      "title": "raw-title-id",
                      "section_id": None,
                      "added_at": "2026-08-31T02:02:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(recovered_session_context, blocked_external)
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="dashboard-storage-recovery",
    )
    recovered_session_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(recovered_session_page)
    recovered_dashboard_session = recovered_session_page.get_by_test_id(
        "dashboard-study-session"
    )
    expect(recovered_dashboard_session).to_have_attribute("data-state", "recovered")
    expect(recovered_dashboard_session).to_contain_text(CRB_TITLE)
    expect(recovered_dashboard_session).not_to_contain_text("raw-title-id")
    recovered_session_page.close()
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="session-storage-recovery",
    )
    recovered_session_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(recovered_session_page)
    expect(
        recovered_session_page.get_by_text(
            re.compile(r"^The saved queue was recovered safely\.")
        )
    ).to_be_visible()
    expect(recovered_session_page.get_by_test_id("study-session-summary")).to_contain_text(
        "1 Article"
    )
    expect(recovered_session_page.get_by_test_id("study-session-item")).to_contain_text(CRB_TITLE)
    expect(recovered_session_page.get_by_test_id("focused-study-session")).not_to_contain_text(
        "raw-title-id"
    )
    recovered_session_page.close()
    recovered_session_page = _new_observed_page(
        recovered_session_context,
        console_errors,
        page_errors,
        label="concept-storage-recovery",
    )
    recovered_session_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(recovered_session_page)
    recovered_concept_set = recovered_session_page.get_by_test_id("concept-study-set")
    expect(recovered_concept_set).to_be_visible(timeout=30_000)
    expect(recovered_concept_set.get_by_role("status")).to_contain_text(
        "recovered valid entries from browser storage"
    )
    checks["study_session_stale_record_recovery"] = True
    checks["concept_study_set_storage_recovery"] = True
    recovered_session_context.close()

    read_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    read_failure_context.add_init_script(
        script="""
        const originalGetItem = Storage.prototype.getItem;
        const originalSetItem = Storage.prototype.setItem;
        window.__p3026ReadFailureSessionWrites = 0;
        Storage.prototype.getItem = function (key) {
          if (key === "scientific-spaces-study-session-v1") {
            throw new Error("intentional study session read failure");
          }
          return originalGetItem.call(this, key);
        };
        Storage.prototype.setItem = function (key, value) {
          if (key === "scientific-spaces-study-session-v1") {
            window.__p3026ReadFailureSessionWrites += 1;
          }
          return originalSetItem.call(this, key, value);
        };
        """
    )
    _install_network_guard(read_failure_context, blocked_external)
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="dashboard-storage-read-failure",
    )
    read_failure_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(read_failure_page)
    expect(read_failure_page.get_by_test_id("dashboard-study-session")).to_have_attribute(
        "data-state", "unavailable"
    )
    expect(read_failure_page.get_by_role("heading", name="Learning Overview", exact=True)).to_be_visible()
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="articles-storage-read-failure",
    )
    read_failure_page.goto(
        f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(read_failure_page)
    expect(
        read_failure_page.get_by_role("link", name=CRB_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    unavailable_capture = read_failure_page.get_by_test_id("article-session-capture")
    expect(unavailable_capture).to_contain_text("Focused Session unavailable")
    _require(
        "0/20 in session" not in unavailable_capture.inner_text(),
        "Article capture falsely reported an empty Session after a storage read failure",
    )
    expect(
        unavailable_capture.get_by_role("button", name="Retry session status", exact=True)
    ).to_be_visible()
    unavailable_checkbox = read_failure_page.get_by_role(
        "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
    )
    unavailable_checkbox.check()
    unavailable_capture.get_by_role(
        "button", name="Add selected to session", exact=True
    ).click()
    unavailable_feedback = read_failure_page.get_by_test_id(
        "article-session-capture-feedback"
    )
    expect(unavailable_feedback).to_be_focused()
    expect(unavailable_feedback).to_contain_text(
        "Browser-local storage is unavailable. No Articles were added."
    )
    expect(unavailable_checkbox).to_be_checked()
    _require(
        read_failure_page.evaluate("window.__p3026ReadFailureSessionWrites") == 0,
        "Article capture wrote Session storage after its read failed",
    )
    checks["article_session_storage_read_unavailable"] = True
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="session-storage-read-failure",
    )
    read_failure_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(read_failure_page)
    expect(read_failure_page.get_by_test_id("study-session-unavailable")).to_be_visible()
    read_failure_page.close()
    read_failure_page = _new_observed_page(
        read_failure_context,
        console_errors,
        page_errors,
        label="concept-storage-read-failure",
    )
    read_failure_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(read_failure_page)
    unavailable_concept_set = read_failure_page.get_by_test_id("concept-study-set")
    expect(unavailable_concept_set).to_be_visible(timeout=30_000)
    expect(unavailable_concept_set.get_by_role("alert")).to_contain_text(
        "Browser-local Focused Session storage is unavailable."
    )
    expect(
        unavailable_concept_set.get_by_role(
            "button", name="Add eligible Articles", exact=True
        )
    ).to_be_disabled()
    checks["study_session_storage_unavailable"] = True
    checks["concept_study_set_storage_unavailable"] = True
    read_failure_context.close()

    write_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    write_failure_context.add_init_script(
        script=f"""
        const studySessionKey = "scientific-spaces-study-session-v1";
        const originalSetItem = Storage.prototype.setItem;
        originalSetItem.call(
          localStorage,
          studySessionKey,
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": ATTENTION_ARTICLE_ID,
              "updated_at": "2026-08-31T02:00:00.000Z",
              "items": [
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
                  {
                      "article_id": "p3-025-advance-target",
                      "title": "Guided advance target",
                      "section_id": None,
                      "added_at": "2026-08-31T02:02:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        Storage.prototype.setItem = function (key, value) {{
          if (key === studySessionKey) {{
            throw new Error("intentional study session write failure");
          }}
          return originalSetItem.call(this, key, value);
        }};
        """
    )
    _install_network_guard(write_failure_context, blocked_external)
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="session-storage-write-failure",
    )
    write_failure_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(write_failure_page)
    crb_write_failure_item = write_failure_page.get_by_test_id("study-session-item").filter(
        has_text=CRB_TITLE
    ).first
    crb_write_failure_item.get_by_role(
        "button", name=f"Move {CRB_TITLE} up", exact=True
    ).click()
    expect(write_failure_page.get_by_test_id("study-session-item").first).to_contain_text(CRB_TITLE)
    expect(write_failure_page.get_by_role("status")).to_contain_text(
        "browser-local storage could not save it"
    )
    write_failure_page.close()
    write_failure_context.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-025-write-failure-timer",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-04T06:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    write_failure_context.route(
        re.compile(r".*/learning/sessions/p3-025-write-failure-timer/end$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-025-write-failure-timer",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-04T06:00:00Z",
                    "ended_at": "2026-09-04T06:01:00Z",
                    "duration_seconds": 60,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="guided-advance-storage-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/articles/{ATTENTION_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_completion = write_failure_page.get_by_test_id(
        "focused-session-completion"
    )
    write_failure_mark = write_failure_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(write_failure_mark).to_be_enabled(timeout=30_000)
    write_failure_mark.focus()
    write_failure_mark.press("Enter")
    expect(write_failure_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(write_failure_completion).to_be_focused(timeout=30_000)
    write_failure_url = write_failure_page.url
    write_failure_advance = write_failure_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    write_failure_advance.focus()
    write_failure_advance.press("Enter")
    expect(write_failure_completion.get_by_role("alert")).to_contain_text(
        "Navigation was cancelled", timeout=30_000
    )
    expect(write_failure_completion).to_be_focused(timeout=30_000)
    _require(
        write_failure_page.url == write_failure_url,
        "guided advance navigated after browser-local pointer persistence failed",
    )
    checks["focused_session_advance_write_failure"] = True
    write_failure_page.close()
    write_failure_page = _new_observed_page(
        write_failure_context,
        console_errors,
        page_errors,
        label="concept-storage-write-failure",
    )
    write_failure_page.goto(
        f"{FRONTEND_URL}/graph?node_id=concept%3Aresearch", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(write_failure_page)
    write_failure_concept_set = write_failure_page.get_by_test_id("concept-study-set")
    expect(write_failure_concept_set).to_be_visible(timeout=30_000)
    write_failure_concept_set.get_by_role(
        "button", name="Add eligible Articles", exact=True
    ).click()
    expect(write_failure_concept_set.get_by_role("status")).to_contain_text(
        "Focused Session storage failed. No saved change is being reported."
    )
    checks["study_session_storage_write_failure"] = True
    checks["concept_study_set_storage_write_failure"] = True
    write_failure_context.close()

    timer_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    timer_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T06:00:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:00:00.000Z",
                  },
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(timer_context, blocked_external)
    timer_record = {
        "session_id": "p3-025-retry-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T06:00:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    timer_end_attempts = {"count": 0}

    def fulfill_timer_collection(route) -> None:
        payload = timer_record if route.request.method == "POST" else {
            "items": [timer_record],
            "total": 1,
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_timer_end(route) -> None:
        timer_end_attempts["count"] += 1
        if timer_end_attempts["count"] == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional uncertain timer end"}',
            )
            return
        timer_record["ended_at"] = "2026-09-04T06:02:00Z"
        timer_record["duration_seconds"] = 120
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(timer_record),
        )

    timer_context.route(re.compile(r".*/learning/sessions$"), fulfill_timer_collection)
    timer_context.route(
        re.compile(r".*/learning/sessions/p3-025-retry-timer/end$"),
        fulfill_timer_end,
    )
    timer_console_start = len(console_errors)
    timer_page = _new_observed_page(
        timer_context,
        console_errors,
        page_errors,
        label="focused-session-timer-reconciliation",
    )
    timer_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(timer_page)
    timer_completion = timer_page.get_by_test_id("focused-session-completion")
    timer_mark_complete = timer_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(timer_mark_complete).to_be_enabled(timeout=30_000)
    timer_mark_complete.focus()
    timer_mark_complete.press("Enter")
    expect(timer_page.get_by_test_id("focused-session-timer-warning")).to_contain_text(
        "exact timer is still open", timeout=30_000
    )
    expect(timer_completion).to_be_focused(timeout=30_000)
    _require(
        timer_end_attempts["count"] == 1,
        f"uncertain timer end was replayed without user action: {timer_end_attempts}",
    )
    timer_retry = timer_completion.get_by_role("button", name="Retry timer check", exact=True)
    timer_retry.focus()
    timer_retry.press("Enter")
    expect(timer_page.get_by_test_id("focused-session-timer-warning")).to_have_count(
        0, timeout=30_000
    )
    expect(timer_completion).to_contain_text("Reader timer end confirmed")
    expect(timer_completion).to_be_focused(timeout=30_000)
    _require(
        timer_end_attempts["count"] == 2,
        f"confirmed-open timer retry did not perform exactly one end request: {timer_end_attempts}",
    )
    timer_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    ).click()
    research_heading = timer_page.get_by_role("heading", name=RESEARCH_TITLE, exact=True)
    expect(research_heading).to_be_visible(timeout=30_000)
    expect(research_heading).to_be_focused(timeout=30_000)
    checks["focused_session_timer_reconciliation"] = True
    timer_context.close()
    expected_timer_console = console_errors[timer_console_start:]
    _require(
        len(expected_timer_console) == 1
        and "status of 503" in expected_timer_console[0],
        f"unexpected timer-reconciliation console output: {expected_timer_console}",
    )
    del console_errors[timer_console_start:]

    manual_timer_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    manual_timer_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T06:30:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:30:00.000Z",
                  },
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T06:31:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(manual_timer_context, blocked_external)
    manual_timer_record = {
        "session_id": "p3-025-manual-uncertain-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T06:30:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    manual_timer_gets = {"count": 0}
    manual_timer_ends = {"count": 0}

    def fulfill_manual_timer_collection(route) -> None:
        if route.request.method == "POST":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(manual_timer_record),
            )
            return
        manual_timer_gets["count"] += 1
        if manual_timer_gets["count"] == 2:
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional manual timer readback failure"}',
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": [manual_timer_record], "total": 1}),
        )

    def fulfill_manual_timer_end(route) -> None:
        manual_timer_ends["count"] += 1
        if manual_timer_ends["count"] == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional manual timer uncertainty"}',
            )
            return
        manual_timer_record["ended_at"] = "2026-09-04T06:34:00Z"
        manual_timer_record["duration_seconds"] = 240
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(manual_timer_record),
        )

    manual_timer_context.route(
        re.compile(r".*/learning/sessions$"), fulfill_manual_timer_collection
    )
    manual_timer_context.route(
        re.compile(r".*/learning/sessions/p3-025-manual-uncertain-timer/end$"),
        fulfill_manual_timer_end,
    )
    manual_timer_console_start = len(console_errors)
    manual_timer_page = _new_observed_page(
        manual_timer_context,
        console_errors,
        page_errors,
        label="manual-timer-uncertainty",
    )
    manual_timer_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(manual_timer_page)
    manual_end = manual_timer_page.get_by_role("button", name="End session", exact=True)
    expect(manual_end).to_be_enabled(timeout=30_000)
    manual_end.click()
    expect(manual_timer_page.get_by_text("Learning request failed: 503", exact=True)).to_be_visible(
        timeout=30_000
    )
    manual_completion = manual_timer_page.get_by_test_id("focused-session-completion")
    manual_mark = manual_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(manual_mark).to_be_enabled(timeout=30_000)
    manual_mark.press("Enter")
    expect(manual_timer_page.get_by_test_id("focused-session-timer-warning")).to_contain_text(
        "exact timer is still open", timeout=30_000
    )
    _require(
        manual_timer_ends["count"] == 1,
        f"completion blindly replayed an uncertain manual timer end: {manual_timer_ends}",
    )
    manual_retry = manual_completion.get_by_role(
        "button", name="Retry timer check", exact=True
    )
    manual_retry.focus()
    manual_retry.press("Enter")
    expect(manual_timer_page.get_by_test_id("focused-session-timer-warning")).to_have_count(
        0, timeout=30_000
    )
    _require(
        manual_timer_ends["count"] == 2,
        f"explicit timer retry did not issue exactly one new end request: {manual_timer_ends}",
    )
    checks["focused_session_manual_timer_uncertainty"] = True
    manual_timer_context.close()
    expected_manual_timer_console = console_errors[manual_timer_console_start:]
    _require(
        len(expected_manual_timer_console) == 2
        and all("status of 503" in message for message in expected_manual_timer_console),
        f"unexpected manual timer uncertainty console output: {expected_manual_timer_console}",
    )
    del console_errors[manual_timer_console_start:]

    uncertain_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    uncertain_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": RESEARCH_ARTICLE_ID,
              "updated_at": "2026-09-04T07:00:00.000Z",
              "items": [
                  {
                      "article_id": RESEARCH_ARTICLE_ID,
                      "title": RESEARCH_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:00:00.000Z",
                  },
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(uncertain_context, blocked_external)
    uncertain_state = {"completed": False, "put_count": 0}

    def uncertain_learning_state_payload() -> dict[str, object]:
        completed = bool(uncertain_state["completed"])
        return {
            "article_id": RESEARCH_ARTICLE_ID,
            "status": "completed" if completed else "unread",
            "last_read_at": "2026-09-04T07:02:00Z" if completed else None,
            "completed_at": "2026-09-04T07:02:00Z" if completed else None,
            "read_count": 1 if completed else 0,
            "updated_at": "2026-09-04T07:02:00Z" if completed else None,
        }

    def fulfill_uncertain_state(route) -> None:
        if route.request.method == "PUT":
            uncertain_state["completed"] = True
            uncertain_state["put_count"] += 1
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional lost completion response"}',
            )
            return
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(uncertain_learning_state_payload()),
        )

    uncertain_context.route(
        re.compile(rf".*/learning/state/{RESEARCH_ARTICLE_ID}$"),
        fulfill_uncertain_state,
    )
    uncertain_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        uncertain_learning_state_payload(),
                        {
                            "article_id": CRB_ARTICLE_ID,
                            "status": "completed",
                            "last_read_at": "2026-09-04T07:00:00Z",
                            "completed_at": "2026-09-04T07:00:00Z",
                            "read_count": 1,
                            "updated_at": "2026-09-04T07:00:00Z",
                        },
                    ],
                    "total": 2,
                }
            ),
        ),
    )
    uncertain_timer = {
        "session_id": "p3-025-uncertain-completion-timer",
        "article_id": RESEARCH_ARTICLE_ID,
        "started_at": "2026-09-04T07:00:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }
    uncertain_context.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(uncertain_timer),
        ),
        times=1,
    )
    uncertain_context.route(
        re.compile(r".*/learning/sessions/p3-025-uncertain-completion-timer/end$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    **uncertain_timer,
                    "ended_at": "2026-09-04T07:03:00Z",
                    "duration_seconds": 180,
                }
            ),
        ),
        times=1,
    )
    uncertain_console_start = len(console_errors)
    uncertain_page = _new_observed_page(
        uncertain_context,
        console_errors,
        page_errors,
        label="focused-session-completion-reconciliation",
    )
    uncertain_page.goto(
        f"{FRONTEND_URL}/articles/{RESEARCH_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(uncertain_page)
    uncertain_completion = uncertain_page.get_by_test_id("focused-session-completion")
    uncertain_mark = uncertain_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(uncertain_mark).to_be_enabled(timeout=30_000)
    uncertain_mark.focus()
    uncertain_mark.press("Enter")
    expect(uncertain_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(uncertain_completion).to_be_focused(timeout=30_000)
    _require(
        uncertain_state["put_count"] == 1,
        f"uncertain completion response caused duplicate writes: {uncertain_state}",
    )
    uncertain_advance = uncertain_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    )
    uncertain_advance.focus()
    uncertain_advance.press("Enter")
    expect(uncertain_completion).to_have_attribute("data-state", "complete", timeout=30_000)
    expect(uncertain_completion).to_be_focused(timeout=30_000)
    checks["focused_session_uncertain_completion_reconciliation"] = True
    uncertain_context.close()
    expected_uncertain_console = console_errors[uncertain_console_start:]
    _require(
        len(expected_uncertain_console) == 1
        and "status of 503" in expected_uncertain_console[0],
        f"unexpected completion-reconciliation console output: {expected_uncertain_console}",
    )
    del console_errors[uncertain_console_start:]

    race_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    race_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T07:30:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:30:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:31:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        window.__p3025CompletionRace = {{ exactGets: 0 }};
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {{
          const request = args[0];
          const init = args[1] || {{}};
          const url = typeof request === "string"
            ? request
            : request instanceof URL
              ? request.toString()
              : request && typeof request.url === "string"
                ? request.url
                : String(request);
          const method = String(
            init.method || (request instanceof Request ? request.method : "GET")
          ).toUpperCase();
          const response = await originalFetch(...args);
          if (method === "POST" && url.endsWith("/learning/sessions")) {{
            await new Promise(resolve => setTimeout(resolve, 2000));
          }}
          if (method === "GET" && url.endsWith("/learning/state/{CRB_ARTICLE_ID}")) {{
            window.__p3025CompletionRace.exactGets += 1;
            if (window.__p3025CompletionRace.exactGets > 1) {{
              await new Promise(resolve => setTimeout(resolve, 800));
            }}
          }}
          return response;
        }};
        """
    )
    _install_network_guard(race_context, blocked_external)
    race_state = {"put_count": 0}

    def fulfill_race_state(route) -> None:
        if route.request.method == "PUT":
            race_state["put_count"] += 1
            status = "completed"
        else:
            status = "unread"
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "article_id": CRB_ARTICLE_ID,
                    "status": status,
                    "last_read_at": None,
                    "completed_at": None,
                    "read_count": 0,
                    "updated_at": None,
                }
            ),
        )

    race_context.route(
        re.compile(rf".*/learning/state/{CRB_ARTICLE_ID}$"),
        fulfill_race_state,
    )
    race_sessions: list[dict[str, object]] = []

    def fulfill_race_sessions(route) -> None:
        if route.request.method == "POST":
            request_payload = route.request.post_data_json
            session = {
                "session_id": f"p3-025-race-timer-{len(race_sessions) + 1}",
                "article_id": request_payload["article_id"],
                "started_at": "2026-09-04T07:32:00Z",
                "ended_at": None,
                "duration_seconds": None,
                "source": "reader",
            }
            race_sessions.append(session)
            payload: object = session
        else:
            payload = {"items": race_sessions, "total": len(race_sessions)}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_race_timer_end(route) -> None:
        session_id = route.request.url.rsplit("/", 2)[-2]
        session = next(item for item in race_sessions if item["session_id"] == session_id)
        session["ended_at"] = "2026-09-04T07:33:00Z"
        session["duration_seconds"] = 60
        route.fulfill(status=200, content_type="application/json", body=json.dumps(session))

    race_context.route(re.compile(r".*/learning/sessions$"), fulfill_race_sessions)
    race_context.route(
        re.compile(r".*/learning/sessions/[^/]+/end$"),
        fulfill_race_timer_end,
    )
    race_page = _new_observed_page(
        race_context,
        console_errors,
        page_errors,
        label="focused-session-navigation-race",
    )
    race_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(race_page)
    race_completion = race_page.get_by_test_id("focused-session-completion")
    expect(race_completion).to_be_visible(timeout=30_000)
    expect(race_completion).to_have_attribute("data-state", "preparing", timeout=1_000)
    race_mark = race_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(race_mark).to_be_disabled()
    expect(race_mark).to_be_enabled(timeout=30_000)
    checks["focused_session_initial_readiness_gate"] = True
    race_mark.press("Enter")
    race_next = race_page.get_by_test_id("study-session-reader-navigation").get_by_role(
        "link", name=f"Next in session: {ATTENTION_TITLE}", exact=True
    )
    expect(race_next).to_have_attribute("aria-disabled", "true")
    race_url = race_page.url
    race_next.click(force=True)
    _require(race_page.url == race_url, "manual navigation escaped while completion was pending")
    expect(race_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    expect(race_completion).to_be_focused(timeout=30_000)
    expect(race_next).to_have_attribute("aria-disabled", "false")
    _require(
        race_state["put_count"] == 1,
        f"completion did not persist exactly once after the pending-navigation guard: {race_state}",
    )
    race_next.click()
    expect(
        race_page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    ).to_be_visible(timeout=30_000)
    expect(race_page.get_by_test_id("focused-session-completion")).to_have_count(0)
    race_session = race_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        race_session["active_article_id"] == CRB_ARTICLE_ID,
        f"manual review navigation changed active state: {race_session}",
    )
    expect(race_page.get_by_test_id("study-session-reader-navigation")).to_contain_text(
        "Review-only view"
    )
    race_page.get_by_test_id("study-session-reader-navigation").get_by_role(
        "link", name=f"Previous in session: {CRB_TITLE}", exact=True
    ).click()
    expect(race_page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    stale_completion = race_page.get_by_test_id("focused-session-completion")
    stale_mark = stale_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(stale_mark).to_be_enabled(timeout=30_000)
    race_page.evaluate(
        """
        const state = JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'));
        state.active_article_id = 'attention-basics';
        state.updated_at = new Date().toISOString();
        localStorage.setItem('scientific-spaces-study-session-v1', JSON.stringify(state));
        """
    )
    stale_mark.click()
    expect(stale_completion.get_by_role("alert")).to_contain_text(
        "no longer the active item", timeout=30_000
    )
    expect(stale_completion).to_be_focused(timeout=30_000)
    expect(stale_completion).to_have_count(1)
    _require(
        race_state["put_count"] == 1,
        f"stale active validation issued another completion write: {race_state}",
    )
    checks["focused_session_manual_navigation_review_only"] = True
    checks["focused_session_navigation_race_guard"] = True
    checks["focused_session_stale_active_failure_focus"] = True
    race_context.close()

    advance_cancel_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    advance_cancel_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T07:45:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:45:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T07:46:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {{
          const request = args[0];
          const init = args[1] || {{}};
          const url = typeof request === "string"
            ? request
            : request instanceof URL
              ? request.toString()
              : request && typeof request.url === "string"
                ? request.url
                : String(request);
          const method = String(
            init.method || (request instanceof Request ? request.method : "GET")
          ).toUpperCase();
          const response = await originalFetch(...args);
          if (method === "GET" && url.endsWith("/learning/state")) {{
            await new Promise(resolve => setTimeout(resolve, 1200));
          }}
          return response;
        }};
        """
    )
    _install_network_guard(advance_cancel_context, blocked_external)
    advance_cancel_state = {
        "article_id": CRB_ARTICLE_ID,
        "status": "completed",
        "last_read_at": "2026-09-04T07:45:00Z",
        "completed_at": "2026-09-04T07:45:30Z",
        "read_count": 1,
        "updated_at": "2026-09-04T07:45:30Z",
    }
    advance_cancel_context.route(
        re.compile(rf".*/learning/state/{CRB_ARTICLE_ID}$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(advance_cancel_state),
        ),
    )
    advance_cancel_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "items": [
                        advance_cancel_state,
                        {
                            "article_id": ATTENTION_ARTICLE_ID,
                            "status": "unread",
                            "last_read_at": None,
                            "completed_at": None,
                            "read_count": 0,
                            "updated_at": None,
                        },
                    ],
                    "total": 2,
                }
            ),
        ),
    )
    advance_cancel_timer = {
        "session_id": "p3-025-cancelled-advance-timer",
        "article_id": CRB_ARTICLE_ID,
        "started_at": "2026-09-04T07:45:00Z",
        "ended_at": None,
        "duration_seconds": None,
        "source": "reader",
    }

    def fulfill_advance_cancel_sessions(route) -> None:
        payload = advance_cancel_timer if route.request.method == "POST" else {
            "items": [advance_cancel_timer],
            "total": 1,
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    def fulfill_advance_cancel_timer_end(route) -> None:
        advance_cancel_timer["ended_at"] = "2026-09-04T07:46:00Z"
        advance_cancel_timer["duration_seconds"] = 60
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(advance_cancel_timer),
        )

    advance_cancel_context.route(
        re.compile(r".*/learning/sessions$"), fulfill_advance_cancel_sessions
    )
    advance_cancel_context.route(
        re.compile(r".*/learning/sessions/p3-025-cancelled-advance-timer/end$"),
        fulfill_advance_cancel_timer_end,
    )
    advance_cancel_page = _new_observed_page(
        advance_cancel_context,
        console_errors,
        page_errors,
        label="focused-session-cancelled-advance",
    )
    advance_cancel_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(advance_cancel_page)
    advance_cancel_completion = advance_cancel_page.get_by_test_id(
        "focused-session-completion"
    )
    advance_cancel_mark = advance_cancel_completion.get_by_role(
        "button", name="Mark Article complete", exact=True
    )
    expect(advance_cancel_mark).to_be_enabled(timeout=30_000)
    advance_cancel_mark.click()
    expect(advance_cancel_completion).to_have_attribute(
        "data-state", "ready-to-advance", timeout=30_000
    )
    advance_cancel_completion.get_by_role(
        "button", name="Open next unfinished Article", exact=True
    ).click()
    advance_cancel_page.get_by_role("link", name="Dashboard", exact=True).click()
    expect(
        advance_cancel_page.get_by_role(
            "heading", name="Scientific Spaces AI Learning OS", exact=True
        )
    ).to_be_visible(timeout=30_000)
    advance_cancel_page.wait_for_timeout(1800)
    _require(
        advance_cancel_page.url == f"{FRONTEND_URL}/",
        f"stale guided advance overrode newer Dashboard navigation: {advance_cancel_page.url}",
    )
    cancelled_advance_session = advance_cancel_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        cancelled_advance_session["active_article_id"] == CRB_ARTICLE_ID,
        f"stale guided advance rewrote the active queue pointer: {cancelled_advance_session}",
    )
    checks["focused_session_cancelled_advance_guard"] = True
    advance_cancel_context.close()

    completion_retry_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    completion_retry_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-09-04T08:00:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": None,
                      "added_at": "2026-09-04T08:00:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(completion_retry_context, blocked_external)
    completion_retry_context.route(
        re.compile(r".*/learning/state$"),
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"intentional completion-list failure"}',
        ),
        times=1,
    )
    completion_retry_console_start = len(console_errors)
    completion_retry_page = _new_observed_page(
        completion_retry_context,
        console_errors,
        page_errors,
        label="focused-session-completion-list-retry",
    )
    completion_retry_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(completion_retry_page)
    expect(
        completion_retry_page.get_by_text("Completion status is unavailable.", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(completion_retry_page.get_by_test_id("study-session-item")).to_contain_text(
        "Status unavailable"
    )
    expect(completion_retry_page.get_by_test_id("study-session-complete")).to_have_count(0)
    completion_retry_page.get_by_role("button", name="Retry status", exact=True).click()
    expect(completion_retry_page.get_by_test_id("study-session-complete")).to_be_visible(
        timeout=30_000
    )
    checks["focused_session_completion_status_retry"] = True
    completion_retry_context.close()
    expected_completion_retry_console = console_errors[completion_retry_console_start:]
    _require(
        len(expected_completion_retry_console) == 1
        and "status of 503" in expected_completion_retry_console[0],
        f"unexpected completion-list retry console output: {expected_completion_retry_console}",
    )
    del console_errors[completion_retry_console_start:]

    full_session_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    full_session_items = [
        {
            "article_id": f"capacity-{index}",
            "title": f"Capacity fixture Article {index}",
            "section_id": None,
            "added_at": f"2026-08-31T03:{index:02d}:00.000Z",
        }
        for index in range(20)
    ]
    full_session_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": "capacity-7",
              "updated_at": "2026-08-31T03:20:00.000Z",
              "items": full_session_items,
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(full_session_context, blocked_external)
    full_session_page = full_session_context.new_page()
    full_session_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    full_session_page.on(
        "pageerror",
        lambda error: _capture_page_error(
            page_errors, "session-full-capacity", full_session_page, error
        ),
    )
    full_session_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(full_session_page)
    full_concept_set = full_session_page.get_by_test_id("concept-study-set")
    expect(full_concept_set).to_be_visible(timeout=30_000)
    expect(full_concept_set.get_by_text("Open Focused Session (20/20)", exact=True)).to_be_visible()
    expect(
        full_concept_set.get_by_role(
            "button", name=f"Add {ATTENTION_TITLE} to study session", exact=True
        )
    ).to_be_disabled()
    full_concept_set.get_by_role("button", name="Add eligible Articles", exact=True).click()
    expect(full_concept_set.get_by_role("status")).to_contain_text(
        "0 added; 0 already present; 0 invalid; 1 omitted by capacity."
    )
    full_session_payload = full_session_page.evaluate(
        "JSON.parse(localStorage.getItem('scientific-spaces-study-session-v1'))"
    )
    _require(
        len(full_session_payload["items"]) == 20
        and full_session_payload["active_article_id"] == "capacity-7",
        f"full Concept Study Set mutation changed the Session: {full_session_payload}",
    )
    checks["concept_study_set_full_capacity"] = True
    full_session_context.close()

    zoom_context = browser.new_context(
        viewport={"width": 720, "height": 450},
        screen={"width": 1440, "height": 900},
        locale="zh-CN",
        reduced_motion="reduce",
    )
    _install_network_guard(zoom_context, blocked_external)
    zoom_page = zoom_context.new_page()
    zoom_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    zoom_page.on(
        "pageerror", lambda error: _capture_page_error(page_errors, "graph-zoom", zoom_page, error)
    )
    zoom_page.goto(
        f"{FRONTEND_URL}/graph?unknown=discard&node_id=concept%3Aattention&q=%20Attention%20#unknown",
        wait_until="domcontentloaded",
    )
    _wait_for_application_shell(zoom_page)
    zoom_page.wait_for_function(
        "() => location.pathname + location.search + location.hash === "
        "'/graph?node_id=concept%3Aattention&q=Attention'"
    )
    zoom_concept_set = zoom_page.get_by_test_id("concept-study-set")
    expect(zoom_concept_set).to_be_visible(timeout=30_000)
    _wait_for_test_id_near_viewport_top(zoom_page, "graph-selected-region")
    zoom_selected_box = zoom_page.get_by_test_id("graph-selected-region").bounding_box()
    _require(
        zoom_selected_box is not None
        and zoom_selected_box["y"] < 200
        and zoom_selected_box["y"] + zoom_selected_box["height"] > 0,
        f"200-percent zoom-equivalent selected detail is below the viewport: {zoom_selected_box}",
    )
    expect(zoom_concept_set.get_by_role("link", name="Explain concept", exact=True)).to_be_visible()
    expect(zoom_concept_set.get_by_role("link", name="Open concept quiz", exact=True)).to_be_visible()
    zoom_metrics = zoom_page.evaluate(
        "({ viewportWidth: window.innerWidth, viewportHeight: window.innerHeight, "
        "screenWidth: window.screen.width, screenHeight: window.screen.height })"
    )
    _require(
        zoom_metrics["screenWidth"] == 1440
        and zoom_metrics["screenHeight"] == 900
        and zoom_metrics["viewportWidth"] == 720
        and zoom_metrics["viewportHeight"] == 450
        and zoom_metrics["screenWidth"] / zoom_metrics["viewportWidth"] == 2
        and zoom_metrics["screenHeight"] / zoom_metrics["viewportHeight"] == 2,
        f"Chromium did not apply the 200-percent zoom-equivalent layout boundary: {zoom_metrics}",
    )
    zoom_concept_box = zoom_concept_set.bounding_box()
    zoom_document_width = _document_width(zoom_page)
    _require(
        zoom_concept_box is not None
        and zoom_concept_box["x"] >= 0
        and zoom_concept_box["x"] + zoom_concept_box["width"] <= zoom_metrics["viewportWidth"],
        f"200-percent display-scale Concept Study Set is clipped: {zoom_concept_box}",
    )
    _require(
        zoom_document_width <= zoom_metrics["viewportWidth"],
        f"200-percent display-scale Graph page overflowed to {zoom_document_width}px",
    )
    for zoom_control in (
        zoom_concept_set.get_by_role("link", name="Explain concept", exact=True),
        zoom_concept_set.get_by_role("link", name="Open concept quiz", exact=True),
        zoom_concept_set.get_by_role("button", name="Add eligible Articles", exact=True),
    ):
        control_box = zoom_control.bounding_box()
        _require(
            control_box is not None
            and zoom_concept_box is not None
            and control_box["x"] >= zoom_concept_box["x"]
            and control_box["x"] + control_box["width"]
            <= zoom_concept_box["x"] + zoom_concept_box["width"],
            f"200-percent zoom-equivalent control is clipped: {control_box}",
        )
    checks["concept_study_set_200_percent_reflow"] = True
    checks["concept_study_set_200_percent_zoom_equivalent"] = True
    zoom_context.close()

    narrow_context = browser.new_context(
        viewport={"width": 320, "height": 640},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    _install_network_guard(narrow_context, blocked_external)
    narrow_context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.fetch = (...args) => {
            const url = String(args[0]);
            if (url.includes('/graph/summary')) {
              return new Promise(() => {});
            }
            return originalFetch(...args);
          };
        })();
        """
    )
    narrow_page = narrow_context.new_page()
    narrow_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    narrow_page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "graph-320", narrow_page, error),
    )
    narrow_page.goto(f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded")
    _wait_for_application_shell(narrow_page)
    expect(narrow_page.get_by_text("Loading graph summary...", exact=True)).to_be_visible()
    expect(narrow_page.get_by_test_id("concept-study-set")).to_be_visible(timeout=30_000)
    _wait_for_test_id_near_viewport_top(narrow_page, "graph-selected-region")
    narrow_selected_box = narrow_page.get_by_test_id("graph-selected-region").bounding_box()
    _require(
        narrow_selected_box is not None
        and narrow_selected_box["y"] < 200
        and narrow_selected_box["y"] + narrow_selected_box["height"] > 0,
        f"320px Graph selected detail is below the viewport: {narrow_selected_box}",
    )
    _require(_document_width(narrow_page) <= 320, "320px Graph workspace overflows horizontally")
    checks["graph_selected_detail_320px"] = True
    checks["graph_detail_reachability_with_pending_summary"] = True
    narrow_context.close()

    deep_link_context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    _install_network_guard(deep_link_context, blocked_external)
    deep_link_page = _new_observed_page(
        deep_link_context, console_errors, page_errors, label="graph-390-deep-link"
    )
    deep_link_page.goto(
        f"{FRONTEND_URL}{ATTENTION_CONCEPT_RETURN}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(deep_link_page)
    deep_link_selected = deep_link_page.get_by_test_id("graph-selected-region")
    expect(deep_link_selected.get_by_role("heading", name=re.compile(r"^attention$", re.I))).to_be_visible(
        timeout=30_000
    )
    _wait_for_test_id_near_viewport_top(deep_link_page, "graph-selected-region")
    deep_link_selected_box = deep_link_selected.bounding_box()
    _require(
        deep_link_selected_box is not None
        and deep_link_selected_box["y"] < 200
        and deep_link_selected_box["y"] + deep_link_selected_box["height"] > 0,
        f"390px deep-linked Graph detail is below the viewport: {deep_link_selected_box}",
    )
    _require(
        _document_width(deep_link_page) <= 390,
        "390px deep-linked Graph workspace overflows horizontally",
    )
    checks["graph_selected_detail_390px_deep_link"] = True
    deep_link_context.close()

    responsive_tutor_response = {
        **markdown_response,
        "answer": (
            f"{markdown_response['answer']}\n\n"
            "## Extended grounded explanation\n\n"
            + "\n\n".join(
                "This local evidence paragraph keeps the scientific explanation readable on narrow screens "
                "while preserving cited context, inline notation $I(\\theta)$, and explicit uncertainty."
                for _ in range(8)
            )
        ),
    }
    responsive_tutor_body = json.dumps(responsive_tutor_response, ensure_ascii=False)
    tutor_workflow_query = urlencode(
        {
            "article_id": CRB_ARTICLE_ID,
            "article_title": CRB_TITLE,
            "return_to": f"/articles/{CRB_ARTICLE_ID}",
        }
    )

    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        completion_viewport_context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            screen={"width": 1440, "height": 900}
            if viewport_label == "zoom-equivalent"
            else None,
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
            reduced_motion="reduce",
        )
        fail_article_capture_write = viewport_label == "narrow"
        completion_viewport_context.add_init_script(
            script=f"""
            if (!sessionStorage.getItem("p3-026-viewport-seeded")) {{
              localStorage.setItem(
                "scientific-spaces-study-session-v1",
                {json.dumps(json.dumps({
                    "version": 1,
                    "active_article_id": CRB_ARTICLE_ID,
                    "updated_at": "2026-09-04T09:00:00.000Z",
                    "items": [
                        {
                            "article_id": CRB_ARTICLE_ID,
                            "title": CRB_TITLE,
                            "section_id": None,
                            "added_at": "2026-09-04T09:00:00.000Z",
                        },
                        {
                            "article_id": RESEARCH_ARTICLE_ID,
                            "title": RESEARCH_TITLE,
                            "section_id": None,
                            "added_at": "2026-09-04T09:01:00.000Z",
                        },
                    ],
                }, ensure_ascii=False))}
              );
              sessionStorage.setItem("p3-026-viewport-seeded", "true");
            }}
            if ({str(fail_article_capture_write).lower()}) {{
              const originalSetItem = Storage.prototype.setItem;
              Storage.prototype.setItem = function (key, value) {{
                if (key === "scientific-spaces-study-session-v1") {{
                  throw new Error("intentional narrow viewport Article capture failure");
                }}
                return originalSetItem.call(this, key, value);
              }};
            }}
            """
        )
        _install_network_guard(completion_viewport_context, blocked_external)
        viewport_timer = {
            "session_id": f"p3-025-{viewport_label}-timer",
            "article_id": CRB_ARTICLE_ID,
            "started_at": "2026-09-04T09:00:00Z",
            "ended_at": None,
            "duration_seconds": None,
            "source": "reader",
        }
        completion_viewport_context.route(
            re.compile(r".*/learning/sessions$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(viewport_timer),
            ),
            times=1,
        )
        completion_viewport_page = _new_observed_page(
            completion_viewport_context,
            console_errors,
            page_errors,
            label=f"focused-completion-{viewport_label}",
        )
        completion_viewport_page.goto(
            f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(completion_viewport_page)
        viewport_heading = completion_viewport_page.get_by_role(
            "heading", name=CRB_TITLE, exact=True
        )
        expect(viewport_heading).to_be_focused(timeout=30_000)
        heading_box = viewport_heading.bounding_box()
        _require(
            heading_box is not None
            and heading_box["y"] < viewport_height
            and heading_box["y"] + heading_box["height"] > 0,
            f"{viewport_label} guided Reader heading does not intersect the viewport: {heading_box}",
        )
        viewport_completion = completion_viewport_page.get_by_test_id(
            "focused-session-completion"
        )
        viewport_completion.scroll_into_view_if_needed()
        completion_box = viewport_completion.bounding_box()
        _require(
            completion_box is not None
            and completion_box["x"] >= 0
            and completion_box["x"] + completion_box["width"] <= viewport_width,
            f"{viewport_label} completion region is horizontally clipped: {completion_box}",
        )
        for action_name in ("Mark Article complete", "Open next unfinished Article"):
            action_box = viewport_completion.get_by_role(
                "button", name=action_name, exact=True
            ).bounding_box()
            _require(
                action_box is not None
                and completion_box is not None
                and action_box["x"] >= completion_box["x"]
                and action_box["x"] + action_box["width"]
                <= completion_box["x"] + completion_box["width"],
                f"{viewport_label} completion action is clipped: {action_box}",
            )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} focused Reader overflows horizontally",
        )
        viewport_mark = viewport_completion.get_by_role(
            "button", name="Mark Article complete", exact=True
        )
        expect(viewport_mark).to_be_enabled(timeout=30_000)
        completion_viewport_page.keyboard.press("Tab")
        expect(viewport_mark).to_be_focused()
        checks[f"focused_session_completion_{viewport_label}_viewport"] = True

        if fail_article_capture_write:
            completion_viewport_page.evaluate(
                "localStorage.removeItem('scientific-spaces-study-session-v1')"
            )

        completion_viewport_page.goto(
            f"{FRONTEND_URL}/articles?q=CRB", wait_until="domcontentloaded"
        )
        _wait_for_application_shell(completion_viewport_page)
        expect(
            completion_viewport_page.get_by_role("link", name=CRB_TITLE, exact=True)
        ).to_be_visible(timeout=30_000)
        viewport_capture = completion_viewport_page.get_by_test_id(
            "article-session-capture"
        )
        viewport_capture.scroll_into_view_if_needed()
        viewport_capture_box = viewport_capture.bounding_box()
        _require(
            viewport_capture_box is not None
            and viewport_capture_box["x"] >= 0
            and viewport_capture_box["x"] + viewport_capture_box["width"]
            <= viewport_width,
            f"{viewport_label} Article capture region is horizontally clipped: "
            f"{viewport_capture_box}",
        )
        for role, name in (
            ("button", "Select page"),
            ("button", "Clear selection"),
            ("button", "Add selected to session"),
            ("link", "Open Focused Session"),
        ):
            control_box = completion_viewport_page.get_by_role(
                role, name=name, exact=True
            ).bounding_box()
            _require(
                control_box is not None
                and viewport_capture_box is not None
                and control_box["x"] >= viewport_capture_box["x"]
                and control_box["x"] + control_box["width"]
                <= viewport_capture_box["x"] + viewport_capture_box["width"],
                f"{viewport_label} Article capture control is clipped: {control_box}",
            )
        viewport_checkbox = completion_viewport_page.get_by_role(
            "checkbox", name=f"Select {CRB_TITLE} for focused session", exact=True
        )
        viewport_select_page = completion_viewport_page.get_by_role(
            "button", name="Select page", exact=True
        )
        viewport_clear = completion_viewport_page.get_by_role(
            "button", name="Clear selection", exact=True
        )
        viewport_add = completion_viewport_page.get_by_role(
            "button", name="Add selected to session", exact=True
        )
        expect(viewport_checkbox).not_to_be_checked()
        expect(viewport_select_page).to_be_enabled()
        expect(viewport_clear).to_be_disabled()
        expect(viewport_add).to_be_disabled()
        checkbox_box = viewport_checkbox.bounding_box()
        _require(
            checkbox_box is not None
            and checkbox_box["x"] >= 0
            and checkbox_box["x"] + checkbox_box["width"] <= viewport_width,
            f"{viewport_label} Article capture checkbox is clipped: {checkbox_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Article capture workspace overflows horizontally",
        )
        _focus_via_tab(completion_viewport_page, viewport_checkbox)
        expect(viewport_checkbox).to_be_focused()
        viewport_checkbox.press("Space")
        expect(viewport_checkbox).to_be_checked()
        expect(viewport_clear).to_be_enabled()
        expect(viewport_add).to_be_enabled()
        completion_viewport_page.keyboard.press("Shift+Tab")
        expect(
            completion_viewport_page.get_by_role(
                "link", name="Open Focused Session", exact=True
            )
        ).to_be_focused()
        completion_viewport_page.keyboard.press("Shift+Tab")
        expect(viewport_add).to_be_focused()
        completion_viewport_page.keyboard.press("Enter")
        viewport_feedback = completion_viewport_page.get_by_test_id(
            "article-session-capture-feedback"
        )
        expect(viewport_feedback).to_be_focused()
        expect(viewport_feedback).to_have_attribute("aria-live", "polite")
        expect(viewport_feedback).to_have_attribute("aria-atomic", "true")
        if fail_article_capture_write:
            expect(viewport_feedback).to_contain_text(
                "Focused Session storage failed. No changes were saved. Selection is ready to retry."
            )
            expect(viewport_checkbox).to_be_checked()
        else:
            expect(viewport_feedback).to_contain_text(
                "0 added; 1 already present; 0 invalid; 0 omitted by capacity."
            )
        _require_visible_focus(
            viewport_feedback, f"{viewport_label} Article capture feedback"
        )
        feedback_box = viewport_feedback.bounding_box()
        _require(
            feedback_box is not None
            and feedback_box["x"] >= 0
            and feedback_box["x"] + feedback_box["width"] <= viewport_width
            and feedback_box["y"] < viewport_height
            and feedback_box["y"] + feedback_box["height"] > 0,
            f"{viewport_label} Article capture feedback is clipped or off-screen: "
            f"{feedback_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Article capture feedback caused horizontal overflow",
        )
        checks[f"article_session_capture_{viewport_label}_viewport"] = True
        checks[f"article_session_capture_{viewport_label}_keyboard_feedback"] = True

        completion_viewport_context.route(
            re.compile(r".*/tutor/ask$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=responsive_tutor_body,
            ),
            times=1,
        )
        completion_viewport_page.goto(
            f"{FRONTEND_URL}/tutor?{tutor_workflow_query}",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(completion_viewport_page)
        expect(
            completion_viewport_page.get_by_role(
                "heading", name="AI Research Tutor", exact=True
            )
        ).to_be_visible(timeout=30_000)
        viewport_question = completion_viewport_page.get_by_label("Question")
        viewport_question.fill("Explain the CRB evidence for this responsive check")
        viewport_ask = completion_viewport_page.get_by_role(
            "button", name="Ask tutor", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_ask)
        viewport_ask.press("Enter")
        viewport_result = completion_viewport_page.get_by_test_id("tutor-result")
        expect(viewport_result).to_be_focused(timeout=30_000)
        expect(
            completion_viewport_page.get_by_test_id("tutor-request-status")
        ).to_have_text("Tutor answer ready.")
        _require_visible_focus(
            viewport_result, f"{viewport_label} Tutor answer result"
        )
        result_box = viewport_result.bounding_box()
        _require(
            result_box is not None
            and result_box["x"] >= 0
            and result_box["x"] + result_box["width"] <= viewport_width
            and result_box["y"] < viewport_height
            and result_box["y"] + result_box["height"] > 0,
            f"{viewport_label} Tutor answer is clipped or off-screen: {result_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor answer caused horizontal overflow",
        )

        viewport_quiz_mode = completion_viewport_page.get_by_role(
            "button", name="Quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_quiz_mode)
        viewport_quiz_mode.press("Enter")
        completion_viewport_page.get_by_label("Prompt").fill("CRB")
        viewport_generate = completion_viewport_page.get_by_role(
            "button", name="Generate quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_generate)
        viewport_generate.press("Enter")
        viewport_quiz = completion_viewport_page.get_by_test_id(
            "tutor-quiz-workspace"
        )
        expect(viewport_quiz).to_be_focused(timeout=30_000)
        viewport_quiz_articles = viewport_quiz.locator("article")
        _require(
            viewport_quiz_articles.count() >= 2,
            f"{viewport_label} Tutor Quiz returned too few questions",
        )
        for quiz_index in range(viewport_quiz_articles.count()):
            viewport_answer = viewport_quiz_articles.nth(quiz_index).locator(
                'input[type="radio"]'
            ).first
            _focus_via_tab(completion_viewport_page, viewport_answer)
            viewport_answer.press("Space")
        viewport_check = completion_viewport_page.get_by_role(
            "button", name="Check answers", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_check)
        viewport_check.press("Enter")
        viewport_score = completion_viewport_page.get_by_test_id(
            "tutor-quiz-score"
        )
        expect(viewport_score).to_be_focused()
        _require_visible_focus(
            viewport_score, f"{viewport_label} Tutor Quiz score"
        )
        score_box = viewport_score.bounding_box()
        _require(
            score_box is not None
            and score_box["x"] >= 0
            and score_box["x"] + score_box["width"] <= viewport_width
            and score_box["y"] < viewport_height
            and score_box["y"] + score_box["height"] > 0,
            f"{viewport_label} Tutor Quiz score is clipped or off-screen: {score_box}",
        )
        quiz_document_width = _document_width(completion_viewport_page)
        quiz_overflowing_elements = completion_viewport_page.evaluate(
            """
            (viewportWidth) => Array.from(document.querySelectorAll("body *"))
              .map((element) => {
                const rect = element.getBoundingClientRect();
                return {
                  tag: element.tagName.toLowerCase(),
                  testId: element.getAttribute("data-testid"),
                  className: typeof element.className === "string" ? element.className : "",
                  left: Math.round(rect.left),
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                };
              })
              .filter((item) => item.right > viewportWidth + 1 || item.left < -1)
              .slice(0, 12)
            """,
            viewport_width,
        )
        _require(
            quiz_document_width <= viewport_width,
            f"{viewport_label} Tutor Quiz review caused horizontal overflow to "
            f"{quiz_document_width}px: {quiz_overflowing_elements}",
        )
        viewport_retry = completion_viewport_page.get_by_role(
            "button", name="Try again", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_retry)
        viewport_retry.press("Enter")
        expect(
            viewport_quiz_articles.first.locator('input[type="radio"]').first
        ).to_be_focused()

        viewport_error_console_start = len(console_errors)
        viewport_explain_mode = completion_viewport_page.get_by_role(
            "button", name="Explain", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_explain_mode)
        viewport_explain_mode.press("Enter")
        completion_viewport_page.route(
            re.compile(r".*/tutor/ask$"),
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"intentional responsive Tutor failure"}',
            ),
            times=1,
        )
        viewport_error_submit = completion_viewport_page.get_by_role(
            "button", name="Ask tutor", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_error_submit)
        viewport_error_submit.press("Enter")
        viewport_error = completion_viewport_page.get_by_test_id("tutor-error")
        expect(viewport_error).to_be_focused(timeout=30_000)
        _require_visible_focus(
            viewport_error, f"{viewport_label} Tutor error feedback"
        )
        error_box = viewport_error.bounding_box()
        _require(
            error_box is not None
            and error_box["x"] >= 0
            and error_box["x"] + error_box["width"] <= viewport_width
            and error_box["y"] < viewport_height
            and error_box["y"] + error_box["height"] > 0,
            f"{viewport_label} Tutor error is clipped or off-screen: {error_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor error caused horizontal overflow",
        )
        viewport_error_console = console_errors[viewport_error_console_start:]
        _require(
            len(viewport_error_console) == 1
            and "status of 503" in viewport_error_console[0],
            f"unexpected {viewport_label} Tutor error console output: "
            f"{viewport_error_console}",
        )
        del console_errors[viewport_error_console_start:]

        viewport_quiz_mode = completion_viewport_page.get_by_role(
            "button", name="Quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_quiz_mode)
        viewport_quiz_mode.press("Enter")
        completion_viewport_page.route(
            re.compile(r".*/tutor/quiz$"),
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"questions":[],"total":0}',
            ),
            times=1,
        )
        viewport_empty_submit = completion_viewport_page.get_by_role(
            "button", name="Generate quiz", exact=True
        )
        _focus_via_tab(completion_viewport_page, viewport_empty_submit)
        viewport_empty_submit.press("Enter")
        viewport_empty = completion_viewport_page.get_by_test_id(
            "tutor-empty-result"
        )
        expect(viewport_empty).to_be_focused(timeout=30_000)
        _require_visible_focus(
            viewport_empty, f"{viewport_label} Tutor empty Quiz feedback"
        )
        empty_box = viewport_empty.bounding_box()
        _require(
            empty_box is not None
            and empty_box["x"] >= 0
            and empty_box["x"] + empty_box["width"] <= viewport_width
            and empty_box["y"] < viewport_height
            and empty_box["y"] + empty_box["height"] > 0,
            f"{viewport_label} Tutor empty Quiz result is clipped or off-screen: "
            f"{empty_box}",
        )
        _require(
            _document_width(completion_viewport_page) <= viewport_width,
            f"{viewport_label} Tutor empty Quiz result caused horizontal overflow",
        )
        checks[f"tutor_dynamic_{viewport_label}_viewport"] = True
        checks[f"tutor_keyboard_feedback_{viewport_label}"] = True
        checks[f"tutor_error_feedback_{viewport_label}"] = True
        checks[f"tutor_empty_quiz_feedback_{viewport_label}"] = True
        completion_viewport_context.close()

    graph_round_trip_path = "/graph?node_id=article%3Acrb-formula&q=CRB"
    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        graph_reader_context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
            reduced_motion="reduce",
        )
        if viewport_label == "desktop":
            graph_reader_context.add_init_script(
                script=f"""
                localStorage.setItem(
                  "scientific-spaces-reader-progress-v1",
                  {json.dumps(json.dumps({
                      "version": 1,
                      "items": [{
                          "article_id": CRB_ARTICLE_ID,
                          "section_id": "regularity",
                          "section_title": "正则条件",
                          "progress": 42,
                          "updated_at": "2026-08-31T02:00:00.000Z",
                      }],
                  }, ensure_ascii=False))}
                );
                """
            )
        _install_network_guard(graph_reader_context, blocked_external)
        graph_reader_page = _new_observed_page(
            graph_reader_context,
            console_errors,
            page_errors,
            label=f"graph-reader-{viewport_label}",
        )
        graph_reader_page.goto(
            f"{FRONTEND_URL}{graph_round_trip_path}", wait_until="domcontentloaded"
        )
        _wait_for_application_shell(graph_reader_page)
        saved_reader_progress = (
            graph_reader_page.evaluate(
                "localStorage.getItem('scientific-spaces-reader-progress-v1')"
            )
            if viewport_label == "desktop"
            else None
        )
        selected_region = graph_reader_page.get_by_test_id("graph-selected-region")
        expect(selected_region).to_be_visible(timeout=30_000)
        viewport_article_link = selected_region.get_by_role(
            "link", name="Open article", exact=True
        ).first
        expect(viewport_article_link).to_be_visible(timeout=30_000)
        selected_region.scroll_into_view_if_needed()
        viewport_article_link.scroll_into_view_if_needed()
        selected_box = selected_region.bounding_box()
        graph_link_box = viewport_article_link.bounding_box()
        _require_viewport_intersection(
            selected_box,
            viewport_width,
            viewport_height,
            f"{viewport_label} selected Graph region",
        )
        _require_viewport_containment(
            graph_link_box,
            viewport_width,
            viewport_height,
            f"{viewport_label} Graph Article action",
        )
        _focus_via_tab(graph_reader_page, viewport_article_link, max_steps=40)
        viewport_article_link.press("Enter")
        graph_reader_page.wait_for_function(
            "articleId => location.pathname === `/articles/${articleId}`",
            arg=CRB_ARTICLE_ID,
            timeout=30_000,
        )
        viewport_reader_heading = graph_reader_page.locator("article#article-start > h1")
        expect(viewport_reader_heading).to_have_text(CRB_TITLE, timeout=30_000)
        expect(viewport_reader_heading).to_be_focused()
        _require_visible_focus(
            viewport_reader_heading, f"{viewport_label} Graph-origin Reader heading"
        )
        if viewport_label == "desktop":
            graph_reader_page.evaluate("window.dispatchEvent(new Event('resize'))")
            graph_reader_page.wait_for_timeout(450)
            _require_viewport_containment(
                viewport_reader_heading.bounding_box(),
                viewport_width,
                viewport_height,
                "Graph-origin Reader heading with saved progress",
            )
            _require(
                graph_reader_page.evaluate(
                    "localStorage.getItem('scientific-spaces-reader-progress-v1')"
                )
                == saved_reader_progress,
                "Graph-origin Reader overwrote saved progress before user movement",
            )
            checks["graph_reader_saved_progress_heading_focus"] = True
        viewport_return = graph_reader_page.get_by_role(
            "link", name="Return to graph", exact=True
        )
        expect(viewport_return).to_have_attribute("href", graph_round_trip_path)
        viewport_reader_heading.scroll_into_view_if_needed()
        viewport_return.scroll_into_view_if_needed()
        _require_viewport_containment(
            viewport_reader_heading.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Reader heading",
        )
        _require_viewport_containment(
            viewport_return.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} Reader return action",
        )
        _require(
            _document_width(graph_reader_page) <= viewport_width,
            f"{viewport_label} Graph-origin Reader overflows horizontally",
        )
        viewport_end_session = graph_reader_page.get_by_role(
            "button", name="End session", exact=True
        )
        expect(viewport_end_session).to_be_enabled(timeout=30_000)
        viewport_end_session.click()
        expect(viewport_end_session).to_be_disabled()
        viewport_return.press("Enter")
        graph_reader_page.wait_for_function(
            "expected => location.pathname + location.search === expected",
            arg=graph_round_trip_path,
            timeout=30_000,
        )
        returned_viewport_link = graph_reader_page.get_by_role(
            "link", name="Open article", exact=True
        ).first
        expect(returned_viewport_link).to_be_focused(timeout=30_000)
        _require_visible_focus(
            returned_viewport_link, f"{viewport_label} restored Graph Article action"
        )
        if viewport_label == "desktop":
            _require(
                graph_reader_page.evaluate(
                    "localStorage.getItem('scientific-spaces-reader-progress-v1')"
                )
                == saved_reader_progress,
                "Graph-origin Reader cleanup overwrote saved progress without scrolling",
            )
        returned_viewport_link.scroll_into_view_if_needed()
        _require_viewport_containment(
            returned_viewport_link.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} restored Graph Article action",
        )
        _require(
            _document_width(graph_reader_page) <= viewport_width,
            f"{viewport_label} returned Graph workspace overflows horizontally",
        )
        checks[f"graph_reader_{viewport_label}_viewport"] = True
        graph_reader_context.close()

    storage_denied_context = browser.new_context(
        viewport={"width": 320, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    storage_denied_context.add_init_script(
        script="""
        (() => {
          const originalSetItem = Storage.prototype.setItem;
          Storage.prototype.setItem = function (key, value) {
            if (this === window.sessionStorage) {
              throw new DOMException("session storage write denied", "QuotaExceededError");
            }
            if (key === "scientific-spaces-reading-history-v1") {
              throw new DOMException("reading history denied", "QuotaExceededError");
            }
            return originalSetItem.call(this, key, value);
          };
        })();
        """
    )
    _install_network_guard(storage_denied_context, blocked_external)
    storage_denied_page = _new_observed_page(
        storage_denied_context,
        console_errors,
        page_errors,
        label="graph-reader-storage-denied",
    )
    storage_denied_reader = (
        f"/articles/{CRB_ARTICLE_ID}?"
        + urlencode({"from": graph_round_trip_path})
    )
    storage_denied_page.goto(
        f"{FRONTEND_URL}{storage_denied_reader}", wait_until="domcontentloaded"
    )
    _wait_for_application_shell(storage_denied_page)
    storage_denied_page.wait_for_function(
        "articleId => location.pathname === `/articles/${articleId}`",
        arg=CRB_ARTICLE_ID,
        timeout=30_000,
    )
    storage_denied_heading = storage_denied_page.locator("article#article-start > h1")
    expect(storage_denied_heading).to_have_text(CRB_TITLE, timeout=30_000)
    expect(storage_denied_heading).to_be_focused()
    _require_visible_focus(storage_denied_heading, "storage-denied Reader heading")
    expect(
        storage_denied_page.get_by_text(
            "Reading history is unavailable in this browser session.", exact=True
        )
    ).to_be_visible()
    expect(
        storage_denied_page.get_by_text("Article unavailable", exact=True)
    ).to_have_count(0)
    storage_denied_return = storage_denied_page.get_by_role(
        "link", name="Return to graph", exact=True
    )
    expect(storage_denied_return).to_have_attribute("href", graph_round_trip_path)
    storage_denied_end_session = storage_denied_page.get_by_role(
        "button", name="End session", exact=True
    )
    expect(storage_denied_end_session).to_be_enabled(timeout=30_000)
    storage_denied_end_session.click()
    expect(storage_denied_end_session).to_be_disabled()
    _focus_via_tab(storage_denied_page, storage_denied_return)
    storage_denied_return.press("Enter")
    storage_denied_page.wait_for_function(
        "expected => location.pathname + location.search === expected",
        arg=graph_round_trip_path,
        timeout=30_000,
    )
    storage_denied_selected_region = storage_denied_page.get_by_test_id(
        "graph-selected-region"
    )
    expect(storage_denied_selected_region).to_be_visible(timeout=30_000)
    expect(storage_denied_selected_region).to_be_focused(timeout=30_000)
    _require_visible_focus(
        storage_denied_selected_region,
        "storage-denied returned Graph selected region",
    )
    storage_denied_selected_region.scroll_into_view_if_needed()
    _require_viewport_containment(
        storage_denied_selected_region.bounding_box(),
        320,
        844,
        "storage-denied returned Graph selected region",
    )
    _require(
        _document_width(storage_denied_page) <= 320,
        "storage-denied Graph round trip overflows horizontally",
    )
    checks["graph_reader_storage_unavailable_fallback"] = True
    storage_denied_context.close()

    mobile_context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    mobile_context.add_init_script(
        script=f"""
        localStorage.setItem(
          "scientific-spaces-reading-history-v1",
          {json.dumps(json.dumps([{
              "id": CRB_ARTICLE_ID,
              "title": CRB_TITLE,
              "url": "https://spaces.ac.cn/archives/6508",
              "last_read_at": "2026-08-31T02:00:00.000Z",
          }], ensure_ascii=False))}
        );
        localStorage.setItem(
          "scientific-spaces-reader-progress-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "items": [{
                  "article_id": CRB_ARTICLE_ID,
                  "section_id": "regularity",
                  "section_title": "正则条件",
                  "progress": 42,
                  "updated_at": "2026-08-31T02:00:00.000Z",
              }],
          }, ensure_ascii=False))}
        );
        localStorage.setItem(
          "scientific-spaces-study-session-v1",
          {json.dumps(json.dumps({
              "version": 1,
              "active_article_id": CRB_ARTICLE_ID,
              "updated_at": "2026-08-31T02:03:00.000Z",
              "items": [
                  {
                      "article_id": CRB_ARTICLE_ID,
                      "title": CRB_TITLE,
                      "section_id": "regularity",
                      "added_at": "2026-08-31T02:00:00.000Z",
                  },
                  {
                      "article_id": ATTENTION_ARTICLE_ID,
                      "title": ATTENTION_TITLE,
                      "section_id": None,
                      "added_at": "2026-08-31T02:01:00.000Z",
                  },
              ],
          }, ensure_ascii=False))}
        );
        """
    )
    _install_network_guard(mobile_context, blocked_external)
    mobile_page = mobile_context.new_page()
    mobile_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    mobile_page.on(
        "pageerror", lambda error: _capture_page_error(page_errors, "mobile", mobile_page, error)
    )
    mobile_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(mobile_page)
    expect(
        mobile_page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "dashboard"
    )
    mobile_search_trigger = mobile_page.get_by_test_id("global-search-trigger-mobile")
    expect(mobile_search_trigger).to_be_visible()
    _require(
        mobile_search_trigger.inner_text().strip() == "Search",
        "mobile search trigger exposes shortcut instructions",
    )
    mobile_search_trigger.click()
    mobile_search_dialog = mobile_page.get_by_test_id("global-search-dialog")
    expect(mobile_search_dialog).to_be_visible()
    mobile_search_input = mobile_search_dialog.get_by_label("Search library")
    expect(mobile_search_input).to_be_focused()
    _require(
        mobile_search_dialog.locator('[data-testid="global-search-result-workspace"]').count() == 7,
        "mobile quick navigation does not expose seven stable workspaces",
    )
    mobile_search_box = mobile_search_dialog.locator('[role="dialog"]').bounding_box()
    _require(
        mobile_search_box is not None and mobile_search_box["width"] <= 390,
        f"mobile global search dialog overflowed: {mobile_search_box}",
    )
    mobile_search_input.fill("CRB")
    mobile_article_result = mobile_search_dialog.get_by_test_id("global-search-result-article").first
    expect(mobile_article_result).to_contain_text(CRB_TITLE, timeout=30_000)
    mobile_search_input.press("Escape")
    expect(mobile_search_dialog).to_have_count(0)
    expect(mobile_search_trigger).to_be_focused()
    _require(_document_width(mobile_page) <= 390, "mobile Shell overflows after global search")
    checks["mobile_global_search"] = True

    mobile_menu_button = mobile_page.get_by_role("button", name="Open navigation", exact=True)
    expect(mobile_menu_button).to_have_attribute("aria-expanded", "false")
    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    expect(mobile_menu_button).to_have_attribute("aria-expanded", "true")
    close_navigation = mobile_page.get_by_role("button", name="Close navigation", exact=True)
    expect(close_navigation).to_be_focused()
    _require(
        mobile_navigation.locator('nav[aria-label="Primary"] a').count() == 7,
        "mobile drawer does not expose seven primary workspaces",
    )
    expect(
        mobile_navigation.locator('nav[aria-label="Primary"] [aria-current="page"]')
    ).to_have_text("Dashboard")
    close_navigation.press("Escape")
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["mobile_navigation_focus_and_escape"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    close_navigation = mobile_page.get_by_role("button", name="Close navigation", exact=True)
    expect(close_navigation).to_be_focused()
    close_navigation.click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["shell_drawer_close_button_dismissal"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_page.get_by_role("button", name="Close navigation overlay", exact=True).click(
        position={"x": 10, "y": 200}
    )
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_menu_button).to_be_focused()
    checks["shell_drawer_backdrop_dismissal"] = True

    stat_boxes = mobile_page.locator('[data-testid="dashboard-stats"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(len({round(item["x"]) for item in stat_boxes}) == 2, "mobile dashboard statistics are not two columns")
    expect(mobile_page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    continue_learning_action = mobile_page.get_by_role(
        "link",
        name="Resume focused session",
        exact=True,
    ).bounding_box()
    _require(
        continue_learning_action is not None
        and continue_learning_action["y"] + continue_learning_action["height"] <= 844,
        "Focused Session resume action is clipped by the first mobile viewport",
    )
    _require(_document_width(mobile_page) <= 390, "mobile Dashboard overflows the viewport")
    expect(mobile_page.get_by_role("heading", name="Next Actions", exact=True)).to_be_visible()
    checks["mobile_dashboard_density"] = True

    mobile_menu_button.click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Saved", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Saved Learning Library", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "library"
    )
    mobile_shell_main = mobile_page.get_by_test_id("shell-main-content")
    expect(mobile_shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_shell_main, "mobile Drawer destination")
    mobile_same_url_history = mobile_page.evaluate("history.length")
    mobile_same_url_location = mobile_page.url
    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Saved", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_shell_main).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_shell_main, "mobile same-URL Drawer destination")
    _require(
        mobile_page.evaluate("history.length") == mobile_same_url_history,
        "mobile same-URL Drawer navigation added history",
    )
    _require(mobile_page.url == mobile_same_url_location, "mobile same-URL Drawer changed URL")
    checks["shell_mobile_drawer_route_focus"] = True
    expect(mobile_page.get_by_role("button", name="Continue (0)", exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(mobile_page.get_by_role("heading", name="Continue Learning", exact=True)).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Bookmarked", exact=True)).to_be_visible()
    expect(mobile_page.get_by_role("heading", name="Recently Read", exact=True)).to_be_visible()
    library_stat_boxes = mobile_page.locator('[data-testid="saved-library-summary"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(
        len({round(item["x"]) for item in library_stat_boxes}) == 2,
        "mobile Saved Library statistics are not two columns",
    )
    library_width = _document_width(mobile_page)
    _require(library_width <= 390, f"mobile Saved Library overflowed to {library_width}px")
    checks["mobile_saved_learning_library"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Session", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "session"
    )
    expect(mobile_page.get_by_test_id("study-session-summary")).to_contain_text("2 Articles")
    expect(mobile_page.get_by_test_id("study-session-item")).to_have_count(2)
    session_width = _document_width(mobile_page)
    first_session_item_box = mobile_page.get_by_test_id("study-session-item").first.bounding_box()
    _require(
        first_session_item_box is not None
        and first_session_item_box["x"] >= 0
        and first_session_item_box["x"] + first_session_item_box["width"] <= 390,
        f"mobile Session queue item is clipped: {first_session_item_box}",
    )
    _require(session_width <= 390, f"mobile Session overflowed to {session_width}px")
    checks["mobile_focused_study_session"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Articles", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("application-shell")).to_have_attribute(
        "data-workspace", "articles"
    )
    expect(mobile_page.get_by_text(re.compile(r"^Page 1 / "))).to_be_visible(timeout=30_000)
    checks["mobile_navigation_route_selection"] = True
    list_width = _document_width(mobile_page)
    mobile_page.get_by_role("link", name=CRB_TITLE, exact=True).click()
    expect(mobile_page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(mobile_page.locator(".reader-markdown .katex").first).to_be_visible()
    reading_tools_link = mobile_page.get_by_role("link", name="Reading tools", exact=True)
    outline_link = mobile_page.get_by_role("link", name="Outline", exact=True)
    expect(reading_tools_link).to_be_visible()
    expect(outline_link).to_be_visible()
    reading_tools_box = reading_tools_link.bounding_box()
    _require(
        reading_tools_box is not None and reading_tools_box["y"] < 844,
        "mobile Reading tools entry is below the first viewport",
    )
    detail_width = _document_width(mobile_page)
    formula_overflow = mobile_page.locator(".reader-markdown .katex-display").first.evaluate(
        "(node) => getComputedStyle(node).overflowX"
    )
    _require(list_width <= 390, f"mobile Article List overflowed to {list_width}px")
    _require(detail_width <= 390, f"mobile Article Detail overflowed to {detail_width}px")
    _require(formula_overflow == "auto", "display formula does not retain local horizontal scrolling")
    _require(
        mobile_page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches"),
        "reduced-motion browser preference is not active",
    )
    outline_link.click()
    expect(mobile_page.get_by_test_id("article-outline")).to_be_visible()
    reading_tools_link.click()
    expect(mobile_page.get_by_role("link", name="Ask tutor", exact=True)).to_be_visible()
    expect(mobile_page.get_by_role("link", name="Explore graph", exact=True)).to_be_visible()
    mobile_end_button = mobile_page.get_by_role("button", name="End session", exact=True)
    expect(mobile_end_button).to_be_enabled(timeout=30_000)
    mobile_end_button.click()
    expect(mobile_end_button).to_be_disabled()
    checks["mobile_layout_and_formula_scroll"] = True

    mobile_page.get_by_role("link", name="Ask tutor", exact=True).click()
    expect(mobile_page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    expect(mobile_page.get_by_test_id("tutor-selected-article")).to_contain_text(CRB_TITLE)
    expect(mobile_page.get_by_text("Advanced context", exact=True)).to_be_visible()
    tutor_width = _document_width(mobile_page)
    _require(tutor_width <= 390, f"mobile Tutor page overflowed to {tutor_width}px")
    checks["mobile_guided_tutor_workspace"] = True

    mobile_page.get_by_role("button", name="Open navigation", exact=True).click()
    mobile_navigation = mobile_page.get_by_test_id("mobile-navigation")
    expect(mobile_navigation).to_be_visible()
    mobile_navigation.get_by_role("link", name="Graph", exact=True).click()
    expect(mobile_navigation).to_have_count(0)
    expect(mobile_page.get_by_role("heading", name="Knowledge Graph", exact=True)).to_be_visible()
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    mobile_page.locator('select[name="node_type"]').select_option("concept")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    mobile_graph_node = (
        mobile_page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(mobile_graph_node).to_be_visible(timeout=30_000)
    mobile_graph_node.click()
    mobile_selected_region = mobile_page.get_by_test_id("graph-selected-region")
    expect(mobile_selected_region).to_be_focused(timeout=30_000)
    _require_visible_focus(mobile_selected_region, "mobile selected Graph region")
    _wait_for_test_id_near_viewport_top(mobile_page, "graph-selected-region")
    mobile_selected_box = mobile_selected_region.bounding_box()
    _require(
        mobile_selected_box is not None
        and mobile_selected_box["y"] < 200
        and mobile_selected_box["y"] + mobile_selected_box["height"] > 0,
        f"mobile selected detail does not intersect the viewport: {mobile_selected_box}",
    )
    _require(
        "node_id=concept%3Aattention" in mobile_page.url and "q=Attention" in mobile_page.url,
        f"mobile Graph selection URL is incomplete: {mobile_page.url}",
    )
    mobile_concept_set = mobile_page.get_by_test_id("concept-study-set")
    expect(mobile_concept_set).to_be_visible(timeout=30_000)
    expect(mobile_concept_set.get_by_role("link", name="Explain concept", exact=True)).to_be_visible()
    expect(mobile_concept_set.get_by_role("link", name="Open concept quiz", exact=True)).to_be_visible()
    mobile_concept_box = mobile_concept_set.bounding_box()
    _require(
        mobile_concept_box is not None
        and mobile_concept_box["x"] >= 0
        and mobile_concept_box["x"] + mobile_concept_box["width"] <= 390,
        f"mobile Concept Study Set is clipped: {mobile_concept_box}",
    )
    mobile_graph_width = _document_width(mobile_page)
    _require(mobile_graph_width <= 390, f"mobile Graph page overflowed to {mobile_graph_width}px")
    checks["mobile_concept_study_set"] = True
    mobile_page.get_by_role("button", name="Back to results", exact=True).click()
    expect(mobile_graph_node).to_be_focused()
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("No matching graph node")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    expect(mobile_page.get_by_text("No nodes match the current filters.", exact=True)).to_be_visible(
        timeout=30_000
    )
    mobile_page.get_by_role("group", name="Explore panel").get_by_role(
        "button", name="Selected", exact=True
    ).click()
    expect(mobile_selected_region).to_be_focused()
    mobile_page.get_by_role("button", name="Back to results", exact=True).click()
    expect(mobile_page.get_by_role("heading", name="Nodes", exact=True)).to_be_focused()
    mobile_page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    mobile_page.get_by_role("button", name="Apply", exact=True).click()
    expect(mobile_graph_node).to_be_visible(timeout=30_000)
    checks["mobile_graph_missing_origin_focus_fallback"] = True
    mobile_graph_node.click()
    expect(mobile_selected_region).to_be_focused()
    mobile_page.get_by_role("group", name="Graph workspace view").get_by_role(
        "button", name="Knowledge context", exact=True
    ).click()
    mobile_context_region = mobile_page.locator("#graph-context-workspace")
    expect(mobile_context_region).to_be_focused()
    _require_visible_focus(mobile_context_region, "mobile Knowledge Context region")
    expect(mobile_page.get_by_test_id("graph-context-explorer")).to_be_visible()
    expect(mobile_page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    mobile_graph_box = mobile_page.locator(".knowledge-graph-canvas").bounding_box()
    mobile_map_node_box = mobile_page.get_by_role(
        "button", name=re.compile(r"^Selected Concept: Attention", re.I)
    ).bounding_box()
    _require(
        mobile_graph_box is not None and mobile_graph_box["width"] <= 390,
        f"mobile visual Graph canvas overflowed: {mobile_graph_box}",
    )
    _require_box_inside(
        mobile_graph_box,
        mobile_map_node_box,
        "mobile selected Graph node",
        minimum_width=80,
        minimum_height=30,
    )
    expect(mobile_page.locator("#graph-context-workspace")).to_be_focused()
    expect(mobile_page.locator(".react-flow__controls")).to_be_visible()
    mobile_page.get_by_test_id("graph-view-list").click()
    expect(mobile_page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    checks["mobile_visual_knowledge_explorer"] = True
    mobile_context.close()

    _verify_reader_learning_mutation_integrity(
        browser,
        iteration=iteration,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )
    checks["reader_learning_mutation_integrity"] = True

    unexpected_console_errors = _unexpected_console_errors(console_errors)
    _require(not blocked_external, f"unexpected external requests: {blocked_external}")
    _require(not unexpected_console_errors, f"unexpected console errors: {unexpected_console_errors}")
    _require(not page_errors, f"uncaught page errors: {page_errors}")
    checks["local_only_network_and_console"] = True

    return {
        "iteration": iteration,
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "checks": checks,
        "mobile_widths": {
            "viewport": 390,
            "saved_library": library_width,
            "study_session": session_width,
            "article_list": list_width,
            "article_detail": detail_width,
            "tutor": tutor_width,
            "graph": mobile_graph_width,
        },
        "external_network_request_count": len(blocked_external),
        "console_error_count": len(unexpected_console_errors),
        "page_error_count": len(page_errors),
    }


def _verify_reader_learning_mutation_integrity(
    browser,
    *,
    iteration: int,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    context.add_init_script(
        script="""
        (() => {
          const originalFetch = window.fetch.bind(window);
          window.__p3029InitialLoadOriginalFetch = originalFetch;
          window.__p3029InitialLoadGate = { pendingCount: 0, releases: [] };
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const method = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            const response = await originalFetch(...args);
            if (
              method === "GET"
              && (target.endsWith("/learning/bookmarks") || target.includes("/learning/notes/"))
            ) {
              window.__p3029InitialLoadGate.pendingCount += 1;
              await new Promise((resolve) => window.__p3029InitialLoadGate.releases.push(resolve));
            }
            return response;
          };
        })();
        """
    )
    _install_network_guard(context, blocked_external)
    session_sequence = 0

    def provide_isolated_reader_session(route) -> None:
        nonlocal session_sequence
        if route.request.method != "POST":
            route.continue_()
            return
        session_sequence += 1
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": f"p3-029-{iteration}-{session_sequence}",
                    "article_id": json.loads(route.request.post_data or "{}").get("article_id"),
                    "started_at": "2026-09-05T00:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        )

    context.route(re.compile(r".*/learning/sessions$"), provide_isolated_reader_session)
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="reader-mutation-integrity",
    )
    page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    page.wait_for_function(
        "() => window.__p3029InitialLoadGate?.pendingCount === 2",
        timeout=30_000,
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_disabled()
    expect(page.get_by_text("Loading bookmark status.", exact=True)).to_be_visible()
    initial_draft = page.get_by_label("New learning note", exact=True)
    initial_draft.fill("P3-029 initial load guard")
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
    expect(page.get_by_text("Loading notes...", exact=True)).to_be_visible()
    page.evaluate(
        """
        () => {
          for (const release of window.__p3029InitialLoadGate.releases.splice(0)) release();
        }
        """
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "false")
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_enabled()
    initial_draft.fill("")
    page.evaluate(
        """
        () => {
          window.fetch = window.__p3029InitialLoadOriginalFetch;
          delete window.__p3029InitialLoadOriginalFetch;
          delete window.__p3029InitialLoadGate;
        }
        """
    )

    context.close()
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.route(re.compile(r".*/learning/sessions$"), provide_isolated_reader_session)
    page = _new_observed_page(
        context,
        console_errors,
        page_errors,
        label="reader-mutation-integrity",
    )
    page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    baseline_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    baseline_note_count = int(baseline_notes["total"])
    baseline_note_content = f"P3-011 iteration {iteration}"
    baseline_note_records = [
        item for item in baseline_notes["items"] if item["content"] == baseline_note_content
    ]
    _require(len(baseline_note_records) == 1, f"Reader mutation baseline note is ambiguous: {baseline_notes}")
    baseline_note_id = baseline_note_records[0]["note_id"]
    duplicate_text = f"P3-029 duplicate guard {iteration}"
    _install_mutation_response_gate(page, f"/learning/notes/{CRB_ARTICLE_ID}", "POST")
    page.get_by_label("New learning note", exact=True).fill(duplicate_text)
    add_note = page.get_by_role("button", name="Add note", exact=True)
    add_note.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Saving note...", exact=True)).to_be_disabled()
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("Saving note...")
    pending_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        pending_notes["total"] == baseline_note_count + 1,
        f"rapid note activation did not persist exactly one record: {pending_notes}",
    )
    _release_mutation_response_gate(page)
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("Note saved.")
    duplicate_note = page.get_by_test_id("learning-note").filter(has_text=duplicate_text)
    expect(duplicate_note).to_have_count(1)
    confirmed_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    duplicate_records = [item for item in confirmed_notes["items"] if item["content"] == duplicate_text]
    _require(
        confirmed_notes["total"] == baseline_note_count + 1
        and len(duplicate_records) == 1,
        f"note persistence and Reader identity diverged: {confirmed_notes}",
    )
    _restore_mutation_response_gate(page)

    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    _install_mutation_response_gate(
        page,
        f"/learning/notes/{duplicate_records[0]['note_id']}",
        "DELETE",
    )
    duplicate_delete.focus()
    _start_note_delete_focus_trace(page)
    duplicate_delete.press("Enter")
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    expect(delete_confirmation).to_be_visible()
    expect(delete_confirmation).to_contain_text("cannot be undone")
    cancel_delete = delete_confirmation.get_by_role("button", name="Cancel", exact=True)
    confirm_delete = delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    )
    expect(cancel_delete).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "opening note deletion confirmation",
        (
            ("testid:note-mutation-status", False),
            ("button:Cancel", True),
        ),
    )
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "opening note deletion confirmation issued a DELETE request",
    )
    expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note.get_by_role("button", name="Edit", exact=True)).to_be_disabled()
    expect(baseline_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    expect(cancel_delete).to_be_enabled()
    expect(confirm_delete).to_be_enabled()
    cancel_delete.press("Tab")
    expect(confirm_delete).to_be_focused()
    confirm_delete.press("Shift+Tab")
    expect(cancel_delete).to_be_focused()
    _start_note_delete_focus_trace(page)
    cancel_delete.press("Escape")
    expect(delete_confirmation).to_have_count(0)
    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    expect(duplicate_delete).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "escaping note deletion confirmation",
        (
            ("testid:note-mutation-status", True),
            ("button:Delete", False),
        ),
    )
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "Escape from note deletion confirmation issued a DELETE request",
    )

    duplicate_delete.press(" ")
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    cancel_delete = delete_confirmation.get_by_role("button", name="Cancel", exact=True)
    expect(cancel_delete).to_be_focused()
    cancel_delete.click()
    duplicate_delete = duplicate_note.get_by_role("button", name="Delete", exact=True)
    expect(duplicate_delete).to_be_focused()
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
        "Cancel from note deletion confirmation issued a DELETE request",
    )

    duplicate_delete.click()
    delete_confirmation = duplicate_note.get_by_test_id("note-delete-confirmation")
    expect(delete_confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_focused()
    confirm_delete = delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    )
    confirm_delete.press("Enter")
    page.keyboard.press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(delete_confirmation).to_be_visible()
    expect(delete_confirmation).to_have_attribute("aria-busy", "true")
    expect(delete_confirmation).to_be_focused()
    expect(delete_confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_disabled()
    expect(delete_confirmation.get_by_role("button", name="Deleting...", exact=True)).to_be_disabled()
    expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note.get_by_role("button", name="Edit", exact=True)).to_be_disabled()
    expect(baseline_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    _start_note_delete_focus_trace(page)
    _release_mutation_response_gate(page)
    note_status = page.get_by_test_id("note-mutation-status")
    expect(note_status).to_have_text("Note deleted.")
    expect(note_status).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "completing confirmed note deletion",
        (("testid:note-mutation-status", True),),
    )
    expect(duplicate_note).to_have_count(0)
    deleted_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        deleted_notes["total"] == baseline_note_count,
        f"confirmed note deletion did not persist exactly once: {deleted_notes}",
    )
    _restore_mutation_response_gate(page)

    response_loss_text = f"P3-031 unconfirmed delete {iteration}"
    note_draft = page.get_by_label("New learning note", exact=True)
    note_draft.fill(response_loss_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("Note saved.")
    response_loss_note = page.get_by_test_id("learning-note").filter(
        has_text=response_loss_text
    )
    expect(response_loss_note).to_have_count(1)
    response_loss_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    response_loss_records = [
        item for item in response_loss_notes["items"] if item["content"] == response_loss_text
    ]
    _require(
        len(response_loss_records) == 1,
        f"response-loss note identity is ambiguous: {response_loss_notes}",
    )
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{response_loss_records[0]['note_id']}",
        "DELETE",
        "intentional P3-029 unconfirmed delete result",
    )
    response_loss_note.get_by_role("button", name="Delete", exact=True).click()
    response_loss_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).focus()
    _start_note_delete_focus_trace(page)
    response_loss_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).click()
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "deletion could not be confirmed"
    )
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "Reload this Article before retrying"
    )
    expect(response_loss_note).to_have_count(1)
    expect(
        response_loss_note.get_by_role("button", name="Delete", exact=True)
    ).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "handling lost note deletion response",
        (
            ("testid:note-mutation-status", True),
            ("button:Delete", False),
        ),
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    page.wait_for_timeout(250)
    _require(
        page.evaluate("() => window.__p3029FailureGate?.callCount") == 1,
        "lost delete response was replayed automatically",
    )
    cleaned_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        cleaned_notes["total"] == baseline_note_count
        and all(
            item["note_id"] != response_loss_records[0]["note_id"]
            for item in cleaned_notes["items"]
        ),
        f"lost delete response did not preserve the exact unknown persistence result: {cleaned_notes}",
    )
    _restore_one_shot_mutation_failure(page)

    failed_text = f"P3-029 unconfirmed draft {iteration}"
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{CRB_ARTICLE_ID}",
        "POST",
        "intentional P3-029 unconfirmed note result",
    )
    note_draft = page.get_by_label("New learning note", exact=True)
    note_draft.fill(failed_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    failed_feedback = page.get_by_test_id("note-mutation-error")
    expect(failed_feedback).to_have_attribute("role", "alert")
    expect(failed_feedback).to_contain_text("could not be confirmed")
    expect(note_draft).to_have_value(failed_text)
    expect(
        page.get_by_test_id("learning-note").filter(has_text=failed_text)
    ).to_have_count(0)
    failed_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    unknown_note_records = [item for item in failed_notes["items"] if item["content"] == failed_text]
    _require(
        failed_notes["total"] == baseline_note_count + 1 and len(unknown_note_records) == 1,
        f"lost note response did not preserve the exact unknown persistence result: {failed_notes}",
    )
    unknown_cleanup = context.request.delete(
        f"{API_URL}/learning/notes/{unknown_note_records[0]['note_id']}"
    )
    _require(unknown_cleanup.status == 204, "unknown-result note cleanup failed")
    _restore_one_shot_mutation_failure(page)

    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    expect(baseline_note).to_have_count(1)
    baseline_note.get_by_role("button", name="Edit", exact=True).click()
    retained_edit = f"P3-029 retained edit {iteration}"
    edit_field = page.get_by_label("Edit learning note", exact=True)
    editing_note = edit_field.locator("xpath=ancestor::article[@data-testid='learning-note']")
    edit_field.fill(retained_edit)
    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/notes/{baseline_note_id}",
        "PUT",
        "intentional P3-029 unconfirmed update result",
    )
    editing_note.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "update could not be confirmed"
    )
    expect(edit_field).to_have_value(retained_edit)
    update_failure_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    updated_unknown_records = [
        item
        for item in update_failure_notes["items"]
        if item["note_id"] == baseline_note_id and item["content"] == retained_edit
    ]
    _require(
        len(updated_unknown_records) == 1,
        f"lost update response did not preserve the exact unknown persistence result: {update_failure_notes}",
    )
    restore_update = context.request.put(
        f"{API_URL}/learning/notes/{baseline_note_id}",
        data={"content": baseline_note_content},
    )
    _require(restore_update.status == 200, "unknown-result note update restore failed")
    restored_update_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        any(
            item["note_id"] == baseline_note_id and item["content"] == baseline_note_content
            for item in restored_update_notes["items"]
        ),
        f"unknown-result note update restore did not read back exactly: {restored_update_notes}",
    )
    _restore_one_shot_mutation_failure(page)
    editing_note.get_by_role("button", name="Cancel", exact=True).click()

    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )

    _install_one_shot_mutation_failure(
        page,
        "/learning/notes/",
        "DELETE",
        "intentional P3-029 unconfirmed delete result",
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    baseline_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).focus()
    _start_note_delete_focus_trace(page)
    baseline_note.get_by_role(
        "button", name="Delete permanently", exact=True
    ).click()
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "deletion could not be confirmed"
    )
    expect(page.get_by_test_id("note-mutation-error")).to_contain_text(
        "Reload this Article before retrying"
    )
    expect(baseline_note).to_have_count(1)
    expect(
        baseline_note.get_by_role("button", name="Delete", exact=True)
    ).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "handling rejected note deletion request",
        (
            ("testid:note-mutation-status", True),
            ("button:Delete", False),
        ),
    )
    page.wait_for_timeout(250)
    _require(
        page.evaluate("() => window.__p3029FailureGate?.callCount") == 1,
        "rejected delete request was replayed automatically",
    )
    delete_failure_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(delete_failure_notes["total"] == baseline_note_count, "unconfirmed delete changed persistence")
    _restore_one_shot_mutation_failure(page)

    session_payload = {
        "version": 1,
        "active_article_id": CRB_ARTICLE_ID,
        "updated_at": "2026-09-05T00:00:00.000Z",
        "items": [
            {
                "article_id": CRB_ARTICLE_ID,
                "title": CRB_TITLE,
                "section_id": None,
                "added_at": "2026-09-05T00:00:00.000Z",
            },
            {
                "article_id": ATTENTION_ARTICLE_ID,
                "title": ATTENTION_TITLE,
                "section_id": None,
                "added_at": "2026-09-05T00:01:00.000Z",
            },
        ],
    }
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["scientific-spaces-study-session-v1", json.dumps(session_payload, ensure_ascii=False)],
    )
    page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}?from=%2Fsession",
        wait_until="domcontentloaded",
    )
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    transition_delete_requests: list[str] = []

    def record_unconfirmed_delete_request(request) -> None:
        if (
            request.method == "DELETE"
            and request.url.endswith(f"/learning/notes/{baseline_note_id}")
        ):
            transition_delete_requests.append(request.url)

    page.on("request", record_unconfirmed_delete_request)
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    _start_note_delete_focus_trace(page)
    page.evaluate(
        "() => window.history.pushState(null, '', '?from=%2Farticles%3Fq%3Dcrb')"
    )
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    _assert_note_delete_focus_continuity(
        page,
        "invalidating an awaiting query intent",
        ((f"heading:{CRB_TITLE}", True),),
    )
    _require(
        not transition_delete_requests,
        f"query transition issued an unconfirmed DELETE: {transition_delete_requests}",
    )

    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    page.go_forward(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    _require(
        not transition_delete_requests,
        f"query history issued an unconfirmed DELETE: {transition_delete_requests}",
    )
    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _require(
        not transition_delete_requests,
        f"Article switch issued an unconfirmed DELETE: {transition_delete_requests}",
    )

    page.go_back(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    page.go_forward(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    page.go_back(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    baseline_note = page.get_by_test_id("learning-note").filter(
        has_text=baseline_note_content
    )
    baseline_note.get_by_role("button", name="Delete", exact=True).click()
    expect(baseline_note.get_by_test_id("note-delete-confirmation")).to_be_visible()
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_test_id("note-delete-confirmation")).to_have_count(0)
    _require(
        not transition_delete_requests,
        f"history or reload issued an unconfirmed DELETE: {transition_delete_requests}",
    )
    transition_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        transition_notes["total"] == baseline_note_count,
        f"unconfirmed navigation changed note persistence: {transition_notes}",
    )

    stale_delete_text = f"P3-031 stale delete completion {iteration}"
    stale_delete_create = context.request.post(
        f"{API_URL}/learning/notes/{CRB_ARTICLE_ID}",
        data={"content": stale_delete_text},
    )
    _require(stale_delete_create.status == 200, "stale delete note setup failed")
    stale_delete_record = stale_delete_create.json()
    stale_delete_id = str(stale_delete_record["note_id"])
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    stale_delete_note = page.get_by_test_id("learning-note").filter(has_text=stale_delete_text)
    expect(stale_delete_note).to_have_count(1)
    _install_mutation_response_gate(
        page,
        f"/learning/notes/{stale_delete_id}",
        "DELETE",
    )
    stale_delete_note.get_by_role("button", name="Delete", exact=True).click()
    stale_delete_confirmation = stale_delete_note.get_by_test_id("note-delete-confirmation")
    expect(stale_delete_confirmation).to_be_visible()
    stale_delete_confirmation.get_by_role(
        "button", name="Delete permanently", exact=True
    ).press("Enter")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    _start_note_delete_focus_trace(page)
    page.evaluate(
        "() => window.history.pushState(null, '', '?from=%2Farticles%3Fq%3Dcrb')"
    )
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/articles?q=crb'"
    )
    expect(stale_delete_confirmation).to_have_count(0)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    expect(page.get_by_test_id("notes-controls")).to_have_attribute("aria-busy", "false")
    stale_delete_note = page.get_by_test_id("learning-note").filter(has_text=stale_delete_text)
    expect(stale_delete_note).to_have_count(1)
    expect(stale_delete_note.get_by_role("button", name="Delete", exact=True)).to_be_disabled()
    stale_delete_warning = page.get_by_test_id("note-mutation-error")
    expect(stale_delete_warning).to_contain_text("could not be confirmed after navigation")
    expect(stale_delete_warning).to_contain_text("Reload this Article before retrying")
    _assert_note_delete_focus_continuity(
        page,
        "invalidating a stale note deletion",
        ((f"heading:{CRB_TITLE}", True),),
    )
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_focused()
    expect(stale_delete_note).to_have_count(1)
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(stale_delete_warning).to_contain_text("could not be confirmed after navigation")
    _require(
        page.evaluate("() => window.__p3029MutationGate?.callCount") == 1,
        "stale delete completion created another DELETE request",
    )
    stale_delete_persisted = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    _require(
        all(item["note_id"] != stale_delete_id for item in stale_delete_persisted["items"]),
        f"stale delete persistence result was not recorded exactly: {stale_delete_persisted}",
    )
    _restore_mutation_response_gate(page)
    page.go_back(wait_until="domcontentloaded")
    page.wait_for_function(
        "() => new URLSearchParams(location.search).get('from') === '/session'"
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_text(stale_delete_text, exact=True)).to_have_count(0)
    page.evaluate(
        "([key, value]) => localStorage.setItem(key, value)",
        ["scientific-spaces-study-session-v1", json.dumps(session_payload, ensure_ascii=False)],
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("notes-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    stale_text = f"P3-029 stale Article A {iteration}"
    _install_mutation_response_gate(page, f"/learning/notes/{CRB_ARTICLE_ID}", "POST")
    page.get_by_label("New learning note", exact=True).fill(stale_text)
    page.get_by_role("button", name="Add note", exact=True).click()
    page.wait_for_function("() => window.__p3029MutationGate?.pendingCount === 1", timeout=30_000)
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_label("New learning note", exact=True)).to_have_value("")
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("note-mutation-error")).to_have_text("")
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(attention_heading).to_be_focused()
    expect(page.get_by_text(stale_text, exact=True)).to_have_count(0)
    expect(page.get_by_test_id("note-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("note-mutation-error")).to_have_text("")
    stale_notes = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
    stale_records = [item for item in stale_notes["items"] if item["content"] == stale_text]
    _require(len(stale_records) == 1, f"stale Article A request accounting failed: {stale_notes}")
    cleanup_response = context.request.delete(
        f"{API_URL}/learning/notes/{stale_records[0]['note_id']}"
    )
    _require(cleanup_response.status == 204, "stale Article A note cleanup failed")
    _restore_mutation_response_gate(page)

    original_stale_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    restore_crb_bookmark = any(
        item["article_id"] == CRB_ARTICLE_ID for item in original_stale_bookmarks["items"]
    )
    if restore_crb_bookmark:
        normalize_crb_bookmark = context.request.delete(
            f"{API_URL}/learning/bookmarks/{CRB_ARTICLE_ID}"
        )
        _require(normalize_crb_bookmark.status == 204, "stale bookmark destination setup failed")
    stale_bookmark_baseline = _api_json(context, "GET", "/learning/bookmarks")
    stale_bookmark_count = int(stale_bookmark_baseline["total"])
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
    )
    page.get_by_role("button", name="Save", exact=True).click()
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1",
        timeout=30_000,
    )
    page.get_by_role("link", name=f"Previous in session: {CRB_TITLE}", exact=True).click()
    crb_heading = page.get_by_role("heading", name=CRB_TITLE, exact=True)
    expect(crb_heading).to_be_visible(timeout=30_000)
    expect(crb_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    expect(page.get_by_text("This article is not bookmarked.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("bookmark-mutation-error")).to_have_text("")
    _release_mutation_response_gate(page)
    page.wait_for_timeout(250)
    expect(crb_heading).to_be_focused()
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    expect(page.get_by_text("This article is not bookmarked.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("")
    expect(page.get_by_test_id("bookmark-mutation-error")).to_have_text("")
    stale_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        stale_bookmarks["total"] == stale_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in stale_bookmarks["items"]) == 1,
        f"stale bookmark response accounting failed: {stale_bookmarks}",
    )
    stale_bookmark_cleanup = context.request.delete(
        f"{API_URL}/learning/bookmarks/{ATTENTION_ARTICLE_ID}"
    )
    _require(stale_bookmark_cleanup.status == 204, "stale bookmark cleanup failed")
    if restore_crb_bookmark:
        restore_crb_response = context.request.post(
            f"{API_URL}/learning/bookmarks/{CRB_ARTICLE_ID}"
        )
        _require(restore_crb_response.status == 200, "stale bookmark destination restore failed")
    _restore_mutation_response_gate(page)
    page.get_by_role("link", name=f"Next in session: {ATTENTION_TITLE}", exact=True).click()
    attention_heading = page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)
    expect(attention_heading).to_be_visible(timeout=30_000)
    expect(attention_heading).to_be_focused(timeout=30_000)
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute(
        "aria-busy", "false", timeout=30_000
    )

    baseline_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    baseline_bookmark_count = int(baseline_bookmarks["total"])
    save_bookmark = page.get_by_role("button", name="Save", exact=True)
    expect(save_bookmark).to_be_visible(timeout=30_000)
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
    )
    save_bookmark.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_test_id("bookmark-controls")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Saving...", exact=True)).to_be_disabled()
    _release_mutation_response_gate(page)
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("Bookmark saved.")
    expect(page.get_by_role("button", name="Remove", exact=True)).to_be_visible()
    stored_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        stored_bookmarks["total"] == baseline_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in stored_bookmarks["items"]) == 1,
        f"rapid bookmark activation did not persist exactly one record: {stored_bookmarks}",
    )
    _restore_mutation_response_gate(page)
    _install_mutation_response_gate(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "DELETE",
    )
    remove_bookmark = page.get_by_role("button", name="Remove", exact=True)
    remove_bookmark.evaluate("button => { button.click(); button.click(); }")
    page.wait_for_function(
        "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
        timeout=30_000,
    )
    expect(page.get_by_role("button", name="Removing...", exact=True)).to_be_disabled()
    removed_before_release = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        removed_before_release["total"] == baseline_bookmark_count,
        f"rapid bookmark removal did not persist exactly once: {removed_before_release}",
    )
    _release_mutation_response_gate(page)
    expect(page.get_by_test_id("bookmark-mutation-status")).to_have_text("Bookmark removed.")
    cleaned_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(cleaned_bookmarks["total"] == baseline_bookmark_count, "bookmark cleanup failed")
    _restore_mutation_response_gate(page)

    _install_one_shot_mutation_response_loss(
        page,
        f"/learning/bookmarks/{ATTENTION_ARTICLE_ID}",
        "POST",
        "intentional P3-029 unconfirmed bookmark result",
    )
    page.get_by_role("button", name="Save", exact=True).click()
    bookmark_failure = page.get_by_test_id("bookmark-mutation-error")
    expect(bookmark_failure).to_have_attribute("role", "alert")
    expect(bookmark_failure).to_contain_text("displayed bookmark state was kept")
    expect(page.get_by_role("button", name="Save", exact=True)).to_be_visible()
    failed_bookmarks = _api_json(context, "GET", "/learning/bookmarks")
    _require(
        failed_bookmarks["total"] == baseline_bookmark_count + 1
        and sum(item["article_id"] == ATTENTION_ARTICLE_ID for item in failed_bookmarks["items"]) == 1,
        f"lost bookmark response did not preserve the exact unknown persistence result: {failed_bookmarks}",
    )
    unknown_bookmark_cleanup = context.request.delete(
        f"{API_URL}/learning/bookmarks/{ATTENTION_ARTICLE_ID}"
    )
    _require(unknown_bookmark_cleanup.status == 204, "unknown-result bookmark cleanup failed")
    _restore_one_shot_mutation_failure(page)
    context.close()

    _verify_reader_note_delete_confirmation_viewports(
        browser,
        iteration=iteration,
        baseline_note_content=baseline_note_content,
        blocked_external=blocked_external,
        console_errors=console_errors,
        page_errors=page_errors,
    )


def _verify_reader_note_delete_confirmation_viewports(
    browser,
    *,
    iteration: int,
    baseline_note_content: str,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    session_sequence = 0

    def provide_isolated_viewport_session(route) -> None:
        nonlocal session_sequence
        if route.request.method != "POST":
            route.continue_()
            return
        session_sequence += 1
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": f"p3-031-viewport-{iteration}-{session_sequence}",
                    "article_id": json.loads(route.request.post_data or "{}").get("article_id"),
                    "started_at": "2026-09-05T00:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        )

    for viewport_width, viewport_height, viewport_label in (
        (1440, 900, "desktop"),
        (390, 844, "mobile"),
        (320, 844, "narrow"),
        (720, 450, "zoom-equivalent"),
    ):
        context = browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            locale="zh-CN",
            is_mobile=viewport_width <= 390,
        )
        _install_network_guard(context, blocked_external)
        context.route(re.compile(r".*/learning/sessions$"), provide_isolated_viewport_session)
        viewport_note_content = f"P3-031 {viewport_label} deletion focus {iteration}"
        viewport_note_create = context.request.post(
            f"{API_URL}/learning/notes/{CRB_ARTICLE_ID}",
            data={"content": viewport_note_content},
        )
        _require(
            viewport_note_create.status == 200,
            f"{viewport_label} note deletion setup failed",
        )
        viewport_note_id = str(viewport_note_create.json()["note_id"])
        page = _new_observed_page(
            context,
            console_errors,
            page_errors,
            label=f"reader-note-delete-{viewport_label}",
        )
        page.goto(f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}", wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(
            timeout=30_000
        )
        expect(page.get_by_test_id("notes-controls")).to_have_attribute(
            "aria-busy", "false", timeout=30_000
        )
        note = page.get_by_test_id("learning-note").filter(has_text=viewport_note_content)
        expect(note).to_have_count(1)
        delete_trigger = note.get_by_role("button", name="Delete", exact=True)
        delete_trigger.scroll_into_view_if_needed()
        _install_mutation_response_gate(page, "/learning/notes/", "DELETE")
        delete_trigger.focus()
        delete_trigger.press(" ")
        confirmation = note.get_by_test_id("note-delete-confirmation")
        expect(confirmation).to_be_visible()
        cancel = confirmation.get_by_role("button", name="Cancel", exact=True)
        destructive = confirmation.get_by_role(
            "button", name="Delete permanently", exact=True
        )
        expect(cancel).to_be_focused()
        _require_visible_focus(cancel, f"{viewport_label} note delete Cancel")
        confirmation.scroll_into_view_if_needed()
        _require_viewport_containment(
            confirmation.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} note deletion confirmation",
        )
        _require_viewport_containment(
            cancel.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} note deletion Cancel",
        )
        _require_viewport_containment(
            destructive.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} permanent deletion action",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} note deletion confirmation caused horizontal overflow",
        )
        cancel.press("Escape")
        expect(note.get_by_test_id("note-delete-confirmation")).to_have_count(0)
        expect(note.get_by_role("button", name="Delete", exact=True)).to_be_focused()
        _require(
            page.evaluate("() => window.__p3029MutationGate?.callCount") == 0,
            f"{viewport_label} confirmation cancellation issued a DELETE request",
        )
        persisted = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
        _require(
            any(item["note_id"] == viewport_note_id for item in persisted["items"]),
            f"{viewport_label} cancellation did not preserve the exact note: {persisted}",
        )
        delete_trigger = note.get_by_role("button", name="Delete", exact=True)
        delete_trigger.click()
        confirmation = note.get_by_test_id("note-delete-confirmation")
        destructive = confirmation.get_by_role(
            "button", name="Delete permanently", exact=True
        )
        destructive.press("Enter")
        page.wait_for_function(
            "() => window.__p3029MutationGate?.pendingCount === 1 && window.__p3029MutationGate?.callCount === 1",
            timeout=30_000,
        )
        expect(confirmation).to_have_attribute("aria-busy", "true")
        expect(confirmation).to_be_focused()
        _require_visible_focus(confirmation, f"{viewport_label} pending deletion confirmation")
        pending_destructive = confirmation.get_by_role("button", name="Deleting...", exact=True)
        expect(confirmation.get_by_role("button", name="Cancel", exact=True)).to_be_disabled()
        expect(pending_destructive).to_be_disabled()
        expect(page.get_by_label("New learning note", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name="Add note", exact=True)).to_be_disabled()
        for edit_button in page.get_by_role("button", name="Edit", exact=True).all():
            expect(edit_button).to_be_disabled()
        for other_delete in page.get_by_role("button", name="Delete", exact=True).all():
            expect(other_delete).to_be_disabled()
        confirmation.scroll_into_view_if_needed()
        _require_viewport_containment(
            confirmation.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} pending deletion confirmation",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} pending deletion caused horizontal overflow",
        )
        _release_mutation_response_gate(page)
        note_status = page.get_by_test_id("note-mutation-status")
        expect(note_status).to_have_text("Note deleted.")
        expect(note_status).to_be_focused()
        _require_visible_focus(note_status, f"{viewport_label} deletion status")
        _require_viewport_containment(
            note_status.bounding_box(),
            viewport_width,
            viewport_height,
            f"{viewport_label} deletion status",
        )
        expect(note).to_have_count(0)
        persisted_after_delete = _api_json(context, "GET", f"/learning/notes/{CRB_ARTICLE_ID}")
        _require(
            all(item["note_id"] != viewport_note_id for item in persisted_after_delete["items"]),
            f"{viewport_label} confirmed deletion did not remove the exact note: {persisted_after_delete}",
        )
        _require(
            any(item["content"] == baseline_note_content for item in persisted_after_delete["items"]),
            f"{viewport_label} confirmed deletion changed the baseline note: {persisted_after_delete}",
        )
        _require(
            _document_width(page) <= viewport_width,
            f"{viewport_label} deletion status caused horizontal overflow",
        )
        _restore_mutation_response_gate(page)
        context.close()


def _start_note_delete_focus_trace(page) -> None:
    page.evaluate(
        """
        () => {
          window.__p3031FocusTrace = [];
          const describe = (node) => {
            if (!(node instanceof HTMLElement)) return "missing";
            const testId = node.dataset.testid;
            if (testId) return `testid:${testId}`;
            if (node instanceof HTMLButtonElement) {
              return `button:${node.textContent?.trim() ?? ""}`;
            }
            if (/^H[1-6]$/.test(node.tagName)) {
              return `heading:${node.textContent?.trim() ?? ""}`;
            }
            return node.tagName;
          };
          const recordFocus = (source) => {
            window.__p3031FocusTrace.push({
              source,
              target: describe(document.activeElement),
              confirmationMounted: Boolean(
                document.querySelector('[data-testid="note-delete-confirmation"]')
              ),
            });
          };
          const focusListener = () => recordFocus("focusin");
          window.__p3031FocusListener = focusListener;
          document.addEventListener("focusin", focusListener, true);
          const observer = new MutationObserver(() => recordFocus("mutation"));
          observer.observe(document.body, { childList: true, subtree: true });
          window.__p3031FocusObserver = observer;
          recordFocus("start");
        }
        """
    )


def _assert_note_delete_focus_continuity(
    page,
    label: str,
    expected_focus_sequence: tuple[tuple[str, bool], ...],
) -> None:
    focus_trace = page.evaluate(
        """
        () => {
          window.__p3031FocusObserver?.disconnect();
          if (typeof window.__p3031FocusListener === "function") {
            document.removeEventListener("focusin", window.__p3031FocusListener, true);
          }
          const trace = [...(window.__p3031FocusTrace ?? [])];
          delete window.__p3031FocusObserver;
          delete window.__p3031FocusListener;
          delete window.__p3031FocusTrace;
          return trace;
        }
        """
    )
    _require(bool(focus_trace), f"{label} produced no focus trace evidence")
    _require(
        all(entry.get("target") != "BODY" for entry in focus_trace),
        f"{label} dropped focus to body: {focus_trace}",
    )
    focus_events = [entry for entry in focus_trace if entry.get("source") == "focusin"]
    next_index = 0
    for expected_target, expected_confirmation in expected_focus_sequence:
        for index in range(next_index, len(focus_events)):
            entry = focus_events[index]
            if (
                entry.get("target") == expected_target
                and entry.get("confirmationMounted") is expected_confirmation
            ):
                next_index = index + 1
                break
        else:
            raise AssertionError(
                f"{label} missed focus bridge {expected_target} "
                f"with confirmationMounted={expected_confirmation}: {focus_trace}"
            )


def _install_mutation_response_gate(page, endpoint: str, method: str) -> None:
    page.evaluate(
        """
        ({ endpoint, method }) => {
          if (typeof window.__p3029MutationOriginalFetch === "function") {
            throw new Error("P3-029 mutation response gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029MutationOriginalFetch = originalFetch;
          window.__p3029MutationGate = {
            endpoint,
            method,
            callCount: 0,
            pendingCount: 0,
            completedCount: 0,
            release: null,
          };
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (!target.includes(endpoint) || requestMethod !== method) {
              return originalFetch(...args);
            }
            const gate = window.__p3029MutationGate;
            gate.callCount += 1;
            const response = await originalFetch(...args);
            gate.pendingCount += 1;
            await new Promise((resolve) => { gate.release = resolve; });
            gate.release = null;
            gate.completedCount += 1;
            return response;
          };
        }
        """,
        {"endpoint": endpoint, "method": method},
    )


def _release_mutation_response_gate(page) -> None:
    page.wait_for_function(
        "() => typeof window.__p3029MutationGate?.release === 'function'",
        timeout=30_000,
    )
    expected_count = page.evaluate(
        """
        () => {
          const gate = window.__p3029MutationGate;
          const release = gate.release;
          gate.release = null;
          release();
          return gate.pendingCount;
        }
        """
    )
    page.wait_for_function(
        "expected => window.__p3029MutationGate?.completedCount >= expected",
        arg=expected_count,
        timeout=30_000,
    )


def _restore_mutation_response_gate(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3029MutationOriginalFetch === "function") {
            window.fetch = window.__p3029MutationOriginalFetch;
            delete window.__p3029MutationOriginalFetch;
            delete window.__p3029MutationGate;
          }
        }
        """
    )


def _install_one_shot_mutation_failure(
    page,
    endpoint: str,
    method: str,
    message: str,
) -> None:
    page.evaluate(
        """
        ({ endpoint, method, message }) => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            throw new Error("P3-029 failure gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029FailureOriginalFetch = originalFetch;
          window.__p3029FailureGate = { callCount: 0 };
          let rejected = false;
          window.fetch = (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.includes(endpoint) && requestMethod === method) {
              window.__p3029FailureGate.callCount += 1;
              if (!rejected) {
                rejected = true;
                return Promise.reject(new Error(message));
              }
            }
            return originalFetch(...args);
          };
        }
        """,
        {"endpoint": endpoint, "method": method, "message": message},
    )


def _install_one_shot_mutation_response_loss(
    page,
    endpoint: str,
    method: str,
    message: str,
) -> None:
    page.evaluate(
        """
        ({ endpoint, method, message }) => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            throw new Error("P3-029 response-loss gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3029FailureOriginalFetch = originalFetch;
          window.__p3029FailureGate = { callCount: 0 };
          let rejected = false;
          window.fetch = async (...args) => {
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.includes(endpoint) && requestMethod === method) {
              window.__p3029FailureGate.callCount += 1;
              if (!rejected) {
                rejected = true;
                await originalFetch(...args);
                throw new Error(message);
              }
            }
            return originalFetch(...args);
          };
        }
        """,
        {"endpoint": endpoint, "method": method, "message": message},
    )


def _restore_one_shot_mutation_failure(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3029FailureOriginalFetch === "function") {
            window.fetch = window.__p3029FailureOriginalFetch;
            delete window.__p3029FailureOriginalFetch;
            delete window.__p3029FailureGate;
          }
        }
        """
    )


def _install_network_guard(context, blocked_external: list[str]) -> None:
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}

    def route_request(route) -> None:
        parsed = urlparse(route.request.url)
        if parsed.scheme in {"about", "blob", "data"} or parsed.hostname in allowed_hosts:
            route.continue_()
            return
        blocked_external.append(route.request.url)
        route.abort("blockedbyclient")

    context.route("**/*", route_request)


def verify_backend_restart_persistence(
    runtime: dict[str, Path | dict[str, str]],
) -> dict[str, object]:
    environment = os.environ.copy()
    environment.update(runtime["environment"])
    log_path = Path(runtime["root"]) / "restart-backend.log"
    process: subprocess.Popen[str] | None = None
    _require_port_free(8000)
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--app-dir",
                    str(BACKEND_ROOT),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            _wait_for_url(f"{API_URL}/health", process, log_path)
        stats = _read_json_url(f"{API_URL}/learning/stats")
        sessions = _read_json_url(f"{API_URL}/learning/sessions")
        checks = {
            "completed_states": stats.get("completed_count") == 2,
            "bookmark": stats.get("bookmark_count") == 1,
            "note": stats.get("note_count") == 1,
            "ended_sessions": sessions.get("total") == 20
            and all(item.get("ended_at") for item in sessions.get("items", [])),
        }
        _require(all(checks.values()), f"restart persistence checks failed: {checks}")
        return {"status": "PASS", "checks": checks}
    finally:
        _stop_process(process)


def _api_json(context, method: str, path: str) -> dict[str, object]:
    response = context.request.fetch(f"{API_URL}{path}", method=method)
    _require(response.ok, f"{method} {path} returned {response.status}")
    payload = response.json()
    _require(isinstance(payload, dict), f"{method} {path} did not return an object")
    return payload


def _read_json_url(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:
        payload = json.load(response)
    _require(isinstance(payload, dict), f"{url} did not return an object")
    return payload


def _new_observed_page(
    context,
    console_errors: list[str],
    page_errors: list[str],
    *,
    label: str,
):
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: _capture_page_error(page_errors, label, page, error))
    return page


def _capture_page_error(page_errors: list[str], label: str, page, error: Exception) -> None:
    stack = getattr(error, "stack", None) or str(error)
    page_errors.append(f"{label} [{page.url}]: {stack}")


def _focus_via_tab(page, locator, *, max_steps: int = 160) -> None:
    page.evaluate(
        """
        () => {
          const active = document.activeElement;
          if (active instanceof HTMLElement) {
            active.blur();
          }
        }
        """
    )
    for _ in range(max_steps):
        page.keyboard.press("Tab")
        if locator.evaluate("element => element === document.activeElement"):
            focus_state = locator.evaluate(
                """
                element => {
                  const style = getComputedStyle(element);
                  return {
                    focusVisible: element.matches(":focus-visible"),
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                  };
                }
                """
            )
            _require(
                focus_state["focusVisible"]
                and focus_state["outlineStyle"] != "none"
                and focus_state["outlineWidth"] != "0px",
                f"keyboard target lacks visible focus: {focus_state}",
            )
            return
    raise E2EFailure(f"keyboard target was not reachable within {max_steps} Tab presses")


def _wait_for_application_shell(page) -> None:
    from playwright.sync_api import expect

    expect(page.get_by_test_id("application-shell")).to_have_attribute(
        "data-hydrated",
        "true",
        timeout=30_000,
    )


def _verify_shell_reader_focus_ownership(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.add_init_script(
        """
        window.IntersectionObserver = class {
          constructor() {}
          observe() {}
          unobserve() {}
          disconnect() {}
          takeRecords() { return []; }
        };
        """
    )
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "shell-reader-owner", page, error),
    )
    delayed_requests: list[str] = []
    delayed_session_pattern = re.compile(r".*/session(?:\?.*)?$")

    def delay_session(route) -> None:
        if "_rsc=" in route.request.url:
            delayed_requests.append(route.request.url)
            time.sleep(2.5)
        route.continue_()

    page.route(delayed_session_pattern, delay_session)
    page.route(
        re.compile(r".*/learning/sessions$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "session_id": "p3-030-reader-owner-probe",
                    "article_id": ATTENTION_ARTICLE_ID,
                    "started_at": "2026-09-05T01:00:00Z",
                    "ended_at": None,
                    "duration_seconds": None,
                    "source": "reader",
                }
            ),
        ),
        times=1,
    )
    try:
        page.goto(
            f"{FRONTEND_URL}/graph?node_id=concept%3Aattention&q=Attention",
            wait_until="domcontentloaded",
        )
        _wait_for_application_shell(page)
        expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(
            timeout=30_000
        )
        graph_article_link = page.get_by_role("link", name="Open article", exact=True).first
        expect(graph_article_link).to_be_visible(timeout=30_000)
        graph_article_href = str(graph_article_link.get_attribute("href") or "")
        _require(
            graph_article_href.startswith(f"/articles/{ATTENTION_ARTICLE_ID}")
            and "from=" in graph_article_href,
            f"Graph Reader ownership probe found an invalid Article href: {graph_article_href}",
        )
        graph_article_link.evaluate(
            "element => element.setAttribute('data-p3030-reader-race-link', 'true')"
        )

        page.get_by_test_id("global-search-trigger-desktop").click()
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        page.evaluate(
            """
            () => {
              window.__p3030ReaderOwnerActions = [];
              window.__p3030ReaderOwnerFocusEvents = [];
              window.__p3030ReaderOwnerFocusObserver = event => {
                if (event.target instanceof Element) {
                  window.__p3030ReaderOwnerFocusEvents.push(
                    event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                  );
                }
              };
              document.addEventListener('focusin', window.__p3030ReaderOwnerFocusObserver, true);
              setTimeout(() => {
                const articleLink = document.querySelector('[data-p3030-reader-race-link="true"]');
                window.__p3030ReaderOwnerActions.push(
                  articleLink ? 'reader' : 'missing-reader'
                );
                articleLink?.click();
              }, 150);
            }
            """
        )
        dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Session")
        ).click()
        expect(page).to_have_url(re.compile(rf"/articles/{ATTENTION_ARTICLE_ID}\?"), timeout=30_000)
        reader_heading = page.locator("article#article-start > h1")
        expect(reader_heading).to_have_text(ATTENTION_TITLE, timeout=30_000)
        expect(reader_heading).to_be_focused(timeout=30_000)
        _wait_for_animation_frames(page, 5)
        focus_evidence = page.evaluate(
            """
            () => {
              document.removeEventListener(
                'focusin',
                window.__p3030ReaderOwnerFocusObserver,
                true
              );
              return {
                actions: window.__p3030ReaderOwnerActions,
                focusEvents: window.__p3030ReaderOwnerFocusEvents,
              };
            }
            """
        )
        expect(reader_heading).to_be_focused()
        _require_visible_focus(reader_heading, "Shell-armed Reader heading")
        _require(
            focus_evidence["actions"] == ["reader"],
            f"Reader ownership action did not execute: {focus_evidence['actions']}",
        )
        _require(
            "shell-main-content" not in focus_evidence["focusEvents"],
            f"Shell stole Reader destination focus: {focus_evidence['focusEvents']}",
        )
        _require(
            len(delayed_requests) == 1 and "/session?" in delayed_requests[0],
            f"Reader ownership probe did not delay the Shell route: {delayed_requests}",
        )
    finally:
        page.unroute(delayed_session_pattern, delay_session)
        context.close()


def _verify_overlapping_shell_route_cancellation(
    browser,
    *,
    blocked_external: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    _install_network_guard(context, blocked_external)
    context.add_init_script(
        """
        window.IntersectionObserver = class {
          constructor() {}
          observe() {}
          unobserve() {}
          disconnect() {}
          takeRecords() { return []; }
        };
        """
    )
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on(
        "pageerror",
        lambda error: _capture_page_error(page_errors, "shell-overlap", page, error),
    )
    delayed_requests: list[str] = []
    delayed_route_pattern = re.compile(r".*/(?:session|library)(?:\?.*)?$")

    def delay_route(route) -> None:
        if "_rsc=" in route.request.url:
            delayed_requests.append(route.request.url)
            time.sleep(2.5)
        route.continue_()

    page.route(delayed_route_pattern, delay_route)
    try:
        page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        _wait_for_application_shell(page)
        page.evaluate("history.pushState(history.state, '', '/')")
        page.get_by_test_id("global-search-trigger-desktop").click()
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        page.evaluate(
            """
            () => {
              window.__p3030OverlapActions = [];
              window.__p3030OverlapFocusBehindModal = [];
              window.__p3030OverlapFocusObserver = event => {
                const activeDialog = document.querySelector('[data-testid="global-search-dialog"]');
                if (activeDialog && event.target instanceof Node && !activeDialog.contains(event.target)) {
                  window.__p3030OverlapFocusBehindModal.push(
                    event.target instanceof Element
                      ? event.target.getAttribute('data-testid') || event.target.id || event.target.tagName
                      : 'non-element'
                  );
                }
              };
              document.addEventListener('focusin', window.__p3030OverlapFocusObserver, true);
              setTimeout(() => {
                const trigger = document.querySelector(
                  '[data-testid="global-search-trigger-desktop"]'
                );
                window.__p3030OverlapActions.push(trigger ? 'reopen' : 'missing-reopen');
                trigger?.click();
              }, 150);
              setTimeout(() => {
                const saved = document.querySelector(
                  '[data-testid="global-search-dialog"] '
                    + '[data-testid="global-search-result-workspace"][href="/library"]'
                );
                window.__p3030OverlapActions.push(saved ? 'saved' : 'missing-saved');
                saved?.click();
              }, 350);
              setTimeout(() => {
                window.__p3030OverlapActions.push('back');
                history.back();
              }, 650);
            }
            """
        )
        dialog.get_by_test_id("global-search-result-workspace").filter(
            has_text=re.compile(r"^Session")
        ).click()
        expect(page).to_have_url(re.compile(r"/$"), timeout=30_000)
        expect(page.get_by_test_id("global-search-dialog")).to_have_count(0)
        main = page.get_by_test_id("shell-main-content")
        expect(main).to_be_focused(timeout=30_000)
        _wait_for_animation_frames(page, 5)
        expect(main).to_be_focused()
        _require_visible_focus(main, "overlapping canceled Shell route")
        overlap_evidence = page.evaluate(
            """
            () => {
              document.removeEventListener('focusin', window.__p3030OverlapFocusObserver, true);
              return {
                actions: window.__p3030OverlapActions,
                focusBehindModal: window.__p3030OverlapFocusBehindModal,
              };
            }
            """
        )
        _require(
            overlap_evidence["actions"] == ["reopen", "saved", "back"],
            f"overlapping Shell actions did not execute in order: "
            f"{overlap_evidence['actions']}",
        )
        _require(
            overlap_evidence["focusBehindModal"] == [],
            "overlapping Shell route focused behind a reopened modal: "
            f"{overlap_evidence['focusBehindModal']}",
        )
        _require(
            len(delayed_requests) == 2
            and any("/session?" in url for url in delayed_requests)
            and any("/library?" in url for url in delayed_requests),
            f"overlapping Shell route probe did not delay both RSC requests: {delayed_requests}",
        )
    finally:
        page.unroute(delayed_route_pattern, delay_route)
        context.close()


def _wait_for_animation_frames(page, count: int) -> None:
    page.evaluate(
        """
        frameCount => new Promise(resolve => {
          let remaining = Math.max(1, frameCount);
          const next = () => {
            remaining -= 1;
            if (remaining === 0) {
              resolve();
              return;
            }
            requestAnimationFrame(next);
          };
          requestAnimationFrame(next);
        })
        """,
        count,
    )


def _document_width(page) -> int:
    return int(
        page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)"
        )
    )


def _wait_for_test_id_near_viewport_top(page, test_id: str, *, max_top: int = 200) -> None:
    page.wait_for_function(
        """
        ({ testId, maxTop }) => {
          const node = document.querySelector(`[data-testid="${testId}"]`);
          if (!(node instanceof HTMLElement)) return false;
          const box = node.getBoundingClientRect();
          return box.top < maxTop && box.bottom > 0;
        }
        """,
        arg={"testId": test_id, "maxTop": max_top},
        timeout=30_000,
    )


def _require_visible_focus(locator, label: str) -> None:
    focus_state = locator.evaluate(
        """
        node => {
          const style = getComputedStyle(node);
          return {
            active: node === document.activeElement,
            boxShadow: style.boxShadow,
            outlineStyle: style.outlineStyle,
            outlineWidth: style.outlineWidth,
          };
        }
        """
    )
    _require(
        focus_state["active"]
        and (
            (
                focus_state["outlineStyle"] != "none"
                and focus_state["outlineWidth"] != "0px"
            )
            or focus_state["boxShadow"] != "none"
        ),
        f"{label} lacks a visible focus indicator: {focus_state}",
    )


def _install_fetch_response_gate(
    page,
    endpoint: str,
    *,
    method: str | None = None,
) -> None:
    page.evaluate(
        """
        ({ endpoint, method }) => {
          if (typeof window.__p3027OriginalFetch === "function") {
            throw new Error("P3-027 fetch response gate is already installed");
          }
          const originalFetch = window.fetch.bind(window);
          window.__p3027OriginalFetch = originalFetch;
          window.__p3027FetchGate = {
            endpoint,
            pendingCount: 0,
            completedCount: 0,
            release: null,
          };
          window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            const target = String(args[0] instanceof Request ? args[0].url : args[0]);
            const requestMethod = String(
              args[0] instanceof Request ? args[0].method : args[1]?.method ?? "GET"
            ).toUpperCase();
            if (target.endsWith(endpoint) && (!method || requestMethod === method)) {
              const gate = window.__p3027FetchGate;
              gate.pendingCount += 1;
              await new Promise((resolve) => {
                gate.release = resolve;
              });
              gate.release = null;
              gate.completedCount += 1;
            }
            return response;
          };
        }
        """,
        {"endpoint": endpoint, "method": method},
    )


def _wait_for_fetch_response_gate_pending(page) -> None:
    page.wait_for_function(
        """
        () => {
          const gate = window.__p3027FetchGate;
          return gate && gate.pendingCount > gate.completedCount
            && typeof gate.release === "function";
        }
        """,
        timeout=30_000,
    )


def _release_fetch_response_gate(page) -> None:
    _wait_for_fetch_response_gate_pending(page)
    expected_count = page.evaluate(
        """
        () => {
          const gate = window.__p3027FetchGate;
          const release = gate.release;
          gate.release = null;
          release();
          return gate.pendingCount;
        }
        """
    )
    page.wait_for_function(
        """expected => window.__p3027FetchGate?.completedCount >= expected""",
        arg=expected_count,
        timeout=30_000,
    )


def _restore_fetch_response_gate(page) -> None:
    page.evaluate(
        """
        () => {
          if (typeof window.__p3027OriginalFetch === "function") {
            window.fetch = window.__p3027OriginalFetch;
            delete window.__p3027OriginalFetch;
            delete window.__p3027FetchGate;
          }
        }
        """
    )


def _unexpected_console_errors(messages: list[str]) -> list[str]:
    expected_statuses = {"404": 1, "503": 8}
    unexpected: list[str] = []
    for message in messages:
        matched = False
        for status, remaining in expected_statuses.items():
            if remaining and f"status of {status}" in message:
                expected_statuses[status] -= 1
                matched = True
                break
        if not matched:
            unexpected.append(message)
    return unexpected


def _reset_mutable_runtime(runtime: dict[str, Path | dict[str, str]]) -> None:
    Path(runtime["learning"]).unlink(missing_ok=True)
    Path(runtime["tutor"]).unlink(missing_ok=True)


def _require_box_inside(
    container: dict[str, float] | None,
    child: dict[str, float] | None,
    label: str,
    *,
    minimum_width: float,
    minimum_height: float,
) -> None:
    _require(container is not None and child is not None, f"{label} has no rendered geometry")
    assert container is not None and child is not None
    _require(
        child["width"] >= minimum_width
        and child["height"] >= minimum_height
        and child["x"] >= container["x"]
        and child["y"] >= container["y"]
        and child["x"] + child["width"] <= container["x"] + container["width"]
        and child["y"] + child["height"] <= container["y"] + container["height"],
        f"{label} is clipped or outside its canvas: container={container}, child={child}",
    )


def _require_viewport_intersection(
    box: dict[str, float] | None,
    viewport_width: int,
    viewport_height: int,
    label: str,
) -> None:
    _require(
        box is not None
        and box["x"] >= 0
        and box["x"] + box["width"] <= viewport_width
        and box["y"] < viewport_height
        and box["y"] + box["height"] > 0,
        f"{label} is clipped or outside the viewport: {box}",
    )


def _require_viewport_containment(
    box: dict[str, float] | None,
    viewport_width: int,
    viewport_height: int,
    label: str,
) -> None:
    _require(
        box is not None
        and box["x"] >= 0
        and box["x"] + box["width"] <= viewport_width
        and box["y"] >= 0
        and box["y"] + box["height"] <= viewport_height,
        f"{label} is clipped or outside the viewport: {box}",
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise E2EFailure(message)


def _require_port_free(port: int) -> None:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise E2EFailure(f"required local port {port} is already in use")


def _wait_for_url(
    url: str,
    process: subprocess.Popen[str],
    log_path: Path,
    *,
    timeout: int = 30,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise E2EFailure(
                f"server exited with {process.returncode}: {_bounded_log_summary(log_path)}"
            )
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            pass
        time.sleep(0.25)
    raise E2EFailure(f"server did not become ready at {url}: {_bounded_log_summary(log_path)}")


def _stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait(timeout=5)


def _bounded_log_summary(path: Path, *, max_lines: int = 30) -> list[str]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [f"{type(exc).__name__}: {exc}"]
    return lines[-max_lines:]


if __name__ == "__main__":
    raise SystemExit(main())
