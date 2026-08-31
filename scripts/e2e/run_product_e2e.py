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
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible(timeout=30_000)
    expect(page.get_by_text(str(EXPECTED_ARTICLE_COUNT), exact=True).first).to_be_visible()
    expect(page.get_by_text("No article in progress.", exact=True)).to_be_visible()
    _require(
        page.locator('nav[aria-label="Primary"] [aria-current="page"]').get_attribute("href") == "/",
        "Dashboard navigation item is not marked as current",
    )
    checks["dashboard"] = True

    page.get_by_role("link", name="Articles", exact=True).click()
    expect(page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(page.locator('nav[aria-label="Primary"] [aria-current="page"]')).to_have_text("Articles")
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
    expect(page.get_by_label("Article ID")).to_have_value(CRB_ARTICLE_ID)
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
    page.get_by_placeholder("Title, concept, or formula").fill("Attention")
    page.get_by_label("Type").select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    context_graph_node = page.locator("button").filter(has_text=re.compile(r"^Attention", re.I)).first
    expect(context_graph_node).to_be_visible(timeout=30_000)
    context_graph_node.click()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
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
    expect(page.get_by_role("heading", name="Continue Reading", exact=True)).to_be_visible()
    continue_link = page.get_by_role("link", name=re.compile(r"^Continue reading CRB"))
    continue_href = continue_link.get_attribute("href") or ""
    _require("#" in continue_href, "Continue Reading does not retain a section anchor")
    expect(page.get_by_role("heading", name="Recent Learning", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Reading History", exact=True)).to_be_visible()
    _require(page.get_by_role("link", name=re.compile(CRB_TITLE)).count() >= 2, "dashboard history is missing")
    checks["dashboard_history"] = True

    continue_link.click()
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
    page.get_by_label("Type").select_option("concept")
    page.get_by_role("button", name="Apply", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Showing 1-\d+ of \d+$"))).to_be_visible(timeout=30_000)
    graph_node = page.locator("button").filter(has_text=re.compile(r"^Attention", re.I)).first
    expect(graph_node).to_be_visible()
    graph_node.click()
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("heading", name="Bounded Context", exact=True)).to_be_visible()
    graph_article_link = page.get_by_role("link", name="Open article").first
    expect(graph_article_link).to_be_visible()
    _require(
        str(graph_article_link.get_attribute("href") or "").startswith("/articles/"),
        "Graph Article deep link is invalid",
    )
    checks["knowledge_graph"] = True

    page.get_by_role("link", name="Tutor", exact=True).click()
    expect(page.get_by_role("heading", name="AI Research Tutor", exact=True)).to_be_visible()
    page.get_by_label("Article ID").fill(CRB_ARTICLE_ID)
    page.get_by_label("Question").fill("什么是 CRB 和 Fisher 信息下界？")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    tutor_article_link = page.get_by_role("link", name="Open local article").first
    expect(tutor_article_link).to_be_visible()
    _require(
        tutor_article_link.get_attribute("href") == f"/articles/{CRB_ARTICLE_ID}",
        "Tutor Article deep link is invalid",
    )
    checks["tutor_explain"] = True

    page.get_by_role("button", name="derive", exact=True).click()
    page.get_by_label("Question").fill("根据文章公式推导 CRB 下界")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name="Answer", exact=True)).to_be_visible(timeout=30_000)
    checks["tutor_derive"] = True

    page.get_by_role("button", name="quiz", exact=True).click()
    page.get_by_label("Prompt").fill("CRB")
    page.get_by_role("button", name="Generate quiz", exact=True).click()
    expect(page.get_by_role("heading", name="Quiz", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text(re.compile(r"^Answer: ")).first).to_be_visible()
    checks["tutor_quiz"] = True

    page.get_by_role("button", name="research", exact=True).click()
    page.get_by_label("Question").fill("基于本地资料给出 CRB 研究方向")
    page.get_by_role("button", name="Ask tutor", exact=True).click()
    expect(page.get_by_role("heading", name=re.compile(r"^(Answer|Refusal)$"))).to_be_visible(
        timeout=30_000
    )
    expect(page.get_by_role("heading", name="Research 模式范围", exact=True)).to_be_visible()
    checks["tutor_research"] = True

    page.goto(f"{FRONTEND_URL}/articles/not-a-real-article", wait_until="domcontentloaded")
    expect(page.get_by_text("Article not found", exact=True)).to_be_visible(timeout=30_000)
    checks["article_not_found_state"] = True

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
    expect(page.get_by_text("Failed to load articles: 503", exact=True)).to_be_visible(timeout=30_000)
    checks["controlled_backend_error_state"] = True
    context.close()

    mobile_context = browser.new_context(
        viewport={"width": 390, "height": 844},
        locale="zh-CN",
        is_mobile=True,
        reduced_motion="reduce",
    )
    _install_network_guard(mobile_context, blocked_external)
    mobile_page = mobile_context.new_page()
    mobile_page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    mobile_page.on("pageerror", lambda error: page_errors.append(str(error)))
    mobile_page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    expect(
        mobile_page.get_by_role("heading", name="Scientific Spaces AI Learning OS", exact=True)
    ).to_be_visible()
    nav_boxes = mobile_page.locator('nav[aria-label="Primary"] a').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    stat_boxes = mobile_page.locator('[data-testid="dashboard-stats"] > div').evaluate_all(
        "nodes => nodes.map(node => node.getBoundingClientRect()).map(box => ({x: box.x, y: box.y}))"
    )
    _require(len({round(item["y"]) for item in nav_boxes}) == 1, "mobile primary navigation wraps")
    _require(len({round(item["x"]) for item in stat_boxes}) == 2, "mobile dashboard statistics are not two columns")
    recent_articles_top = mobile_page.get_by_role("heading", name="Recent Articles", exact=True).bounding_box()
    _require(
        recent_articles_top is not None and recent_articles_top["y"] < 844,
        "Recent Articles is below the first mobile viewport",
    )
    checks["mobile_dashboard_density"] = True

    mobile_page.goto(f"{FRONTEND_URL}/articles", wait_until="domcontentloaded")
    expect(mobile_page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()
    expect(mobile_page.get_by_text(re.compile(r"^Page 1 / "))).to_be_visible(timeout=30_000)
    list_width = _document_width(mobile_page)
    mobile_page.goto(
        f"{FRONTEND_URL}/articles/{CRB_ARTICLE_ID}",
        wait_until="domcontentloaded",
    )
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
            "article_list": list_width,
            "article_detail": detail_width,
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
            "ended_sessions": sessions.get("total") == 5
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


def _document_width(page) -> int:
    return int(
        page.evaluate(
            "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)"
        )
    )


def _unexpected_console_errors(messages: list[str]) -> list[str]:
    expected_statuses = {"404": 1, "503": 1}
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
