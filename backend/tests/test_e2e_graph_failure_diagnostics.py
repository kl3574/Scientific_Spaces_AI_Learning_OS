"""Offline contracts for failure-only evidence, not a graph failure reproduction."""

import ast
import json
from pathlib import Path
import re
import runpy
import traceback
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "e2e" / "run_product_e2e.py"
PREFIX = "Graph map post-assertion-failure geometry: "
SENSITIVE_SENTINEL = "synthetic-sensitive-value-must-not-enter-diagnostic-note"


@pytest.fixture(scope="module")
def runner_ast():
    return ast.parse(RUNNER.read_text(encoding="utf-8"), filename=str(RUNNER))


@pytest.fixture(scope="module")
def failure_note():
    # Load lazily, outside collection, and restore the import path afterward.
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(ROOT / "backend"))
        namespace = runpy.run_path(str(RUNNER), run_name="_graph_diagnostic_contract")
    assert callable(namespace.get("_graph_map_failure_note")), "Runner helper integration is pending"
    return namespace["_graph_map_failure_note"]


@pytest.fixture(scope="module")
def assertion_try(runner_ast):
    iteration = next(
        node for node in runner_ast.body
        if isinstance(node, ast.FunctionDef) and node.name == "_run_single_iteration"
    )
    matches = [
        node for node in ast.walk(iteration)
        if isinstance(node, ast.Try)
        and any(
            isinstance(child, ast.Constant) and child.value == "^Selected Article: "
            for statement in node.body for child in ast.walk(statement)
        )
    ]
    assert len(matches) == 1, "Expected the actual Selected Article assertion try statement"
    return matches[0]


@pytest.fixture(scope="module")
def assertion_code(assertion_try):
    # Execute the production AST itself, not a separately written try/except.
    module = ast.Module(body=[assertion_try], type_ignores=[])
    return compile(module, filename=str(RUNNER), mode="exec")


class CaptureErrorWithoutReadableMessage(RuntimeError):
    def __str__(self):
        raise AssertionError("Diagnostic capture must not inspect exception messages")


class PageStub:
    def __init__(self, snapshot=None, capture_error=None):
        self.snapshot = snapshot
        self.capture_error = capture_error
        self.evaluate_calls = []
        self.locator_calls = []
        self.first = object()

    def evaluate(self, script):
        self.evaluate_calls.append(script)
        if self.capture_error is not None:
            raise self.capture_error
        return self.snapshot

    def get_by_role(self, role, *, name):
        self.locator_calls.append((role, name.pattern, name.flags))
        assert role == "button"
        assert isinstance(name, re.Pattern)
        assert name.pattern == "^Selected Article: "
        assert name.flags == re.compile("^Selected Article: ").flags
        return self


def execute_assertion(code, page, note_helper, assertion_error=None):
    class Expectation:
        def to_be_visible(self, *, timeout):
            assert timeout == 30_000
            if assertion_error is not None:
                raise assertion_error

    def expect(locator):
        assert locator is page.first
        return Expectation()

    exec(code, {"page": page, "expect": expect, "re": re, "_graph_map_failure_note": note_helper})


def decode_note(note):
    assert note.startswith(PREFIX)

    def reject_nonfinite(token):
        pytest.fail(f"Non-finite JSON token: {token}")

    return json.loads(note[len(PREFIX):], parse_constant=reject_nonfinite)


def test_production_wrapper_is_only_the_original_assertion_and_annotation(assertion_try):
    assert len(assertion_try.body) == 1
    assert isinstance(assertion_try.body[0], ast.Expr)
    assertion = assertion_try.body[0].value
    assert isinstance(assertion, ast.Call)
    assert isinstance(assertion.func, ast.Attribute)
    assert assertion.func.attr == "to_be_visible"
    assert not assertion.args
    assert [(keyword.arg, ast.literal_eval(keyword.value)) for keyword in assertion.keywords] == [
        ("timeout", 30_000)
    ]
    assert not assertion_try.orelse
    assert not assertion_try.finalbody
    assert len(assertion_try.handlers) == 1
    handler = assertion_try.handlers[0]
    assert isinstance(handler.type, ast.Name) and handler.type.id == "AssertionError"
    assert handler.name == "error"
    assert len(handler.body) == 2
    annotation_try = handler.body[0]
    assert isinstance(annotation_try, ast.Try)
    assert len(annotation_try.body) == 1
    assert ast.unparse(annotation_try.body[0]) == "error.add_note(_graph_map_failure_note(page))"
    assert not annotation_try.orelse and not annotation_try.finalbody
    assert len(annotation_try.handlers) == 1
    annotation_handler = annotation_try.handlers[0]
    assert isinstance(annotation_handler.type, ast.Name)
    assert annotation_handler.type.id == "Exception"
    assert len(annotation_handler.body) == 1
    assert isinstance(annotation_handler.body[0], ast.Pass)
    assert isinstance(handler.body[1], ast.Raise)
    assert handler.body[1].exc is None and handler.body[1].cause is None


