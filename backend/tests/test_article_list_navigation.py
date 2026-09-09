"""Offline contracts for the isolated Article List navigation profile."""

from contextlib import contextmanager
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def suite(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/e2e"))
    gate = runpy.run_path(str(ROOT / "scripts/e2e/check_graph_provenance_return.py"))
    return gate["runtime_module"]()["main"].__globals__


def articles(suite):
    return [suite["StoredArticle"](
        id=f"navigation-{number:02d}", title=f"Navigation {number:02d}",
        url=f"http://localhost:3000/articles/navigation-{number:02d}",
        content=f"## Navigation {number:02d}\n\nSynthetic navigation fixture.",
        metadata={"date": f"2025-01-{number:02d}", "references": [], "images": []},
    ) for number in range(1, 23)]


def test_explicit_fixture_reaches_all_derived_stores(suite, tmp_path, monkeypatch):
    records = articles(suite)
    install = Mock(wraps=suite["install_reference_store"])
    monkeypatch.setitem(suite, "install_reference_store", install)
    runtime = suite["prepare_runtime"](tmp_path, fixture_articles=records)
    assert json.loads(runtime["articles"].read_text()) == [item.to_dict() for item in records]
    graph = suite["GraphStore"](runtime["graph"]).load()
    assert {node.node_id for node in graph.nodes if node.node_type == "article"} == {
        f"article:{item.id}" for item in records}
    assert runtime["references"].is_dir()
    assert any(runtime["references"].rglob("*.json"))
    assert install.call_args.kwargs["article_ids"] == [item.id for item in records]
    assert install.call_args.kwargs["corpus_fingerprint"] == suite["compute_corpus_fingerprint"](records)


def test_ambiguous_fixture_is_rejected_before_allocation(suite, tmp_path):
    root = tmp_path / "not-created"
    with pytest.raises(ValueError, match="^ambiguous_fixture$"):
        suite["prepare_runtime"](root, fixture_articles=articles(suite), reader_inline_images=True)
    assert not root.exists()


@pytest.fixture
def profile(suite):
    return importlib.import_module("check_article_list_navigation")


def test_original_and_image_fixtures_keep_their_existing_content(suite, tmp_path):
    baseline = [item.to_dict() for item in suite["_load_fixture_articles"]()]
    for images in (False, True):
        runtime = suite["prepare_runtime"](tmp_path / str(images), reader_inline_images=images)
        expected = copy.deepcopy(baseline)
        if images:
            next(item for item in expected if item["id"] == suite["CRB_ARTICLE_ID"])["content"] += suite["READER_INLINE_IMAGE_MARKDOWN"]
        assert json.loads(runtime["articles"].read_text()) == expected
    assert [item.to_dict() for item in suite["_load_fixture_articles"]()] == baseline


def test_navigation_fixture_is_exact_and_contains_native_second_page(profile, suite):
    records = profile.pagination_articles(suite)
    assert len(records) == len({item.id for item in records}) == 22
    assert [item.id for item in records if "Alpha" in item.title] == [f"navigation-{i:02d}" for i in range(1, 22)]
    assert [item.id for item in records if "Beta" in item.title] == ["navigation-22"]
    assert all(item.metadata["references"] == [] for item in records)
    assert len(profile.CASE_IDS) == 10
    assert sum(len(profile.expected_checks(case)) for case in profile.CASE_IDS) == 36


@pytest.fixture
def runtime_harness(profile, suite, monkeypatch, tmp_path):
    """Real profile/guards/reset/cleanup; mock only owned resources and UI body."""
    def arrange(failure=None):
        active = {"size": None, "runtime": None, "last_errors": None}
        paths, events, calls, resets = [], [], [], []
        resources = set()
        bindings = {"count": 0}

        def source_bindings(_suite):
            bindings["count"] += 1
            return {"source": "changed" if failure == "binding" and bindings["count"] > 1 else "synthetic",
                    "build": "synthetic", "fixture": "synthetic", "navigation_profile": "synthetic"}

        @contextmanager
        def temporary_directory(*, prefix):
            size = 22 if prefix.endswith("22-") else 3
            try:
                with tempfile.TemporaryDirectory(prefix=prefix, dir=tmp_path) as temporary:
                    paths.append(Path(temporary))
                    yield temporary
            finally:
                events.append((size, "temp_teardown"))
                if size == 22 and failure == "temp_teardown":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")

        def prepare(root, *, fixture_articles=None):
            records = suite["_load_fixture_articles"]() if fixture_articles is None else fixture_articles
            size = len(records)
            events.append((size, "prepare"))
            runtime = {"root": root, "environment": {}, **{key: root / (key + ".json")
                       for key in ("articles", "graph", "learning", "tutor")}, "references": root / "references"}
            for key in ("graph", "learning", "tutor"):
                runtime[key].write_text("{}")
            payload = [item.to_dict() for item in records]
            if failure == "wrong_fixture" and size == 22:
                payload.pop()
            runtime["articles"].write_text(json.dumps(payload))
            runtime["references"].mkdir()
            (runtime["references"] / "records.json").write_text("[]")
            return runtime

        @contextmanager
        def servers(runtime, **kwargs):
            active["runtime"] = runtime
            active["size"] = 22 if "22-" in runtime["root"].name else 3
            size = active["size"]
            assert not resources
            resources.add("servers")
            events.append((size, "server_setup"))
            try:
                if size == 22 and failure == "server_setup":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")
                yield {}
            finally:
                resources.remove("servers")
                events.append((size, "server_teardown"))
                if size == 22 and failure == "server_teardown":
                    active["last_errors"].append("synthetic late navigation console")
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")

        class Context:
            pages = []

            def __init__(self):
                resources.add(self)

            def close(self):
                if self not in resources:
                    return
                resources.remove(self)
                events.append((active["size"], "context_teardown"))
                if active["size"] == 3 and failure == "first_late_audit":
                    active["last_errors"].append("synthetic first late console")
                if active["size"] == 3 and failure == "first_context":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")
                if active["size"] == 22 and failure == "context_teardown":
                    active["last_errors"].append("synthetic context console")
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")

        class Browser:
            def __init__(self):
                self.contexts = []
                self.version = "different" if active["size"] == 22 and failure == "browser_mismatch" else "synthetic"

            def new_context(self, **options):
                assert options["service_workers"] == "block"
                assert options["viewport"] in ({"width": 1440, "height": 1000}, {"width": 390, "height": 844})
                context = Context()
                self.contexts.append(context)
                return context

            def close(self):
                if self not in resources:
                    return
                resources.remove(self)
                for context in self.contexts:
                    context.close()
                events.append((active["size"], "browser_teardown"))
                if active["size"] == 3 and failure == "first_browser_audit":
                    active["last_errors"].append("synthetic first browser console")
                if active["size"] == 22 and failure in {"late_audit", "browser_teardown"}:
                    active["last_errors"].append("synthetic late navigation console")
                if active["size"] == 22 and failure == "browser_teardown":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")

        @contextmanager
        def driver():
            resources.add("driver")
            browsers = []

            def launch(**kwargs):
                events.append((active["size"], "launch"))
                if active["size"] == 22 and failure == "browser_setup":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")
                browser = Browser()
                resources.add(browser)
                browsers.append(browser)
                return browser

            try:
                yield SimpleNamespace(chromium=SimpleNamespace(launch=launch))
            finally:
                try:
                    for browser in browsers:
                        browser.close()
                finally:
                    resources.remove("driver")
                    events.append((active["size"], "driver_teardown"))

        real_reset = suite["_reset_mutable_runtime"]

        def reset(runtime):
            resets.append(runtime["root"])
            real_reset(runtime)

        def body(page, _suite, case_id, errors, expect, row, deadline):
            assert isinstance(errors, suite["ConsoleErrorLog"])
            assert deadline > profile.time.monotonic()
            active["last_errors"] = errors
            calls.append((case_id, errors))
            for key in ("learning", "tutor"):
                assert not active["runtime"][key].exists()
                active["runtime"][key].write_text("synthetic mutation")
            row["stage"] = "synthetic_body"
            if active["size"] == 3 and failure == "first_audit":
                errors.append("synthetic first console")
            if active["size"] == 22:
                if failure == "body":
                    raise RuntimeError("PRIVATE_NAV_SENTINEL")
                if failure == "interrupt":
                    raise KeyboardInterrupt
                if failure == "fixture_drift":
                    (active["runtime"]["references"] / "records.json").write_text("[{}]")
            checks = dict.fromkeys(profile.expected_checks(case_id), True)
            if active["size"] == 22:
                if failure in {"missing", "wrong_key"}:
                    checks.pop(next(iter(checks)))
                if failure in {"wrong_key", "extra"}:
                    checks["synthetic_extra"] = True
                if failure == "nontrue":
                    checks[next(iter(checks))] = 1
            return checks

        monkeypatch.setattr(profile, "source_bindings", source_bindings)
        monkeypatch.setattr(profile, "tempfile", SimpleNamespace(TemporaryDirectory=temporary_directory))
        monkeypatch.setattr(profile, "run_case", body)
        monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(sync_playwright=driver, expect=object()))
        monkeypatch.setitem(suite, "prepare_runtime", prepare)
        monkeypatch.setitem(suite, "product_servers", servers)
        monkeypatch.setitem(suite, "_reset_mutable_runtime", reset)
        monkeypatch.setitem(suite, "_install_network_guard", lambda *args: None)
        monkeypatch.setitem(suite, "_new_observed_page", lambda *args, **kwargs: SimpleNamespace(
            set_default_timeout=lambda value: None, set_default_navigation_timeout=lambda value: None))
        return SimpleNamespace(paths=paths, resources=resources, events=events, calls=calls, resets=resets,
                               run=lambda: profile.run_article_list_navigation_profile(suite))
    return arrange


