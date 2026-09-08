from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import shutil
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/e2e/graph_render_probe.js"
NODE = shutil.which("node")

HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({window: {}, performance: {now: () => 1}});
if (process.argv[2] === 'existing') context.window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {original: true};
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const api = context.window.__scientificGraphProbe;
const hook = context.window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
const metadata = {version:'19.2.0-canary-0bdb9206-20250818',reconcilerVersion:'19.2.0-canary-0bdb9206-20250818',rendererPackageName:'react-dom',bundleType:0};
function fixture() {
  const dom = {};
  const ref = {current:dom};
  const id = 'article:attention-basics';
  const e1 = {tag:8,deps:[false,undefined], private:'PRIVATE_SENTINEL'};
  const e2 = {tag:8,deps:[]};
  const e3 = {tag:8,deps:[id,'knowledge','right','left']};
  e1.next=e2;e2.next=e3;e3.next=e1;
  const values=[ref,{current:dom},{current:'right'},{current:'left'},{current:'knowledge'},e1,e2,e3];
  const hooks=values.map(memoizedState=>({memoizedState,next:null}));
  hooks.forEach((h,i)=>h.next=hooks[i+1]||null);
  const host={tag:5,memoizedProps:{'data-id':id,'data-testid':'rf__node-'+id,className:'react-flow__node selected',title:'PRIVATE_SENTINEL'},ref,stateNode:dom};
  const fiber={tag:0,memoizedProps:{id},memoizedState:hooks[0],updateQueue:{lastEffect:e3},child:host};
  const visual={tag:5,memoizedProps:{'data-testid':'graph-visualization'},child:fiber};
  return {root:{current:visual},visual,fiber,host,hooks,e1,e2,e3};
}
const mode=process.argv[2];
if (mode === 'existing') {
  if (!hook.original) throw Error('original hook changed');
} else {
  if(mode==='inject-exception') Object.defineProperty(metadata,'version',{get(){throw Error('PRIVATE_SENTINEL');}});
  const renderer=hook.inject(mode==='metadata'?{version:'PRIVATE_SENTINEL'}:metadata);
  const f=fixture();
  if (mode==='ambiguous') {const other=fixture();f.fiber.sibling=other.fiber;}
  if (mode==='ambiguous-selector') f.visual.child={...f.fiber,child:f.fiber};
  if (mode==='selector') f.e3.deps[1]='PRIVATE_SENTINEL';
  if (mode==='exception') Object.defineProperty(f.root,'current',{get(){throw Error('PRIVATE_SENTINEL');}});
  if (mode==='fiber-cycle') f.host.sibling=f.fiber;
  if (mode==='fiber-budget') {let n=f.visual;for(let i=0;i<4100;i++){n.sibling={tag:5,memoizedProps:{}};n=n.sibling;}}
  if (mode==='depth-budget') {let n=f.host;for(let i=0;i<130;i++){n.child={tag:5,memoizedProps:{}};n=n.child;}}
  if (mode==='hook-cycle') f.hooks[7].next=f.hooks[0];
  if (mode==='hook-budget') {let n=f.hooks[7];for(let i=0;i<129;i++){n.next={memoizedState:null,next:null};n=n.next;}}
  if (mode==='effect-cycle') f.e2.next=f.e2;
  if (mode==='effect-budget') {let n=f.e3;for(let i=0;i<65;i++){n.next={tag:8,deps:[]};n=n.next;}n.next=f.e1;}
  hook.onCommitFiberRoot(renderer,f.root);
  if(mode==='healthy'||mode==='alternate'||mode==='remount') {
    if(mode==='alternate') {const next={...f.fiber,alternate:f.fiber};f.fiber.alternate=next;f.visual.child=next;}
    if(mode==='remount') {const replacement=fixture();f.visual.child=replacement.fiber;replacement.e1.deps[0]=true;}
    else f.e1.deps[0]=true;
    hook.onCommitFiberRoot(renderer,f.root);
  }
  if(mode==='events') for(let i=0;i<514;i++)hook.onCommitFiberRoot(renderer,f.root);
  if(mode==='renderers') for(let i=0;i<5;i++)hook.inject(metadata);
}
process.stdout.write(JSON.stringify(api.snapshot()));
"""


def run_probe(mode):
    if NODE is None:
        pytest.skip("Node is required for browser probe contracts")
    result = subprocess.run(
        [NODE, "-e", HARNESS, str(PROBE), mode],
        check=True, capture_output=True, text=True, timeout=10,
    )
    assert "PRIVATE_SENTINEL" not in result.stdout + result.stderr
    return json.loads(result.stdout)


def test_committed_snapshots_are_copied_and_content_free():
    result = run_probe("healthy")
    assert not result["capture_error"]
    assert not result["coverage_incomplete"]
    assert [item["initialized"] for item in result["events"]] == [False, True]
    assert {item["hidden"] for item in result["events"]} == {"undefined"}
    assert result["events"][0]["wrapper"] == result["events"][1]["wrapper"]
    assert result["events"][0]["fiber"] == result["events"][1]["fiber"]


@pytest.mark.parametrize("mode,same", [("alternate", True), ("remount", False)])
def test_alternate_swap_and_remount_identity(mode, same):
    result = run_probe(mode)
    assert not result["capture_error"]
    first, second = result["events"]
    assert (first["fiber"] == second["fiber"]) is same
    assert (first["wrapper"] == second["wrapper"]) is same


@pytest.mark.parametrize("mode,reason", [
    ("existing", "existing_hook"),
    ("metadata", "renderer_metadata"),
    ("ambiguous", "ambiguous_target"),
    ("ambiguous-selector", "ambiguous_selector"),
    ("selector", "missing_selector"),
    ("exception", "capture_exception"),
    ("inject-exception", "capture_exception"),
    ("fiber-cycle", "fiber_cycle"),
    ("hook-cycle", "hook_cycle"),
    ("effect-cycle", "effect_cycle"),
    ("fiber-budget", "fiber_budget"),
    ("depth-budget", "fiber_budget"),
    ("hook-budget", "hook_budget"),
    ("effect-budget", "effect_budget"),
    ("events", "event_budget"),
    ("renderers", "renderer_budget"),
])
def test_incomplete_capture_is_latched_without_sensitive_output(mode, reason):
    result = run_probe(mode)
    assert result["capture_error"] and result["coverage_incomplete"]
    assert result["error"] == reason
    assert result["overflow"] is ("budget" in reason)
    assert len(result["events"]) <= 512


@pytest.fixture
def python_probe():
    return runpy.run_path(str(ROOT / "scripts/e2e/probe_graph_render_lifecycle.py"), run_name="probe_contract")


def empty_snapshot():
    return {"schema_version": 1, "capture_error": False, "overflow": False,
            "coverage_incomplete": False, "error": "none", "commit_count": 0,
            "renderers": [], "events": []}


def test_missing_registration_never_calibrates(python_probe):
    value = python_probe["validate_snapshot"](empty_snapshot())
    assert not python_probe["observation_valid"](value)


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("error", "PRIVATE_SENTINEL"),
    ("unknown", "PRIVATE_SENTINEL"), ("capture_error", "PRIVATE_SENTINEL"),
    ("overflow", True), ("coverage_incomplete", True), ("commit_count", 1),
    ("commit_count", True), ("events", ["PRIVATE_SENTINEL"]),
    ("renderers", [{"id": 1, "version": "PRIVATE_SENTINEL", "package": "react-dom"}]),
])
def test_export_rejects_unknown_or_incomplete_values(python_probe, field, value):
    snapshot = empty_snapshot()
    snapshot[field] = value
    with pytest.raises(ValueError, match="^invalid_snapshot$") as error:
        python_probe["validate_snapshot"](snapshot)
    assert "PRIVATE_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("mode", ["healthy", "alternate", "remount", "exception", "events", "metadata"])
def test_js_export_satisfies_whole_output_contract(python_probe, mode):
    snapshot = run_probe(mode)
    assert python_probe["validate_snapshot"](snapshot) == snapshot


@pytest.mark.parametrize("ui,observation,audit,cleanup,binding,expected", [
    ("FAIL", "INCONCLUSIVE", "PASS", True, True, "BLOCKED"),
    ("PASS", "INCONCLUSIVE", "PASS", True, True, "INCONCLUSIVE"),
    ("NOT_RUN", "VALID", "PASS", True, True, "INCONCLUSIVE"),
    ("PASS", "VALID", "FAIL", True, True, "BLOCKED"),
    ("PASS", "VALID", "PASS", False, True, "BLOCKED"),
    ("PASS", "VALID", "PASS", True, False, "BLOCKED"),
    ("PASS", "VALID", "PASS", True, True, "CALIBRATED"),
])
def test_ui_audit_and_observation_verdicts_remain_separate(python_probe, ui, observation, audit, cleanup, binding, expected):
    assert python_probe["verdict"](ui, observation, audit, cleanup, binding) == expected


def test_cli_failure_output_never_contains_exception_text(python_probe, monkeypatch, capsys):
    def fail_binding():
        raise RuntimeError("PRIVATE_SENTINEL")

    monkeypatch.setitem(python_probe["main"].__globals__, "source_bindings", fail_binding)
    assert python_probe["main"]() == 2
    output = capsys.readouterr()
    assert "PRIVATE_SENTINEL" not in output.out + output.err
    result = json.loads(output.out)
    assert result["status"] == "BLOCKED"
    assert result["ui"] == "NOT_RUN"
    assert result["incident"] == "OPEN_UNKNOWN"


def test_missing_commit_is_rejected_even_without_failure_flags(python_probe):
    snapshot = run_probe("healthy")
    snapshot["events"].pop(0)
    with pytest.raises(ValueError, match="^invalid_snapshot$"):
        python_probe["validate_snapshot"](snapshot)


@pytest.fixture
def run_cli(python_probe, monkeypatch, capsys):
    """Exercise real orchestration with no servers, browser or network."""
    def run(mode):
        calls = []
        state = {"visibility_failed": False}

        def fail():
            raise RuntimeError("PRIVATE_SENTINEL")

        class Locator:
            def __init__(self, name=""):
                self.name = name
                self.first = self

            def click(self):
                calls.append("click")

            def focus(self):
                calls.append("focus")

            def press(self, key):
                calls.append("press:" + key)

            def get_by_label(self, name):
                return Locator(name)

        class Assertion:
            def __init__(self, locator):
                self.locator = locator

            def to_be_visible(self, **kwargs):
                if self.locator.name == "^Selected Article: ":
                    calls.append("visibility")
                    assert kwargs == {"timeout": 30_000}
                    if mode.startswith("visibility_failure"):
                        state["visibility_failed"] = True
                        fail()

            def to_be_focused(self):
                pass

            def to_have_count(self, count):
                pass

            def to_contain_text(self, pattern):
                calls.append("counts")

        class Page:
            def goto(self, *args, **kwargs):
                pass

            def get_by_role(self, role, name, **kwargs):
                return Locator(getattr(name, "pattern", name))

            def get_by_test_id(self, name):
                return Locator(name)

            def locator(self, name):
                return Locator(name)

            def wait_for_function(self, *args, **kwargs):
                pass

            def evaluate(self, script):
                calls.append("capture")
                if state["visibility_failed"] and mode == "visibility_failure_capture_error":
                    fail()
                value = empty_snapshot()
                value["commit_count"] = 1
                value["renderers"] = [{"id": 1, "version": python_probe["VERSION"], "package": "react-dom"}]
                value["events"] = [{"sequence": 1, "time": 1, "renderer": 1,
                    "root": 1, "present": True, "wrapper": 2, "fiber": 3,
                    "initialized": True, "hidden": "undefined", "selected": True}]
                return value

        class Context:
            def add_init_script(self, **kwargs):
                pass

            def close(self):
                calls.append("context_teardown")
                if mode == "context_teardown":
                    fail()

        class Browser:
            def new_context(self, **kwargs):
                return Context()

            def close(self):
                calls.append("browser_teardown")
                if mode == "browser_teardown":
                    fail()

        @contextmanager
        def resource(name, value):
            try:
                yield value
            finally:
                calls.append(name)
                if mode == name:
                    fail()

        helpers = {
            "NetworkGuardLog": list, "ConsoleErrorLog": list,
            "prepare_runtime": lambda path: path,
            "product_servers": lambda *a, **k: resource("server_teardown", None),
            "LocalOnlyBrowser": lambda browser: browser,
            "_install_network_guard": lambda *a: None,
            "_new_observed_page": lambda *a, **k: Page(),
            "_wait_for_page_requests_to_settle": lambda *a: None,
            "_declare_expected_route_transition": lambda *a, **k: object(),
            "_complete_expected_route_transition": lambda *a: None,
            "_require_visible_focus": lambda *a: None,
            "_unexpected_console_errors": lambda log: log,
            "_unexpected_context_pages": lambda log: log,
            "FRONTEND_URL": "http://127.0.0.1:3000",
            "ATTENTION_CONCEPT_RETURN": "/graph?node_id=concept%3Aattention",
            "ATTENTION_ARTICLE_ID": "attention-basics",
        }
        import playwright.sync_api

        monkeypatch.setattr(playwright.sync_api, "expect", Assertion)
        monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: resource(
            "playwright_teardown", SimpleNamespace(chromium=SimpleNamespace(launch=lambda **k: Browser()))))
        globals_ = python_probe["main"].__globals__
        monkeypatch.setitem(globals_, "source_bindings", lambda: {"build": "a" * 64})
        monkeypatch.setitem(globals_, "runpy", SimpleNamespace(run_path=lambda *a, **k: helpers))
        exit_code = python_probe["main"]()
        output = capsys.readouterr()
        assert "PRIVATE_SENTINEL" not in output.out + output.err
        assert output.err == ""
        return exit_code, json.loads(output.out), calls

    return run


@pytest.mark.parametrize("stage", ["context_teardown", "browser_teardown", "playwright_teardown", "server_teardown"])
def test_teardown_failure_after_ui_success_blocks_calibration(run_cli, stage):
    code, result, calls = run_cli(stage)
    assert code == 2
    assert result["status"] == "BLOCKED"
    assert result["ui"] == "PASS"
    assert result["runtime_removed"]
    assert result["execution_failed"]
    assert result["failure_stage"] == stage
    assert "browser_teardown" in calls


@pytest.mark.parametrize("mode,capture_failed", [
    ("visibility_failure", False), ("visibility_failure_capture_error", True),
])
def test_visibility_failure_captures_before_close_without_erasing_ui_failure(run_cli, mode, capture_failed):
    code, result, calls = run_cli(mode)
    assert code == 2 and result["status"] == "BLOCKED"
    assert result["ui"] == "FAIL"
    assert result["failure_stage"] == "article_visibility"
    assert result["capture_failed"] is capture_failed
    assert calls.index("visibility") < len(calls) - 1 - calls[::-1].index("capture") < calls.index("context_teardown")
    if not capture_failed:
        assert result["capture"]["events"]
        assert result["observation"] == "VALID"
    else:
        assert result["observation"] == "INCONCLUSIVE"
    assert result["runtime_removed"]


def test_successful_cli_requires_observation_ui_audit_and_cleanup(run_cli):
    code, result, calls = run_cli("success")
    assert code == 0 and result["status"] == "CALIBRATED"
    assert result["ui"] == "PASS" and result["observation"] == "VALID"
    assert result["audit"] == "PASS" and result["runtime_removed"]
    assert not result["execution_failed"] and not result["capture_failed"]
    assert result["failure_stage"] == "none"
    assert calls.count("capture") == 2