def test_success_path_never_invokes_capture(assertion_code):
    page = PageStub()
    helper_calls = []

    def forbidden_capture(candidate):
        helper_calls.append(candidate)
        raise AssertionError("The success path must not capture diagnostics")

    execute_assertion(assertion_code, page, forbidden_capture)
    assert len(page.locator_calls) == 1
    assert helper_calls == []
    assert page.evaluate_calls == []


@pytest.mark.parametrize(
    "case, expected_error_type",
    [
        ("geometry", None),
        ("capture", "RuntimeError"),
        ("unreadable_message", "Exception"),
        ("unserializable", "TypeError"),
        ("nan", "ValueError"),
        ("positive_infinity", "ValueError"),
        ("negative_infinity", "ValueError"),
    ],
)
def test_original_exception_and_notes_survive_capture_and_serialization_failures(
    assertion_code, failure_note, case, expected_error_type,
):
    snapshot = {"map_present": False, "node_wrapper_total": 0, "nodes": []}
    capture_error = None
    if case == "capture":
        capture_error = RuntimeError(SENSITIVE_SENTINEL)
    elif case == "unreadable_message":
        capture_error = CaptureErrorWithoutReadableMessage(SENSITIVE_SENTINEL)
    elif case == "unserializable":
        snapshot = {"synthetic_sensitive": SENSITIVE_SENTINEL, "invalid": object()}
    elif case in {"nan", "positive_infinity", "negative_infinity"}:
        invalid = {"nan": float("nan"), "positive_infinity": float("inf"), "negative_infinity": -float("inf")}
        snapshot = {"synthetic_sensitive": SENSITIVE_SENTINEL, "invalid": invalid[case]}
    page = PageStub(snapshot, capture_error)
    original = AssertionError("Selected Article is not visible")
    original.add_note("Existing diagnostic note")
    original_args = original.args
    original_message = str(original)
    helper_calls = []

    def capture(candidate):
        helper_calls.append(candidate)
        return failure_note(candidate)

    try:
        execute_assertion(assertion_code, page, capture, original)
    except AssertionError as caught:
        assert caught is original
        assert caught.args == original_args
        assert str(caught) == original_message
        assert caught.__notes__[0] == "Existing diagnostic note"
        assert len(caught.__notes__) == 2
        note = caught.__notes__[1]
        expected = snapshot if expected_error_type is None else {"capture_error_type": expected_error_type}
        assert decode_note(note) == expected
        assert SENSITIVE_SENTINEL not in note
        formatted = traceback.format_exc(limit=12)
        assert note in formatted
        assert "Existing diagnostic note" in formatted
        assert original_message in formatted
    else:
        pytest.fail("The production wrapper swallowed the original assertion")

    assert helper_calls == [page]
    assert len(page.locator_calls) == 1
    assert len(page.evaluate_calls) == 1


@pytest.mark.parametrize("capture_fails_first", [False, True])
def test_persistent_json_failure_cannot_break_fallback_or_replace_assertion(
    assertion_code, failure_note, monkeypatch, capture_fails_first,
):
    serializer_calls = []

    def broken_dumps(*args, **kwargs):
        serializer_calls.append((args, kwargs))
        raise RuntimeError(SENSITIVE_SENTINEL)

    # Replace only the runner's binding, not pytest's shared json module.
    monkeypatch.setitem(failure_note.__globals__, "json", SimpleNamespace(dumps=broken_dumps))
    page = PageStub(
        {"map_present": False},
        TimeoutError(SENSITIVE_SENTINEL) if capture_fails_first else None,
    )
    original = AssertionError("Original visibility failure")
    original.add_note("Existing diagnostic note")
    with pytest.raises(AssertionError) as caught:
        execute_assertion(assertion_code, page, failure_note, original)

    assert caught.value is original
    assert original.args == ("Original visibility failure",)
    assert str(original) == "Original visibility failure"
    assert original.__notes__[0] == "Existing diagnostic note"
    assert len(original.__notes__) == 2
    note = original.__notes__[1]
    assert decode_note(note) == {
        "capture_error_type": "TimeoutError" if capture_fails_first else "RuntimeError"
    }
    assert SENSITIVE_SENTINEL not in note
    assert len(page.evaluate_calls) == 1
    assert len(serializer_calls) == (0 if capture_fails_first else 1)


