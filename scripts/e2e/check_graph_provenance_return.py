#!/usr/bin/env python3
"""Owned synthetic Graph return-focus regression against a production build.

CLI: no arguments; stdout is one JSON object, exit 0 PASS, 1 UI FAIL, 2 BLOCKED.
Schema v1 exports fixed status/error/stage enums, booleans, counts and seven case
summaries only. FAIL requires clean strict audit, stable source/build/fixture
bindings and removed temporary runtime. It is not historical Graph-blink proof.
Default port 8000 uses the existing build; an explicit alternate backend port
uses an owned source-verified temporary build. No canonical-data mutation,
external services or image/log export. Per-run bindings prove stability; the
alternate-port helper separately verifies copied inputs and shared-state safety.
"""

from __future__ import annotations

from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import tempfile
import time
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
GRAPH_HREF = "/graph?node_id=concept%3Aattention&q=Attention"
CONCEPT_ID = "concept:attention"
ARTICLE_IDS = ("attention-basics", "crb-formula", "local-research-map")
FOCUS_KEY = "scientific-spaces:graph-article-return-focus:v1"
VIEWPORTS = (("desktop", 1440, 1000), ("mobile", 390, 844))
SCENARIOS = ("roundtrip", "missing_origin", "wrong_article")
MORE = "Show 1 more returned sources"
FEWER = "Show fewer returned sources"
LINKS = '[data-graph-article-focus^="provenance-"]'
ERRORS = frozenset({"none", "invalid_arguments", "ui_assertion", "execution_failed",
                    "audit_failed", "binding_changed", "fixture_changed", "cleanup_failed"})
STAGES = frozenset({"setup", "bindings", "runtime_setup", "runtime_teardown", "seed",
                    "server_setup", "server_teardown", "playwright_setup", "playwright_teardown",
                    "browser_setup", "browser_teardown", "context_setup", "context_teardown",
                    "initial_graph", "expand", "source", "reader_route", "reader_heading",
                    "end_session", "return_route", "expanded_return", "manual_collapse",
                    "ordinary_return", "cold_revisit", "fallback", "case_bindings",
                    "detail_hold", "superseding_intent", "detail_release", "arrival_superseded",
                    "audit", "final_bindings", "complete"})


def digest_paths(paths, *, relative_root=None):
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(relative_root or ROOT)).encode("utf-8") + b"\0")
        with path.open("rb") as handle:
            file_digest = hashlib.file_digest(handle, "sha256").digest()
        digest.update(file_digest)
    return digest.hexdigest()


def source_bindings(*, frontend_root=None):
    build = (frontend_root or ROOT / "frontend") / ".next"
    if not (build / "BUILD_ID").is_file() or not (build / "BUILD_ID").read_bytes().strip():
        raise ValueError("execution_failed")
    build_files = [build / "BUILD_ID"]
    for name in ("server", "static"):
        files = [path for path in (build / name).rglob("*") if path.is_file()]
        if not files:
            raise ValueError("execution_failed")
        build_files.extend(files)
    build_files.extend(build.glob("*manifest.json"))
    sources = [path for path in (ROOT / "frontend/src").rglob("*") if path.is_file()]
    sources.extend((ROOT / "backend/app").rglob("*.py"))
    sources.extend(ROOT / path for path in (
        "scripts/e2e/run_product_e2e.py", "scripts/e2e/check_graph_provenance_return.py",
        "scripts/e2e/product_test_runtime.py", "frontend/package.json",
        "frontend/package-lock.json", "backend/pyproject.toml", "backend/uv.lock",
    ))
    return {"source": digest_paths(sources), "build": digest_paths(build_files, relative_root=frontend_root),
            "fixture": digest_paths([ROOT / "backend/tests/fixtures/evaluation/articles.json"])}


def owned_paths(runtime, root):
    root = root.resolve()
    if Path(runtime["root"]).resolve() != root:
        raise ValueError("fixture_changed")
    paths = [Path(runtime[key]).resolve() for key in ("articles", "graph")]
    if any(not path.is_relative_to(root) or path == root for path in paths):
        raise ValueError("fixture_changed")
    return paths


