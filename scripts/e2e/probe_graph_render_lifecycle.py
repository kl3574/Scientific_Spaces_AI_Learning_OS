#!/usr/bin/env python3
"""Calibrate bounded commit observation; never declare the Graph incident fixed."""

from __future__ import annotations

from contextlib import closing, contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import runpy
import tempfile


ROOT = Path(__file__).resolve().parents[2]
VERSION = "19.2.0-canary-0bdb9206-20250818"
ERRORS = {
    "none", "event_budget", "hook_cycle", "hook_budget", "effect_cycle",
    "effect_budget", "ambiguous_selector", "missing_selector", "missing_renderer",
    "missing_root", "fiber_cycle", "fiber_budget", "ambiguous_target",
    "invalid_clock", "existing_hook", "renderer_budget", "renderer_metadata",
    "capture_exception",
}


def validate_snapshot(value):
    """Validate the whole export without interpolating rejected input in errors."""
    fields = {"schema_version", "capture_error", "overflow", "coverage_incomplete",
              "error", "commit_count", "renderers", "events"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("invalid_snapshot")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or type(value["error"]) is not str or value["error"] not in ERRORS:
        raise ValueError("invalid_snapshot")
    if any(type(value[key]) is not bool for key in ("capture_error", "overflow", "coverage_incomplete")):
        raise ValueError("invalid_snapshot")
    if value["capture_error"] != value["coverage_incomplete"] or value["capture_error"] != (value["error"] != "none") or (value["overflow"] and not value["capture_error"]):
        raise ValueError("invalid_snapshot")
    if type(value["commit_count"]) is not int or not 0 <= value["commit_count"] <= 1_000_000:
        raise ValueError("invalid_snapshot")
    if not isinstance(value["renderers"], list) or len(value["renderers"]) > 4:
        raise ValueError("invalid_snapshot")
    for index, renderer in enumerate(value["renderers"], 1):
        if not isinstance(renderer, dict) or set(renderer) != {"id", "version", "package"}:
            raise ValueError("invalid_snapshot")
        if type(renderer["id"]) is not int or renderer["id"] != index:
            raise ValueError("invalid_snapshot")
        if (renderer["version"], renderer["package"]) not in ((VERSION, "react-dom"), ("unrecognized", "unrecognized")):
            raise ValueError("invalid_snapshot")
        if renderer["version"] == "unrecognized" and not value["capture_error"]:
            raise ValueError("invalid_snapshot")
    events = value["events"]
    if not isinstance(events, list) or len(events) > 512:
        raise ValueError("invalid_snapshot")
    previous = 0
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or type(event.get("present")) is not bool:
            raise ValueError("invalid_snapshot")
        required = {"sequence", "time", "renderer", "root", "present"}
        if event["present"]:
            required |= {"wrapper", "fiber", "initialized", "hidden", "selected"}
        if set(event) != required:
            raise ValueError("invalid_snapshot")
        for key in required & {"sequence", "renderer", "root", "wrapper", "fiber"}:
            if type(event[key]) is not int or not 1 <= event[key] <= 1_000_000:
                raise ValueError("invalid_snapshot")
        if event["sequence"] != index or not previous < event["sequence"] <= value["commit_count"] or event["renderer"] > len(value["renderers"]):
            raise ValueError("invalid_snapshot")
        previous = event["sequence"]
        if type(event["time"]) not in (int, float) or not math.isfinite(event["time"]) or event["time"] < 0:
            raise ValueError("invalid_snapshot")
        if event["present"] and (type(event["initialized"]) is not bool or type(event["selected"]) is not bool or event["hidden"] not in ("undefined", "true", "false")):
            raise ValueError("invalid_snapshot")
    if not value["capture_error"] and len(events) != value["commit_count"]:
        raise ValueError("invalid_snapshot")
    return value


def observation_valid(snapshot):
    return bool(snapshot and snapshot["renderers"] and not any(
        snapshot[key] for key in ("capture_error", "overflow", "coverage_incomplete")
    ) and snapshot["error"] == "none" and any(
        event["present"] for event in snapshot["events"]
    ))


def verdict(ui, observation, audit, cleanup, bindings_equal, execution_failed=False):
    if execution_failed or ui == "FAIL" or audit == "FAIL" or not cleanup or not bindings_equal:
        return "BLOCKED"
    if ui == "PASS" and observation == "VALID" and audit == "PASS":
        return "CALIBRATED"
    return "INCONCLUSIVE"


def source_bindings():
    paths = {
        "graph_view": "frontend/src/components/GraphView.tsx",
        "graph_visualization": "frontend/src/components/GraphVisualization.tsx",
        "graph_model": "frontend/src/lib/graphVisualization.ts",
        "e2e_runner": "scripts/e2e/run_product_e2e.py",
        "build": "frontend/.next/BUILD_ID",
    }
    return {key: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for key, path in paths.items()}


def execution_failure(result):
    result["execution_failed"] = True
    if result["failure_stage"] == "none":
        result["failure_stage"] = result["stage"]


@contextmanager
def execution_resource(result, manager, setup, teardown):
    """Latch the first failing phase before nested resource cleanup changes it."""
    result["stage"] = setup
    try:
        with manager as resource:
            try:
                yield resource
            except (Exception, KeyboardInterrupt):
                execution_failure(result)
                raise
            finally:
                result["stage"] = teardown
    except (Exception, KeyboardInterrupt):
        execution_failure(result)
        raise


def capture_snapshot(result, page):
    try:
        captured = validate_snapshot(page.evaluate("() => window.__scientificGraphProbe.snapshot()"))
    except Exception:
        result["capture_failed"] = True
        result["observation"] = "INCONCLUSIVE"
        return None
    result["capture"] = captured
    result["capture_stage"] = result["stage"]
    result["observation"] = "VALID" if observation_valid(captured) and any(
        event.get("selected") and event.get("initialized") for event in captured["events"]
    ) else "INCONCLUSIVE"
    return captured


def check_graph(result, page, module, errors, expect):
    try:
        result["stage"] = "initial_map"
        page.goto(module["FRONTEND_URL"] + module["ATTENTION_CONCEPT_RETURN"], wait_until="domcontentloaded")
        page.get_by_role("button", name="Knowledge context", exact=True).click()
        expect(page.get_by_test_id("graph-visualization")).to_be_visible(timeout=30_000)
        edge = page.locator('.react-flow__edge[tabindex="0"]').first
        expect(edge).to_be_visible(timeout=30_000)
        edge.focus()
        expect(edge).to_be_focused()
        edge.press("Control+k")
        dialog = page.get_by_test_id("global-search-dialog")
        expect(dialog.get_by_label("Search library")).to_be_focused()
        dialog.get_by_label("Search library").press("Escape")
        expect(dialog).to_have_count(0)
        expect(edge).to_be_focused()
        article = page.get_by_role("button", name=re.compile(r"^Article: ")).first
        expect(article).to_be_visible()
        module["_wait_for_page_requests_to_settle"](page, errors)
        result["stage"] = "initial_observation"
        try:
            page.wait_for_function("() => {const s=window.__scientificGraphProbe?.snapshot();return s && (s.capture_error || s.events.some(e=>e.present));}", timeout=5000)
        except Exception:
            capture_snapshot(result, page)
            result["observation"] = "INCONCLUSIVE"
            return
        initial = capture_snapshot(result, page)
        if not observation_valid(initial):
            return
        result["stage"] = "article_transition"
        transition = module["_declare_expected_route_transition"](
            page, destination_url=f"{module['FRONTEND_URL']}/graph?node_id=article%3A{module['ATTENTION_ARTICLE_ID']}")
        result["stage"] = "article_activation"
        result["ui"] = "RUNNING"
        article.press("Enter")
        result["stage"] = "article_url"
        page.wait_for_function("() => new URL(location.href).searchParams.get('node_id')?.startsWith('article:')")
        result["stage"] = "article_focus"
        module["_require_visible_focus"](page.locator("#graph-context-workspace"), "desktop Context region after map selection")
        result["stage"] = "article_visibility"
        expect(page.get_by_role("button", name=re.compile(r"^Selected Article: ")).first).to_be_visible(timeout=30_000)
        result["stage"] = "article_settlement"
        module["_wait_for_page_requests_to_settle"](page, errors)
        module["_complete_expected_route_transition"](page, transition)
        result["stage"] = "article_counts"
        expect(page.get_by_test_id("graph-map-counts")).to_contain_text(re.compile(r"7 nodes.*6 relationships"))
        result["ui"] = "PASS"
        result["stage"] = "final_observation"
        capture_snapshot(result, page)
    except (Exception, KeyboardInterrupt):
        execution_failure(result)
        if result["ui"] == "RUNNING":
            result["ui"] = "FAIL"
        # Preserve committed history while the failing page is still alive.
        capture_snapshot(result, page)


def main():
    result = {"schema_version": 1, "status": "INCONCLUSIVE", "incident": "OPEN_UNKNOWN",
              "observation": "INCONCLUSIVE", "ui": "NOT_RUN", "audit": "NOT_RUN",
              "stage": "setup", "runtime_removed": False, "bindings_equal": False,
              "execution_failed": False, "failure_stage": "none", "capture_failed": False}
    temporary_path = None
    before = None
    try:
        from playwright.sync_api import expect, sync_playwright

        before = source_bindings()
        module = runpy.run_path(str(ROOT / "scripts/e2e/run_product_e2e.py"), run_name="graph_probe_runtime")
        blocked = module["NetworkGuardLog"]()
        errors = module["ConsoleErrorLog"]()
        page_errors = []
        with execution_resource(result, tempfile.TemporaryDirectory(prefix="scientific-spaces-p3-039-calibration-"), "runtime_setup", "runtime_teardown") as temporary:
            temporary_path = Path(temporary)
            runtime = module["prepare_runtime"](temporary_path)
            with execution_resource(result, module["product_servers"](runtime, frontend_mode="start"), "server_setup", "server_teardown"):
                with execution_resource(result, sync_playwright(), "playwright_setup", "playwright_teardown") as playwright:
                    result["stage"] = "browser_setup"
                    browser = module["LocalOnlyBrowser"](playwright.chromium.launch(headless=True))
                    with execution_resource(result, closing(browser), "browser_setup", "browser_teardown"):
                        result["stage"] = "context_setup"
                        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN", reduced_motion="reduce")
                        with execution_resource(result, closing(context), "context_setup", "context_teardown"):
                            module["_install_network_guard"](context, blocked)
                            context.add_init_script(path=str(ROOT / "scripts/e2e/graph_render_probe.js"))
                            page = module["_new_observed_page"](context, errors, page_errors, label="graph-calibration")
                            check_graph(result, page, module, errors, expect)
                        result["stage"] = "audit"
                        unexpected = module["_unexpected_console_errors"](errors)
                        pages = module["_unexpected_context_pages"](blocked)
                        result["audit_counts"] = {"external": len(blocked), "console": len(unexpected), "page": len(page_errors), "unexpected_pages": len(pages)}
                        result["audit"] = "PASS" if not any(result["audit_counts"].values()) else "FAIL"
    except (Exception, KeyboardInterrupt):
        execution_failure(result)
        if result["ui"] == "RUNNING":
            result["ui"] = "FAIL"
    finally:
        result["runtime_removed"] = temporary_path is not None and not temporary_path.exists()
        result["stage"] = "final_bindings"
        try:
            result["bindings_equal"] = before is not None and before == source_bindings()
            if before is not None:
                result["source_sha256"] = before
        except Exception:
            execution_failure(result)
            result["bindings_equal"] = False
    result["status"] = verdict(result["ui"], result["observation"], result["audit"], result["runtime_removed"], result["bindings_equal"], result["execution_failed"])
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "CALIBRATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