def test_real_profile_orchestration_has_exact_coverage_and_two_separate_fixtures(runtime_harness, profile):
    harness = runtime_harness()
    result = harness.run()
    assert result["status"] == "PASS", result
    assert profile.profile_passes(result)
    assert [item["count"] for item in result["fixtures"]] == [3, 22]
    assert len(harness.calls) == len(harness.resets) == 10
    assert len({id(errors) for _, errors in harness.calls}) == 10
    assert harness.events.index((3, "temp_teardown")) < harness.events.index((22, "prepare"))
    assert all(not path.exists() for path in harness.paths) and not harness.resources


@pytest.mark.parametrize("failure", ["wrong_fixture", "server_setup", "browser_setup", "body", "interrupt",
                                    "missing", "extra", "wrong_key", "nontrue", "fixture_drift", "binding",
                                    "browser_mismatch", "late_audit", "context_teardown", "browser_teardown",
                                    "server_teardown", "temp_teardown"])
def test_profile_failures_are_blocked_with_cleaned_owned_resources(runtime_harness, profile, failure, capsys):
    harness = runtime_harness(failure)
    result = harness.run()
    assert result["status"] == "BLOCKED" and not profile.profile_passes(result), failure
    assert result["runtime_removed"] and all(not path.exists() for path in harness.paths)
    assert not harness.resources
    assert len(result["cases"]) >= 2
    assert all(row["status"] == "PASS" for row in result["cases"][:2])
    assert "PRIVATE_NAV_SENTINEL" not in json.dumps(result) + capsys.readouterr().out
    if failure in {"late_audit", "context_teardown", "browser_teardown", "server_teardown"}:
        assert result["cases"][-1]["audit_after_cleanup"]["console"] == 1


@pytest.mark.parametrize("failure", ["first_audit", "first_late_audit", "first_context"])
def test_first_case_failure_blocks_next_case_and_fixture(runtime_harness, profile, failure):
    harness = runtime_harness(failure)
    result = harness.run()
    assert result["status"] == "BLOCKED" and not profile.profile_passes(result)
    assert len(harness.calls) == len(harness.resets) == len(result["cases"]) == 1
    first = result["cases"][0]
    assert first["case"] == "desktop_original" and first["status"] == "BLOCKED"
    assert profile.exact_checks(first["checks"], profile.expected_checks(first["case"]))
    assert len(result["fixtures"]) == 1 and result["fixtures"][0]["stable"]
    assert not any(size == 22 for size, _ in harness.events)
    assert result["runtime_removed"] and result["bindings_equal"]
    assert not harness.resources and all(not path.exists() for path in harness.paths)
    assert (3, "server_teardown") in harness.events and (3, "temp_teardown") in harness.events
    assert first["audit_before_cleanup"]["console"] == (1 if failure == "first_audit" else 0)
    assert first["audit_after_cleanup"]["console"] == (0 if failure == "first_context" else 1)


def test_first_fixture_late_browser_audit_blocks_second_fixture(runtime_harness, profile):
    harness = runtime_harness("first_browser_audit")
    result = harness.run()
    assert result["status"] == "BLOCKED" and not profile.profile_passes(result)
    assert len(harness.calls) == len(result["cases"]) == 2
    assert len(result["fixtures"]) == 1 and result["fixtures"][0]["stable"]
    assert result["cases"][-1]["status"] == "BLOCKED"
    assert result["cases"][-1]["audit_after_cleanup"]["console"] == 1
    assert not any(size == 22 for size, _ in harness.events)
    assert result["runtime_removed"] and not harness.resources


@pytest.mark.parametrize("mutation", ["missing_case", "duplicate_case", "extra_case", "missing_check", "extra_check",
                                     "nontrue", "binding", "fixture", "cleanup", "error", "browser", "audit_before",
                                     "audit_after", "audit_missing"])
def test_profile_admission_rejects_partial_or_corrupted_results(runtime_harness, profile, mutation):
    result = runtime_harness().run()
    assert profile.profile_passes(result)
    if mutation == "missing_case":
        result["cases"].pop()
    elif mutation == "duplicate_case":
        result["cases"][-1] = result["cases"][0]
    elif mutation == "extra_case":
        result["cases"].append(result["cases"][0])
    elif mutation == "missing_check":
        result["cases"][0]["checks"].pop(next(iter(result["cases"][0]["checks"])))
    elif mutation == "extra_check":
        result["cases"][0]["checks"]["unrelated"] = True
    elif mutation == "nontrue":
        result["cases"][0]["checks"][next(iter(result["cases"][0]["checks"]))] = 1
    elif mutation in {"binding", "fixture", "cleanup"}:
        result[{"binding": "bindings_equal", "fixture": "fixture_stable", "cleanup": "runtime_removed"}[mutation]] = False
    elif mutation == "error":
        result["errors"].append("execution_failed")
    elif mutation == "browser":
        result["browser_version"] = ""
    elif mutation == "audit_missing":
        result["cases"][0]["audit_after_cleanup"].pop("page")
    else:
        result["cases"][0]["audit_before_cleanup" if mutation == "audit_before" else "audit_after_cleanup"]["page"] = 1
    assert not profile.profile_passes(result)


