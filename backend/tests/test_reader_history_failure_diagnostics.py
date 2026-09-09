"""Failure-only Reader evidence contracts, not a reproduction or product repair."""

import ast
import json
from pathlib import Path
import runpy
import shutil
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/e2e/run_product_e2e.py"
PREFIX = "Guided Reader history focus failure: "
SENTINEL = "private-diagnostic-sentinel"


@pytest.fixture(scope="module")
def tree():
    return ast.parse(RUNNER.read_text(), filename=str(RUNNER))


@pytest.fixture(scope="module")
def helper():
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(ROOT / "backend"))
        patch.syspath_prepend(str(ROOT / "scripts/e2e"))
        namespace = runpy.run_path(str(RUNNER), run_name="reader_focus_diagnostic_contract")
    assert "_reader_history_focus_failure_note" in namespace
    return namespace["_reader_history_focus_failure_note"]


@pytest.fixture(scope="module")
def wrapper(tree):
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_verify_reader_fragment_focus_ownership")
    matches = [n for n in ast.walk(function) if isinstance(n, ast.Try) and len(n.body) == 1
               and ast.unparse(n.body[0]) == "expect(guided_heading).to_be_focused(timeout=30000)"]
    assert len(matches) == 1
    return matches[0]


def snapshot():
    return {"owner": "heading", "document_focused": True, "document_visibility": "visible",
            "reader_present": True, "heading_connected": True, "heading_active": True,
            "owner_pending": False, "modal_present": False, "guided_session": True,
            "hash_kind": "none", "heading_box": [0, 1, 300, 32]}


class Page:
    def __init__(self, value=None, error=None):
        self.value = snapshot() if value is None else value
        self.error = error
        self.calls = []

    def evaluate(self, script):
        self.calls.append(script)
        if self.error:
            raise self.error
        return self.value


def invoke(wrapper, page, note, failure=None):
    heading = object()

    class Expectation:
        def to_be_focused(self, *, timeout):
            assert timeout == 30_000
            if failure is not None:
                raise failure

    def expect(actual):
        assert actual is heading
        return Expectation()

    exec(compile(ast.Module(body=[wrapper], type_ignores=[]), str(RUNNER), "exec"),
         {"guided_heading": heading, "page": page, "expect": expect,
          "_reader_history_focus_failure_note": note})


def test_wrapper_preserves_exact_assertion_and_original_raise(wrapper):
    assert ast.unparse(wrapper.body[0]) == "expect(guided_heading).to_be_focused(timeout=30000)"
    assert not wrapper.orelse and not wrapper.finalbody
    assert len(wrapper.handlers) == 1
    handler = wrapper.handlers[0]
    assert ast.unparse(handler.type) == "AssertionError" and handler.name == "error"
    assert len(handler.body) == 2
    annotation = handler.body[0]
    assert isinstance(annotation, ast.Try)
    assert [ast.unparse(n) for n in annotation.body] == ["error.add_note(_reader_history_focus_failure_note(page))"]
    assert len(annotation.handlers) == 1
    assert ast.unparse(annotation.handlers[0].type) == "Exception"
    assert len(annotation.handlers[0].body) == 1 and isinstance(annotation.handlers[0].body[0], ast.Pass)
    assert isinstance(handler.body[1], ast.Raise) and handler.body[1].exc is None


def test_success_never_captures(wrapper):
    def forbidden(_page):
        raise AssertionError("success path captured evidence")

    invoke(wrapper, Page(), forbidden)


def test_original_failure_and_notes_survive(wrapper, helper):
    original = AssertionError("original failure")
    original.add_note("prior note")
    page = Page()
    with pytest.raises(AssertionError) as captured:
        invoke(wrapper, page, helper, original)
    assert captured.value is original
    assert original.__notes__[0] == "prior note"
    assert json.loads(original.__notes__[1].removeprefix(PREFIX)) == snapshot()
    assert len(page.calls) == 1


@pytest.mark.parametrize("failure", [RuntimeError(SENTINEL), ValueError(SENTINEL)])
def test_capture_failure_cannot_replace_assertion(wrapper, helper, failure):
    original = AssertionError("original")
    with pytest.raises(AssertionError) as captured:
        invoke(wrapper, Page(error=failure), helper, original)
    assert captured.value is original
    assert original.__notes__ == [PREFIX + '{"capture_status":"UNAVAILABLE"}']
    assert SENTINEL not in str(original.__notes__)