def fixture_binding(runtime, root):
    return tuple(hashlib.sha256(path.read_bytes()).digest() for path in owned_paths(runtime, root))


def seed_graph(module, runtime, root):
    """Replace only one temporary concept's provenance; reuse actual sections."""
    articles_path, graph_path = owned_paths(runtime, root)
    records = json.loads(articles_path.read_text(encoding="utf-8"))
    articles = {item["id"]: item for item in records}
    if len(records) != 3 or set(articles) != set(ARTICLE_IDS):
        raise ValueError("fixture_changed")
    store = module["GraphStore"](graph_path)
    graph = store.load()
    targets = [node for node in graph.nodes if node.node_id == CONCEPT_ID and node.node_type == "concept"]
    if len(targets) != 1:
        raise ValueError("fixture_changed")
    sources = []
    # Source 3 deliberately shares Article 0, but identifies a different section.
    for article_id, index in ((ARTICLE_IDS[0], 0), (ARTICLE_IDS[1], 0),
                              (ARTICLE_IDS[2], 0), (ARTICLE_IDS[0], 1)):
        sections = sorted((node for node in graph.nodes if node.node_type == "section"
                           and node.metadata.get("article_id") == article_id),
                          key=lambda node: (node.metadata["chunk_index"], node.node_id))
        if len(sections) <= index:
            raise ValueError("fixture_changed")
        section = sections[index]
        article = articles[article_id]
        sources.append({"article_id": article_id, "article_title": article["title"],
                        "article_url": article["url"], "source_type": "section_content",
                        "source_context": section.label, "section_title": section.label,
                        "section_node_id": section.node_id, "chunk_index": section.metadata["chunk_index"],
                        "evidence": "Owned synthetic return-focus provenance."})
    target = targets[0]
    replacement = replace(target, metadata={**target.metadata, "source_count": 4,
                                            "sources": sources, "truncated": False})
    store.save(replace(graph, nodes=[replacement if node is target else node for node in graph.nodes]))
    readback = next(node for node in store.load().nodes if node.node_id == CONCEPT_ID)
    if readback.metadata != replacement.metadata:
        raise ValueError("fixture_changed")
    return sources


def fail(state, error):
    if error not in ERRORS:
        error = "execution_failed"
    if state["failure_stage"] == "none":
        state["failure_stage"] = state["stage"]
    if state["error"] == "none" or error != "ui_assertion":
        state["error"] = error


@contextmanager
def resource(state, manager, setup, teardown):
    state["stage"] = setup
    try:
        with manager as value:
            try:
                yield value
            except (Exception, KeyboardInterrupt):
                fail(state, "execution_failed")
                raise
            finally:
                state["stage"] = teardown
    except (Exception, KeyboardInterrupt):
        fail(state, "execution_failed")
        raise


def source_link(page, index):
    return page.locator(f'[data-graph-article-focus="provenance-{index}"]')


def marker(scenario):
    if scenario not in ("missing_origin", "wrong_article", "arrival_superseded"):
        raise ValueError("invalid_arguments")
    return {"articleId": ARTICLE_IDS[1] if scenario == "wrong_article" else ARTICLE_IDS[0],
            "focusTarget": "provenance-9" if scenario == "missing_origin" else "provenance-3",
            "returnTo": GRAPH_HREF}


def collapsed(page, expect):
    expect(page.locator(LINKS)).to_have_count(3)
    expect(source_link(page, 3)).to_have_count(0)
    expect(page.get_by_role("button", name=MORE, exact=True)).to_be_visible()
    expect(page.get_by_role("button", name=FEWER, exact=True)).to_have_count(0)


def consumed(page):
    page.wait_for_function("key => sessionStorage.getItem(key) === null", arg=FOCUS_KEY, timeout=5000)


def settled(page, module, errors):
    module["_wait_for_page_requests_to_settle"](page, errors)


def activate(page, locator, module):
    module["_focus_via_tab"](page, locator)
    locator.press("Enter")


