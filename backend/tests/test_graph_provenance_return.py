"""Offline contracts only: temporary fixture/store and mocked browser lifecycle."""

from contextlib import closing, contextmanager
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/e2e/check_graph_provenance_return.py"
SENTINEL = "PRIVATE_SENTINEL"
IMAGE_CHECKS = {
    f"reader_inline_image_{viewport}_{check}": True
    for viewport in ("desktop", "mobile")
    for check in ("exact_source", "visible_decoded", "non_raster_rejected", "remote_placeholder")
}


@pytest.fixture
def check():
    return runpy.run_path(str(CLI), run_name="provenance_return_contract")


def test_isolated_runtime_configures_actual_imported_function_globals(check, tmp_path):
    module = check["runtime_module"]()
    configure = module.get("configure_runtime")
    assert callable(configure), "runner needs an explicit runtime configuration boundary"
    runtime = SimpleNamespace(
        backend_port=18000, frontend_root=tmp_path / "frontend",
        api_url="http://127.0.0.1:18000", browser_api_url="http://localhost:18000",
        environment={},
    )
    configured = configure(runtime)
    assert configured is inspect.unwrap(module["product_servers"]).__globals__
    assert configured is module["verify_backend_restart_persistence"].__globals__
    assert configured["FRONTEND_ROOT"] == runtime.frontend_root
    assert configured["API_URL"] == runtime.api_url
    assert configured["BROWSER_API_URL"] == runtime.browser_api_url
    assert configured["BACKEND_PORT"] == 18000
    for origin in (runtime.api_url, runtime.browser_api_url, "http://127.0.0.1:3000"):
        assert configured["_is_allowed_http_url"](origin)
    for origin in ("http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:18001"):
        assert not configured["_is_allowed_http_url"](origin)


