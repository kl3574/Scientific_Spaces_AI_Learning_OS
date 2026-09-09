#!/usr/bin/env python3
"""P3-042 synthetic navigation regression, separate from the original 298 checks.

run_article_list_navigation_profile(suite, *, frontend_mode='start') -> dict;
profile_passes(result) validates exact named coverage and final safety receipts.
CLI: no arguments, backend port must explicitly be 18000; stdout JSON only,
exit 0 PASS / 2 BLOCKED. No browser/build occurs on import. Two owned runtimes
(unchanged 3 Articles, separately derived 22 Articles), ten fresh contexts.
900s profile / 180s case admission budgets plus bounded in-flight calls/cleanup.
Browser bodies are independently mockable; orchestration and audits stay real.
"""

from __future__ import annotations

from contextlib import closing, redirect_stderr, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
from urllib.parse import unquote, urlencode, urlsplit

import check_graph_provenance_return as gate


ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = (("desktop", 1440, 1000), ("mobile", 390, 844))
CASE_CHECKS = {
    "original": ("filtered_shell_reset", "reload_control"),
    "controls": ("canonical_equivalence", "local_filter_shell_reset", "submit_echo_draft_selection",
                 "draft_sort", "draft_next_previous", "history_tuple", "history_feedback_focus", "same_search_refresh",
                 "clear_focus", "retry_focus"),
    "old_success": ("pending_rows_clear", "superseded_rows_selection_focus"),
    "old_failure": ("pending_rows_clear", "superseded_rows_selection_focus"),
    "aba": ("pending_rows_clear", "superseded_rows_selection_focus"),
}
CASE_IDS = tuple(f"{viewport}_{case}" for viewport, _, _ in VIEWPORTS for case in CASE_CHECKS)
AUDIT_KEYS = frozenset(("external", "console", "page", "unexpected_pages"))
ORIGINAL_IDS = ("attention-basics", "crb-formula", "local-research-map")


def expected_checks(case_id):
    viewport, case = case_id.split("_", 1)
    if viewport not in {item[0] for item in VIEWPORTS} or case not in CASE_CHECKS:
        raise ValueError("invalid_case")
    return {f"{case_id}_{name}" for name in CASE_CHECKS[case]}


def exact_checks(checks, names):
    return isinstance(checks, dict) and set(checks) == set(names) and all(value is True for value in checks.values())


def clean_audit(counts):
    return (isinstance(counts, dict) and set(counts) == AUDIT_KEYS
            and all(type(value) is int and value == 0 for value in counts.values()))


def failure_location(error):
    """Only fixed categories and trusted source line numbers, never exception text."""
    category = type(error).__name__
    if category not in {"AssertionError", "E2EFailure", "Error", "TimeoutError", "ValueError", "RuntimeError", "KeyboardInterrupt"}:
        category = "other"
    trusted = {str(ROOT / "scripts/e2e" / name): name for name in (
        "check_article_list_navigation.py", "check_graph_provenance_return.py", "run_product_e2e.py")}
    frames, trace, visited = [], error.__traceback__, 0
    while trace is not None and visited < 64:
        filename = trusted.get(trace.tb_frame.f_code.co_filename)
        if filename is not None:
            frames.append({"file": filename, "line": trace.tb_lineno})
        trace, visited = trace.tb_next, visited + 1
    return {"category": category, "frames": frames[-8:]}


def failure_audit_kinds(suite, errors):
    known = {"invalid_route_transition_expectation", "duplicate_route_transition_expectation",
             "duplicate_route_transition_request_binding", "invalid_http_error_declarations",
             "unsettled_product_request", "failed_product_request_after_http_response",
             "failed_product_request_without_http_response", "console_cardinality",
             "unregistered_http_error_response", "console_evidence_alignment"}
    failures = suite["_unexpected_console_errors"](errors)
    return {"kinds": [item["kind"] if isinstance(item, dict) and item.get("kind") in known else "other"
                      for item in failures[:8]], "omitted": max(0, len(failures) - 8)}


def profile_passes(result):
    if not isinstance(result, dict) or result.get("errors") != []:
        return False
    if not all(result.get(key) is True for key in ("bindings_equal", "fixture_stable", "runtime_removed")):
        return False
    if not isinstance(result.get("browser_version"), str) or not result["browser_version"]:
        return False
    cases = result.get("cases")
    if not isinstance(cases, list) or len(cases) != len(CASE_IDS):
        return False
    if any(not isinstance(row, dict) for row in cases) or {row.get("case") for row in cases} != set(CASE_IDS):
        return False
    for row in cases:
        if (row.get("status") != "PASS" or not exact_checks(row.get("checks"), expected_checks(row["case"]))
                or not clean_audit(row.get("audit_before_cleanup")) or not clean_audit(row.get("audit_after_cleanup"))):
            return False
    return result.get("status") == "PASS"


def pagination_articles(suite):
    return [suite["StoredArticle"](
        id=f"navigation-{number:02d}",
        title=f"Navigation {number:02d} {'Alpha' if number <= 21 else 'Beta'}",
        url=f"http://localhost:3000/articles/navigation-{number:02d}",
        content=f"## Navigation {number:02d}\n\nOwned synthetic navigation material.",
        metadata={"date": f"2025-01-{number:02d}", "category": "navigation-fixture", "references": [], "images": []},
    ) for number in range(1, 23)]


