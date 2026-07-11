#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import Page, Route, sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the bounded full-corpus graph UI.")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = run_smoke(args.frontend_url, args.api_url)
    except Exception as exc:  # pragma: no cover - exercised by the runtime smoke itself
        result = {"status": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


def run_smoke(frontend_url: str, api_url: str) -> dict[str, object]:
    allowed_hosts = {
        "localhost",
        "127.0.0.1",
        "::1",
        urlparse(frontend_url).hostname,
        urlparse(api_url).hostname,
    }
    graph_requests: list[str] = []
    blocked_external_requests: list[str] = []
    console_errors: list[str] = []
    state = {
        "fail_next_nodes": False,
        "fail_next_subgraph": False,
        "empty_next_subgraph": False,
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        def route_request(route: Route) -> None:
            parsed = urlparse(route.request.url)
            if parsed.scheme in {"data", "blob"}:
                route.continue_()
                return
            if parsed.hostname in allowed_hosts:
                is_graph_nodes_request = parsed.path in {"/graph/nodes", "/v1.1/graph/nodes"}
                is_graph_subgraph_request = parsed.path in {"/graph/subgraph", "/v1.1/graph/subgraph"}
                if parsed.path.startswith("/graph") or parsed.path.startswith("/v1.1/graph"):
                    graph_requests.append(route.request.url)
                if state["fail_next_nodes"] and is_graph_nodes_request:
                    state["fail_next_nodes"] = False
                    route.abort("failed")
                    return
                if state["fail_next_subgraph"] and is_graph_subgraph_request:
                    state["fail_next_subgraph"] = False
                    route.abort("failed")
                    return
                if state["empty_next_subgraph"] and is_graph_subgraph_request:
                    state["empty_next_subgraph"] = False
                    route.fulfill(status=200, content_type="application/json", body='{"nodes":[],"edges":[]}')
                    return
                route.continue_()
                return
            blocked_external_requests.append(route.request.url)
            route.abort("blockedbyclient")

        page.route("**/*", route_request)
        page.goto(urljoin(frontend_url.rstrip("/") + "/", "graph"), wait_until="domcontentloaded")
        page.get_by_text(re.compile(r"Showing 1-20 of ")).wait_for(timeout=60_000)

        initial_node_request = next(
            url for url in graph_requests if urlparse(url).path in {"/graph/nodes", "/v1.1/graph/nodes"}
        )
        initial_node_request_path = urlparse(initial_node_request).path
        initial_node_request_query = parse_qs(urlparse(initial_node_request).query)
        initial_page_size = int(initial_node_request_query.get("page_size", ["20"])[0])
        checks: dict[str, bool] = {
            "initial_summary_and_20_nodes": any(
                urlparse(url).path == "/graph/summary" for url in graph_requests
            )
            and initial_page_size == 20
            and initial_node_request_path == "/v1.1/graph/nodes",
            "initial_has_no_build_action": page.get_by_role("button", name=re.compile("build", re.I)).count() == 0,
            "desktop_no_horizontal_overflow": _no_horizontal_overflow(page),
        }

        page.get_by_placeholder("Title, concept, or formula").fill("attention")
        page.get_by_label("Type").select_option("concept")
        page.get_by_role("button", name="Apply").click()
        page.get_by_text(re.compile(r"Showing 1-\d+ of ")).wait_for(timeout=30_000)
        attention_button = page.locator("button").filter(has_text=re.compile(r"^attention", re.I)).first
        attention_button.click()
        page.get_by_text("Concept Provenance", exact=True).wait_for(timeout=30_000)
        page.get_by_text("Bounded Context", exact=True).wait_for(timeout=30_000)
        page.get_by_text("Related Nodes", exact=True).wait_for(timeout=30_000)
        checks["concept_search_and_provenance"] = page.get_by_text("Concept Provenance", exact=True).is_visible()
        checks["bounded_subgraph_loaded"] = page.get_by_text("Related Nodes", exact=True).is_visible()
        checks["original_source_link"] = page.get_by_role("link", name="Original source").count() > 0
        page.get_by_role("button", name=re.compile(r"Show \d+ more returned sources")).click()
        page.get_by_role("button", name="Show fewer returned sources").wait_for(timeout=10_000)
        checks["provenance_truncation_and_expand"] = True

        state["fail_next_subgraph"] = True
        attention_button.click()
        page.get_by_role("alert").wait_for(timeout=30_000)
        page.get_by_role("button", name="Retry").click()
        page.get_by_text("Related Nodes", exact=True).wait_for(timeout=30_000)
        checks["subgraph_error_and_retry_state"] = True

        state["empty_next_subgraph"] = True
        attention_button.click()
        page.get_by_text("No related nodes or relationships were returned.", exact=True).wait_for(timeout=30_000)
        checks["subgraph_empty_state"] = True

        article_link = page.get_by_role("link", name="Open article").first
        article_href = article_link.get_attribute("href") or ""
        article_link.click()
        page.wait_for_url(re.compile(r"/articles/[^/]+$"), timeout=30_000)
        checks["article_navigation"] = article_href.startswith("/articles/") and "/articles/" in page.url

        page.goto(urljoin(frontend_url.rstrip("/") + "/", "graph"), wait_until="domcontentloaded")
        page.get_by_text(re.compile(r"Showing 1-20 of ")).wait_for(timeout=60_000)
        page.get_by_role("button", name="Next").click()
        page.get_by_text("Page 2 of", exact=False).wait_for(timeout=30_000)
        checks["pagination"] = page.get_by_text("Page 2 of", exact=False).is_visible()

        search = page.get_by_placeholder("Title, concept, or formula")
        search.fill("__p2_003_no_matching_graph_node__")
        page.get_by_role("button", name="Apply").click()
        page.get_by_text("No nodes match the current filters.", exact=True).wait_for(timeout=30_000)
        checks["empty_state"] = True

        state["fail_next_nodes"] = True
        search.fill("attention")
        page.get_by_role("button", name="Apply").click()
        page.get_by_role("alert").wait_for(timeout=30_000)
        page.get_by_role("button", name="Retry").click()
        page.get_by_text(re.compile(r"Showing 1-\d+ of ")).wait_for(timeout=30_000)
        checks["error_and_retry_state"] = True

        subgraph_requests = [
            url for url in graph_requests if urlparse(url).path in {"/graph/subgraph", "/v1.1/graph/subgraph"}
        ]
        bounded_subgraph = False
        if subgraph_requests:
            params = parse_qs(urlparse(subgraph_requests[-1]).query)
            bounded_subgraph = (
                params.get("depth") == ["1"]
                and params.get("node_limit") == ["25"]
                and params.get("edge_limit") == ["50"]
            )
        checks["bounded_request_contract"] = bounded_subgraph

        body_text = page.locator("body").inner_text()
        checks["no_local_path_exposure"] = not re.search(
            r"(?:file://|(?:^|[\"'\s:=])/(?:home|users|root|tmp|var|etc|opt|mnt|srv|data)/"
            r"|(?:^|[\"'\s:=])[A-Za-z]:[\\/])",
            body_text,
            re.I,
        )
        page.set_viewport_size({"width": 390, "height": 844})
        checks["mobile_no_horizontal_overflow"] = _no_horizontal_overflow(page)
        checks["local_only_network_policy"] = all(
            urlparse(url).hostname in allowed_hosts for url in graph_requests
        )

        unexpected_console_errors = _unexpected_console_errors(console_errors, expected_failed_requests=2)
        browser_version = browser.version
        browser.close()

    return {
        "status": "PASS" if all(checks.values()) and not unexpected_console_errors else "BLOCKED",
        "browser_version": browser_version,
        "checks": checks,
        "graph_api_request_count": len(graph_requests),
        "initial_node_page_size": initial_page_size,
        "subgraph_limits": {"depth": 1, "node_limit": 25, "edge_limit": 50},
        "blocked_external_request_count": len(blocked_external_requests),
        "external_network_request_count": 0,
        "console_error_count": len(unexpected_console_errors),
        "console_errors": unexpected_console_errors,
        "expected_console_error_count": len(console_errors) - len(unexpected_console_errors),
    }


def _no_horizontal_overflow(page: Page) -> bool:
    return bool(
        page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth "
            "&& document.body.scrollWidth <= window.innerWidth"
        )
    )


def _unexpected_console_errors(messages: list[str], *, expected_failed_requests: int) -> list[str]:
    remaining_expected = expected_failed_requests
    unexpected: list[str] = []
    for message in messages:
        if remaining_expected and "net::ERR_FAILED" in message:
            remaining_expected -= 1
            continue
        unexpected.append(message)
    return unexpected


if __name__ == "__main__":
    raise SystemExit(main())