def test_build_bindings_follow_the_selected_temporary_build(check, monkeypatch, tmp_path):
    root = tmp_path / "source"
    for relative in (
        "frontend/src/component.tsx", "backend/app/main.py",
        "scripts/e2e/run_product_e2e.py", "scripts/e2e/check_graph_provenance_return.py",
        "scripts/e2e/product_test_runtime.py", "frontend/package.json",
        "frontend/package-lock.json", "backend/pyproject.toml", "backend/uv.lock",
        "backend/tests/fixtures/evaluation/articles.json",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic input")
    selected = tmp_path / "owned-build" / "frontend"
    for frontend in (root / "frontend", selected):
        for relative in ("BUILD_ID", "server/page.js", "static/chunk.js", "routes-manifest.json"):
            path = frontend / ".next" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic build")
    monkeypatch.setitem(check["source_bindings"].__globals__, "ROOT", root)
    initial = check["source_bindings"](frontend_root=selected)
    (root / "frontend/.next/server/page.js").write_text("unrelated shared build")
    assert check["source_bindings"](frontend_root=selected) == initial
    (selected / ".next/server/page.js").write_text("changed selected build")
    changed = check["source_bindings"](frontend_root=selected)
    assert changed["build"] != initial["build"]
    assert changed["source"] == initial["source"]
    assert changed["fixture"] == initial["fixture"]
    (root / "scripts/e2e/product_test_runtime.py").write_text("changed execution helper")
    assert check["source_bindings"](frontend_root=selected)["source"] != initial["source"]


@pytest.mark.parametrize("port", [8000, 18000, 9000, 65535])
def test_original_network_evidence_contract_remains_strict_at_each_port(check, tmp_path, port):
    module = check["runtime_module"]()
    configured = module["configure_runtime"](SimpleNamespace(
        backend_port=port, frontend_root=tmp_path,
        api_url=f"http://127.0.0.1:{port}", browser_api_url=f"http://localhost:{port}",
        environment={},
    ))
    configured["_verify_http_error_evidence_contract"]()
    for host in ("127.0.0.1", "localhost"):
        assert configured["_is_allowed_http_url"](f"http://{host}:{port}/health")
        for excluded in {8000, 18000, 9000, 65535} - {port}:
            assert not configured["_is_allowed_http_url"](f"http://{host}:{excluded}/health")


@pytest.mark.parametrize("failure", [None, "backend_spawn", "backend_ready", "frontend_spawn", "frontend_ready", "body"])
def test_servers_use_only_configured_owned_processes_and_sanitized_environment(check, monkeypatch, tmp_path, failure):
    module = check["runtime_module"]()
    environment = {"HOME": str(tmp_path / "home"), "TMPDIR": str(tmp_path / "temporary"), "NEXT_TELEMETRY_DISABLED": "1"}
    configured = module["configure_runtime"](SimpleNamespace(
        backend_port=18000, frontend_root=tmp_path / "build",
        api_url="http://127.0.0.1:18000", browser_api_url="http://localhost:18000",
        environment=environment,
    ))
    environment["HOME"] = "modified after configuration"
    monkeypatch.setenv("SCIENTIFIC_SPACES_PRIVATE_SENTINEL", SENTINEL)
    calls, owned, stopped, ready = [], [], [], []
    ports = Mock()
    monkeypatch.setitem(configured, "_require_port_free", ports)
    monkeypatch.setitem(configured, "_stop_process", lambda process: stopped.append(process) if process else None)

    def spawn(command, **kwargs):
        label = "backend" if len(calls) == 0 else "frontend"
        calls.append((command, kwargs))
        if failure == label + "_spawn":
            raise RuntimeError("synthetic spawn failure")
        process = SimpleNamespace(pid=100 + len(calls))
        owned.append(process)
        return process

    def wait(url, process, path, **kwargs):
        label = "backend" if len(ready) == 0 else "frontend"
        ready.append(url)
        if failure == label + "_ready":
            raise RuntimeError("synthetic readiness failure")

    monkeypatch.setattr(configured["subprocess"], "Popen", spawn)
    monkeypatch.setitem(configured, "_wait_for_url", wait)
    runtime = {"root": tmp_path, "environment": {"SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake"}}

    def execute():
        with configured["product_servers"](runtime, frontend_mode="start"):
            if failure == "body":
                raise RuntimeError("synthetic suite failure")

    if failure:
        with pytest.raises(RuntimeError, match="synthetic"):
            execute()
    else:
        execute()
    assert [call.args[0] for call in ports.call_args_list] == [18000, 3000]
    assert stopped == list(reversed(owned))
    for command, kwargs in calls:
        assert kwargs["start_new_session"] is True
        assert "SCIENTIFIC_SPACES_PRIVATE_SENTINEL" not in kwargs["env"]
        assert kwargs["env"]["SCIENTIFIC_SPACES_ZOTERO_PROVIDER"] == "fake"
        assert kwargs["env"]["NEXT_TELEMETRY_DISABLED"] == "1"
        assert kwargs["env"]["HOME"] == str(tmp_path / "home")
        assert kwargs["env"]["TMPDIR"] == str(tmp_path / "temporary")
        assert command[command.index("--port") + 1] == ("18000" if "uvicorn" in command else "3000")
    assert all(url in {"http://127.0.0.1:18000/health", "http://127.0.0.1:3000"} for url in ready)


@pytest.mark.parametrize("failure", [None, "spawn", "ready", "read", "validation"])
def test_restart_owns_its_group_and_never_uses_the_shared_backend(check, monkeypatch, tmp_path, failure):
    module = check["runtime_module"]()
    configured = module["configure_runtime"](SimpleNamespace(
        backend_port=18000, frontend_root=tmp_path,
        api_url="http://127.0.0.1:18000", browser_api_url="http://localhost:18000",
        environment={"HOME": str(tmp_path / "home"), "TMPDIR": str(tmp_path / "temporary")},
    ))
    process = SimpleNamespace(pid=12345)
    stopped, requests, calls = [], [], []
    monkeypatch.setitem(configured, "_require_port_free", lambda port: requests.append(port))
    monkeypatch.setitem(configured, "_stop_process", lambda owned: stopped.append(owned))

    def spawn(command, **kwargs):
        calls.append((command, kwargs))
        if failure == "spawn":
            raise RuntimeError("synthetic spawn failure")
        return process

    def wait(url, owned, path):
        requests.append(url)
        assert owned is process
        if failure == "ready":
            raise RuntimeError("synthetic readiness failure")

    def read(url):
        requests.append(url)
        if failure == "read":
            raise RuntimeError("synthetic read failure")
        if url.endswith("stats"):
            return {"completed_count": 0 if failure == "validation" else 2, "bookmark_count": 1, "note_count": 1}
        return {"total": 25, "items": [{"ended_at": "synthetic"}] * 25}

    monkeypatch.setattr(configured["subprocess"], "Popen", spawn)
    monkeypatch.setitem(configured, "_wait_for_url", wait)
    monkeypatch.setitem(configured, "_read_json_url", read)
    runtime = {"root": tmp_path, "environment": {}}
    if failure:
        with pytest.raises((RuntimeError, configured["E2EFailure"])):
            configured["verify_backend_restart_persistence"](runtime)
    else:
        assert configured["verify_backend_restart_persistence"](runtime)["status"] == "PASS"
    assert stopped == [None if failure == "spawn" else process]
    assert requests[0] == 18000
    assert all(str(value).startswith("http://127.0.0.1:18000/") for value in requests[1:])
    command, kwargs = calls[0]
    assert command[command.index("--port") + 1] == "18000"
    assert kwargs["start_new_session"] is True
    assert kwargs["env"]["HOME"] == str(tmp_path / "home")
    assert kwargs["env"]["TMPDIR"] == str(tmp_path / "temporary")


def test_frontend_teardown_failure_still_attempts_owned_backend_cleanup(check, monkeypatch, tmp_path):
    module = check["runtime_module"]()
    globals_ = inspect.unwrap(module["product_servers"]).__globals__
    processes = [SimpleNamespace(pid=101), SimpleNamespace(pid=102)]
    stopped = []
    monkeypatch.setattr(module["subprocess"], "Popen", Mock(side_effect=processes))
    monkeypatch.setitem(globals_, "_require_port_free", lambda port: None)
    monkeypatch.setitem(globals_, "_wait_for_url", lambda *args, **kwargs: None)

    def stop(process):
        stopped.append(process)
        if process is processes[1]:
            raise RuntimeError("synthetic frontend teardown failure")

    monkeypatch.setitem(globals_, "_stop_process", stop)
    with pytest.raises(RuntimeError, match="synthetic frontend teardown failure"):
        with module["product_servers"]({"root": tmp_path, "environment": {}}, frontend_mode="start"):
            pass
    assert stopped == [processes[1], processes[0]]


def test_process_group_cleanup_retires_descendants_after_leader_exit(check, monkeypatch):
    module = check["runtime_module"]()
    process = Mock(pid=12345)
    process.wait.return_value = 0
    process.poll.return_value = 0
    kill = Mock()
    monkeypatch.setattr(module["os"], "killpg", kill)
    module["_stop_process"](process)
    assert [(call.args[0], call.args[1]) for call in kill.call_args_list] == [
        (12345, module["signal"].SIGTERM), (12345, module["signal"].SIGKILL),
    ]
    process.wait.assert_called_once_with(timeout=10)


@pytest.fixture
def cli_lifetime(check, monkeypatch, tmp_path):
    """Real CLI/suite orchestration; only resource boundaries are synthetic."""
    def arrange(port, outcome="success", *, image_failure=None, original_cleanup_failure=False):
        full = check["runtime_module"]()["main"].__globals__
        dedicated = check["main"].__globals__
        helper = importlib.import_module("product_test_runtime")
        private_keys = ("SCIENTIFIC_SPACES_PRIVATE_SENTINEL", "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER",
                        "SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "OPENAI_API_KEY", "NODE_OPTIONS", "PYTHONPATH",
                        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                        "http_proxy", "https_proxy", "all_proxy", "no_proxy")
        for key in private_keys:
            monkeypatch.setenv(key, SENTINEL)
        monkeypatch.setenv(helper.PORT_ENV, str(port))
        previous_environment = dict(helper.os.environ)
        environment = {"PATH": helper.os.defpath, "HOME": str(tmp_path / "configured-home"),
                       "TMPDIR": str(tmp_path / "configured-tmp"), "XDG_CACHE_HOME": str(tmp_path / "configured-cache"),
                       "PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "existing-browser-cache"),
                       "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1", "NEXT_TELEMETRY_DISABLED": "1",
                       helper.PORT_ENV: str(port), "NEXT_PUBLIC_API_BASE_URL": f"http://localhost:{port}"}
        for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME", "PLAYWRIGHT_BROWSERS_PATH"):
            Path(environment[key]).mkdir()
        source = tmp_path / "source"
        shared = source / "frontend"
        (shared / ".next").mkdir(parents=True)
        (shared / ".next/BUILD_ID").write_text("synthetic-default-build")
        events, observations, paths = [], [], []
        runtimes, resets, image_calls = [], [], []
        active_runtime = None
        resources = set()
        scope_depth = 0
        real_environment = helper.process_environment

        @contextmanager
        def process_environment(configured):
            nonlocal scope_depth
            with real_environment(configured):
                scope_depth += 1
                try:
                    yield
                finally:
                    scope_depth -= 1

        def observe(stage):
            events.append(stage)
            observations.append({"stage": stage, "private_absent": not any(key in helper.os.environ for key in private_keys),
                                 "configured_retained": all(helper.os.environ.get(key) == value for key, value in environment.items()),
                                 "scope_active": scope_depth > 0})

        build_enter = Mock()

        @contextmanager
        def frontend_runtime(root, *, backend_port=None, frontend_mode="start"):
            assert root == source and backend_port == port and frontend_mode == "start"
            with tempfile.TemporaryDirectory(prefix="owned-frontend-", dir=tmp_path) as temporary:
                path = Path(temporary)
                paths.append(path)
                (path / "BUILD_ID").write_text("synthetic-owned-build")
                events.append("frontend_enter")
                try:
                    build_enter()
                    yield helper.FrontendRuntime(path, port, dict(environment), {"isolated": port != 8000})
                finally:
                    events.append("frontend_teardown")

        @contextmanager
        def owned_temporary_directory(*, prefix):
            phase = "image" if "reader-image" in prefix else "original"
            try:
                with tempfile.TemporaryDirectory(prefix=prefix, dir=tmp_path) as temporary:
                    path = Path(temporary)
                    paths.append(path)
                    events.append(f"{phase}_temp_enter")
                    yield temporary
            finally:
                events.append(f"{phase}_temp_teardown")
                if (phase == "image" and image_failure == "temp_teardown") or (
                    phase == "original" and original_cleanup_failure
                ):
                    if phase == "image" and image_calls:
                        image_calls[-1]["console_errors"].append("synthetic_late_console_error")
                    raise RuntimeError(f"synthetic_{phase}_temp_teardown")

        def prepare(root, *, reader_inline_images=False):
            assert isinstance(reader_inline_images, bool)
            assert reader_inline_images == ("reader-image" in root.name)
            phase = "image" if reader_inline_images else "original"
            events.append(f"{phase}_prepare")
            paths.append(root)
            articles = [article.to_dict() for article in full["_load_fixture_articles"]()]
            assert len(articles) == 3
            if reader_inline_images and image_failure != "wrong_fixture":
                for article in articles:
                    if article["id"] == full["CRB_ARTICLE_ID"]:
                        article["content"] += (
                            f"\n![Synthetic inline PNG]({full['READER_INLINE_PNG']})\n"
                            "\n![Rejected inline SVG](data:image/svg+xml;base64,PHN2Zy8+)\n"
                        )
            (root / "articles.json").write_text(json.dumps(articles))
            for name in ("graph", "learning", "tutor", "zotero"):
                (root / (name + ".json")).write_text("{}")
            references = root / "references"
            references.mkdir()
            (references / "records.json").write_text("[]")
            runtime = {"root": root, "references": references, "environment": {},
                       **{name: root / (name + ".json")
                          for name in ("articles", "graph", "learning", "tutor", "zotero")}}
            runtimes.append((phase, runtime))
            return runtime

        real_reset = full["_reset_mutable_runtime"]

        def reset(runtime):
            phase = next(phase for phase, item in runtimes if item is runtime)
            events.append(f"{phase}_reset")
            resets.append((phase, runtime["root"]))
            real_reset(runtime)

        def phase_now():
            return next(phase for phase, item in runtimes if item is active_runtime)

        @contextmanager
        def servers(runtime, **kwargs):
            nonlocal active_runtime
            assert "servers" not in resources
            active_runtime = runtime
            phase = phase_now()
            observe(f"{phase}_server_enter")
            resources.add("servers")
            try:
                if phase == "image" and image_failure == "server_startup":
                    raise RuntimeError("synthetic_image_server_startup")
                yield {"backend": Path(runtime["root"]) / "backend.log", "frontend": Path(runtime["root"]) / "frontend.log"}
            finally:
                resources.remove("servers")
                events.append("server_teardown")
                observe(f"{phase}_server_teardown")
                if phase == "image" and image_failure == "server_teardown":
                    image_calls[-1]["console_errors"].append("synthetic_late_console_error")
                    raise RuntimeError("synthetic_image_server_teardown")

        class Context:
            pages = []

            def __init__(self):
                resources.add(self)

            def close(self):
                if self in resources:
                    resources.remove(self)
                    observe("image_context_teardown")
                    if image_failure == "context_teardown":
                        image_calls[-1]["console_errors"].append("synthetic_late_console_error")
                        raise RuntimeError("synthetic_image_context_teardown")

        class Browser:
            version = "synthetic"

            def __init__(self, phase):
                self.phase = phase
                self.contexts = []
                if phase == "image" and image_failure == "browser_mismatch":
                    self.version = "synthetic-other"

            def new_context(self, **options):
                assert options["service_workers"] == "block"
                assert self.phase == "image"
                context = Context()
                self.contexts.append(context)
                observe("image_context_enter")
                return context

            def close(self):
                if "browser" in resources:
                    observe("browser_teardown")
                    resources.remove("browser")
                    for context in self.contexts:
                        context.close()
                    if self.phase == "image":
                        observe("image_browser_teardown")
                        if image_failure in {"late_audit", "body_late_audit", "browser_teardown"}:
                            image_calls[-1]["console_errors"].append("synthetic_late_console_error")
                        if image_failure in {"browser_teardown", "body_late_audit"}:
                            raise RuntimeError("synthetic_image_browser_teardown")

        browsers = []

        def launch(**kwargs):
            observe("browser_launch")
            phase = phase_now()
            if outcome == "startup_error" or (phase == "image" and image_failure == "startup"):
                raise RuntimeError("synthetic_browser_startup")
            resources.add("browser")
            browser = Browser(phase)
            browsers.append(browser)
            return browser

        @contextmanager
        def sync_playwright():
            observe("driver_enter")
            resources.add("driver")
            try:
                yield SimpleNamespace(chromium=SimpleNamespace(launch=launch))
            finally:
                observe("driver_teardown")
                # Stopping the driver also retires browsers not explicitly closed.
                try:
                    for browser in browsers:
                        if browser.phase == phase_now():
                            browser.close()
                finally:
                    resources.remove("driver")

        def iteration(*args, **kwargs):
            observe("suite_body")
            if outcome == "interrupt":
                raise KeyboardInterrupt
            return {"status": "PASS", "checks": {"synthetic": True}, **dict.fromkeys((
                "external_network_request_count", "framework_prefetch_cancellation_count", "route_transition_cancellation_count",
                "route_with_complete_precursor_snapshot_count", "declared_cancelled_route_request_count",
                "declared_route_read_cancellation_count", "route_transition_expectation_count", "bound_route_transition_request_count",
                "superseded_successful_read_count", "next_static_chunk_cancellation_count", "successful_no_content_response_count"), 0)}

        def image_iteration(browser, *, iteration, blocked_external, console_errors, page_errors):
            observe("image_body")
            assert phase_now() == "image"
            assert isinstance(blocked_external, full["NetworkGuardLog"])
            assert isinstance(console_errors, full["ConsoleErrorLog"])
            assert isinstance(page_errors, list)
            image_calls.append({"iteration": iteration, "blocked_external": blocked_external,
                                "console_errors": console_errors, "page_errors": page_errors})
            for name in ("learning", "tutor"):
                assert not active_runtime[name].exists(), "image mutable state was not reset"
                active_runtime[name].write_text("synthetic mutation")
            for width, height in ((1440, 1000), (390, 844)):
                with closing(browser.new_context(viewport={"width": width, "height": height})):
                    if iteration == 2:
                        if image_failure in {"body", "body_late_audit"}:
                            raise RuntimeError("synthetic_image_body")
                        if image_failure == "interrupt":
                            raise KeyboardInterrupt
                        if image_failure == "sigterm":
                            events.append("image_sigterm")
                            handler["current"](full["signal"].SIGTERM, None)
                            pytest.fail("SIGTERM did not interrupt the image body")
                    if image_failure == "fixture_drift":
                        (active_runtime["references"] / "records.json").write_text("[{}]")
            checks = dict(IMAGE_CHECKS)
            if image_failure in {"incomplete", "wrong_checks"}:
                checks.pop("reader_inline_image_mobile_visible_decoded")
            if image_failure == "wrong_checks":
                checks["synthetic_unrelated_check"] = True
            if image_failure == "non_boolean":
                checks["reader_inline_image_mobile_visible_decoded"] = 1
            return checks

        def restart(runtime):
            assert phase_now() == "original" and "servers" not in resources
            assert runtime["root"].exists()
            events.append("original_restart")
            return {"status": "PASS"}

        def run_cases(result, *args):
            iteration()
            result["cases"] = [{"status": "PASS", "fixture_unchanged": True} for _ in range(7)]

        prior_handler = Mock(name="prior_SIGTERM_handler")
        handler = {"current": prior_handler}

        def install(signum, replacement):
            assert signum == full["signal"].SIGTERM
            previous = handler["current"]
            handler["current"] = replacement
            return previous

        monkeypatch.setattr(full["signal"], "getsignal", lambda signum: handler["current"])
        monkeypatch.setattr(full["signal"], "signal", install)
        monkeypatch.setattr(helper, "frontend_runtime", frontend_runtime)
        monkeypatch.setattr(helper, "sanitized_environment", lambda: dict(environment))
        monkeypatch.setattr(helper, "process_environment", process_environment)
        monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(sync_playwright=sync_playwright, expect=object()))
        monkeypatch.setattr(sys, "argv", ["run_product_e2e.py"])
        for globals_ in (full, dedicated):
            monkeypatch.setitem(globals_, "ROOT", source)
            monkeypatch.setitem(globals_, "process_environment", process_environment)
        for name, value in {"FRONTEND_ROOT": shared, "prepare_runtime": prepare, "product_servers": servers,
                            "tempfile": SimpleNamespace(TemporaryDirectory=owned_temporary_directory),
                            "_verify_http_error_evidence_contract": lambda: None, "_reset_mutable_runtime": reset,
                            "_run_single_iteration": iteration, "_bounded_log_summary": lambda path: [],
                            "_run_reader_inline_image_iteration": image_iteration,
                            "verify_backend_restart_persistence": restart}.items():
            monkeypatch.setitem(full, name, value)
        monkeypatch.setitem(dedicated, "runtime_module", lambda: full)
        monkeypatch.setitem(dedicated, "source_bindings", lambda **kwargs: {"source": "synthetic", "build": "synthetic"})
        monkeypatch.setitem(dedicated, "seed_graph", lambda *args: None)
        monkeypatch.setitem(dedicated, "run_cases", run_cases)

        def invoke(entry):
            try:
                return full["main"]() if entry == "full" else dedicated["main"]([])
            except KeyboardInterrupt:
                return 130

        return SimpleNamespace(full=full, dedicated=dedicated, helper=helper, environment=environment,
                               events=events, observations=observations, paths=paths, resources=resources,
                               runtimes=runtimes, resets=resets, image_calls=image_calls,
                               invoke=invoke, observe=observe, build_enter=build_enter, handler=handler,
                               prior_handler=prior_handler,
                               parent_restored=lambda: dict(helper.os.environ) == previous_environment)
    return arrange