def navigate_link(state, page, locator, href, stage, module, errors, expect):
    state["stage"] = stage
    expect(locator).to_have_attribute("href", href)
    module["_focus_via_tab"](page, locator)
    settled(page, module, errors)
    transition = module["_declare_expected_route_transition"](
        page, destination_url=module["FRONTEND_URL"] + href)
    locator.press("Enter")
    expect(page).to_have_url(module["FRONTEND_URL"] + href, timeout=30_000)
    settled(page, module, errors)
    # Complete the strict route ledger before an expected pre-fix UI assertion.
    module["_complete_expected_route_transition"](page, transition)


def roundtrip(state, page, index, module, errors, expect):
    state["stage"] = "source"
    link = source_link(page, index)
    expect(link).to_be_visible(timeout=30_000)
    expect(link).to_have_attribute("data-graph-article-id", ARTICLE_IDS[0])
    href = f"/articles/{ARTICLE_IDS[0]}?" + urlencode({"from": GRAPH_HREF})
    navigate_link(state, page, link, href, "reader_route", module, errors, expect)
    state["stage"] = "reader_heading"
    heading = page.locator("article#article-start > h1")
    expect(heading).to_have_text(module["ATTENTION_TITLE"])
    expect(heading).to_be_visible(timeout=30_000)
    expect(heading).to_be_focused(timeout=30_000)
    module["_require_visible_focus"](heading, "reader_heading")
    state["stage"] = "end_session"
    end = page.get_by_role("button", name="End session", exact=True)
    expect(end).to_be_enabled(timeout=30_000)
    activate(page, end, module)
    expect(end).to_be_disabled(timeout=30_000)
    settled(page, module, errors)
    back = page.get_by_role("link", name="Back to concept", exact=True).first
    navigate_link(state, page, back, GRAPH_HREF, "return_route", module, errors, expect)
    state["stage"] = "expanded_return" if index == 3 else "ordinary_return"
    returned = source_link(page, index)
    expect(returned).to_be_visible(timeout=30_000)
    expect(returned).to_be_focused(timeout=30_000)
    module["_require_visible_focus"](returned, "exact_provenance_origin")
    consumed(page)


class HeldDetail:
    """Own exactly one unchanged backend response until newer UI intent commits."""

    def __init__(self, page, url):
        self.page, self.url = page, url
        self.route = self.response = None
        self.count = 0
        self.active = 0
        self.closing = False
        self.invalid = self.released = False
        self.handler = self.intercept
        page.route(url, self.handler)

    def intercept(self, route):
        self.active += 1
        try:
            if route.request.url != self.url or route.request.method != "GET":
                route.fallback()
                return
            self.count += 1
            if self.count != 1 or self.closing:
                self.invalid = True
                route.abort()
                return
            self.route = route
            response = route.fetch(max_redirects=0, timeout=5000)
            if self.closing:
                self.invalid = True
                response.dispose()
                return
            self.response = response
            if self.response.status != 200 or self.response.url != self.url:
                self.invalid = True
        except (Exception, KeyboardInterrupt):
            self.invalid = True
        finally:
            self.active -= 1

    def require_held(self):
        if self.invalid or self.active or self.count != 1 or self.response is None or self.route is None or self.released:
            raise ValueError("detail_interception")

    def wait_ready(self):
        deadline = time.monotonic() + 8
        while (self.response is None or self.active) and not self.invalid and time.monotonic() < deadline:
            self.page.wait_for_timeout(20)
        self.require_held()

    def release(self):
        self.require_held()
        try:
            self.route.fulfill(response=self.response)
        except Exception:
            self.invalid = True
            raise ValueError("detail_interception") from None
        self.route = None
        self.released = True

    def verify_released(self):
        if self.invalid or self.count != 1 or not self.released:
            raise ValueError("detail_interception")

    def close(self):
        self.closing = True
        # Public unroute(url, handler) has no wait option. Remove only ours,
        # then pump its in-flight callbacks; never suppress errors via unroute_all.
        try:
            self.page.unroute(self.url, self.handler)
        except (Exception, KeyboardInterrupt):
            self.invalid = True
        if self.route is not None:
            try:
                self.route.abort()
            except (Exception, KeyboardInterrupt):
                self.invalid = True
            self.route = None
        deadline = time.monotonic() + 6
        while self.active and time.monotonic() < deadline:
            try:
                self.page.wait_for_timeout(20)
            except (Exception, KeyboardInterrupt):
                self.invalid = True
                break
        if self.active:
            self.invalid = True
        if self.response is not None:
            try:
                self.response.dispose()
            except (Exception, KeyboardInterrupt):
                self.invalid = True
            self.response = None
        if self.invalid:
            raise ValueError("detail_interception")


