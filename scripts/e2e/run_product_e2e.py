#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Iterator
from urllib.error import URLError
from urllib.parse import unquote, urlparse
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
    page.on("pageerror", lambda error: page_errors.append(f"{page.url}: {error}"))

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_text(str(EXPECTED_ARTICLE_COUNT), exact=True).first).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-command-center")).to_be_visible()
    expect(page.get_by_role("heading", name="Learning Overview", exact=True)).to_be_visible()
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

    search_trigger.click()
    search_dialog = page.get_by_test_id("global-search-dialog")
    session_workspace_result = search_dialog.get_by_test_id(
        "global-search-result-workspace"
    ).filter(has_text=re.compile(r"^Session"))
    expect(session_workspace_result).to_be_visible()
    session_workspace_result.click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("study-session-empty")).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
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
    _require("node_id=concept%3Aattention" in page.url, f"Graph deep link was not preserved: {page.url}")
    checks["global_search_reference_and_graph_deep_link"] = True

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
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(
        page.get_by_role("button", name=f"Selected Article: {CRB_TITLE}", exact=True)
    ).to_be_visible(timeout=30_000)
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.locator('select[name="node_type"]').select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    context_graph_node = (
        page.get_by_test_id("graph-node-results")
        .locator("button")
        .filter(has_text=re.compile(r"^Attention", re.I))
        .first
    )
    expect(context_graph_node).to_be_visible(timeout=30_000)
    context_graph_node.click()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
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
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
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
    continue_link = page.get_by_role("link", name=re.compile(r"^Continue learning CRB"))
    continue_href = continue_link.get_attribute("href") or ""
    _require("#" in continue_href, "Continue Reading does not retain a section anchor")
    expect(page.get_by_role("heading", name="Learning Activity", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="New in Library", exact=True)).to_be_visible()
    expect(page.get_by_test_id("dashboard-activity")).to_contain_text(CRB_TITLE)
    expect(page.get_by_test_id("dashboard-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["dashboard_history"] = True

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
    checks["saved_learning_library"] = True

    page.get_by_role("link", name="Open study session (2)", exact=True).click()
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    expect(page.get_by_test_id("application-shell")).to_have_attribute("data-workspace", "session")
    expect(page.get_by_test_id("study-session-summary")).to_contain_text("2 Articles")
    crb_queue_item = page.get_by_test_id("study-session-item").filter(has_text=CRB_TITLE).first
    crb_queue_item.get_by_role("button", name=f"Move {CRB_TITLE} up", exact=True).click()
    crb_queue_item.get_by_role("button", name=f"Set {CRB_TITLE} as current", exact=True).click()
    expect(crb_queue_item).to_contain_text("Current")
    page.reload(wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_role("heading", name="Focused Study Session", exact=True)).to_be_visible()
    crb_queue_item = page.get_by_test_id("study-session-item").first
    expect(crb_queue_item).to_contain_text(CRB_TITLE)
    expect(crb_queue_item).to_contain_text("Current")
    page.get_by_role(
        "link", name=f"Continue current Article: {CRB_TITLE}", exact=True
    ).click()
    expect(page.get_by_role("heading", name=CRB_TITLE, exact=True)).to_be_visible(timeout=30_000)
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 1 of 2")
    next_session_article = session_reader_navigation.get_by_role(
        "link", name=f"Next in session: {ATTENTION_TITLE}", exact=True
    )
    current_queue_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(current_queue_reader_session).to_be_enabled(timeout=30_000)
    current_queue_reader_session.click()
    expect(current_queue_reader_session).to_be_disabled()
    next_session_article.click()
    expect(page.get_by_role("heading", name=ATTENTION_TITLE, exact=True)).to_be_visible(timeout=30_000)
    session_reader_navigation = page.get_by_test_id("study-session-reader-navigation")
    expect(session_reader_navigation).to_contain_text("Article 2 of 2")
    expect(
        session_reader_navigation.get_by_role(
            "link", name=f"Previous in session: {CRB_TITLE}", exact=True
        )
    ).to_be_visible()
    next_queue_reader_session = page.get_by_role("button", name="End session", exact=True)
    expect(next_queue_reader_session).to_be_enabled(timeout=30_000)
    next_queue_reader_session.click()
    expect(next_queue_reader_session).to_be_disabled()
    page.get_by_role("link", name="Back to study session", exact=True).first.click()
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
    expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("graph-map-counts")).to_contain_text("relationships")
    graph_article_node = page.get_by_role("button", name=re.compile(r"^Article: ")).first
    expect(graph_article_node).to_be_visible()
    graph_article_node.press("Enter")
    expect(page.get_by_role("button", name=re.compile(r"^Selected Article: ")).first).to_be_visible(
        timeout=30_000
    )
    graph_article_link = page.get_by_role("link", name="Open article").first
    expect(graph_article_link).to_be_visible()
    _require(
        str(graph_article_link.get_attribute("href") or "").startswith("/articles/"),
        "Graph Article deep link is invalid",
    )
    page.get_by_test_id("graph-view-list").click()
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
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
    page.route(
        re.compile(r".*/tutor/ask$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(markdown_response, ensure_ascii=False),
        ),
        times=1,
    )
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
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
    expect(page.get_by_test_id("tutor-activity")).to_contain_text(CRB_TITLE, timeout=30_000)
    expect(page.get_by_test_id("tutor-activity")).not_to_contain_text(CRB_ARTICLE_ID)
    checks["tutor_explain"] = True
    checks["guided_tutor_article_markdown_and_follow_up"] = True

    page.get_by_role("button", name="Derive", exact=True).click()
    page.get_by_label("Question").fill("根据文章公式推导 CRB 下界")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    checks["tutor_derive"] = True

    page.get_by_role("button", name="Quiz", exact=True).click()
    page.get_by_label("Prompt").fill("CRB")
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz disclosed answers before submission")
    quiz_articles = page.get_by_test_id("tutor-quiz-workspace").locator("article")
    _require(quiz_articles.count() >= 2, "Quiz did not return enough grounded questions for choices")
    for quiz_index in range(quiz_articles.count()):
        quiz_articles.nth(quiz_index).locator('input[type="radio"]').first.check()
    page.get_by_role("button", name="Check answers", exact=True).click()
    expect(page.get_by_test_id("tutor-quiz-score")).to_be_visible()
    expect(page.get_by_text(re.compile(r"^Correct answer:")).first).to_be_visible()
    expect(page.get_by_role("heading", name="题目来源", exact=True).first).to_be_visible()
    page.get_by_role("button", name="Try again", exact=True).click()
    _require(page.get_by_text(re.compile(r"^Correct answer:")).count() == 0, "Quiz retry retained answer disclosure")
    checks["tutor_quiz"] = True
    checks["tutor_quiz_hidden_review_and_score"] = True

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

    _require(not page_errors, f"primary workflow emitted page errors: {page_errors}")
    page.close()
    page = context.new_page()
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(f"{page.url}: {error}"))

    page.goto(f"{FRONTEND_URL}/articles/not-a-real-article", wait_until="domcontentloaded")
    _wait_for_application_shell(page)
    expect(page.get_by_text("Article not found", exact=True)).to_be_visible(timeout=30_000)
    _require(not page_errors, f"Article not-found route emitted page errors: {page_errors}")
    checks["article_not_found_state"] = True

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
    checks["route_not_found_state"] = True

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
    checks["controlled_backend_error_state"] = True

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
    checks["dashboard_partial_failure"] = True

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
    checks["saved_library_partial_failure"] = True
    context.close()

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
        "pageerror", lambda error: page_errors.append(f"{unavailable_page.url}: {error}")
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
    recovered_session_page = recovered_session_context.new_page()
    recovered_session_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    recovered_session_page.on(
        "pageerror", lambda error: page_errors.append(f"{recovered_session_page.url}: {error}")
    )
    recovered_session_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(recovered_session_page)
    expect(recovered_session_page.get_by_role("status")).to_contain_text(
        "The saved queue was recovered safely"
    )
    expect(recovered_session_page.get_by_test_id("study-session-summary")).to_contain_text(
        "1 Article"
    )
    expect(recovered_session_page.get_by_test_id("study-session-item")).to_contain_text(CRB_TITLE)
    expect(recovered_session_page.get_by_test_id("focused-study-session")).not_to_contain_text(
        "raw-title-id"
    )
    checks["study_session_stale_record_recovery"] = True
    recovered_session_context.close()

    read_failure_context = browser.new_context(
        viewport={"width": 1440, "height": 900}, locale="zh-CN"
    )
    read_failure_context.add_init_script(
        script="""
        const originalGetItem = Storage.prototype.getItem;
        Storage.prototype.getItem = function (key) {
          if (key === "scientific-spaces-study-session-v1") {
            throw new Error("intentional study session read failure");
          }
          return originalGetItem.call(this, key);
        };
        """
    )
    _install_network_guard(read_failure_context, blocked_external)
    read_failure_page = read_failure_context.new_page()
    read_failure_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    read_failure_page.on(
        "pageerror", lambda error: page_errors.append(f"{read_failure_page.url}: {error}")
    )
    read_failure_page.goto(f"{FRONTEND_URL}/session", wait_until="domcontentloaded")
    _wait_for_application_shell(read_failure_page)
    expect(read_failure_page.get_by_test_id("study-session-unavailable")).to_be_visible()
    checks["study_session_storage_unavailable"] = True
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
    write_failure_page = write_failure_context.new_page()
    write_failure_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    write_failure_page.on(
        "pageerror", lambda error: page_errors.append(f"{write_failure_page.url}: {error}")
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
    checks["study_session_storage_write_failure"] = True
    write_failure_context.close()

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
    mobile_page.on("pageerror", lambda error: page_errors.append(f"{mobile_page.url}: {error}"))
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

    stat_boxes = mobile_page.locator('[data-testid="dashboard-stats"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(len({round(item["x"]) for item in stat_boxes}) == 2, "mobile dashboard statistics are not two columns")
    continue_learning_action = mobile_page.get_by_role(
        "link",
        name=re.compile(r"^Continue learning "),
    ).bounding_box()
    _require(
        continue_learning_action is not None
        and continue_learning_action["y"] + continue_learning_action["height"] <= 844,
        "Continue Learning action is clipped by the first mobile viewport",
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
    expect(mobile_page.get_by_role("heading", name="Continue Learning", exact=True)).to_be_visible(
        timeout=30_000
    )
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
    expect(mobile_page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
    mobile_graph_box = mobile_page.locator(".knowledge-graph-canvas").bounding_box()
    mobile_graph_width = _document_width(mobile_page)
    _require(
        mobile_graph_box is not None and mobile_graph_box["width"] <= 390,
        f"mobile visual Graph canvas overflowed: {mobile_graph_box}",
    )
    _require(mobile_graph_width <= 390, f"mobile Graph page overflowed to {mobile_graph_width}px")
    expect(mobile_page.locator(".react-flow__controls")).to_be_visible()
    mobile_page.get_by_test_id("graph-view-list").click()
    expect(mobile_page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    checks["mobile_visual_knowledge_explorer"] = True
    mobile_context.close()

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
            "completed_state": stats.get("completed_count") == 1,
            "bookmark": stats.get("bookmark_count") == 1,
            "note": stats.get("note_count") == 1,
            "ended_sessions": sessions.get("total") == 8
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


def _wait_for_application_shell(page) -> None:
    from playwright.sync_api import expect

    expect(page.get_by_test_id("application-shell")).to_have_attribute(
        "data-hydrated",
        "true",
        timeout=30_000,
    )


def _document_width(page) -> int:
    return int(
        page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)"
        )
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
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
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