@pytest.mark.parametrize(
    "error_type",
    [
        type("Error", (Exception,), {}), TimeoutError, RuntimeError, ValueError,
        TypeError, OverflowError, RecursionError, MemoryError,
    ],
    ids=lambda error_type: error_type.__name__,
)
def test_known_capture_exception_names_are_enumerated(failure_note, error_type):
    page = PageStub(capture_error=error_type(SENSITIVE_SENTINEL))
    note = failure_note(page)
    assert decode_note(note) == {"capture_error_type": error_type.__name__}
    assert SENSITIVE_SENTINEL not in note
    assert len(page.evaluate_calls) == 1


@pytest.mark.parametrize(
    "class_name",
    [
        "UnlistedCaptureError",
        "Custom" + SENSITIVE_SENTINEL,
        "Error" + "X" * 4096 + SENSITIVE_SENTINEL,
        'Error", "private": "' + SENSITIVE_SENTINEL,
    ],
    ids=["unknown", "sensitive-custom-name", "long-name", "json-like-name"],
)
def test_unknown_capture_class_names_are_bounded_and_redacted(failure_note, class_name):
    error_type = type(class_name, (RuntimeError,), {})
    page = PageStub(capture_error=error_type(SENSITIVE_SENTINEL))
    note = failure_note(page)
    assert decode_note(note) == {"capture_error_type": "Exception"}
    assert SENSITIVE_SENTINEL not in note
    assert class_name not in note
    assert len(note) <= len(PREFIX) + 40
    assert len(page.evaluate_calls) == 1


def test_failing_add_note_cannot_replace_original_exception(assertion_code, failure_note):
    annotation_attempts = []

    class RefusesAnnotation(AssertionError):
        def add_note(self, note):
            annotation_attempts.append(note)
            raise RuntimeError(SENSITIVE_SENTINEL)

    page = PageStub({"map_present": False})
    original = RefusesAnnotation("Original visibility failure")
    BaseException.add_note(original, "Existing diagnostic note")
    try:
        execute_assertion(assertion_code, page, failure_note, original)
    except AssertionError as caught:
        assert caught is original
        assert caught.args == ("Original visibility failure",)
        assert str(caught) == "Original visibility failure"
        assert caught.__notes__ == ["Existing diagnostic note"]
        formatted = traceback.format_exc(limit=12)
        assert "Existing diagnostic note" in formatted
        assert SENSITIVE_SENTINEL not in formatted
    else:
        pytest.fail("Annotation failure swallowed the original assertion")
    assert len(annotation_attempts) == 1
    assert decode_note(annotation_attempts[0]) == {"map_present": False}
    assert len(page.evaluate_calls) == 1


def test_unexpected_helper_failure_cannot_replace_original_exception(assertion_code):
    page = PageStub()
    helper_calls = []
    original = AssertionError("Original visibility failure")
    original.add_note("Existing diagnostic note")

    def broken_helper(candidate):
        helper_calls.append(candidate)
        raise RuntimeError(SENSITIVE_SENTINEL)

    with pytest.raises(AssertionError) as caught:
        execute_assertion(assertion_code, page, broken_helper, original)
    assert caught.value is original
    assert original.args == ("Original visibility failure",)
    assert str(original) == "Original visibility failure"
    assert original.__notes__ == ["Existing diagnostic note"]
    assert helper_calls == [page]
    assert page.evaluate_calls == []


@pytest.mark.parametrize("error_type", [RuntimeError, TypeError])
def test_non_assertion_errors_are_not_intercepted(assertion_code, error_type):
    page = PageStub()
    original = error_type("Non-assertion failure")
    helper_calls = []

    def forbidden_capture(candidate):
        helper_calls.append(candidate)
        return "Unexpected capture"

    with pytest.raises(error_type) as caught:
        execute_assertion(assertion_code, page, forbidden_capture, original)
    assert caught.value is original
    assert not getattr(original, "__notes__", [])
    assert helper_calls == []
    assert page.evaluate_calls == []


