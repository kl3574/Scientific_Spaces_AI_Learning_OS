"""Offline contracts only: temporary fixture/store and mocked browser lifecycle."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/e2e/check_graph_provenance_return.py"
SENTINEL = "PRIVATE_SENTINEL"


@pytest.fixture
def check():
    return runpy.run_path(str(CLI), run_name="provenance_return_contract")


def test_seed_is_four_sections_over_three_existing_articles_and_only_owned_graph_changes(check, tmp_path):
    module = check["runtime_module"]()
    canonical = module["ARTICLE_FIXTURE"]
    before_canonical = canonical.read_bytes()
    runtime = module["prepare_runtime"](tmp_path)
    before_articles = Path(runtime["articles"]).read_bytes()
    store = module["GraphStore"](runtime["graph"])
    before = store.load().to_dict()

    sources = check["seed_graph"](module, runtime, tmp_path)

    assert len(sources) == 4
    assert {source["article_id"] for source in sources} == set(check["ARTICLE_IDS"])
    assert sources[0]["article_id"] == sources[3]["article_id"]
    assert sources[0]["section_node_id"] != sources[3]["section_node_id"]
    nodes = {node.node_id: node for node in store.load().nodes}
    for source in sources:
        section = nodes[source["section_node_id"]]
        assert section.node_type == "section"
        assert source["source_type"] == "section_content"
        assert source["section_title"] == section.label
        assert source["chunk_index"] == section.metadata["chunk_index"]
        assert source["article_id"] == section.metadata["article_id"]
    after = store.load().to_dict()
    changed = [node for node in after["nodes"] if node not in before["nodes"]]
    assert len(changed) == 1 and changed[0]["node_id"] == check["CONCEPT_ID"]
    assert changed[0]["metadata"]["source_count"] == 4
    assert changed[0]["metadata"]["sources"] == sources
    assert changed[0]["metadata"]["truncated"] is False
    assert {key: value for key, value in after.items() if key != "nodes"} == {
        key: value for key, value in before.items() if key != "nodes"
    }
    assert Path(runtime["articles"]).read_bytes() == before_articles
    assert canonical.read_bytes() == before_canonical
    binding = check["fixture_binding"](runtime, tmp_path)
    assert check["fixture_binding"](runtime, tmp_path) == binding
    assert hashlib.sha256(before_articles).digest() == binding[0]


@pytest.mark.parametrize("escape", ["root", "articles", "graph"])
def test_fixture_ownership_rejected_before_store_access(check, tmp_path, escape):
    runtime = {"root": tmp_path, "articles": tmp_path / "articles.json", "graph": tmp_path / "graph.json"}
    runtime[escape] = tmp_path.parent / "outside"
    store = Mock(side_effect=AssertionError("must not open store"))
    with pytest.raises(ValueError, match="^fixture_changed$"):
        check["seed_graph"]({"GraphStore": store}, runtime, tmp_path)
    store.assert_not_called()


def test_negative_markers_use_exact_existing_v1_contract(check):
    missing = check["marker"]("missing_origin")
    wrong = check["marker"]("wrong_article")
    assert check["FOCUS_KEY"] == "scientific-spaces:graph-article-return-focus:v1"
    assert missing == {"articleId": "attention-basics", "focusTarget": "provenance-9",
                       "returnTo": check["GRAPH_HREF"]}
    assert wrong == {"articleId": "crb-formula", "focusTarget": "provenance-3",
                     "returnTo": check["GRAPH_HREF"]}
    assert check["marker"]("arrival_superseded") == {
        "articleId": "attention-basics", "focusTarget": "provenance-3", "returnTo": check["GRAPH_HREF"],
    }
    assert set(wrong) == {"articleId", "focusTarget", "returnTo"}
    with pytest.raises(ValueError, match="^invalid_arguments$"):
        check["marker"](SENTINEL)


@pytest.fixture
def run_cli(check, monkeypatch):
    """Exercise actual CLI/resource/case orchestration without any server or browser."""
    def run(mode="success"):
        events = []
        contexts = []
        runtime_paths = []

        def event(name):
            events.append(name)
            if mode == name:
                print(SENTINEL)
                print(SENTINEL, file=sys.stderr)
                raise RuntimeError(SENTINEL)

        @contextmanager
        def manager(name, value):
            event(name + "_setup")
            try:
                yield value
            finally:
                event(name + "_teardown")

        def prepare(root):
            runtime_paths.append(root)
            event("prepare")
            runtime = {"root": root, "graph": root / "graph.json", "articles": root / "articles.json"}
            for key in ("graph", "articles"):
                runtime[key].write_text("{}", encoding="utf-8")
            return runtime

        class Context:
            def add_init_script(self, script):
                events.append("marker")
                assert "sessionStorage.setItem" in script
                assert check["FOCUS_KEY"] in script

            def close(self):
                event("context_teardown")

        class Browser:
            def new_context(self, **kwargs):
                event("context_setup")
                contexts.append(kwargs)
                return Context()

            def close(self):
                event("browser_teardown")

        def check_case(state, page, module, errors, expect):
            event("journey")
            assert len(contexts) == len([item for item in events if item == "guard"])
            state["stage"] = "expanded_return"
            if mode == "ui_red" and state["scenario"] == "roundtrip":
                raise AssertionError(SENTINEL)
            if state["scenario"] == "arrival_superseded":
                if mode in ("arrival_pre_focus", "arrival_post_detail"):
                    state["stage"] = "superseding_intent" if mode == "arrival_pre_focus" else "detail_release"
                    raise AssertionError(SENTINEL)
                state["stage"] = "arrival_superseded"
                if mode == "arrival_red":
                    raise AssertionError(SENTINEL)
            if mode == "fixture_changed":
                (runtime_paths[-1] / "graph.json").write_text(SENTINEL, encoding="utf-8")
            if mode == "interrupt":
                raise KeyboardInterrupt(SENTINEL)
            for key in state["checks"]:
                state["checks"][key] = (key == "arrival_superseded" if state["scenario"] == "arrival_superseded"
                                        else key == "fallback" if state["scenario"] != "roundtrip" else key != "fallback")
            print(SENTINEL)  # Even incidental helper output must not escape the CLI.

        def audit(errors):
            events.append("audit")
            return [SENTINEL] if mode == "audit_dirty" else []

        helpers = {
            "NetworkGuardLog": list, "ConsoleErrorLog": list,
            "prepare_runtime": prepare,
            "product_servers": lambda runtime, **kw: servers(runtime, kw),
            "LocalOnlyBrowser": lambda browser: browser,
            "_install_network_guard": lambda *args: event("guard"),
            "_new_observed_page": lambda *args, **kwargs: SimpleNamespace(),
            "_wait_for_page_requests_to_settle": lambda *args: event("settled"),
            "_unexpected_console_errors": audit,
            "_unexpected_context_pages": lambda *args: [],
        }

        def servers(runtime, kwargs):
            assert kwargs == {"frontend_mode": "start"}
            assert Path(runtime["root"]).exists()
            return manager("server", None)

        def bindings():
            event("bindings")
            return {"source": "b" if mode == "binding_changed" and "audit" in events else "a"}

        globals_ = check["main"].__globals__
        monkeypatch.setitem(globals_, "source_bindings", bindings)
        monkeypatch.setitem(globals_, "runtime_module", lambda: helpers)
        monkeypatch.setitem(globals_, "seed_graph", lambda *args: event("seed"))
        monkeypatch.setitem(globals_, "check_case", check_case)
        driver = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: Browser()))
        monkeypatch.setitem(globals_, "browser_driver", lambda: (lambda: manager("playwright", driver), object()))
        code = check["main"]([])
        return code, events, contexts, runtime_paths

    return run


def read_result(capsys):
    output = capsys.readouterr()
    assert SENTINEL not in output.out + output.err
    assert not output.err
    assert len(output.out.splitlines()) == 1
    return json.loads(output.out)


def test_all_seven_cases_have_fresh_contexts_strict_audit_and_cleanup(run_cli, capsys, check):
    code, events, contexts, paths = run_cli()
    result = read_result(capsys)
    assert code == 0 and result["status"] == "PASS"
    assert len(contexts) == 7
    assert [c["viewport"] for c in contexts] == [{"width": 1440, "height": 1000}] * 3 + [{"width": 390, "height": 844}] * 4
    assert events.count("marker") == 5
    assert events.count("context_teardown") == 7
    assert events.index("audit") > max(index for index, event in enumerate(events) if event == "context_teardown")
    assert all(not path.exists() for path in paths)
    assert result["runtime_removed"] and result["fixture_unchanged"] and result["bindings_equal"]
    assert result["audit"] == "PASS" and not any(result["audit_counts"].values())
    assert {case["scenario"] for case in result["cases"]} == set(check["SCENARIOS"]) | {"arrival_superseded"}
    assert all(case["status"] == "PASS" for case in result["cases"])


def test_expected_ui_red_still_audits_both_viewports_and_closes_every_resource(run_cli, capsys):
    code, events, contexts, paths = run_cli("ui_red")
    result = read_result(capsys)
    assert code == 1 and result["status"] == "FAIL"
    assert result["audit"] == "PASS" and result["runtime_removed"]
    assert len(contexts) == 7
    assert all(not path.exists() for path in paths)
    failures = [case for case in result["cases"] if case["status"] == "FAIL"]
    assert [case["viewport"] for case in failures] == ["desktop", "mobile"]
    assert all(case["failure_stage"] == "expanded_return" and case["error"] == "ui_assertion" for case in failures)
    assert all(name in events for name in ("server_teardown", "browser_teardown", "playwright_teardown", "audit"))


@pytest.mark.parametrize("mode,stage", [("arrival_pre_focus", "superseding_intent"),
                                      ("arrival_post_detail", "detail_release")])
def test_arrival_prerequisite_failure_is_not_product_red(run_cli, capsys, mode, stage):
    code, events, contexts, paths = run_cli(mode)
    result = read_result(capsys)
    assert code == 2 and result["status"] == "BLOCKED"
    assert all(case["status"] == "PASS" for case in result["cases"][:6])
    assert result["cases"][6]["status"] == "BLOCKED"
    assert result["cases"][6]["failure_stage"] == stage
    assert result["audit"] == "PASS" and result["runtime_removed"]
    assert all(not path.exists() for path in paths)


def test_arrival_red_preserves_six_old_passes_and_cleanup(run_cli, capsys):
    code, events, contexts, paths = run_cli("arrival_red")
    result = read_result(capsys)
    assert code == 1 and result["status"] == "FAIL"
    assert all(case["status"] == "PASS" for case in result["cases"][:6])
    assert result["cases"][6]["failure_stage"] == "arrival_superseded"
    assert result["cases"][6]["viewport"] == "mobile"
    assert result["audit"] == "PASS" and result["runtime_removed"]
    assert events.count("context_teardown") == len(contexts) == 7
    assert all(not path.exists() for path in paths)


@pytest.mark.parametrize("mode", ["bindings", "prepare", "seed", "server_setup", "playwright_setup",
                                  "context_setup", "guard", "settled", "interrupt", "context_teardown",
                                  "browser_teardown", "playwright_teardown", "server_teardown",
                                  "audit_dirty", "binding_changed", "fixture_changed"])
def test_setup_ui_infrastructure_and_teardown_failures_never_pass_or_leak(run_cli, capsys, mode, check):
    code, events, contexts, paths = run_cli(mode)
    result = read_result(capsys)
    assert code == 2 and result["status"] == "BLOCKED"
    assert result["error"] in check["ERRORS"] - {"none"}
    assert result["failure_stage"] in check["STAGES"]
    assert all(not path.exists() for path in paths)
    if contexts:
        assert "browser_teardown" in events and "server_teardown" in events
    if mode == "audit_dirty":
        assert result["audit_counts"]["console"] == 1
    if mode == "binding_changed":
        assert not result["bindings_equal"]
    if mode == "fixture_changed":
        assert not result["fixture_unchanged"]


def test_invalid_cli_input_is_fixed_json_without_starting_runtime(check, monkeypatch, capsys):
    execute = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setitem(check["main"].__globals__, "execute", execute)
    assert check["main"]([SENTINEL]) == 2
    result = read_result(capsys)
    assert result["error"] == "invalid_arguments" and result["audit"] == "NOT_RUN"
    execute.assert_not_called()


@pytest.mark.parametrize("scenario", ["roundtrip", "missing_origin", "wrong_article"])
def test_real_journey_calls_native_keyboard_and_completes_routes_before_focus_assertions(check, scenario):
    state = {"stage": "setup", "scenario": scenario, "checks": {}}
    events = []
    locators = []

    def locator(*args, **kwargs):
        value = Mock()
        value.first = value
        value.press.side_effect = lambda key: events.append(("key", state["stage"], key))
        locators.append(value)
        return value

    page = Mock()
    page.locator.side_effect = locator
    page.get_by_role.side_effect = locator
    page.get_by_test_id.side_effect = locator
    page.reload.side_effect = lambda **kwargs: events.append(("reload", state["stage"]))
    assertion = Mock()
    assertion.to_be_focused.side_effect = lambda **kwargs: events.append(("focus_assertion", state["stage"]))
    expect = Mock(return_value=assertion)
    module = {"FRONTEND_URL": "http://127.0.0.1:3000", "ATTENTION_TITLE": "Synthetic title",
              "_focus_via_tab": lambda *args: events.append(("tab", state["stage"])),
              "_declare_expected_route_transition": lambda *args, **kwargs: events.append(("declare", state["stage"])) or "transition",
              "_complete_expected_route_transition": lambda *args: events.append(("complete", state["stage"])),
              "_wait_for_page_requests_to_settle": lambda *args: events.append(("settled", state["stage"])),
              "_wait_for_application_shell": lambda *args: None,
              "_require_visible_focus": lambda *args: events.append(("visible_focus", state["stage"]))}

    check["check_case"](state, page, module, [], expect)

    page.evaluate.assert_not_called()
    for value in locators:
        value.focus.assert_not_called()
        value.click.assert_not_called()
    if scenario == "roundtrip":
        assert state["checks"] == {"expanded_return": True, "manual_collapse": True,
                                   "ordinary_return": True, "cold_revisit": True}
        assert sum(event[0] == "declare" for event in events) == 4
        assert sum(event[0] == "complete" for event in events) == 4
        assert events.index(("complete", "return_route")) < events.index(("focus_assertion", "expanded_return"))
        for index, event in enumerate(events):
            if event[0] == "key":
                assert event[2] == "Enter"
                assert any(previous == ("tab", event[1]) for previous in events[:index])
        assert ("key", "cold_revisit", "Enter") in events
        assert ("reload", "cold_revisit") in events
        counts = [call.args[0] for call in assertion.to_have_count.call_args_list]
        assert 3 in counts and 4 in counts and 0 in counts
    else:
        assert state["checks"] == {"fallback": True}
        assert ("focus_assertion", "fallback") in events
        assert not any(event[0] == "key" for event in events)


@pytest.fixture
def held_detail(check):
    page = Mock()
    url = "http://localhost:8000/graph/nodes/concept%3Aattention"
    response = Mock(status=200, url=url)
    route = Mock(request=SimpleNamespace(url=url, method="GET"))
    route.fetch.return_value = response
    held = check["HeldDetail"](page, url)
    page.route.assert_called_once_with(url, held.handler)
    return held, page, route, response


def test_hold_forwards_only_exact_get_and_fulfills_same_real_response(held_detail):
    held, page, route, response = held_detail
    for url, method in ((held.url, "OPTIONS"), (held.url + "?q=other", "GET"),
                        ("http://localhost:8000/v1.1/graph/subgraph", "GET")):
        other = Mock(request=SimpleNamespace(url=url, method=method))
        held.intercept(other)
        other.fallback.assert_called_once_with()
        other.fetch.assert_not_called()
    held.intercept(route)
    held.wait_ready()
    route.fetch.assert_called_once_with(max_redirects=0, timeout=5000)
    route.fulfill.assert_not_called()
    held.release()
    held.verify_released()
    route.fulfill.assert_called_once_with(response=response)
    held.close()
    response.dispose.assert_called_once_with()
    route.abort.assert_not_called()
    page.unroute.assert_called_once_with(held.url, held.handler)
    page.unroute_all.assert_not_called()


@pytest.mark.parametrize("failure", ["missing", "duplicate", "bad_status", "redirect", "fetch",
                                     "fallback", "duplicate_abort", "release"])
def test_held_interception_fails_closed_without_callback_exceptions(held_detail, check, monkeypatch, failure):
    held, page, route, response = held_detail
    if failure == "missing":
        ticks = iter((0, 9))
        monkeypatch.setitem(check["HeldDetail"].wait_ready.__globals__, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    else:
        if failure == "bad_status":
            response.status = 500
        if failure == "redirect":
            response.url += "/redirected"
        if failure == "fetch":
            route.fetch.side_effect = RuntimeError(SENTINEL)
        if failure == "fallback":
            route.request.method = "OPTIONS"
            route.fallback.side_effect = RuntimeError(SENTINEL)
        held.intercept(route)  # Callback errors must be latched, never raised.
        if failure in ("duplicate", "duplicate_abort"):
            duplicate = Mock(request=route.request)
            if failure == "duplicate_abort":
                duplicate.abort.side_effect = RuntimeError(SENTINEL)
            held.intercept(duplicate)
            duplicate.fetch.assert_not_called()
    if failure == "release":
        route.fulfill.side_effect = RuntimeError(SENTINEL)
        operation = held.release
    else:
        operation = held.wait_ready
    with pytest.raises(ValueError, match="^detail_interception$") as error:
        operation()
    assert SENTINEL not in str(error.value)
    if failure == "missing":
        monkeypatch.setitem(check["HeldDetail"].close.__globals__, "time", SimpleNamespace(monotonic=lambda: 0))
        held.close()
    else:
        with pytest.raises(ValueError, match="^detail_interception$"):
            held.close()
    page.unroute.assert_called_once_with(held.url, held.handler)
    assert held.route is None and held.response is None


@pytest.mark.parametrize("failure", ["abort", "dispose", "unroute"])
def test_held_cleanup_attempts_every_owned_resource_and_reports_failure(held_detail, failure):
    held, page, route, response = held_detail
    held.intercept(route)
    {"abort": route.abort, "dispose": response.dispose, "unroute": page.unroute}[failure].side_effect = RuntimeError(SENTINEL)
    with pytest.raises(ValueError, match="^detail_interception$"):
        held.close()
    route.abort.assert_called_once_with()
    response.dispose.assert_called_once_with()
    page.unroute.assert_called_once_with(held.url, held.handler)
    assert held.route is None and held.response is None


def test_cleanup_waits_only_its_inflight_callback_and_late_response_is_disposed(held_detail):
    held, page, route, response = held_detail
    held.intercept(route)
    held.active = 1
    page.wait_for_timeout.side_effect = lambda milliseconds: setattr(held, "active", 0)
    held.close()
    page.wait_for_timeout.assert_called_once_with(20)
    page.unroute_all.assert_not_called()
    response.dispose.assert_called_once_with()


def test_capture_finishing_during_cleanup_never_publishes_or_leaks_response(held_detail):
    held, page, route, response = held_detail

    def finish_late(**kwargs):
        held.closing = True
        return response

    route.fetch.side_effect = finish_late
    held.intercept(route)
    assert held.invalid and held.active == 0 and held.response is None
    response.dispose.assert_called_once_with()
    with pytest.raises(ValueError, match="^detail_interception$"):
        held.close()


@pytest.mark.parametrize("failure", [None, "before_release", "after_release"])
def test_arrival_waits_for_capture_before_native_intent_and_always_cleans_owned_hold(check, failure):
    state = {"stage": "setup", "scenario": "arrival_superseded", "checks": {}}
    events = []
    page = Mock()
    captured = {}
    url = "http://localhost:8000/graph/nodes/concept%3Aattention"
    response = Mock(status=200, url=url)
    route = Mock(request=SimpleNamespace(url=url, method="GET"))
    route.fetch.side_effect = lambda **kwargs: events.append("captured_200") or response
    route.fulfill.side_effect = lambda **kwargs: events.append("release")
    page.route.side_effect = lambda url, handler: captured.update(handler=handler)
    page.wait_for_timeout.side_effect = lambda milliseconds: captured["handler"](route)
    page.evaluate.return_value = True

    def locator(*args, **kwargs):
        value = Mock()
        value.first = value
        value.get_by_role.side_effect = locator
        value.press.side_effect = lambda key: events.append((kwargs.get("name"), key))
        return value

    page.get_by_role.side_effect = locator
    page.get_by_test_id.side_effect = locator
    page.locator.side_effect = locator
    assertion = Mock()

    def focused(**kwargs):
        events.append(("focused", state["stage"]))
        if (failure == "before_release" and state["stage"] == "superseding_intent") or (
            failure == "after_release" and state["stage"] == "arrival_superseded"
        ):
            raise AssertionError(SENTINEL)

    assertion.to_be_focused.side_effect = focused

    def settle(*args):
        assert "release" in events
        events.append("settled")

    module = {"FRONTEND_URL": "http://127.0.0.1:3000", "BROWSER_API_URL": "http://localhost:8000",
              "_wait_for_application_shell": lambda *args: None,
              "_wait_for_page_requests_to_settle": settle,
              "_focus_via_tab": lambda *args: events.append("tab"),
              "_require_visible_focus": lambda *args: None}
    if failure:
        with pytest.raises(AssertionError, match=SENTINEL):
            check["check_case"](state, page, module, [], Mock(return_value=assertion))
    else:
        check["check_case"](state, page, module, [], Mock(return_value=assertion))
        assert state["checks"] == {"arrival_superseded": True}
    assert events.index("captured_200") < events.index(("Results", "Enter")) < events.index(("Selected", "Enter"))
    if failure != "before_release":
        assert events.index(("focused", "superseding_intent")) < events.index("release") < events.index("settled")
        route.fulfill.assert_called_once_with(response=response)
        route.abort.assert_not_called()
    else:
        route.abort.assert_called_once_with()
        route.fulfill.assert_not_called()
    response.dispose.assert_called_once_with()
    page.unroute.assert_called_once_with(url, captured["handler"])