def test_held_article_retains_handler_until_release_and_falls_back_later_requests(profile):
    page = Mock()
    url = "http://localhost:18000/v1.1/articles?q=Alpha&page=1&page_size=20&sort=date_desc"
    response = Mock(status=200, url=url)
    route = Mock(request=SimpleNamespace(url=url, method="GET"))
    route.fetch.return_value = response
    held = profile.HeldArticle(page, url)
    held.intercept(route)
    held.wait_ready()
    page.unroute.assert_not_called()
    route.fetch.assert_called_once_with(max_redirects=0, timeout=5000)
    later = Mock(request=SimpleNamespace(url=url, method="GET"))
    held.intercept(later)
    later.fallback.assert_called_once_with()
    later.fetch.assert_not_called()
    later.abort.assert_not_called()
    assert held.route is route and held.response is response and held.count == 1
    held.release()
    held.verify_released()
    held.close()
    route.fulfill.assert_called_once_with(response=response)
    route.abort.assert_not_called()
    response.dispose.assert_called_once()
    page.unroute.assert_called_once_with(url, held.handler)


def test_held_failure_uses_original_request_bound_error_helper(profile):
    page = Mock()
    url = "http://localhost:18000/v1.1/articles?q=Alpha"
    response = Mock(status=200, url=url)
    route = Mock(request=SimpleNamespace(url=url, method="GET"))
    route.fetch.return_value = response
    helper = Mock()
    held = profile.HeldArticle(page, url)
    held.intercept(route)
    held.wait_ready()
    errors = object()
    held.release_error({"_fulfill_expected_http_error": helper}, errors, ("owned-expectation",))
    held.verify_released()
    held.close()
    assert helper.call_args.args == (route,)
    assert helper.call_args.kwargs["console_errors"] is errors
    assert helper.call_args.kwargs["expectation_ids"] == ("owned-expectation",)
    response.dispose.assert_called_once()


def test_later_fallback_failure_invalidates_capture_and_keeps_cleanup(profile):
    page = Mock()
    url = "http://localhost:18000/v1.1/articles?q=Alpha"
    response = Mock(status=200, url=url)
    route = Mock(request=SimpleNamespace(url=url, method="GET"))
    route.fetch.return_value = response
    held = profile.HeldArticle(page, url)
    held.intercept(route)
    held.wait_ready()
    later = Mock(request=SimpleNamespace(url=url, method="GET"))
    later.fallback.side_effect = RuntimeError("synthetic fallback failure")
    held.intercept(later)
    assert held.invalid and held.active == 0 and held.count == 1
    with pytest.raises(ValueError, match="detail_interception"):
        held.close()
    page.unroute.assert_called_once_with(url, held.handler)
    route.abort.assert_called_once_with()
    response.dispose.assert_called_once_with()


@pytest.mark.parametrize("capture_focus,newer_focus", [(0, True), (1, True), (0, False)])
def test_actual_feedback_back_body_orders_new_focus_before_release_and_fails_on_focus_theft(
    profile, monkeypatch, capture_focus, newer_focus,
):
    events = []
    page, search, feedback = Mock(), Mock(), Mock()
    page.get_by_test_id.return_value = feedback
    search.fill.side_effect = lambda text: events.append("typed")

    def evaluate(script):
        if script == "window.__articleNavigationFocus.count":
            return capture_focus
        events.append("observer_removed" if "delete window" in script else "observer_added")

    page.evaluate.side_effect = evaluate
    held = Mock()
    held.wait_ready.side_effect = lambda: events.append("captured")
    held.release.side_effect = lambda: events.append("released")
    held.close.side_effect = lambda: events.append("held_closed")
    monkeypatch.setattr(profile, "HeldArticle", Mock(return_value=held))
    released = lambda: "released" in events

    def expect(locator):
        assertion = Mock()

        def focused():
            if locator is search:
                events.append("newer_focus_checked" if released() else "user_focus_checked")
                assert not released() or newer_focus, "focus_stolen"
            elif locator is feedback:
                events.append("feedback_focused")

        assertion.to_be_focused.side_effect = focused
        return assertion

    journey = Mock(page=page, search=search, expect=expect)
    journey.responses = SimpleNamespace(responses=[object(), object()])
    journey.suite = {
        "FRONTEND_URL": "http://localhost:3000", "BROWSER_API_URL": "http://localhost:18000",
        "_focus_via_tab": Mock(), "_declare_expected_route_transition": Mock(return_value="owned-back"),
        "_complete_expected_route_transition": Mock(),
    }
    journey.history_length.return_value = 3
    journey.loaded.side_effect = lambda *args, **kwargs: events.append("loaded")
    if capture_focus or not newer_focus:
        with pytest.raises(AssertionError, match="external_navigation_focused_capture|focus_stolen"):
            profile.history_feedback_case(journey, ["navigation-21"])
        journey.mark.assert_not_called()
    else:
        profile.history_feedback_case(journey, ["navigation-21"])
        journey.mark.assert_called_once_with("history_feedback_focus")
    assert events.index("feedback_focused") < events.index("captured")
    assert events.index("captured") < events.index("typed") < events.index("user_focus_checked")
    assert events.index("user_focus_checked") < events.index("released") < events.index("loaded")
    assert events[-2:] == ["held_closed", "observer_removed"]
    page.go_back.assert_called_once_with(wait_until="domcontentloaded")
    journey.suite["_complete_expected_route_transition"].assert_called_once_with(page, "owned-back")
    journey.loaded.assert_called_once_with(
        ["navigation-21"], 21, "Alpha", "title_asc", 2, draft="Newer history draft", after=2)


def test_response_receipt_requires_a_new_phase_match_and_releases_handles(profile):
    page = Mock()
    suite = {"BROWSER_API_URL": "http://localhost:18000"}
    url = profile.article_url(suite, "Alpha")
    response = Mock(url=url, status=200, request=SimpleNamespace(method="GET"))
    response.finished.return_value = None
    response.json.return_value = {"page": 1, "sort": "date_desc", "items": [{"id": "navigation-21"}]}
    capture = profile.ArticleResponses(page, suite)
    capture.record(response)
    page.wait_for_timeout.side_effect = lambda milliseconds: capture.record(response)
    capture.receipt("Alpha", "date_desc", 1, ["navigation-21"], after=1)
    page.wait_for_timeout.assert_called_once_with(20)
    response.json.assert_called_once()
    response.finished.assert_not_called()
    capture.close()
    assert capture.responses == []
    page.remove_listener.assert_called_once_with("response", capture.handler)


def test_response_receipt_rejects_same_members_in_wrong_order(profile):
    page = Mock()
    suite = {"BROWSER_API_URL": "http://localhost:18000"}
    response = Mock(url=profile.article_url(suite, "Alpha", "title_asc"), status=200,
                    request=SimpleNamespace(method="GET"))
    response.finished.return_value = None
    response.json.return_value = {"page": 1, "sort": "title_asc", "items": [
        {"id": "navigation-02"}, {"id": "navigation-01"}]}
    capture = profile.ArticleResponses(page, suite)
    try:
        capture.record(response)
        with pytest.raises(ValueError, match="article_response_mismatch"):
            capture.receipt("Alpha", "title_asc", 1, ["navigation-01", "navigation-02"])
    finally:
        capture.close()


def test_rendered_rows_reject_same_members_in_wrong_order(profile):
    page, responses = Mock(), Mock()
    page.get_by_test_id.return_value.locator.return_value.evaluate_all.return_value = [
        "/articles/navigation-02", "/articles/navigation-01"]
    journey = profile.Journey(page, {"FRONTEND_URL": "http://localhost:3000"}, "desktop_controls",
                              [], Mock(), {}, 100, responses)
    with pytest.raises(AssertionError, match="visible_article_mismatch"):
        journey.loaded(["navigation-01", "navigation-02"], 2, "Alpha", "title_asc", settle=False)
    responses.receipt.assert_called_once_with("Alpha", "title_asc", 1, ["navigation-01", "navigation-02"], after=0)