def check_arrival_superseded(state, page, module, errors, expect):
    state["stage"] = "detail_hold"
    url = module["BROWSER_API_URL"] + "/graph/nodes/concept%3Aattention"
    with closing(HeldDetail(page, url)) as held:
        page.goto(module["FRONTEND_URL"] + GRAPH_HREF, wait_until="domcontentloaded")
        module["_wait_for_application_shell"](page)
        held.wait_ready()
        expect(page.get_by_role("button", name="Apply", exact=True)).to_be_enabled(timeout=30_000)
        node = page.get_by_test_id("graph-result-node-" + CONCEPT_ID)
        expect(node).to_be_attached(timeout=30_000)
        region = page.get_by_test_id("graph-selected-region")
        expect(region.get_by_text("Loading node details...", exact=True)).to_be_visible()
        if not page.evaluate("([key, value]) => sessionStorage.getItem(key) === JSON.stringify(value)",
                             [FOCUS_KEY, marker("arrival_superseded")]):
            raise ValueError("detail_interception")
        # No global request settlement while the exact detail GET is held.
        state["stage"] = "superseding_intent"
        panels = page.get_by_role("group", name="Explore panel", exact=True)
        activate(page, panels.get_by_role("button", name="Results", exact=True), module)
        expect(node).to_be_visible(timeout=30_000)
        activate(page, panels.get_by_role("button", name="Selected", exact=True), module)
        expect(region).to_be_focused(timeout=30_000)
        module["_require_visible_focus"](region, "newer_selected_intent")
        expect(region.get_by_text("Loading node details...", exact=True)).to_be_visible()
        state["stage"] = "detail_release"
        held.release()
        expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
        expect(page.get_by_test_id("graph-selection-status")).to_contain_text("Details ready.")
        settled(page, module, errors)
        held.verify_released()
        state["stage"] = "arrival_superseded"
        expect(page).to_have_url(module["FRONTEND_URL"] + GRAPH_HREF)
        expect(region).to_be_focused(timeout=30_000)
        module["_require_visible_focus"](region, "superseded_return_stays_in_region")
        collapsed(page, expect)
        consumed(page)
        state["checks"]["arrival_superseded"] = True


def check_case(state, page, module, errors, expect):
    if state["scenario"] == "arrival_superseded":
        return check_arrival_superseded(state, page, module, errors, expect)
    state["stage"] = "initial_graph"
    page.goto(module["FRONTEND_URL"] + GRAPH_HREF, wait_until="domcontentloaded")
    module["_wait_for_application_shell"](page)
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    expect(page).to_have_url(module["FRONTEND_URL"] + GRAPH_HREF)
    settled(page, module, errors)
    collapsed(page, expect)
    if state["scenario"] != "roundtrip":
        state["stage"] = "fallback"
        region = page.get_by_test_id("graph-selected-region")
        expect(region).to_be_focused(timeout=30_000)
        module["_require_visible_focus"](region, "invalid_origin_fallback")
        consumed(page)
        collapsed(page, expect)
        state["checks"]["fallback"] = True
        return
    state["stage"] = "expand"
    activate(page, page.get_by_role("button", name=MORE, exact=True), module)
    expect(page.locator(LINKS)).to_have_count(4)
    expect(source_link(page, 3)).to_be_visible()
    roundtrip(state, page, 3, module, errors, expect)
    expect(page.locator(LINKS)).to_have_count(4)
    expect(page.get_by_role("button", name=FEWER, exact=True)).to_be_visible()
    state["checks"]["expanded_return"] = True
    state["stage"] = "manual_collapse"
    activate(page, page.get_by_role("button", name=FEWER, exact=True), module)
    collapsed(page, expect)
    state["checks"]["manual_collapse"] = True
    roundtrip(state, page, 0, module, errors, expect)
    collapsed(page, expect)
    state["checks"]["ordinary_return"] = True
    state["stage"] = "cold_revisit"
    # Reload from an expanded view without re-arming a return marker.
    activate(page, page.get_by_role("button", name=MORE, exact=True), module)
    expect(page.locator(LINKS)).to_have_count(4)
    consumed(page)
    settled(page, module, errors)
    page.reload(wait_until="domcontentloaded")
    module["_wait_for_application_shell"](page)
    expect(page.get_by_role("heading", name="Concept Provenance", exact=True)).to_be_visible(timeout=30_000)
    settled(page, module, errors)
    expect(page).to_have_url(module["FRONTEND_URL"] + GRAPH_HREF)
    collapsed(page, expect)
    consumed(page)
    state["checks"]["cold_revisit"] = True