@pytest.fixture(scope="module")
def projection(runner_ast):
    helper = next(
        node for node in runner_ast.body
        if isinstance(node, ast.FunctionDef) and node.name == "_graph_map_failure_note"
    )
    calls = [
        node for node in ast.walk(helper)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name) and node.func.value.id == "page"
    ]
    assert len(calls) == 1 and calls[0].func.attr == "evaluate"
    assert len(calls[0].args) == 1 and not calls[0].keywords
    assert isinstance(calls[0].args[0], ast.Constant)
    assert isinstance(calls[0].args[0].value, str)
    return calls[0].args[0].value


def test_projection_uses_whitelisted_dom_reads_and_boolean_selection(projection):
    # Source tripwires for the fixed projection; real DOM validation is separate.
    assert not re.search(
        r"\.\s*(?:innerHTML|outerHTML|innerText|value|title|cookie|headers)\b"
        r"|\[\s*['\"](?:innerHTML|outerHTML|innerText|value|title|cookie|headers)['\"]\s*\]",
        projection,
    )
    assert not re.search(r"\.\s*(?:focus|click|scrollTo|scrollIntoView|setAttribute|remove)\s*\(", projection)
    assert not re.search(
        r"\b(?:fetch|XMLHttpRequest|WebSocket|eval|Function|Promise|setTimeout|setInterval|"
        r"requestAnimationFrame|ResizeObserver|MutationObserver)\s*\(",
        projection,
    )
    selectors = re.findall(r"\.querySelector(?:All)?\(\s*(['\"])(.*?)\1\s*\)", projection)
    assert len(selectors) == len(re.findall(r"\.querySelector(?:All)?\s*\(", projection))
    assert {selector for _, selector in selectors} == {
        '[data-testid="graph-visualization"]', '[data-testid="graph-map-counts"]',
        ".react-flow__node", "[data-node-type]", "button", ".react-flow__handle",
        ".knowledge-graph-canvas", ".react-flow__viewport",
    }
    attributes = re.findall(r"\.getAttribute\(\s*['\"]([^'\"]+)['\"]\s*\)", projection)
    assert len(attributes) == len(re.findall(r"\.getAttribute\s*\(", projection))
    assert set(attributes) <= {"data-node-type", "aria-pressed"}
    assert re.search(
        r"\bselected\s*:\s*button\?\.getAttribute\(['\"]aria-pressed['\"]\)\s*===\s*['\"]true['\"]\s*,",
        projection,
    ), "Emit rendered selection as a strict boolean, not raw attribute text"
    assert projection.count("textContent") == 1
    assert re.search(
        r"querySelector\('[^']*graph-map-counts[^']*'\)\s*\?\.textContent",
        projection,
    ), "Only the numeric model-count element may have its text read"


def test_projection_schema_and_sample_are_bounded(projection):
    assert re.search(r"\.slice\(\s*0\s*,\s*25\s*\)", projection)
    assert "Number.isFinite" in projection
    assert "DOMMatrixReadOnly" in projection and "toFloat64Array" in projection
    for dimension in ("x", "y", "width", "height"):
        assert re.search(rf"\b{dimension}\s*:\s*number\(rect\.{dimension}\)", projection)
    assert re.search(r"Array\.from\(matrix\.toFloat64Array\(\),\s*number\)", projection)
    assert "..." not in projection, "Projection must not spread arbitrary objects into evidence"
    keys = set(re.findall(r"(?:\{|,)\s*([A-Za-z_]\w*)\s*:", projection))
    assert keys == {
        "x", "y", "width", "height", "display", "visibility", "type", "selected",
        "wrapper", "button", "handle_count", "document_visibility", "viewport", "scroll",
        "map_present", "model_node_count", "model_edge_count", "canvas", "flow_viewport",
        "node_wrapper_total", "node_sample_count", "node_sample_truncated", "nodes",
    }
    shorthand_keys = set(re.findall(r"(?:\{|,)\s*([A-Za-z_]\w*)\s*(?=,|\})", projection))
    assert shorthand_keys == {"transform"}
    assert re.search(r"\.includes\(type\)\s*\?\s*type\s*:\s*['\"]other['\"]", projection)
    enum_arrays = {
        target: ast.literal_eval(array)
        for array, target in re.findall(
            r"(\[[^\[\]]+\])\s*\.includes\((type|style\.visibility|document\.visibilityState)\)",
            projection,
        )
    }
    assert enum_arrays == {
        "type": ["article", "section", "concept", "formula", "zotero_item"],
        "style.visibility": ["visible", "hidden", "collapse"],
        "document.visibilityState": ["visible", "hidden"],
    }