def test_serialization_failure_uses_fixed_fallback(wrapper, helper, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setitem(helper.__globals__, "json", SimpleNamespace(dumps=broken))
    original = AssertionError("original")
    with pytest.raises(AssertionError) as captured:
        invoke(wrapper, Page(), helper, original)
    assert captured.value is original
    assert original.__notes__ == [PREFIX + '{"capture_status":"UNAVAILABLE"}']


def test_annotation_failure_does_not_replace_assertion(wrapper, helper):
    class BrokenNote(AssertionError):
        def add_note(self, _note):
            raise RuntimeError(SENTINEL)

    original = BrokenNote("original")
    with pytest.raises(BrokenNote) as captured:
        invoke(wrapper, Page(), helper, original)
    assert captured.value is original


def test_unexpected_helper_failure_does_not_replace_assertion(wrapper):
    def broken(_page):
        raise RuntimeError(SENTINEL)

    original = AssertionError("original")
    with pytest.raises(AssertionError) as captured:
        invoke(wrapper, Page(), broken, original)
    assert captured.value is original


def test_non_assertion_is_not_captured(wrapper):
    def forbidden(_page):
        raise AssertionError("non-assertion captured")

    original = RuntimeError("original")
    with pytest.raises(RuntimeError) as captured:
        invoke(wrapper, Page(), forbidden, original)
    assert captured.value is original


@pytest.mark.parametrize("key,value", [
    ("private", SENTINEL), ("owner", SENTINEL), ("document_visibility", SENTINEL),
    ("hash_kind", SENTINEL), ("heading_box", [float("nan"), 0, 0, 0]),
    ("heading_box", [0, float("inf"), 0, 0]), ("heading_box", [True, 0, 0, 0]),
    ("heading_box", [0] * 5), ("heading_box", SENTINEL),
    ("document_focused", 1), ("heading_connected", None), ("owner_pending", SENTINEL),
])
def test_projection_rejects_unknown_fields_and_unbounded_values(helper, key, value):
    payload = snapshot()
    payload[key] = value
    assert helper(Page(payload)) == PREFIX + '{"capture_status":"UNAVAILABLE"}'


@pytest.mark.parametrize("payload", [[], SENTINEL, True, {}, {"owner": "heading"}])
def test_missing_fields_and_invalid_container_are_rejected(helper, payload):
    assert helper(Page(payload)) == PREFIX + '{"capture_status":"UNAVAILABLE"}'


@pytest.mark.parametrize("value", [None, [None, 0, -100, 30]])
def test_missing_or_finite_geometry_is_permitted(helper, value):
    payload = snapshot()
    payload["heading_box"] = value
    note = helper(Page(payload))
    assert len(note.encode()) <= 1536
    assert json.loads(note.removeprefix(PREFIX)) == payload


@pytest.fixture(scope="module")
def projection(tree):
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_reader_history_focus_failure_note")
    calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "evaluate"]
    assert len(calls) == 1
    return ast.literal_eval(calls[0].args[0])


@pytest.mark.parametrize("owner", ["heading", "outline_link", "outline_target", "body", "main", "dialog", "other", "unavailable", "missing_reader"])
def test_actual_projection_outputs_only_admitted_metadata(projection, helper, owner):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for projection contracts")
    harness = r"""
const vm = require('node:vm');
const mode = process.argv[1];
const element = () => ({isConnected:true, matches:()=>false, textContent:'private-diagnostic-sentinel'});
const h1 = {...element(),getBoundingClientRect:()=>({x:1,y:2,width:300,height:32})};
const outline = element(), body = element(), main = element();
const link = {...element(),matches:s=>s==='a[href="#article-outline"]'};
const other = element(), dialogChild = element();
const modal = {contains:e=>e===dialogChild};
const active = {heading:h1,outline_link:link,outline_target:outline,body,main,dialog:dialogChild,other,unavailable:null,missing_reader:body}[mode];
const reader = mode==='missing_reader'?null:{querySelector:s=>s===':scope > h1'?h1:null};
const nodes = {'article#article-start':reader,'#article-outline':outline,'#main-content':main,
  '[role="dialog"][aria-modal="true"]':modal,'article#article-start[data-shell-focus-owner="pending"]':null};
const document = {activeElement:active,body,visibilityState:'visible',hasFocus:()=>false,
  querySelector:s=>{if(!(s in nodes))throw Error('unbounded selector');return nodes[s];}};
const context = vm.createContext({document,location:{hash:'',search:'?from=%2Fsession&private=private-diagnostic-sentinel'},URLSearchParams});
const fn = vm.runInContext(process.argv[2],context);
process.stdout.write(JSON.stringify(fn()));
"""
    result = subprocess.run([node, "-e", harness, owner, projection], check=True,
                            capture_output=True, text=True, timeout=10)
    assert result.stderr == "" and SENTINEL not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["owner"] == ("body" if owner == "missing_reader" else owner)
    assert payload["document_focused"] is False
    assert payload["heading_active"] is (owner == "heading")
    assert payload["reader_present"] is (owner != "missing_reader")
    assert json.loads(helper(Page(payload)).removeprefix(PREFIX)) == payload