def run_cases(result, browser, module, runtime, root, expected_fixture, logs, expect):
    blocked, errors, page_errors = logs
    for viewport, width, height in VIEWPORTS:
        scenarios = SCENARIOS + (("arrival_superseded",) if viewport == "mobile" else ())
        for scenario in scenarios:
            state = {"viewport": viewport, "scenario": scenario, "status": "NOT_RUN",
                     "stage": "context_setup", "failure_stage": "none", "error": "none",
                     "fixture_unchanged": False,
                     "checks": dict.fromkeys(("expanded_return", "manual_collapse", "ordinary_return",
                                               "cold_revisit", "fallback"), False)}
            if scenario == "arrival_superseded":
                state["checks"] = {"arrival_superseded": False}
            result["cases"].append(state)
            try:
                if fixture_binding(runtime, root) != expected_fixture:
                    raise ValueError("fixture_changed")
                context = browser.new_context(viewport={"width": width, "height": height},
                                              locale="zh-CN", reduced_motion="reduce")
                with resource(state, closing(context), "context_setup", "context_teardown"):
                    module["_install_network_guard"](context, blocked)
                    if scenario != "roundtrip":
                        payload = json.dumps([FOCUS_KEY, marker(scenario)])
                        context.add_init_script("(() => {const [key, value] = " + payload +
                                                "; if (location.origin === 'http://127.0.0.1:3000') "
                                                "sessionStorage.setItem(key, JSON.stringify(value));})();")
                    page = module["_new_observed_page"](context, errors, page_errors, label=viewport + "-" + scenario)
                    try:
                        check_case(state, page, module, errors, expect)
                        state["status"] = "PASS"
                    except AssertionError:
                        if scenario == "arrival_superseded" and state["stage"] != "arrival_superseded":
                            raise ValueError("detail_interception") from None
                        fail(state, "ui_assertion")
                        state["status"] = "FAIL"
                    finally:
                        settled(page, module, errors)
            except (Exception, KeyboardInterrupt):
                fail(state, "execution_failed")
                state["status"] = "BLOCKED"
                # Infrastructure failure cannot authorize another live case.
                raise
            finally:
                state["stage"] = "case_bindings"
                state["fixture_unchanged"] = fixture_binding(runtime, root) == expected_fixture
                if not state["fixture_unchanged"]:
                    fail(state, "fixture_changed")
                    state["status"] = "BLOCKED"
                    raise ValueError("fixture_changed")


def runtime_module():
    return runpy.run_path(str(ROOT / "scripts/e2e/run_product_e2e.py"), run_name="provenance_return_runtime")


def browser_driver():
    from playwright.sync_api import expect, sync_playwright
    return sync_playwright, expect