@pytest.mark.parametrize("failure", ["missing", "wrong_ids", "wrong_page", "wrong_sort", "body_unavailable", "method", "budget"])
def test_response_receipts_fail_closed(profile, monkeypatch, failure):
    page = Mock()
    suite = {"BROWSER_API_URL": "http://localhost:18000"}
    response = Mock(url=profile.article_url(suite, "Alpha"), status=200,
                    request=SimpleNamespace(method="POST" if failure == "method" else "GET"))
    response.finished.return_value = None
    if failure == "body_unavailable":
        response.json.side_effect = ValueError("invalid_article_response")
    response.json.return_value = {
        "page": 2 if failure == "wrong_page" else 1,
        "sort": "title_asc" if failure == "wrong_sort" else "date_desc",
        "items": [{"id": "wrong" if failure == "wrong_ids" else "navigation-21"}],
    }
    capture = profile.ArticleResponses(page, suite)
    if failure != "missing":
        for _ in range(129 if failure == "budget" else 1):
            capture.record(response)
    clock = iter((0, 11))
    monkeypatch.setattr(profile, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    with pytest.raises(ValueError, match="missing_article_response|invalid_article_response|article_response_mismatch|response_capture_failed"):
        capture.receipt("Alpha", "date_desc", 1, ["navigation-21"])
    if failure == "budget":
        assert len(capture.responses) == 128
        with pytest.raises(ValueError, match="response_capture_failed"):
            capture.close()
    else:
        capture.close()
    assert capture.responses == []


@pytest.mark.parametrize("failure", [None, "body", "interrupt", "frontend_cleanup", "component_build",
                                     "component_body", "component_interrupt", "component_prefix",
                                     "component_browser_version", "component_late_audit", "component_context_cleanup"])
def test_dedicated_main_restores_environment_and_cleans_before_json(runtime_harness, profile, suite, monkeypatch, tmp_path, capsys, failure):
    component_failure = failure.removeprefix("component_") if failure and failure.startswith("component_") else None
    harness = runtime_harness(None if component_failure else failure)
    component = install_component_runtime(profile, suite, monkeypatch, tmp_path, component_failure)
    helper = importlib.import_module("product_test_runtime")
    monkeypatch.setenv(helper.PORT_ENV, "18000")
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_NAV_SENTINEL")
    previous = dict(os.environ)
    environment = {"PATH": os.defpath, "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
                   "PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "cached-browser"), "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    observed = []
    body = profile.run_case

    def inspect_body(*args):
        observed.append(dict(os.environ))
        return body(*args)

    @contextmanager
    def frontend_runtime(root, *, backend_port, frontend_mode):
        assert backend_port == 18000 and frontend_mode == "start"
        with tempfile.TemporaryDirectory(dir=tmp_path) as temporary:
            path = Path(temporary)
            config = helper.FrontendRuntime(path, backend_port, environment, {
                "copy_verified": True, "bindings_stable": True, "cleanup_complete": False})
            try:
                yield config
            finally:
                config.evidence["cleanup_complete"] = True
        if failure == "frontend_cleanup":
            raise RuntimeError("PRIVATE_NAV_SENTINEL")

    monkeypatch.setattr(profile, "run_case", inspect_body)
    monkeypatch.setattr(profile.gate, "runtime_module", lambda: suite)
    monkeypatch.setattr(helper, "frontend_runtime", frontend_runtime)
    code = profile.main([])
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert not output.err and "PRIVATE_NAV_SENTINEL" not in output.out
    assert dict(os.environ) == previous
    assert observed and all(item == environment for item in observed)
    assert not harness.resources and all(not path.exists() for path in harness.paths)
    assert not component.resources and all(not path.exists() for path in component.paths)
    assert code == (0 if failure is None else 2)
    assert result["status"] == ("PASS" if failure is None else "BLOCKED")
    if component_failure:
        assert len(result["cases"]) == 10
        assert result["component_contract"]["status"] == ("PASS" if component_failure == "browser_version" else "BLOCKED")


def test_dedicated_cli_never_enters_runtime_on_default_user_port(profile, monkeypatch, capsys):
    helper = importlib.import_module("product_test_runtime")
    monkeypatch.delenv(helper.PORT_ENV, raising=False)
    runtime = Mock(side_effect=AssertionError("must not build or touch port 8000"))
    monkeypatch.setattr(helper, "frontend_runtime", runtime)
    assert profile.main([]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"
    runtime.assert_not_called()


def test_failure_location_does_not_export_exception_text_or_external_frames(profile):
    try:
        raise RuntimeError("PRIVATE_NAV_SENTINEL https://private.invalid/body")
    except RuntimeError as error:
        result = profile.failure_location(error)
    assert result == {"category": "RuntimeError", "frames": []}
    assert "PRIVATE_NAV_SENTINEL" not in json.dumps(result)


def test_failure_location_retains_only_bounded_trusted_lines(profile):
    try:
        profile.expected_checks("unknown_case")
    except ValueError as error:
        result = profile.failure_location(error)
    assert result["category"] == "ValueError"
    assert 0 < len(result["frames"]) <= 8
    assert all(set(frame) == {"file", "line"} for frame in result["frames"])
    assert result["frames"][-1]["file"] == "check_article_list_navigation.py"
    assert type(result["frames"][-1]["line"]) is int


def test_journey_retains_completed_checks_before_later_failure(profile):
    row = {"checks": {}}
    journey = profile.Journey(Mock(), {}, "desktop_controls", [], Mock(), row, 100, Mock())
    journey.mark("draft_sort")
    assert row["checks"] == {"desktop_controls_draft_sort": True}


def test_failure_audit_kinds_are_bounded_and_never_export_payload(profile):
    failures = [{"kind": "invalid_route_transition_expectation", "payload": "PRIVATE_NAV_SENTINEL"},
                {"kind": "PRIVATE_NAV_SENTINEL"}] + ["PRIVATE_NAV_SENTINEL"] * 9
    suite = {"_unexpected_console_errors": lambda _errors: failures}
    result = profile.failure_audit_kinds(suite, [])
    assert result == {"kinds": ["invalid_route_transition_expectation"] + ["other"] * 7, "omitted": 3}
    assert "PRIVATE_NAV_SENTINEL" not in json.dumps(result)


def test_component_mutants_change_only_the_two_identified_lines(profile):
    source = (ROOT / "frontend/src/components/ArticleListView.tsx").read_text()
    variants = profile.component_variants(source)
    assert set(variants) == {"current", "without_invalidation", "without_revision"}
    assert variants["current"] == source
    assert variants["without_invalidation"] == source.replace("    articleRequestId.current += 1;\n", "", 1)
    assert variants["without_revision"] == source.replace("    listRevisionRef.current += 1;\n", "", 1)


@pytest.mark.parametrize("source", ["", "    articleRequestId.current += 1;\n" * 2])
def test_component_mutants_reject_drift_instead_of_mutating_an_ambiguous_target(profile, source):
    with pytest.raises(ValueError, match="component_mutation_binding"):
        profile.component_variants(source)


COMPONENT_RUNS = (
    ("current", "accept_success", None),
    ("current", "accept_failure", None),
    ("current", "batched_aba", None),
    ("without_invalidation", "accept_success", "stale_success_read"),
    ("without_invalidation", "accept_failure", "stale_failure_read"),
    ("without_revision", "batched_aba", "replacement_fetch_missing"),
)
COMPONENT_VERSIONS = {"react": "19.0.0", "react_dom": "19.0.0", "typescript": "5.7.3", "next": "15.5.24"}
COMPONENT_SOURCE = "function accept() {\n    articleRequestId.current += 1;\n    listRevisionRef.current += 1;\n}\n"


def component_receipt(case, error=None):
    names = ["setup_single_request", "draft_committed", "accepted_before_effect"]
    if case == "batched_aba":
        names.append("same_batch_aba")
    names.append("old_continuation_drained")
    if error not in {"stale_success_read", "stale_failure_read"}:
        names.append("stale_result_ignored")
        if error != "replacement_fetch_missing":
            names.append("replacement_fetch")
            if case == "accept_failure":
                names.append("current_error_read")
            names.extend(("current_result_read", "final_rows", "selection_and_focus"))
    names.append("cleanup")
    return {"status": "BLOCKED" if error else "PASS", "error": error, "checks": dict.fromkeys(names, True),
            "stage": "acceptance_window" if error and error.startswith("stale_") else "replacement" if error else "current_result",
            "react_version": "19.0.0", "react_dom_version": "19.0.0"}


@pytest.mark.parametrize("anchor", ["articleRequestId", "listRevisionRef"])
@pytest.mark.parametrize("change", ["missing", "duplicate", "indent"])
def test_component_variant_anchor_failures_are_exact(profile, anchor, change):
    line = f"    {anchor}.current += 1;\n"
    replacement = "" if change == "missing" else line * 2 if change == "duplicate" else "  " + line
    with pytest.raises(ValueError, match="^component_mutation_binding$"):
        profile.component_variants(COMPONENT_SOURCE.replace(line, replacement))


def test_component_scope_is_six_cases_and_mutation_does_not_remove_cleanup_invalidation(profile):
    assert profile.COMPONENT_RUNS == COMPONENT_RUNS
    source = COMPONENT_SOURCE + "function cleanup() {\n      articleRequestId.current += 1;\n}\n"
    variants = profile.component_variants(source)
    assert variants["current"] == source
    assert all("      articleRequestId.current += 1;" in value for value in variants.values())
    for _, case, error in COMPONENT_RUNS:
        assert profile.component_check_names(case, error) == set(component_receipt(case, error)["checks"])


@pytest.mark.parametrize("failure", [None, "occupied", "symlink", "startup", "timeout", "bad_versions", "subject_drift", "input_drift"])
def test_component_compiler_owns_only_temporary_copies_and_uses_existing_runner(profile, monkeypatch, tmp_path, failure):
    helper = importlib.import_module("product_test_runtime")
    frontend = tmp_path / "frontend"
    source = frontend / "src/components/ArticleListView.tsx"
    source.parent.mkdir(parents=True)
    source.write_text(COMPONENT_SOURCE)
    shared_build = frontend / ".next/BUILD_ID"
    shared_build.parent.mkdir()
    shared_build.write_text("shared-build-sentinel")
    node_modules = frontend / "node_modules"
    node_modules.mkdir()
    (node_modules / "locked-dependency").write_text("locked-dependency-sentinel")
    before = {path.relative_to(frontend): path.read_bytes() for path in frontend.rglob("*") if path.is_file()}
    root = tmp_path / "owned-component"
    root.mkdir()
    if failure == "occupied":
        (root / "existing").write_text("owned-existing")
    if failure == "symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(root, target_is_directory=True)
        root = alias
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_COMPONENT_SENTINEL")
    calls = []

    def run(command, cwd, environment, *, timeout):
        calls.append(command)
        assert command == ["node", str(root / "build.cjs"), str(root), str(frontend)]
        assert cwd == root and timeout == 120
        assert "OPENAI_API_KEY" not in environment and "NODE_OPTIONS" not in environment
        assert environment["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] == "1"
        assert (root / "current/ArticleListView.tsx").read_bytes() == source.read_bytes()
        expected = profile.component_variants(COMPONENT_SOURCE)
        for name, contents in expected.items():
            assert (root / name / "ArticleListView.tsx").read_text() == contents
        assert (root / "build.cjs").read_text() == profile.COMPONENT_BUILD
        assert (root / "entry.js").read_text() == profile.COMPONENT_ENTRY
        if failure == "startup":
            raise OSError("PRIVATE_COMPONENT_SENTINEL")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, timeout, output="PRIVATE_COMPONENT_SENTINEL")
        versions = {**COMPONENT_VERSIONS, "react_dom": "18.0.0"} if failure == "bad_versions" else COMPONENT_VERSIONS
        (root / "manifest.json").write_text(json.dumps(versions))
        for name in expected:
            (root / name / "bundle.js").write_bytes((name + "-synthetic-bundle").encode())
        if failure in {"subject_drift", "input_drift"}:
            (root / ("current/ArticleListView.tsx" if failure == "subject_drift" else "entry.js")).write_text("changed-copy")

    monkeypatch.setattr(helper, "_run_owned", run)
    if failure:
        exception = OSError if failure == "startup" else subprocess.TimeoutExpired if failure == "timeout" else ValueError
        with pytest.raises(exception):
            profile.build_component_bundles(root, frontend)
    else:
        result = profile.build_component_bundles(root, frontend)
        assert result["versions"] == COMPONENT_VERSIONS
        assert result["subjects"] == {name: hashlib.sha256(value.encode()).hexdigest()
                                      for name, value in profile.component_variants(COMPONENT_SOURCE).items()}
        assert result["bundles"] == {name: hashlib.sha256((root / name / "bundle.js").read_bytes()).hexdigest()
                                     for name in result["subjects"]}
    assert len(calls) == (0 if failure in {"occupied", "symlink"} else 1)
    assert before == {path.relative_to(frontend): path.read_bytes() for path in frontend.rglob("*") if path.is_file()}


@pytest.mark.parametrize("failure", [None, "run", "stats", "close", "foreign_react", "foreign_react_dom", "assets", "budget"])
def test_actual_compiler_program_uses_one_installed_react_and_closes_on_failures(profile, failure):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable for synthetic compiler contract")
    # Execute the actual wrapper, not webpack: all compiler and filesystem APIs
    # below are in-memory doubles, with no project build or dependency loading.
    script = r"""
const vm = require('node:vm'), path = require('node:path');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const root = '/owned/component', frontend = '/owned/frontend', modules = frontend + '/node_modules';
const report = {configs: [], runs: 0, closes: 0, errors: [], manifest: null};
const versions = {react: '19.0.0', 'react-dom': '19.0.0', typescript: '5.7.3', next: '15.5.24'};
const fs = {
  realpathSync(value) { if (value !== modules) throw Error('unexpected_path'); return modules; },
  statSync() { return {size: input.failure === 'budget' ? 8 * 1024 * 1024 + 1 : 10}; },
  writeFileSync(file, text) { if (file !== root + '/manifest.json') throw Error('outside_output'); report.manifest = JSON.parse(text); },
};
function webpack(config) {
  report.configs.push(config);
  const resource = name => (input.failure === 'foreign_' + name.replace('-', '_') ? '/other/node_modules' : modules)
    + '/' + name + '/index.js';
  return {
    run(callback) {
      report.runs++;
      callback(input.failure === 'run' ? Error('PRIVATE_COMPONENT_SENTINEL') : null, {
        hasErrors: () => input.failure === 'stats',
        compilation: {modules: ['react', 'react-dom'].map(name => ({resource: resource(name)})),
          assets: input.failure === 'assets' ? {'bundle.js': {}, 'unexpected.js': {}} : {'bundle.js': {}}},
      });
    },
    close(callback) { report.closes++; callback(input.failure === 'close' ? Error('PRIVATE_COMPONENT_SENTINEL') : null); },
  };
}
webpack.DefinePlugin = class { constructor(definitions) { this.definitions = definitions; } };
const required = [];
const context = {
  process: {argv: ['node', root + '/build.cjs', root, frontend], env: {}, exitCode: 0},
  console: {error: value => report.errors.push(value)},
  require(name) {
    required.push(name);
    if (name === 'node:fs') return fs;
    if (name === 'node:path') return path;
    if (name === modules + '/next/dist/compiled/webpack/webpack.js') return {init() {}, webpack};
    const dependency = Object.keys(versions).find(key => name === modules + '/' + key + '/package.json');
    if (dependency) return {version: versions[dependency]};
    throw Error('unexpected_require');
  },
};
vm.runInNewContext(input.program, context, {timeout: 1000});
(async () => {
  for (let i = 0; i < 25 && !report.manifest && !report.errors.length; i++) await new Promise(setImmediate);
  report.exitCode = context.process.exitCode; report.required = required;
  process.stdout.write(JSON.stringify(report));
})();
"""
    completed = subprocess.run([node, "-e", script], input=json.dumps({"program": profile.COMPONENT_BUILD, "failure": failure}),
                               text=True, capture_output=True, timeout=10, check=True)
    assert not completed.stderr and "PRIVATE_COMPONENT_SENTINEL" not in completed.stdout
    result = json.loads(completed.stdout)
    assert result["runs"] == result["closes"] == (3 if failure is None else 1)
    assert result["errors"] == ([] if failure is None else ["component_compile_failed"])
    assert result["exitCode"] == (0 if failure is None else 1)
    assert bool(result["manifest"]) == (failure is None)
    for config in result["configs"]:
        assert config["mode"] == "development" and config["target"] == "web"
        assert config["cache"] is False and config["devtool"] is False
        assert config["output"]["path"].startswith("/owned/component/")
        assert config["output"]["filename"] == "bundle.js"
        assert config["resolve"]["modules"] == ["/owned/frontend/node_modules"]
        assert config["resolve"]["alias"]["react"] == "/owned/frontend/node_modules/react"
        assert config["resolve"]["alias"]["react-dom"] == "/owned/frontend/node_modules/react-dom"
        assert config["plugins"][0]["definitions"]["process.env.NEXT_PUBLIC_API_BASE_URL"] == '"http://localhost:18000"'


@pytest.mark.parametrize("variant,case,error", COMPONENT_RUNS)
def test_component_receipt_filter_preserves_only_expected_scalar_fields(profile, variant, case, error):
    payload = component_receipt(case, error)
    assert profile.component_result(payload, COMPONENT_VERSIONS, case) == payload


@pytest.mark.parametrize("field,value", [
    ("payload", None), ("payload", []), ("payload", "PRIVATE_COMPONENT_SENTINEL"),
    ("extra", "PRIVATE_COMPONENT_SENTINEL"), ("missing", None),
    ("status", "PRIVATE_COMPONENT_SENTINEL"), ("status", []), ("error", []), ("stage", {}),
    ("error", "PRIVATE_COMPONENT_SENTINEL"), ("stage", "PRIVATE_COMPONENT_SENTINEL"),
    ("react_version", "PRIVATE_COMPONENT_SENTINEL"), ("react_dom_version", "18.0.0"),
    ("checks", []), ("checks", {"PRIVATE_COMPONENT_SENTINEL": True}),
    ("checks", {"setup_single_request": 1}), ("checks", {"setup_single_request": False}),
])
def test_component_receipt_filter_rejects_invalid_shapes_with_fixed_error(profile, field, value, capsys):
    payload = component_receipt("accept_success")
    if field == "payload":
        payload = value
    elif field == "missing":
        del payload["stage"]
    else:
        payload[field] = value
    with pytest.raises(ValueError, match="^component_receipt_invalid$"):
        profile.component_result(payload, COMPONENT_VERSIONS, "accept_success")
    output = capsys.readouterr()
    assert not output.out and not output.err


def valid_component_contract():
    return {"status": "PASS", "errors": [], "bindings_equal": True, "runtime_removed": True,
            "browser_version": "synthetic-browser", "build": {
                "versions": dict(COMPONENT_VERSIONS),
                "subjects": dict.fromkeys(("current", "without_invalidation", "without_revision"), "a" * 64),
                "bundles": dict.fromkeys(("current", "without_invalidation", "without_revision"), "b" * 64)},
            "cases": [{"variant": variant, "case": case, "result": component_receipt(case, error),
                       "audit_before_cleanup": dict.fromkeys(("external", "console", "page", "unexpected_pages"), 0),
                       "audit_after_cleanup": dict.fromkeys(("external", "console", "page", "unexpected_pages"), 0)}
                      for variant, case, error in COMPONENT_RUNS]}


@pytest.mark.parametrize("failure", [
    "status", "errors", "bindings_equal", "runtime_removed", "browser_version", "missing_case", "extra_case",
    "reorder", "duplicate_case", "variant", "case", "current_blocked", "mutant_pass", "mutant_error",
    "missing_prefix", "extra_prefix", "missing_cleanup", "nonbool", "before_audit", "after_audit",
    "audit_shape", "bool_audit", "react_mismatch", "receipt_version", "versions_missing", "empty_version",
])
def test_component_qualifier_rejects_missing_or_contradictory_evidence(profile, failure):
    result = valid_component_contract()
    assert profile.component_contract_passes(result)
    rows = result["cases"]
    if failure in {"status", "errors", "bindings_equal", "runtime_removed", "browser_version"}:
        result[failure] = {"status": "BLOCKED", "errors": ["component_failed"], "bindings_equal": False,
                           "runtime_removed": False, "browser_version": ""}[failure]
    elif failure == "missing_case":
        rows.pop()
    elif failure == "extra_case":
        rows.append(copy.deepcopy(rows[0]))
    elif failure == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    elif failure == "duplicate_case":
        rows[1] = copy.deepcopy(rows[0])
    elif failure in {"variant", "case"}:
        rows[0][failure] = "unknown"
    elif failure == "current_blocked":
        rows[0]["result"]["status"] = "BLOCKED"
    elif failure == "mutant_pass":
        rows[3]["result"]["status"] = "PASS"
    elif failure == "mutant_error":
        rows[3]["result"]["error"] = "component_execution"
    elif failure in {"missing_prefix", "missing_cleanup"}:
        rows[3]["result"]["checks"].pop("cleanup" if failure == "missing_cleanup" else "old_continuation_drained")
    elif failure == "extra_prefix":
        rows[3]["result"]["checks"]["stale_result_ignored"] = True
    elif failure == "nonbool":
        rows[0]["result"]["checks"]["cleanup"] = 1
    elif failure in {"before_audit", "after_audit", "bool_audit"}:
        key = "audit_before_cleanup" if failure == "before_audit" else "audit_after_cleanup"
        rows[0][key]["console"] = False if failure == "bool_audit" else 1
    elif failure == "audit_shape":
        rows[0]["audit_after_cleanup"].pop("page")
    elif failure == "react_mismatch":
        result["build"]["versions"]["react_dom"] = "18.0.0"
    elif failure == "receipt_version":
        rows[0]["result"]["react_version"] = "18.0.0"
    elif failure == "versions_missing":
        result["build"]["versions"].pop("typescript")
    elif failure == "empty_version":
        result["build"]["versions"]["next"] = ""
    assert not profile.component_contract_passes(result)


def install_component_runtime(profile, suite, monkeypatch, tmp_path, failure=None, observe=None):
    """Keep real component orchestration/qualifiers; replace resource and UI boundaries."""
    helper = importlib.import_module("product_test_runtime")
    previous_driver = sys.modules.get("playwright.sync_api")
    previous_bindings = profile.source_bindings
    previous_temporary = profile.tempfile.TemporaryDirectory
    previous_page = suite["_new_observed_page"]
    previous_guard = suite["_install_network_guard"]
    previous_settle = suite["_wait_for_page_requests_to_settle"]
    active = {"component": False, "bindings": 0, "errors": None, "blocked": None, "page_errors": None}
    events, paths, calls, resources, browsers = [], [], [], set(), []

    def event(name):
        events.append(name)
        if observe:
            observe("component_" + name)

    def require_port_free(port):
        active["component"] = True
        event("port")
        assert port in (3000, suite["BACKEND_PORT"])
        if failure == "port":
            raise ValueError("PRIVATE_COMPONENT_SENTINEL")

    def bindings(module):
        if not active["component"]:
            return previous_bindings(module)
        active["bindings"] += 1
        return {"source": "changed" if failure == "source_drift" and active["bindings"] > 1 else "synthetic-component",
                "build": "synthetic-production"}

    @contextmanager
    def temporary(*, prefix):
        if "article-component" not in prefix:
            with previous_temporary(prefix=prefix) as directory:
                yield directory
            return
        try:
            with tempfile.TemporaryDirectory(prefix=prefix, dir=tmp_path) as directory:
                paths.append(Path(directory))
                yield directory
        finally:
            event("temp_cleanup")
            if failure == "temp_cleanup":
                raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")

    def build(root, frontend):
        event("build")
        assert root == paths[-1] and root.is_dir() and not any(root.iterdir())
        if failure == "build":
            raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")
        result = copy.deepcopy(valid_component_contract()["build"])
        for name in result["bundles"]:
            (root / name).mkdir()
            (root / name / "ArticleListView.tsx").write_text(COMPONENT_SOURCE)
            result["subjects"][name] = hashlib.sha256(COMPONENT_SOURCE.encode()).hexdigest()
            bundle = (name + "-synthetic-bundle").encode()
            (root / name / "bundle.js").write_bytes(bundle)
            result["bundles"][name] = hashlib.sha256(bundle).hexdigest()
        if failure == "bundle_drift":
            (root / "current/bundle.js").write_text("changed-owned-bundle")
        return result

    class Context:
        pages = []
        is_component_resource = True

        def __init__(self):
            resources.add(self)

        def close(self):
            if self not in resources:
                return
            resources.remove(self)
            event("context_cleanup")
            if failure in {"context_audit", "context_cleanup"}:
                active["errors"].append("synthetic component context console")
            if failure == "context_cleanup":
                raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")

    class Browser:
        version = "different-component-browser" if failure == "browser_version" else "synthetic"

        def __init__(self):
            self.contexts = []
            resources.add(self)

        def new_context(self, **options):
            assert options["service_workers"] == "block" and options["viewport"] == {"width": 1440, "height": 1000}
            if failure == "context_setup":
                raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")
            context = Context()
            self.contexts.append(context)
            return context

        def close(self):
            if self not in resources:
                return
            resources.remove(self)
            try:
                for context in self.contexts:
                    context.close()
            finally:
                event("browser_cleanup")
            if failure in {"late_audit", "browser_cleanup"}:
                active["errors"].append("synthetic component late console")
            if failure == "browser_cleanup":
                raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")

    @contextmanager
    def driver():
        if not active["component"]:
            with previous_driver.sync_playwright() as value:
                yield value
            return
        event("driver")
        resources.add("driver")

        def launch(**options):
            event("launch")
            assert options == {"headless": True}
            if failure == "launch":
                raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")
            browser = Browser()
            browsers.append(browser)
            return browser

        try:
            yield SimpleNamespace(chromium=SimpleNamespace(launch=launch))
        finally:
            try:
                for browser in browsers:
                    browser.close()
            finally:
                resources.remove("driver")
                event("driver_cleanup")
                if failure == "driver_cleanup":
                    raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")

    class Page:
        set_default_timeout = staticmethod(lambda value: None)
        set_default_navigation_timeout = staticmethod(lambda value: None)

    def new_page(context, errors, page_errors, **kwargs):
        if not getattr(context, "is_component_resource", False):
            return previous_page(context, errors, page_errors, **kwargs)
        active.update(errors=errors, page_errors=page_errors)
        return Page()

    def guard(context, blocked):
        if getattr(context, "is_component_resource", False):
            active["blocked"] = blocked
        else:
            previous_guard(context, blocked)

    def settle(page, errors):
        if isinstance(page, Page):
            event("settle")
        else:
            previous_settle(page, errors)

    def body(page, module, bundle, blocked, case, versions):
        index = len(calls)
        variant, expected_case, error = COMPONENT_RUNS[index]
        assert case == expected_case and bundle == (variant + "-synthetic-bundle").encode()
        calls.append((variant, case, active["errors"]))
        event("body")
        if failure == "body":
            raise RuntimeError("PRIVATE_COMPONENT_SENTINEL")
        if failure == "interrupt":
            raise KeyboardInterrupt
        receipt = component_receipt(case, error)
        if failure == "prefix":
            receipt["checks"].pop("old_continuation_drained")
        if failure == "status":
            receipt["status"] = "BLOCKED"
        if failure == "wrong_receipt_version":
            receipt["react_version"] = "18.0.0"
        if failure == "audit":
            active["errors"].append("synthetic component console")
        if failure == "external":
            blocked.append("synthetic_component_external")
        if failure == "page_error":
            active["page_errors"].append("synthetic component page error")
        if failure == "final_bundle_drift" and index == 5:
            (paths[-1] / "current/bundle.js").write_text("changed-after-final-use")
        if failure == "final_subject_drift" and index == 5:
            (paths[-1] / "current/ArticleListView.tsx").write_text("changed-after-final-use")
        return profile.component_result(receipt, versions, case)

    monkeypatch.setattr(helper, "require_port_free", require_port_free)
    monkeypatch.setattr(profile, "source_bindings", bindings)
    monkeypatch.setattr(profile, "tempfile", SimpleNamespace(TemporaryDirectory=temporary))
    monkeypatch.setattr(profile, "build_component_bundles", build)
    monkeypatch.setattr(profile, "run_component_case", body)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(
        sync_playwright=driver, expect=getattr(previous_driver, "expect", Mock())))
    monkeypatch.setitem(suite, "_new_observed_page", new_page)
    monkeypatch.setitem(suite, "_install_network_guard", guard)
    monkeypatch.setitem(suite, "_wait_for_page_requests_to_settle", settle)
    return SimpleNamespace(events=events, calls=calls, paths=paths, resources=resources,
                           run=lambda: profile.run_article_list_component_contract(suite))


def test_component_real_orchestration_qualifies_all_six_with_fresh_contexts(profile, suite, monkeypatch, tmp_path):
    harness = install_component_runtime(profile, suite, monkeypatch, tmp_path)
    result = harness.run()
    assert profile.component_contract_passes(result), result
    assert [(variant, case) for variant, case, _ in harness.calls] == [(variant, case) for variant, case, _ in COMPONENT_RUNS]
    assert len({id(errors) for _, _, errors in harness.calls}) == 6
    assert harness.events.count("context_cleanup") == harness.events.count("settle") == 6
    assert harness.events[-3:] == ["browser_cleanup", "driver_cleanup", "temp_cleanup"]
    assert not harness.resources and all(not path.exists() for path in harness.paths)


@pytest.mark.parametrize("failure", [
    "port", "build", "launch", "context_setup", "body", "interrupt", "prefix", "status", "wrong_receipt_version",
    "audit", "external", "page_error", "context_audit", "context_cleanup", "late_audit", "browser_cleanup",
    "driver_cleanup", "temp_cleanup", "source_drift", "bundle_drift", "final_bundle_drift", "final_subject_drift",
])
def test_component_real_orchestration_failure_stops_and_cleans(profile, suite, monkeypatch, tmp_path, failure, capsys):
    harness = install_component_runtime(profile, suite, monkeypatch, tmp_path, failure)
    result = harness.run()
    assert not profile.component_contract_passes(result) and result["status"] == "BLOCKED", failure
    assert not harness.resources and all(not path.exists() for path in harness.paths)
    if failure != "port":
        assert result["runtime_removed"] and harness.events[-1] == "temp_cleanup"
    if failure in {"port", "build", "launch", "context_setup", "bundle_drift"}:
        assert not harness.calls
    elif failure not in {"late_audit", "browser_cleanup", "driver_cleanup", "temp_cleanup", "source_drift",
                         "final_bundle_drift", "final_subject_drift"}:
        assert len(harness.calls) == 1 and len(result["cases"]) == 1
    if failure == "late_audit":
        assert result["cases"][-1]["audit_before_cleanup"]["console"] == 0
        assert result["cases"][-1]["audit_after_cleanup"]["console"] == 1
    assert "PRIVATE_COMPONENT_SENTINEL" not in json.dumps(result)
    output = capsys.readouterr()
    assert not output.out and not output.err


@pytest.mark.parametrize("artifact,method,resource,navigation,allowed", [
    ("document", "GET", "document", True, True), ("script", "GET", "script", False, True),
    ("document", "POST", "document", True, False), ("script", "POST", "script", False, False),
    ("document", "GET", "fetch", False, False), ("script", "GET", "fetch", False, False),
    ("document", "GET", "document", False, False), ("script", "GET", "script", True, False),
    ("unowned", "GET", "script", False, False),
])
def test_component_artifacts_require_exact_owned_request_shape(profile, artifact, method, resource, navigation, allowed):
    page, blocked = Mock(), []
    base = "http://localhost:3000"
    profile.serve_component(page, {"FRONTEND_URL": base}, b"owned-synthetic-bundle", blocked)
    assert [call.args[0] for call in page.route.call_args_list] == [base + "/articles", base + "/__article_component_contract.js"]
    handler = page.route.call_args_list[0].args[1]
    assert page.route.call_args_list[1].args[1] is handler
    request = Mock(method=method, resource_type=resource, url={
        "document": base + "/articles", "script": base + "/__article_component_contract.js",
        "unowned": base + "/unowned.js"}[artifact])
    request.is_navigation_request.return_value = navigation
    route = Mock(request=request)
    handler(route)
    if allowed:
        route.abort.assert_not_called()
        assert not blocked
        assert route.fulfill.call_args.kwargs["status"] == 200
        assert "default-src 'none'" in route.fulfill.call_args.kwargs["headers"]["content-security-policy"]
        if artifact == "script":
            assert route.fulfill.call_args.kwargs["body"] == b"owned-synthetic-bundle"
    else:
        route.fulfill.assert_not_called()
        route.abort.assert_called_once()
        assert blocked == ["component_artifact_request_shape"]


@pytest.mark.parametrize("invalid", [False, True])
def test_component_case_uses_real_receipt_filter_and_bounded_browser_calls(profile, invalid):
    page = Mock()
    payload = component_receipt("accept_success")
    if invalid:
        payload["private_extra"] = "PRIVATE_COMPONENT_SENTINEL"
    page.evaluate.return_value = payload
    call = lambda: profile.run_component_case(page, {"FRONTEND_URL": "http://localhost:3000"},
                                             b"synthetic-bundle", [], "accept_success", COMPONENT_VERSIONS)
    if invalid:
        with pytest.raises(ValueError, match="^component_receipt_invalid$"):
            call()
    else:
        assert call() == payload
    page.goto.assert_called_once_with("http://localhost:3000/articles", wait_until="load")
    assert page.wait_for_function.call_args.kwargs["timeout"] == 10_000
    assert page.evaluate.call_args.args[1] == "accept_success"
    assert "30000" in page.evaluate.call_args.args[0] and "clearTimeout(timer)" in page.evaluate.call_args.args[0]


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("settle_first", [False, True])
def test_component_continuation_observer_preserves_real_promise_order(profile, failed, settle_first):
    source = profile.COMPONENT_API.replace("export { formatMetadata } from 'actual-articles';", "")
    source += "\nconst failed = " + json.dumps(failed) + ", settleFirst = " + json.dumps(settle_first) + ";\n"
    source += r"""
let accepted = false, effect = false, reads = 0;
const events = [];
const consume = (async () => {
  try { const value = await fetchArticles({q: ''}); value.items; }
  catch (error) { error.message; }
  events.push('consumer');
})();
const call = requests[0];
const observed = call.afterContinuation(() => {
  events.push('observer');
  return {accepted, effect, reads, consumerFirst: events[0] === 'consumer'};
});
function settle() {
  if (failed) {
    const error = new Error();
    Object.defineProperty(error, 'message', {get() { reads++; return 'synthetic'; }});
    call.failure(error);
  } else call.success({get items() { reads++; return []; }});
}
if (settleFirst) settle();
accepted = true;
queueMicrotask(() => { effect = true; events.push('effect'); });
if (!settleFirst) settle();
const snapshot = await observed;
await consume;
await call.checkpoint;
if (!snapshot.accepted || snapshot.effect !== !settleFirst || snapshot.reads !== 1
    || !snapshot.consumerFirst && settleFirst || !call.drained || !call.settled) {
  throw new Error('continuation_order');
}
if (events.join(',') !== (settleFirst ? 'consumer,observer,effect' : 'effect,consumer,observer')) {
  throw new Error('continuation_sequence');
}
console.log(JSON.stringify({status: 'PASS', snapshot, drained: call.drained}));
"""
    result = subprocess.run(["node", "--input-type=module", "-"], input=source, text=True,
                            capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS" and payload["drained"] is True
    assert payload["snapshot"]["effect"] is not settle_first


@pytest.mark.parametrize("failure", [RuntimeError("synthetic body unavailable"), json.JSONDecodeError("invalid JSON", "{", 0)])
def test_response_body_failure_propagates_without_creating_finished_task(profile, failure):
    page = Mock()
    suite = {"BROWSER_API_URL": "http://localhost:18000"}
    response = Mock(url=profile.article_url(suite, "Alpha"), status=200, request=SimpleNamespace(method="GET"))
    response.finished.return_value = None
    response.json.side_effect = failure
    capture = profile.ArticleResponses(page, suite)
    capture.record(response)
    try:
        with pytest.raises(type(failure)) as raised:
            capture.receipt("Alpha", "date_desc", 1, ["navigation-21"])
        assert raised.value is failure
        response.json.assert_called_once()
        response.finished.assert_not_called()
    finally:
        capture.close()
    assert capture.responses == []


@pytest.mark.parametrize("finished,failure,expected", [
    (True, None, None),
    (False, "net::ERR_FAILED", "failed_product_request_after_http_response"),
    (False, None, "unsettled_product_request"),
])
def test_valid_response_body_does_not_waive_terminal_network_audit(profile, suite, finished, failure, expected):
    url = profile.article_url(suite, "Alpha")
    response = Mock(url=url, status=200, request=SimpleNamespace(method="GET"))
    response.json.return_value = {"page": 1, "sort": "date_desc", "items": [{"id": "navigation-21"}]}
    capture = profile.ArticleResponses(Mock(), suite)
    capture.record(response)
    try:
        capture.receipt("Alpha", "date_desc", 1, ["navigation-21"])
    finally:
        capture.close()
    response.finished.assert_not_called()
    errors = suite["ConsoleErrorLog"]()
    errors.request_evidence["synthetic-navigation-receipt"] = {
        "label": "synthetic-navigation", "page_id": "synthetic-page",
        "page_url": suite["FRONTEND_URL"] + "/articles", "source_url": url,
        "method": "GET", "resource_type": "fetch", "navigation_request": False,
        "main_frame": True, "response_status": 200, "response_url": url,
        "start_sequence": 1, "terminal_sequence": 3 if finished or failure else None,
        "finished": finished, "failure": failure,
    }
    failures = suite["_unexpected_console_errors"](errors)
    assert [item["kind"] for item in failures] == ([expected] if expected else [])
    counts = profile.audit(suite, suite["NetworkGuardLog"](), errors, [])
    assert profile.clean_audit(counts) is (expected is None)