@pytest.mark.parametrize("entry", ["full", "dedicated"])
@pytest.mark.parametrize("port", [8000, 18000])
@pytest.mark.parametrize("outcome", ["success", "startup_error", "interrupt"])
def test_cli_driver_browser_environment_lifetime(cli_lifetime, capsys, entry, port, outcome):
    harness = cli_lifetime(port, outcome)
    code = harness.invoke(entry)
    output = capsys.readouterr()
    result = json.loads(output.out) if output.out else None
    assert SENTINEL not in output.out + output.err
    assert not output.err
    assert harness.parent_restored(), "CLI did not restore the exact parent environment"
    assert harness.handler["current"] is harness.prior_handler
    assert not harness.resources and all(not path.exists() for path in harness.paths)
    assert {"driver_enter", "browser_launch", "driver_teardown"} <= set(harness.events)
    if outcome != "startup_error":
        assert {"suite_body", "browser_teardown"} <= set(harness.events)
    failures = [(item["stage"], key) for item in harness.observations
                for key in ("private_absent", "configured_retained", "scope_active") if not item[key]]
    assert not failures, f"CLI environment lifetime failed: {failures}"
    if outcome == "success":
        assert code == 0 and result["status"] == "PASS"
    else:
        assert code != 0 and (result is None or result["status"] != "PASS")