def execute(result, configuration=None):
    result["stage"] = "bindings"
    bindings = source_bindings if configuration is None else lambda: source_bindings(frontend_root=configuration.frontend_root)
    before = bindings()
    module = runtime_module()
    if configuration is not None:
        module = module["configure_runtime"](configuration)
    blocked, errors, page_errors = module["NetworkGuardLog"](), module["ConsoleErrorLog"](), []
    path = runtime = expected_fixture = None
    try:
        with resource(result, tempfile.TemporaryDirectory(prefix="scientific-spaces-provenance-return-"),
                      "runtime_setup", "runtime_teardown") as temporary:
            path = Path(temporary)
            runtime = module["prepare_runtime"](path)
            result["stage"] = "seed"
            seed_graph(module, runtime, path)
            expected_fixture = fixture_binding(runtime, path)
            try:
                with resource(result, module["product_servers"](runtime, frontend_mode="start"),
                              "server_setup", "server_teardown"):
                    sync_playwright, expect = browser_driver()
                    with resource(result, sync_playwright(), "playwright_setup", "playwright_teardown") as playwright:
                        result["stage"] = "browser_setup"
                        browser = module["LocalOnlyBrowser"](playwright.chromium.launch(headless=True))
                        with resource(result, closing(browser), "browser_setup", "browser_teardown"):
                            run_cases(result, browser, module, runtime, path, expected_fixture,
                                      (blocked, errors, page_errors), expect)
            finally:
                result["fixture_unchanged"] = fixture_binding(runtime, path) == expected_fixture
    finally:
        result["runtime_removed"] = path is not None and not path.exists()
        result["stage"] = "audit"
        try:
            result["audit_counts"] = {
                "external": len(blocked), "console": len(module["_unexpected_console_errors"](errors)),
                "page": len(page_errors), "unexpected_pages": len(module["_unexpected_context_pages"](blocked)),
            }
            result["audit"] = "FAIL" if any(result["audit_counts"].values()) else "PASS"
        except Exception:
            result["audit"] = "FAIL"
            fail(result, "audit_failed")
        result["stage"] = "final_bindings"
        try:
            result["bindings_equal"] = bindings() == before
        except Exception:
            fail(result, "binding_changed")


def finalize(result):
    cases = result["cases"]
    if result["error"] != "none":
        return "BLOCKED"
    for valid, error in ((result["audit"] == "PASS", "audit_failed"),
                         (result["bindings_equal"], "binding_changed"),
                         (result["fixture_unchanged"], "fixture_changed"),
                         (result["runtime_removed"], "cleanup_failed")):
        if not valid:
            fail(result, error)
            return "BLOCKED"
    if len(cases) != 7 or any(case["status"] not in ("PASS", "FAIL") or not case["fixture_unchanged"] for case in cases):
        fail(result, "execution_failed")
        return "BLOCKED"
    return "FAIL" if any(case["status"] == "FAIL" for case in cases) else "PASS"


def main(argv=None):
    result = {"schema_version": 1, "status": "BLOCKED", "stage": "setup", "failure_stage": "none",
              "error": "none", "audit": "NOT_RUN", "audit_counts": {"external": 0, "console": 0,
              "page": 0, "unexpected_pages": 0}, "bindings_equal": False, "fixture_unchanged": False,
              "runtime_removed": False, "cases": []}
    previous_handler = signal.getsignal(signal.SIGTERM)
    try:
        def terminate(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, terminate)
        # Helpers may raise exceptions containing URLs or server logs. Never print them.
        with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink), redirect_stderr(sink):
            if list(sys.argv[1:] if argv is None else argv):
                fail(result, "invalid_arguments")
            else:
                e2e_root = str(ROOT / "scripts/e2e")
                if e2e_root not in sys.path:
                    sys.path.insert(0, e2e_root)
                from product_test_runtime import (
                    frontend_runtime, get_backend_port, process_environment, sanitized_environment,
                )

                backend_port = get_backend_port()
                if backend_port == 8000:
                    with process_environment(sanitized_environment()):
                        execute(result)
                else:
                    with frontend_runtime(ROOT, backend_port=backend_port) as configuration:
                        with process_environment(configuration.environment):
                            execute(result, configuration)
    except (Exception, KeyboardInterrupt):
        fail(result, "execution_failed")
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    result["status"] = finalize(result)
    result["stage"] = "complete"
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