def source_bindings(suite):
    return {**gate.source_bindings(frontend_root=suite["FRONTEND_ROOT"]),
            "navigation_profile": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def fixture_binding(runtime, root):
    root = root.resolve()
    paths = [Path(runtime[key]) for key in ("articles", "graph")]
    references = Path(runtime["references"])
    if references.is_symlink() or not references.resolve().is_relative_to(root):
        raise ValueError("fixture_ownership")
    paths.extend(path for path in references.rglob("*") if path.is_file())
    if len(paths) <= 2 or any(path.is_symlink() or not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("fixture_ownership")
    return gate.digest_paths(paths, relative_root=root)


def audit(suite, blocked, errors, page_errors):
    return {"external": len(blocked), "console": len(suite["_unexpected_console_errors"](errors)),
            "page": len(page_errors), "unexpected_pages": len(suite["_unexpected_context_pages"](blocked))}


def run_article_list_navigation_profile(suite, *, frontend_mode="start"):
    from playwright.sync_api import expect, sync_playwright

    result = {"schema_version": 1, "status": "BLOCKED", "errors": [], "cases": [], "fixtures": [],
              "bindings_equal": False, "fixture_stable": False, "runtime_removed": False}
    observations, paths, versions = [], [], []
    before = None
    deadline = time.monotonic() + 900
    try:
        before = source_bindings(suite)
        result["bindings"] = before
        for size in (3, 22):
            fixture = {"count": size, "stable": False}
            result["fixtures"].append(fixture)
            with tempfile.TemporaryDirectory(prefix=f"scientific-spaces-article-navigation-{size}-") as temporary:
                root = Path(temporary)
                paths.append(root)
                records = suite["_load_fixture_articles"]() if size == 3 else pagination_articles(suite)
                options = {} if size == 3 else {"fixture_articles": records}
                runtime = suite["prepare_runtime"](root, **options)
                if json.loads(Path(runtime["articles"]).read_text()) != [item.to_dict() for item in records]:
                    raise ValueError("fixture_mismatch")
                initial = fixture_binding(runtime, root)
                fixture["binding"] = initial
                try:
                    with suite["product_servers"](runtime, frontend_mode=frontend_mode):
                        with sync_playwright() as playwright:
                            with closing(suite["LocalOnlyBrowser"](playwright.chromium.launch(headless=True))) as browser:
                                versions.append(browser.version)
                                result["browser_version"] = versions[0]
                                for viewport, width, height in VIEWPORTS:
                                    for case in (("original",) if size == 3 else tuple(CASE_CHECKS)[1:]):
                                        if time.monotonic() >= deadline:
                                            raise TimeoutError("profile_budget")
                                        suite["_reset_mutable_runtime"](runtime)
                                        case_id = f"{viewport}_{case}"
                                        row = {"case": case_id, "status": "BLOCKED", "checks": {}, "stage": "context_setup"}
                                        result["cases"].append(row)
                                        ledgers = suite["NetworkGuardLog"](), suite["ConsoleErrorLog"](), []
                                        observations.append((row, ledgers))
                                        try:
                                            with closing(browser.new_context(viewport={"width": width, "height": height},
                                                                             locale="zh-CN", reduced_motion="reduce")) as context:
                                                try:
                                                    suite["_install_network_guard"](context, ledgers[0])
                                                    page = suite["_new_observed_page"](context, ledgers[1], ledgers[2], label=case_id)
                                                    page.set_default_timeout(10_000)
                                                    page.set_default_navigation_timeout(30_000)
                                                    row["checks"] = run_case(page, suite, case_id, ledgers[1], expect, row,
                                                                             min(deadline, time.monotonic() + 180))
                                                    if not exact_checks(row["checks"], expected_checks(case_id)):
                                                        raise ValueError("incomplete_checks")
                                                except (Exception, KeyboardInterrupt) as exc:
                                                    row["failure_location"] = failure_location(exc)
                                                    raise
                                                finally:
                                                    row["audit_before_cleanup"] = audit(suite, *ledgers)
                                        finally:
                                            row["audit_after_cleanup"] = audit(suite, *ledgers)
                                        if not all(clean_audit(row[key]) for key in ("audit_before_cleanup", "audit_after_cleanup")):
                                            raise ValueError("audit_failed")
                                        row["status"] = "PASS"
                finally:
                    fixture["stable"] = fixture_binding(runtime, root) == initial
            for row, ledgers in observations:
                row["audit_after_cleanup"] = audit(suite, *ledgers)
                if not clean_audit(row["audit_after_cleanup"]):
                    row["status"] = "BLOCKED"
                    raise ValueError("audit_failed")
            if not fixture["stable"] or root.exists():
                raise ValueError("fixture_cleanup_failed")
    except (Exception, KeyboardInterrupt) as exc:
        result["failure_location"] = failure_location(exc)
        result["errors"].append("interrupted" if isinstance(exc, KeyboardInterrupt) else "execution_failed")
    finally:
        result["runtime_removed"] = bool(paths) and all(not path.exists() for path in paths)
        result["fixture_stable"] = len(result["fixtures"]) == 2 and all(item["stable"] for item in result["fixtures"])
        for row, ledgers in observations:
            try:
                row["audit_after_cleanup"] = audit(suite, *ledgers)
                if not clean_audit(row["audit_after_cleanup"]) or not clean_audit(row.get("audit_before_cleanup")):
                    row["status"] = "BLOCKED"
                    row["failure_audit"] = failure_audit_kinds(suite, ledgers[1])
                    result["errors"].append("audit_failed")
            except Exception:
                row["status"] = "BLOCKED"
                result["errors"].append("audit_failed")
        try:
            result["bindings_equal"] = before is not None and source_bindings(suite) == before
        except Exception:
            result["errors"].append("binding_failed")
        if len(versions) != 2 or len(set(versions)) != 1:
            result["errors"].append("browser_mismatch")
    result["status"] = "PASS"
    if not profile_passes(result):
        result["status"] = "BLOCKED"
    return result


def article_url(suite, q="", sort="date_desc", page=1):
    params = {}
    if q:
        params["q"] = q
    params.update(page=page, page_size=20, sort=sort)
    return suite["BROWSER_API_URL"] + "/v1.1/articles?" + urlencode(params)


def list_href(q="", sort="date_desc", page=1):
    params = {}
    if q:
        params["q"] = q
    if sort != "date_desc":
        params["sort"] = sort
    if page > 1:
        params["page"] = page
    return "/articles" + ("?" + urlencode(params) if params else "")


class ArticleResponses:
    """Bounded response handles; decode only explicitly while the page is alive."""

    def __init__(self, page, suite):
        self.page, self.suite = page, suite
        self.responses, self.invalid = [], False
        self.handler = self.record
        page.on("response", self.handler)

    def record(self, response):
        try:
            if response.url.startswith(self.suite["BROWSER_API_URL"] + "/v1.1/articles?"):
                if len(self.responses) >= 128:
                    self.invalid = True
                else:
                    self.responses.append(response)
        except (Exception, KeyboardInterrupt):
            self.invalid = True

    def receipt(self, q, sort, page, ids, *, after=0):
        url = article_url(self.suite, q, sort, page)
        deadline = time.monotonic() + 10
        while not any(item.url == url and item.status == 200 for item in self.responses[after:]):
            if self.invalid or time.monotonic() >= deadline:
                raise ValueError("missing_article_response")
            self.page.wait_for_timeout(20)
        response = [item for item in self.responses[after:] if item.url == url and item.status == 200][-1]
        if response.request.method != "GET":
            raise ValueError("invalid_article_response")
        # Body retrieval waits for termination; the separate ledger rejects failed requests.
        payload = response.json()
        if (payload["page"] != page or payload["sort"] != sort
                or [item["id"] for item in payload["items"]] != list(ids)):
            raise ValueError("article_response_mismatch")
        if self.invalid:
            raise ValueError("response_capture_failed")

    def close(self):
        self.page.remove_listener("response", self.handler)
        self.responses.clear()
        if self.invalid:
            raise ValueError("response_capture_failed")


class HeldArticle(gate.HeldDetail):
    """Reuse the reviewed one-response capture/abort/dispose lifecycle."""

    def __init__(self, page, url):
        self.accepting = True
        super().__init__(page, url)

    def intercept(self, route):
        if not self.accepting and not self.closing:
            self.active += 1
            try:
                route.fallback()
            except (Exception, KeyboardInterrupt):
                self.invalid = True
            finally:
                self.active -= 1
            return
        super().intercept(route)

    def wait_ready(self):
        super().wait_ready()
        # Unrouting a paused handler resumes it; retain ownership until release.
        self.accepting = False

    def release_error(self, suite, errors, expectation_ids):
        self.require_held()
        try:
            suite["_fulfill_expected_http_error"](
                self.route, console_errors=errors, page=self.page, expectation_ids=expectation_ids,
                body='{"detail":"controlled navigation failure"}')
        except (Exception, KeyboardInterrupt):
            self.invalid = True
            raise
        self.route = None
        self.released = True


class Journey:
    def __init__(self, page, suite, case_id, errors, expect, row, deadline, responses):
        self.page, self.suite, self.case_id = page, suite, case_id
        self.errors, self.expect, self.row, self.deadline, self.responses = errors, expect, row, deadline, responses
        self.checks = row.setdefault("checks", {})

    def stage(self, name):
        self.row["stage"] = name
        if time.monotonic() >= self.deadline:
            raise TimeoutError("case_budget")

    def mark(self, name):
        self.checks[f"{self.case_id}_{name}"] = True

    @property
    def search(self):
        return self.page.get_by_role("searchbox", name="Search", exact=True)

    @property
    def sort(self):
        return self.page.get_by_role("combobox", name="Sort", exact=True)

    @property
    def rows(self):
        return self.page.get_by_test_id("article-discovery-workspace").locator('article a[href^="/articles/"]')

    def settle(self):
        self.suite["_wait_for_page_requests_to_settle"](self.page, self.errors)

    def activate(self, locator):
        self.suite["_focus_via_tab"](self.page, locator)
        locator.press("Enter")

    def history_length(self):
        return self.page.evaluate("history.length")

    def loaded(self, ids, total, q="", sort="date_desc", page=1, *, draft=None, after=0, settle=True):
        self.expect(self.page).to_have_url(self.suite["FRONTEND_URL"] + list_href(q, sort, page))
        self.responses.receipt(q, sort, page, ids, after=after)
        self.expect(self.search).to_have_value(q if draft is None else draft)
        self.expect(self.sort).to_have_value(sort)
        self.expect(self.rows).to_have_count(len(ids))
        actual = self.rows.evaluate_all('links => links.map(link => link.getAttribute("href"))')
        if [unquote(urlsplit(href).path.split("/")[-1]) for href in actual] != list(ids):
            raise AssertionError("visible_article_mismatch")
        start = (page - 1) * 20 + 1
        self.expect(self.page.get_by_test_id("article-list-status")).to_have_text(
            f"Showing {start}-{min(page * 20, total)} of {total}")
        if settle:
            self.settle()

    def goto(self, href):
        self.page.goto(self.suite["FRONTEND_URL"] + href, wait_until="domcontentloaded")
        self.suite["_wait_for_application_shell"](self.page)
        self.expect(self.page.get_by_role("heading", name="Article List", exact=True)).to_be_visible()

    def submit(self, text):
        self.search.fill(text)
        self.search.press("Enter")

    def shell_reset(self):
        self.settle()
        previous = self.history_length()
        old_url = self.page.url
        if self.case_id.startswith("mobile_"):
            self.activate(self.page.get_by_role("button", name="Open navigation", exact=True))
        link = self.page.get_by_test_id("primary-nav-articles")
        if self.case_id.startswith("mobile_"):
            link = self.page.locator('[data-variant="drawer"]').get_by_test_id("primary-nav-articles")
        self.expect(link).to_have_attribute("href", "/articles")
        self.suite["_focus_via_tab"](self.page, link)
        transition = self.suite["_declare_expected_route_transition"](
            self.page, destination_url=self.suite["FRONTEND_URL"] + "/articles")
        link.press("Enter")
        self.expect(self.page).to_have_url(self.suite["FRONTEND_URL"] + "/articles", timeout=30_000)
        self.expect(self.page.get_by_test_id("shell-main-content")).to_be_focused(timeout=40_000)
        self.suite["_complete_expected_route_transition"](self.page, transition)
        self.settle()
        if self.history_length() != previous + (old_url != self.page.url):
            raise AssertionError("shell_history_mismatch")

    def history(self, direction, href):
        self.settle()
        size = self.history_length()
        transition = self.suite["_declare_expected_route_transition"](
            self.page, destination_url=self.suite["FRONTEND_URL"] + href)
        getattr(self.page, "go_" + direction)(wait_until="domcontentloaded")
        self.expect(self.page).to_have_url(self.suite["FRONTEND_URL"] + href, timeout=30_000)
        self.suite["_complete_expected_route_transition"](self.page, transition)
        self.settle()
        if self.history_length() != size:
            raise AssertionError("history_length_changed")


def run_case(page, suite, case_id, errors, expect, row, deadline):
    with closing(ArticleResponses(page, suite)) as responses:
        journey = Journey(page, suite, case_id, errors, expect, row, deadline, responses)
        case = case_id.split("_", 1)[1]
        if case == "original":
            original_case(journey)
        elif case == "controls":
            controls_case(journey)
        else:
            race_case(journey, case)
        return journey.checks


def original_case(j):
    j.stage("filtered_entry")
    j.goto(list_href("Attention", "relevance"))
    j.loaded([ORIGINAL_IDS[0]], 1, "Attention", "relevance")
    j.stage("filtered_shell_reset")
    before = len(j.responses.responses)
    j.shell_reset()
    j.loaded(tuple(reversed(ORIGINAL_IDS)), 3, after=before)
    j.mark("filtered_shell_reset")
    j.stage("reload_control")
    size = j.history_length()
    before = len(j.responses.responses)
    j.page.reload(wait_until="domcontentloaded")
    j.suite["_wait_for_application_shell"](j.page)
    j.loaded(tuple(reversed(ORIGINAL_IDS)), 3, after=before)
    assert j.history_length() == size, "reload_history_changed"
    j.mark("reload_control")


def controls_case(j):
    alpha = [f"navigation-{number:02d}" for number in range(1, 22)]
    default = [f"navigation-{number:02d}" for number in range(22, 2, -1)]
    draft = "Unsubmitted learner draft"
    j.stage("canonical_equivalence")
    j.goto("/articles?page=1&sort=date_desc")
    j.loaded(default, 22)
    assert len(j.responses.responses) == 1, "canonical_duplicate_request"
    j.mark("canonical_equivalence")
    j.stage("local_filter_shell_reset")
    before = len(j.responses.responses)
    j.submit("Alpha")
    j.loaded(list(reversed(alpha))[:20], 21, "Alpha", after=before)
    before = len(j.responses.responses)
    j.shell_reset()
    j.loaded(default, 22, after=before)
    j.mark("local_filter_shell_reset")
    j.stage("submit_echo_draft_selection")
    size, before = j.history_length(), len(j.responses.responses)
    j.submit("Alpha")
    j.search.fill(draft)
    j.loaded(list(reversed(alpha))[:20], 21, "Alpha", draft=draft, after=before)
    checkbox = j.page.get_by_role("checkbox").first
    j.suite["_focus_via_tab"](j.page, checkbox)
    checkbox.press("Space")
    j.settle()
    j.expect(checkbox).to_be_checked()
    j.expect(j.search).to_have_value(draft)
    assert len(j.responses.responses) == before + 1 and j.history_length() == size, "local_echo_mutated_history_or_requests"
    j.mark("submit_echo_draft_selection")
    j.stage("draft_sort")
    before = len(j.responses.responses)
    j.sort.select_option("title_asc")
    j.loaded(alpha[:20], 21, "Alpha", "title_asc", draft=draft, after=before)
    j.expect(j.page.locator('article input[type="checkbox"]:checked')).to_have_count(0)
    j.mark("draft_sort")
    j.stage("draft_next_previous")
    before = len(j.responses.responses)
    j.activate(j.page.get_by_role("button", name="Next", exact=True))
    j.loaded(alpha[20:], 21, "Alpha", "title_asc", 2, draft=draft, after=before)
    before = len(j.responses.responses)
    j.activate(j.page.get_by_role("button", name="Previous", exact=True))
    j.loaded(alpha[:20], 21, "Alpha", "title_asc", draft=draft, after=before)
    assert j.history_length() == size, "local_paging_pushed_history"
    j.mark("draft_next_previous")
    j.stage("same_search_refresh")
    before = len(j.responses.responses)
    j.submit("Alpha")
    j.loaded(alpha[:20], 21, "Alpha", "title_asc", after=before)
    assert len(j.responses.responses) == before + 1 and j.history_length() == size, "refresh_not_exact"
    j.mark("same_search_refresh")
    j.stage("history_tuple")
    before = len(j.responses.responses)
    j.activate(j.page.get_by_role("button", name="Next", exact=True))
    j.loaded(alpha[20:], 21, "Alpha", "title_asc", 2, after=before)
    before = len(j.responses.responses)
    j.shell_reset()
    j.loaded(default, 22, after=before)
    history_feedback_case(j, alpha[20:])
    before = len(j.responses.responses)
    j.history("forward", "/articles")
    j.loaded(default, 22, after=before)
    j.mark("history_tuple")
    j.stage("clear_focus")
    before = len(j.responses.responses)
    j.submit("Alpha")
    j.loaded(list(reversed(alpha))[:20], 21, "Alpha", after=before)
    before = len(j.responses.responses)
    j.activate(j.page.get_by_role("button", name="Clear", exact=True))
    j.loaded(default, 22, after=before)
    j.expect(j.search).to_be_focused()
    j.suite["_require_visible_focus"](j.search, "article_clear")
    j.mark("clear_focus")
    j.stage("retry_focus")
    failure = j.suite["_declare_expected_http_errors"](
        j.errors, label=j.case_id, page_url=j.page.url, source_url=article_url(j.suite))
    with closing(HeldArticle(j.page, article_url(j.suite))) as held:
        j.submit("")
        held.wait_ready()
        j.expect(j.rows).to_have_count(0)
        held.release_error(j.suite, j.errors, failure)
        j.suite["_wait_for_declared_http_errors"](j.page, j.errors, expectation_ids=failure)
        held.verify_released()
    retry = j.page.get_by_role("button", name="Retry articles", exact=True)
    j.expect(retry).to_be_visible()
    j.expect(j.rows).to_have_count(0)
    before = len(j.responses.responses)
    j.activate(retry)
    j.loaded(default, 22, after=before)
    target = j.page.get_by_test_id("article-list-status")
    j.expect(target).to_be_focused()
    j.suite["_require_visible_focus"](target, "article_retry")
    j.mark("retry_focus")


def history_feedback_case(j, ids):
    j.stage("history_feedback_select")
    selected = j.page.get_by_role("checkbox").first
    j.suite["_focus_via_tab"](j.page, selected)
    selected.press("Space")
    j.stage("history_feedback_capture")
    j.activate(j.page.get_by_role("button", name="Add selected to session", exact=True))
    feedback = j.page.get_by_test_id("article-session-capture-feedback")
    j.expect(feedback).to_be_focused()
    j.stage("history_feedback_settle")
    j.settle()
    # Observe only; do not change DOM, focus, history or the router from JS.
    j.page.evaluate("""() => {
      const state = {count: 0};
      state.listener = event => {
        if (event.target === document.querySelector('[data-testid="article-session-capture"]')) state.count++;
      };
      window.__articleNavigationFocus = state;
      document.addEventListener('focusin', state.listener);
    }""")
    try:
        href = list_href("Alpha", "title_asc", 2)
        size = j.history_length()
        before = len(j.responses.responses)
        with closing(HeldArticle(j.page, article_url(j.suite, "Alpha", "title_asc", 2))) as held:
            j.stage("history_feedback_back")
            transition = j.suite["_declare_expected_route_transition"](
                j.page, destination_url=j.suite["FRONTEND_URL"] + href)
            j.page.go_back(wait_until="domcontentloaded")
            j.expect(j.page).to_have_url(j.suite["FRONTEND_URL"] + href, timeout=30_000)
            j.stage("history_feedback_hold")
            held.wait_ready()
            j.stage("history_feedback_pending")
            j.expect(j.rows).to_have_count(0)
            j.stage("history_feedback_newer_focus")
            j.suite["_focus_via_tab"](j.page, j.search)
            j.search.fill("Newer history draft")
            j.expect(j.search).to_be_focused()
            j.stage("history_feedback_release")
            held.release()
            held.verify_released()
            j.stage("history_feedback_route_completion")
            j.suite["_complete_expected_route_transition"](j.page, transition)
            j.stage("history_feedback_loaded")
            j.loaded(ids, 21, "Alpha", "title_asc", 2, draft="Newer history draft", after=before)
            j.stage("history_feedback_focus_check")
            j.expect(j.search).to_be_focused()
            assert j.history_length() == size, "feedback_back_pushed_history"
            assert j.page.evaluate("window.__articleNavigationFocus.count") == 0, "external_navigation_focused_capture"
        j.mark("history_feedback_focus")
    finally:
        j.page.evaluate("""() => {
          document.removeEventListener('focusin', window.__articleNavigationFocus.listener);
          delete window.__articleNavigationFocus;
        }""")


def race_case(j, case):
    j.stage("race_setup")
    j.goto("/articles")
    j.loaded([f"navigation-{number:02d}" for number in range(22, 2, -1)], 22)
    initial_selection = j.page.get_by_role("checkbox").first
    j.suite["_focus_via_tab"](j.page, initial_selection)
    initial_selection.press("Space")
    url = article_url(j.suite, "Alpha")
    failure = None
    if case != "old_success":
        failure = j.suite["_declare_expected_http_errors"](
            j.errors, label=j.case_id, page_url=j.suite["FRONTEND_URL"] + list_href("Alpha"), source_url=url)
    with closing(HeldArticle(j.page, url)) as held:
        j.stage("hold_old_response")
        j.submit("Alpha")
        held.wait_ready()
        j.expect(j.rows).to_have_count(0)
        j.expect(j.page.get_by_test_id("article-session-capture")).to_contain_text("0 selected on this page")
        j.mark("pending_rows_clear")
        # The old GET is intentionally pending: qualify the new response/UI,
        # but do not ask the unchanged global settlement helper to ignore it.
        j.stage("newer_intent")
        before = len(j.responses.responses)
        j.submit("Beta")
        j.loaded(["navigation-22"], 1, "Beta", after=before, settle=False)
        ids, q, total = ["navigation-22"], "Beta", 1
        if case == "aba":
            before = len(j.responses.responses)
            j.submit("Alpha")
            ids, q, total = [f"navigation-{number:02d}" for number in range(21, 1, -1)], "Alpha", 21
            j.loaded(ids, total, q, after=before, settle=False)
        selected = j.page.get_by_role("checkbox").first
        j.suite["_focus_via_tab"](j.page, selected)
        selected.press("Space")
        j.expect(selected).to_be_checked()
        j.suite["_focus_via_tab"](j.page, j.search)
        j.stage("release_old_response")
        if failure is None:
            held.release()
        else:
            held.release_error(j.suite, j.errors, failure)
            j.suite["_wait_for_declared_http_errors"](j.page, j.errors, expectation_ids=failure)
        held.verify_released()
        j.settle()
        j.loaded(ids, total, q)
        j.expect(selected).to_be_checked()
        j.expect(j.page.get_by_test_id("article-session-capture")).to_contain_text("1 selected on this page")
        j.expect(j.search).to_be_focused()
        j.expect(j.page.get_by_role("button", name="Retry articles", exact=True)).to_have_count(0)
        j.mark("superseded_rows_selection_focus")


COMPONENT_RUNS = (
    ("current", "accept_success", None),
    ("current", "accept_failure", None),
    ("current", "batched_aba", None),
    ("without_invalidation", "accept_success", "stale_success_read"),
    ("without_invalidation", "accept_failure", "stale_failure_read"),
    ("without_revision", "batched_aba", "replacement_fetch_missing"),
)
COMPONENT_COMMON_CHECKS = (
    "setup_single_request", "draft_committed", "accepted_before_effect",
    "old_continuation_drained", "stale_result_ignored", "replacement_fetch",
    "current_result_read", "final_rows", "selection_and_focus", "cleanup",
)


def component_variants(source):
    anchors = {"without_invalidation": "    articleRequestId.current += 1;\n",
               "without_revision": "    listRevisionRef.current += 1;\n"}
    lines = source.splitlines(keepends=True)
    if any(lines.count(anchor) != 1 for anchor in anchors.values()):
        raise ValueError("component_mutation_binding")
    return {"current": source, **{name: "".join(line for line in lines if line != anchor)
                                 for name, anchor in anchors.items()}}


COMPONENT_API = r"""
export { formatMetadata } from 'actual-articles';
export const requests = [];
export function fetchArticles(options) {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  const call = {options, resolve, reject, settled: false, drained: false};
  // The second reaction runs after the component's already-registered await.
  call.checkpoint = promise.then(() => {}, () => {}).then(() => { call.drained = true; });
  call.afterContinuation = observe => promise.then(observe, observe);
  call.success = value => { call.settled = true; resolve(value); };
  call.failure = value => { call.settled = true; reject(value); };
  requests.push(call);
  return promise;
}
"""

COMPONENT_ENTRY = r"""
import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { createRoot } from 'react-dom/client';
import { ArticleListView } from 'test-subject';
import { requests } from './api.js';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const {act, Profiler} = React;
const cases = new Set(['accept_success', 'accept_failure', 'batched_aba']);
class ContractFailure extends Error { constructor(code) { super(code); this.code = code; } }
function require(value, code) { if (!value) throw new ContractFailure(code); }
const frames = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const input = () => document.querySelector('input[type=search]');
const button = name => [...document.querySelectorAll('button')].find(node => node.textContent.trim() === name);
const rowIds = () => [...document.querySelectorAll('article a[href^="/articles/"]')]
  .map(node => new URL(node.href).pathname.split('/').pop());
const response = (query, counter) => ({
  get items() {
    counter.reads++;
    return [1, 2].map(n => ({id: `component-${query || 'all'}-${n}`, title: `Component Article ${n}`,
      url: `http://localhost:3000/articles/component-${n}`, content_preview: 'Owned synthetic component material.',
      metadata: {date: '2025-01-01', category: 'component-fixture', references: [], images: []}}));
  }, total: 2, page: 1, page_size: 20, sort: 'date_desc', query: query || null,
  total_pages: 1, has_next: false, has_previous: false,
});
function rejection(counter) {
  const error = new Error();
  Object.defineProperty(error, 'message', {get() { counter.reads++; return 'Controlled component failure'; }});
  return error;
}

async function run(name) {
  const result = {status: 'BLOCKED', error: 'component_setup', checks: {}, stage: 'setup',
    react_version: React.version, react_dom_version: ReactDOM.version};
  let root, commits = 0;
  const mark = name => { result.checks[name] = true; };
  try {
    require(cases.has(name) && requests.length === 0 && location.pathname === '/articles' && !location.search,
      'component_setup');
    require(React.version === BUILD_REACT_VERSION && ReactDOM.version === BUILD_REACT_DOM_VERSION,
      'react_version');
    root = createRoot(document.getElementById('root'));
    await act(async () => {
      root.render(React.createElement(Profiler, {id: 'ArticleList', onRender: () => { commits++; }},
        React.createElement(ArticleListView, {initialState: {q: '', sort: 'date_desc', page: 1}})));
    });
    require(commits > 0 && requests.length === 1 && requests[0].options.q === '', 'initial_request');
    mark('setup_single_request');
    result.stage = 'draft';
    await act(async () => {
      input().focus();
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input(), 'B');
      input().dispatchEvent(new Event('input', {bubbles: true}));
    });
    require(input().value === 'B' && button('Clear') && !button('Clear').disabled && requests.length === 1,
      'draft_not_committed');
    mark('draft_committed');
    const before = commits;
    const old = requests[0], stale = {reads: 0};
    const aba = name === 'batched_aba', failed = name === 'accept_failure';
    result.stage = 'acceptance_window';
    await act(async () => {
      const observed = old.afterContinuation(() => Object.freeze({
        accepted: result.checks.accepted_before_effect === true, search: location.search,
        commits, requests: requests.length, reads: stale.reads,
      }));
      // Queue the old continuation before React's root microtask, then accept new intent synchronously.
      if (failed) old.failure(rejection(stale)); else old.success(response('', stale));
      document.querySelector('form').requestSubmit();
      require(location.search === '?q=B', 'query_not_accepted');
      if (aba) {
        button('Clear').click();
        require(!location.search, 'aba_not_accepted');
      }
      require(commits === before && requests.length === 1, 'window_not_qualified');
      mark('accepted_before_effect');
      if (aba) mark('same_batch_aba');
      const snapshot = await observed;
      await old.checkpoint;
      require(old.drained && snapshot.accepted && snapshot.search === (aba ? '' : '?q=B')
        && snapshot.commits === before && snapshot.requests === 1, 'continuation_not_qualified');
      mark('old_continuation_drained');
      require(snapshot.reads === 0, failed ? 'stale_failure_read' : 'stale_success_read');
      mark('stale_result_ignored');
    });
    result.stage = 'replacement';
    const query = aba ? '' : 'B';
    require(requests.length === 2 && requests[1].options.q === query && commits > before,
      'replacement_fetch_missing');
    require(rowIds().length === 0, 'pending_rows_exposed');
    mark('replacement_fetch');
    if (failed) {
      const currentError = {reads: 0};
      await act(async () => { requests[1].failure(rejection(currentError)); await requests[1].checkpoint; });
      require(currentError.reads > 0 && button('Retry articles') && rowIds().length === 0,
        'current_error_not_read');
      mark('current_error_read');
      await act(async () => {
        button('Retry articles').focus();
        button('Retry articles').click();
      });
      require(requests.length === 3 && requests[2].options.q === query, 'retry_request');
    }
    result.stage = 'current_result';
    const current = requests[requests.length - 1], currentReads = {reads: 0};
    await act(async () => { current.success(response(query, currentReads)); await current.checkpoint; });
    await act(async () => { await frames(); });
    require(currentReads.reads > 0, 'current_result_not_read');
    mark('current_result_read');
    require(JSON.stringify(rowIds()) === JSON.stringify([1, 2].map(n => `component-${query || 'all'}-${n}`)),
      'current_rows');
    require(document.querySelector('[data-testid=article-list-status]').textContent === 'Showing 1-2 of 2',
      'current_range');
    mark('final_rows');
    const focus = failed ? document.querySelector('[data-testid=article-list-status]') : input();
    require(document.activeElement === focus, 'result_focus');
    await act(async () => { document.querySelector('article input[type=checkbox]').click(); });
    await act(async () => { await frames(); });
    require(document.querySelector('article input[type=checkbox]').checked
      && document.querySelector('[data-testid=article-session-capture]').textContent.includes('1 selected on this page')
      && document.activeElement === focus, 'selection_focus');
    mark('selection_and_focus');
    result.status = 'PASS'; result.error = null;
  } catch (error) {
    result.error = error instanceof ContractFailure ? error.code : 'component_execution';
  } finally {
    try {
      await act(async () => {
        if (root) root.unmount();
        for (const call of requests) if (!call.settled) call.success(response('', {reads: 0}));
        await Promise.all(requests.map(call => call.checkpoint));
        await frames();
      });
      require(requests.every(call => call.settled && call.drained)
        && document.getElementById('root').childElementCount === 0, 'component_cleanup');
      mark('cleanup');
    } catch (_) { result.status = 'BLOCKED'; result.error = 'component_cleanup'; }
  }
  return result;
}
window.articleComponentContract = {run};
"""

COMPONENT_BUILD = r"""
const fs = require('node:fs');
const path = require('node:path');
const [root, frontend] = process.argv.slice(2);
const modules = fs.realpathSync(path.join(frontend, 'node_modules'));
const nextWebpack = require(path.join(modules, 'next/dist/compiled/webpack/webpack.js'));
nextWebpack.init();
const webpack = nextWebpack.webpack;
const versions = {
  react: require(path.join(modules, 'react/package.json')).version,
  react_dom: require(path.join(modules, 'react-dom/package.json')).version,
  typescript: require(path.join(modules, 'typescript/package.json')).version,
  next: require(path.join(modules, 'next/package.json')).version,
};
async function build(variant) {
  const directory = path.join(root, variant);
  const compiler = webpack({
    mode: 'development', target: 'web', devtool: false, cache: false,
    context: root, entry: path.join(root, 'entry.js'),
    output: {path: directory, filename: 'bundle.js', clean: false},
    resolve: {extensions: ['.tsx', '.ts', '.js'], modules: [modules], alias: {
      'react': path.join(modules, 'react'), 'react-dom': path.join(modules, 'react-dom'),
      'next/link$': path.join(root, 'link.js'), 'next/navigation$': path.join(root, 'navigation.js'),
      '@/lib/articles$': path.join(root, 'api.js'), '@/lib/learning$': path.join(root, 'learning.js'),
      'actual-articles$': path.join(frontend, 'src/lib/articles.ts'),
      'test-subject$': path.join(directory, 'ArticleListView.tsx'), '@': path.join(frontend, 'src'),
    }},
    module: {rules: [{test: /\.tsx?$/, use: [{loader: path.join(root, 'typescript-loader.cjs'), options: {modules}}]}]},
    optimization: {minimize: false, concatenateModules: false, splitChunks: false, runtimeChunk: false},
    plugins: [new webpack.DefinePlugin({
      BUILD_REACT_VERSION: JSON.stringify(versions.react), BUILD_REACT_DOM_VERSION: JSON.stringify(versions.react_dom),
      'process.env.NEXT_PUBLIC_API_BASE_URL': JSON.stringify('http://localhost:18000'),
    })],
  });
  let stats;
  try {
    stats = await new Promise((resolve, reject) => compiler.run((error, value) => error ? reject(error) : resolve(value)));
  } finally {
    await new Promise((resolve, reject) => compiler.close(error => error ? reject(error) : resolve()));
  }
  if (stats.hasErrors()) throw new Error('component_compile');
  const resources = [...stats.compilation.modules].map(item => item.resource).filter(Boolean);
  for (const name of ['react', 'react-dom']) {
    const matches = resources.filter(file => file.includes(`/node_modules/${name}/`));
    if (!matches.length || matches.some(file => !file.startsWith(path.join(modules, name) + path.sep))) {
      throw new Error('react_instance');
    }
  }
  const assets = Object.keys(stats.compilation.assets);
  if (assets.length !== 1 || assets[0] !== 'bundle.js' || fs.statSync(path.join(directory, 'bundle.js')).size > 8 * 1024 * 1024) {
    throw new Error('component_bundle_budget');
  }
}
(async () => {
  for (const variant of ['current', 'without_invalidation', 'without_revision']) await build(variant);
  fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify(versions));
})().catch(() => { console.error('component_compile_failed'); process.exitCode = 1; });
"""


def build_component_bundles(root, frontend):
    from product_test_runtime import _run_owned, sanitized_environment

    if root.is_symlink() or any(root.iterdir()):
        raise ValueError("component_build_ownership")
    component = frontend / "src/components/ArticleListView.tsx"
    variants = component_variants(component.read_text())
    inputs = {
        "entry.js": COMPONENT_ENTRY, "api.js": COMPONENT_API, "build.cjs": COMPONENT_BUILD,
        "link.js": "import * as React from 'react'; export default function Link(props) { return React.createElement('a', props); }",
        "navigation.js": "export const usePathname = () => location.pathname; export const useSearchParams = () => new URLSearchParams(location.search);",
        "learning.js": "export const fetchLearningStates = async () => ({items: [], total: 0}); export const fetchBookmarks = fetchLearningStates;",
        "typescript-loader.cjs": """module.exports = function(source) {
          const ts = require(require('node:path').join(this.getOptions().modules, 'typescript'));
          return ts.transpileModule(source, {fileName: this.resourcePath, compilerOptions: {
            target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX,
          }}).outputText;
        };""",
    }
    for name, source in inputs.items():
        (root / name).write_text(source)
    for name, source in variants.items():
        (root / name).mkdir()
        (root / name / "ArticleListView.tsx").write_text(source)
    _run_owned(["node", str(root / "build.cjs"), str(root), str(frontend)], root, sanitized_environment(), timeout=120)
    if (any((root / name).read_text() != source for name, source in inputs.items())
            or any((root / name / "ArticleListView.tsx").read_text() != source for name, source in variants.items())):
        raise ValueError("component_source_drift")
    versions = json.loads((root / "manifest.json").read_text())
    if (not isinstance(versions, dict) or set(versions) != {"react", "react_dom", "typescript", "next"}
            or any(not isinstance(value, str) or not value or len(value) > 64 for value in versions.values())
            or versions["react"] != versions["react_dom"]):
        raise ValueError("component_versions")
    bindings = {name: hashlib.sha256((root / name / "bundle.js").read_bytes()).hexdigest() for name in variants}
    return {"versions": versions, "bundles": bindings,
            "subjects": {name: hashlib.sha256(source.encode()).hexdigest() for name, source in variants.items()}}


def component_check_names(case, error=None):
    names = list(COMPONENT_COMMON_CHECKS)
    if case == "batched_aba":
        names.insert(names.index("old_continuation_drained"), "same_batch_aba")
    if case == "accept_failure":
        names.insert(names.index("current_result_read"), "current_error_read")
    stop = {"stale_success_read": "stale_result_ignored", "stale_failure_read": "stale_result_ignored",
            "replacement_fetch_missing": "replacement_fetch"}.get(error)
    return set(names[:names.index(stop)] + ["cleanup"] if stop else names)


def component_contract_passes(result):
    if not isinstance(result, dict) or result.get("status") != "PASS" or result.get("errors") != []:
        return False
    if not all(result.get(key) is True for key in ("bindings_equal", "runtime_removed")):
        return False
    build = result.get("build")
    if not isinstance(build, dict) or not isinstance(build.get("versions"), dict):
        return False
    versions = build["versions"]
    if (set(versions) != {"react", "react_dom", "typescript", "next"}
            or any(not isinstance(value, str) or not value or len(value) > 64 for value in versions.values())
            or versions["react"] != versions["react_dom"]):
        return False
    rows = result.get("cases")
    if not isinstance(rows, list) or len(rows) != len(COMPONENT_RUNS):
        return False
    for row, (variant, case, error) in zip(rows, COMPONENT_RUNS):
        if not isinstance(row, dict) or row.get("variant") != variant or row.get("case") != case:
            return False
        receipt = row.get("result")
        if (not isinstance(receipt, dict) or receipt.get("status") != ("BLOCKED" if error else "PASS")
                or receipt.get("error") != error or receipt.get("react_version") != versions["react"]
                or receipt.get("react_dom_version") != versions["react_dom"]
                or not exact_checks(receipt.get("checks"), component_check_names(case, error))):
            return False
        if not clean_audit(row.get("audit_before_cleanup")) or not clean_audit(row.get("audit_after_cleanup")):
            return False
    return isinstance(result.get("browser_version"), str) and bool(result["browser_version"])


def component_result(payload, versions, case):
    errors = {None, "component_setup", "react_version", "initial_request", "draft_not_committed",
              "query_not_accepted", "aba_not_accepted", "window_not_qualified", "continuation_not_qualified",
              "stale_failure_read", "stale_success_read", "replacement_fetch_missing", "pending_rows_exposed",
              "current_error_not_read", "retry_request", "current_result_not_read", "current_rows", "current_range",
              "result_focus", "selection_focus", "component_execution", "component_cleanup", "component_timeout"}
    if (not isinstance(payload, dict) or set(payload) != {"status", "error", "checks", "stage", "react_version", "react_dom_version"}
            or not isinstance(payload["status"], str) or payload["status"] not in {"PASS", "BLOCKED"}
            or (payload["error"] is not None and not isinstance(payload["error"], str)) or payload["error"] not in errors
            or not isinstance(payload["stage"], str)
            or payload["stage"] not in {"setup", "draft", "acceptance_window", "replacement", "current_result"}
            or payload["react_version"] != versions["react"] or payload["react_dom_version"] != versions["react_dom"]
            or not isinstance(payload["checks"], dict) or not set(payload["checks"]) <= component_check_names(case)
            or any(value is not True for value in payload["checks"].values())):
        raise ValueError("component_receipt_invalid")
    return payload


def serve_component(page, suite, bundle, blocked):
    base = suite["FRONTEND_URL"]
    document_url, script_url = base + "/articles", base + "/__article_component_contract.js"
    document = ('<!doctype html><html lang="en"><head><meta charset="UTF-8">'
                '<title>Article component contract</title><link rel="icon" href="data:,"></head>'
                '<body><div id="root"></div><script src="/__article_component_contract.js"></script></body></html>')

    def serve(route):
        request = route.request
        is_document = request.url == document_url and request.resource_type == "document" and request.is_navigation_request()
        is_script = request.url == script_url and request.resource_type == "script" and not request.is_navigation_request()
        if request.method != "GET" or not (is_document or is_script):
            blocked.append("component_artifact_request_shape")
            route.abort()
            return
        route.fulfill(status=200, content_type="text/html; charset=utf-8" if is_document else "text/javascript",
                      body=document if is_document else bundle,
                      headers={"content-security-policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; img-src data:"})

    page.route(document_url, serve)
    page.route(script_url, serve)


def run_component_case(page, suite, bundle, blocked, case, versions):
    serve_component(page, suite, bundle, blocked)
    page.goto(suite["FRONTEND_URL"] + "/articles", wait_until="load")
    page.wait_for_function("typeof window.articleComponentContract?.run === 'function'", timeout=10_000)
    payload = page.evaluate("""async name => {
      let timer;
      try {
        return await Promise.race([window.articleComponentContract.run(name), new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error('component_timeout')), 30000);
        })]);
      } finally { clearTimeout(timer); }
    }""", case)
    return component_result(payload, versions, case)


def run_article_list_component_contract(suite):
    from playwright.sync_api import sync_playwright
    from product_test_runtime import require_port_free

    result = {"status": "BLOCKED", "errors": [], "cases": [], "bindings_equal": False, "runtime_removed": False}
    observations, root, before = [], None, None
    try:
        require_port_free(3000)
        require_port_free(suite["BACKEND_PORT"])
        before = source_bindings(suite)
        result["bindings"] = before
        with tempfile.TemporaryDirectory(prefix="scientific-spaces-article-component-") as temporary:
            root = Path(temporary)
            result["build"] = build_component_bundles(root, suite["FRONTEND_ROOT"])
            versions = result["build"]["versions"]
            with sync_playwright() as playwright:
                with closing(suite["LocalOnlyBrowser"](playwright.chromium.launch(headless=True))) as browser:
                    result["browser_version"] = browser.version
                    for variant, case, expected_error in COMPONENT_RUNS:
                        row = {"variant": variant, "case": case}
                        result["cases"].append(row)
                        ledgers = suite["NetworkGuardLog"](), suite["ConsoleErrorLog"](), []
                        observations.append((row, ledgers))
                        bundle = (root / variant / "bundle.js").read_bytes()
                        if hashlib.sha256(bundle).hexdigest() != result["build"]["bundles"][variant]:
                            raise ValueError("component_bundle_drift")
                        try:
                            with closing(browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")) as context:
                                try:
                                    suite["_install_network_guard"](context, ledgers[0])
                                    page = suite["_new_observed_page"](context, ledgers[1], ledgers[2], label=variant + "_" + case)
                                    page.set_default_timeout(10_000)
                                    page.set_default_navigation_timeout(10_000)
                                    row["result"] = run_component_case(page, suite, bundle, ledgers[0], case, versions)
                                    suite["_wait_for_page_requests_to_settle"](page, ledgers[1])
                                finally:
                                    row["audit_before_cleanup"] = audit(suite, *ledgers)
                        finally:
                            row["audit_after_cleanup"] = audit(suite, *ledgers)
                        receipt = row["result"]
                        if (receipt["status"] != ("BLOCKED" if expected_error else "PASS")
                                or receipt["error"] != expected_error
                                or not exact_checks(receipt["checks"], component_check_names(case, expected_error))
                                or not clean_audit(row["audit_before_cleanup"]) or not clean_audit(row["audit_after_cleanup"])):
                            raise ValueError("component_case_failed")
            for kind, filename in (("bundles", "bundle.js"), ("subjects", "ArticleListView.tsx")):
                for variant, digest in result["build"][kind].items():
                    if hashlib.sha256((root / variant / filename).read_bytes()).hexdigest() != digest:
                        raise ValueError("component_artifact_drift")
    except (Exception, KeyboardInterrupt) as exc:
        result["errors"].append("component_failed")
        result["failure_location"] = failure_location(exc)
    finally:
        result["runtime_removed"] = root is not None and not root.exists()
        for row, ledgers in observations:
            try:
                row["audit_after_cleanup"] = audit(suite, *ledgers)
                if not clean_audit(row["audit_after_cleanup"]):
                    row["failure_audit"] = failure_audit_kinds(suite, ledgers[1])
                    result["errors"].append("audit_failed")
            except Exception:
                result["errors"].append("audit_failed")
        try:
            result["bindings_equal"] = before is not None and source_bindings(suite) == before
        except Exception:
            result["errors"].append("binding_failed")
    result["status"] = "PASS"
    if not component_contract_passes(result):
        result["status"] = "BLOCKED"
    return result


def main(argv=None):
    result = {"status": "BLOCKED", "errors": ["invalid_arguments"]}
    previous = signal.getsignal(signal.SIGTERM)
    try:
        def terminate(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, terminate)
        with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
            if list(sys.argv[1:] if argv is None else argv):
                raise ValueError("invalid_arguments")
            from product_test_runtime import frontend_runtime, get_backend_port, process_environment

            if get_backend_port() != 18000:
                raise ValueError("isolated_port_required")
            suite = gate.runtime_module()
            with frontend_runtime(ROOT, backend_port=18000, frontend_mode="start") as configuration:
                with process_environment(configuration.environment):
                    suite = suite["configure_runtime"](configuration)
                    result = run_article_list_navigation_profile(suite)
                    if profile_passes(result):
                        contract = run_article_list_component_contract(suite)
                        result["component_contract"] = contract
                        if (not component_contract_passes(contract)
                                or contract.get("browser_version") != result.get("browser_version")):
                            result["status"] = "BLOCKED"
                            result["errors"].append("component_contract_failed")
            result["runtime_isolation"] = dict(configuration.evidence)
            if not all(configuration.evidence.get(key) is True for key in ("copy_verified", "bindings_stable", "cleanup_complete")):
                result["status"] = "BLOCKED"
                result["errors"].append("isolation_failed")
    except (Exception, KeyboardInterrupt):
        result["status"] = "BLOCKED"
        result.setdefault("errors", []).append("execution_failed")
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if profile_passes(result) and component_contract_passes(result.get("component_contract")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