def run_full_image_contract(harness, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_product_e2e.py", "--repeat", "3"])
    code = harness.invoke("full")
    output = capsys.readouterr()
    assert SENTINEL not in output.out + output.err and not output.err
    assert harness.parent_restored(), "image phase did not restore the exact parent environment"
    assert harness.handler["current"] is harness.prior_handler
    harness.prior_handler.assert_not_called()
    assert not harness.resources and all(not path.exists() for path in harness.paths)
    assert all(item["private_absent"] and item["configured_retained"] and item["scope_active"]
               for item in harness.observations)
    result = json.loads(output.out)
    assert len(result["runs"]) == 3, "image or cleanup failure discarded the original runs"
    assert all(row["status"] == "PASS" and row["checks"] == {"synthetic": True} for row in result["runs"])
    assert result["restart_persistence"] == {"status": "PASS"}
    return code, result


@pytest.mark.parametrize("port", [8000, 18000])
def test_image_profile_follows_original_cleanup_with_three_independent_repeats(cli_lifetime, monkeypatch, capsys, port):
    harness = cli_lifetime(port)
    code, result = run_full_image_contract(harness, monkeypatch, capsys)
    assert code == 0 and result["status"] == "PASS"
    phases = ["original_prepare", "original_server_enter", "suite_body", "original_server_teardown",
              "original_restart", "original_temp_teardown", "image_prepare", "image_server_enter",
              "image_body", "image_browser_teardown", "image_server_teardown", "image_temp_teardown",
              "frontend_teardown"]
    positions = [harness.events.index(phase) for phase in phases]
    assert positions == sorted(positions), "image profile started before original cleanup completed"
    assert [phase for phase, _ in harness.runtimes] == ["original", "image"]
    assert [phase for phase, _ in harness.resets] == ["original"] * 3 + ["image"] * 3
    assert [call["iteration"] for call in harness.image_calls] == [1, 2, 3]
    for key in ("blocked_external", "console_errors", "page_errors"):
        assert len({id(call[key]) for call in harness.image_calls}) == 3
    assert harness.events.count("image_context_enter") == 6
    assert harness.events.count("image_context_teardown") == 6
    profile = result["reader_inline_image_profile"]
    assert profile["status"] == "PASS" and profile["repeat_count"] == 3
    assert profile["errors"] == []
    assert profile["fixture_stable"] and profile["runtime_removed"]
    assert profile["browser_version"] == result["browser_version"] == "synthetic"
    assert [row["iteration"] for row in profile["runs"]] == [1, 2, 3]
    for row in profile["runs"]:
        assert row["status"] == "PASS" and row["checks"] == IMAGE_CHECKS
        assert all(row[key] == 0 for key in ("external_network_request_count", "console_error_count",
                                            "page_error_count", "unexpected_page_count"))


@pytest.mark.parametrize("port", [8000, 18000])
@pytest.mark.parametrize("failure", [
    "server_startup", "startup", "wrong_fixture", "body", "incomplete", "wrong_checks", "non_boolean", "browser_mismatch",
    "fixture_drift", "late_audit", "body_late_audit", "context_teardown", "browser_teardown",
    "server_teardown", "temp_teardown", "interrupt", "sigterm",
])
def test_image_profile_failures_never_pass_or_erase_original_evidence(cli_lifetime, monkeypatch, capsys, port, failure):
    harness = cli_lifetime(port, image_failure=failure)
    code, result = run_full_image_contract(harness, monkeypatch, capsys)
    assert code != 0 and result["status"] == "BLOCKED", failure
    profile = result["reader_inline_image_profile"]
    assert profile["runtime_removed"]
    assert profile["status"] == ("PASS" if failure == "browser_mismatch" else "BLOCKED")
    errors = "\n".join(profile["errors"])
    if failure == "browser_mismatch":
        assert "browser version mismatch" in result["error"]
    else:
        expected_error = {
            "server_startup": "synthetic_image_server_startup", "startup": "synthetic_browser_startup",
            "wrong_fixture": "fixture mismatch", "body": "synthetic_image_body",
            "incomplete": "incomplete Reader image-profile coverage",
            "wrong_checks": "incomplete Reader image-profile coverage",
            "non_boolean": "incomplete Reader image-profile coverage",
            "fixture_drift": "immutable fixture", "late_audit": "post-cleanup audit failed",
            "body_late_audit": "synthetic_image_body", "context_teardown": "synthetic_image_context_teardown",
            "browser_teardown": "synthetic_image_browser_teardown", "server_teardown": "synthetic_image_server_teardown",
            "temp_teardown": "synthetic_image_temp_teardown", "interrupt": "KeyboardInterrupt", "sigterm": "KeyboardInterrupt",
        }[failure]
        assert expected_error in errors, "failure was blocked for an unrelated reason"
    if failure in {"startup", "server_startup", "wrong_fixture"}:
        assert not harness.image_calls
        if failure == "wrong_fixture":
            assert "image_server_enter" not in harness.events
    else:
        assert 1 <= len(harness.image_calls) <= 3
    if failure in {"body", "body_late_audit", "interrupt", "sigterm"}:
        assert [call["iteration"] for call in harness.image_calls] == [1, 2]
        assert profile["runs"][0]["status"] == "CHECKS_PASSED"
        assert profile["runs"][0]["checks"] == IMAGE_CHECKS
        assert profile["runs"][-1]["iteration"] == 2
        assert profile["runs"][-1]["status"] == "BLOCKED"
    if failure in {"late_audit", "body_late_audit", "context_teardown", "browser_teardown",
                   "server_teardown", "temp_teardown"}:
        last = profile["runs"][-1]
        assert last["status"] == "BLOCKED"
        assert last["console_error_count"] == len(harness.image_calls[-1]["console_errors"]) > 0
    if failure == "body_late_audit":
        assert "synthetic_image_browser_teardown" in errors
        assert "post-cleanup audit failed" in errors
    if failure == "fixture_drift":
        assert profile["fixture_stable"] is False
    if failure == "sigterm":
        assert "image_sigterm" in harness.events


@pytest.mark.parametrize("port", [8000, 18000])
def test_original_temp_cleanup_failure_prevents_image_phase_and_preserves_results(cli_lifetime, monkeypatch, capsys, port):
    harness = cli_lifetime(port, original_cleanup_failure=True)
    code, result = run_full_image_contract(harness, monkeypatch, capsys)
    assert code != 0 and result["status"] == "BLOCKED"
    assert not harness.image_calls and "image_prepare" not in harness.events
    assert "reader_inline_image_profile" not in result
    assert [phase for phase, _ in harness.runtimes] == ["original"]


@pytest.mark.parametrize("phase", ["frontend_build", "suite_body"])
def test_full_cli_sigterm_cleans_owned_build_and_suite_scopes(cli_lifetime, monkeypatch, tmp_path, capsys, phase):
    harness = cli_lifetime(18000)
    continued = []

    def terminate():
        harness.events.append("term_requested")
        harness.handler["current"](harness.full["signal"].SIGTERM, None)
        continued.append("continued_after_sigterm")

    if phase == "frontend_build":
        harness.build_enter.side_effect = terminate

    def suite(args):
        with tempfile.TemporaryDirectory(prefix="owned-suite-", dir=tmp_path) as temporary:
            harness.paths.append(Path(temporary))
            (Path(temporary) / "resource").write_text("synthetic")
            harness.observe("suite_body")
            if phase == "suite_body":
                terminate()
            return {"status": "PASS"}

    monkeypatch.setitem(harness.full, "_run_configured_suite", suite)
    code = harness.invoke("full")
    output = capsys.readouterr()
    result = json.loads(output.out) if output.out else None
    assert harness.parent_restored(), "SIGTERM path did not restore the exact environment"
    assert harness.handler["current"] is harness.prior_handler
    assert harness.paths and all(not path.exists() for path in harness.paths)
    assert not harness.resources and "frontend_teardown" in harness.events
    assert "term_requested" in harness.events
    assert not continued, "SIGTERM did not interrupt the owned CLI scope"
    harness.prior_handler.assert_not_called()
    assert code != 0 and (result is None or result["status"] != "PASS")
    assert SENTINEL not in output.out + output.err and not output.err
    assert all(item["private_absent"] and item["configured_retained"] and item["scope_active"]
               for item in harness.observations)


@pytest.mark.parametrize("timeout", [False, True])
def test_missing_process_group_still_reaps_owned_leader(check, monkeypatch, timeout):
    module = check["runtime_module"]()
    process = Mock(pid=12345)
    process.wait.side_effect = [module["subprocess"].TimeoutExpired("synthetic", 10), 0] if timeout else [0]
    process.poll.return_value = None if timeout else 0
    kill = Mock(side_effect=ProcessLookupError)
    monkeypatch.setattr(module["os"], "killpg", kill)
    module["_stop_process"](process)
    assert [call.kwargs["timeout"] for call in process.wait.call_args_list] == ([10, 5] if timeout else [10])
    assert [call.args for call in kill.call_args_list] == [
        (12345, module["signal"].SIGTERM), (12345, module["signal"].SIGKILL)]


def test_process_cleanup_timeout_after_kill_is_not_suppressed(check, monkeypatch):
    module = check["runtime_module"]()
    process = Mock(pid=12345)
    process.wait.side_effect = module["subprocess"].TimeoutExpired("synthetic", 10)
    process.poll.return_value = None
    kill = Mock()
    monkeypatch.setattr(module["os"], "killpg", kill)
    with pytest.raises(module["subprocess"].TimeoutExpired):
        module["_stop_process"](process)
    assert [call.kwargs["timeout"] for call in process.wait.call_args_list] == [10, 5]
    assert [call.args for call in kill.call_args_list] == [
        (12345, module["signal"].SIGTERM), (12345, module["signal"].SIGKILL)]


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
