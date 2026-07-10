#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test full-corpus tutor frontend behavior in a local-only mode.")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = run_smoke(args.frontend_url, args.api_url, mode=args.mode)
    except Exception as exc:  # pragma: no cover - exercised by the runtime smoke itself
        result = {
            "status": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


def run_smoke(frontend_url: str, api_url: str, *, mode: str = "fixture") -> dict[str, object]:
    if mode == "live":
        return _run_live_smoke(frontend_url, api_url)
    if mode != "fixture":
        raise ValueError(f"unsupported smoke mode: {mode}")
    return _run_fixture_smoke(frontend_url, api_url)


def _run_fixture_smoke(frontend_url: str, api_url: str) -> dict[str, object]:
    parsed_frontend = urlparse(frontend_url)
    parsed_api = urlparse(api_url)
    allowed_hosts = {
        "localhost",
        "127.0.0.1",
        "::1",
        parsed_frontend.hostname,
        parsed_api.hostname,
    }

    route_calls: list[str] = []
    blocked_requests: list[str] = []
    console_errors: list[str] = []
    checks: dict[str, bool] = {}

    state: dict[str, object] = {
        "ask_calls": 0,
        "quiz_calls": 0,
        "quiz_topic": None,
        "sessions_calls": 0,
        "fail_next_ask": True,
    }

    def safe_profile(_request) -> dict[str, object]:
        response: dict[str, object] = {"answer": "", "mode": "explain", "sources": [], "graph_context": {}, "zotero_context": [], "follow_up_questions": [], "refusal_reason": None}
        return response

    def tutor_ask_payload(body: dict[str, object]) -> dict[str, object]:
        mode = str(body.get("mode", "explain"))
        question = str(body.get("question", "")).lower()

        if mode == "derive":
            if "refuse" in question:
                return {
                    "answer": "",
                    "mode": "derive",
                    "sources": [],
                    "graph_context": {"nodes": [], "edges": []},
                    "zotero_context": [],
                    "follow_up_questions": [],
                    "refusal_reason": "insufficient_formula_sources",
                    "selection_summary": {
                        "candidate_count": 9,
                        "selected_article_count": 0,
                        "selected_chunk_count": 0,
                        "graph_node_count": 0,
                        "graph_edge_count": 0,
                        "graph_latency_ms": 0.0,
                        "graph_error_code": None,
                        "context_character_count": 0,
                        "estimated_token_count": 0,
                        "truncated": True,
                        "supplement_omitted_count": 0,
                    },
                    "evidence_summary": {
                        "source_count": 0,
                        "article_count": 0,
                        "refusal_reason": "insufficient_formula_evidence",
                        "has_formula_evidence": False,
                        "has_definition_evidence": False,
                        "has_answerable_evidence": False,
                        "source_schema_valid": True,
                        "unsupported_or_out_of_scope": False,
                    },
                }

            return {
                "answer": "Derive mode completed with bounded local steps and no unsupported inference.",
                "mode": "derive",
                "sources": [
                    {
                        "source_type": "article_chunk",
                        "source_id": "attention-001:0",
                        "title": "Derivation source",
                        "url": "https://spaces.ac.cn/archives/6508",
                        "section_title": "Derivation",
                        "chunk_index": 0,
                        "evidence": "balanced formula delimiters",
                        "metadata": {
                            "article_id": "attention-001",
                        },
                    },
                    {
                        "source_type": "article_chunk",
                        "source_id": "attention-001:0",
                        "title": "Duplicate source",
                        "url": "https://spaces.ac.cn/archives/6508",
                        "section_title": "Derivation",
                        "chunk_index": 0,
                        "evidence": "duplicate",
                        "metadata": {
                            "article_id": "attention-001",
                        },
                    },
                    {
                        "source_type": "graph_node",
                        "source_id": "concept:attention",
                        "title": "Graph context",
                        "url": "file:///home/local/article.md",
                        "section_title": "Graph provenance",
                        "chunk_index": None,
                        "evidence": "not used",
                        "metadata": {},
                    },
                ],
                "graph_context": {"nodes": [{"node_id": "concept:attention"}], "edges": [{"source": "a", "target": "b"}]},
                "zotero_context": [],
                "follow_up_questions": ["可否给出更短的证明？"],
                "refusal_reason": None,
                "selection_summary": {
                    "candidate_count": 18,
                    "selected_article_count": 1,
                    "selected_chunk_count": 2,
                    "graph_node_count": 1,
                    "graph_edge_count": 1,
                    "graph_latency_ms": 1.5,
                    "graph_error_code": None,
                    "context_character_count": 900,
                    "estimated_token_count": 225,
                    "truncated": False,
                    "supplement_omitted_count": 0,
                },
                "evidence_summary": {
                    "source_count": 1,
                    "article_count": 1,
                    "refusal_reason": None,
                    "has_formula_evidence": True,
                    "has_definition_evidence": True,
                    "has_answerable_evidence": True,
                    "source_schema_valid": True,
                    "unsupported_or_out_of_scope": False,
                },
            }

        if mode == "qa":
            if "empty" in question:
                return {
                    "answer": "No direct local answer could be grounded.",
                    "mode": "qa",
                    "sources": [],
                    "graph_context": {"nodes": [], "edges": []},
                    "zotero_context": [],
                    "follow_up_questions": [],
                    "refusal_reason": None,
                    "selection_summary": {
                        "candidate_count": 4,
                        "selected_article_count": 0,
                        "selected_chunk_count": 0,
                        "graph_node_count": 0,
                        "graph_edge_count": 0,
                        "graph_latency_ms": 0.0,
                        "graph_error_code": None,
                        "context_character_count": 0,
                        "estimated_token_count": 0,
                        "truncated": False,
                        "supplement_omitted_count": 0,
                    },
                    "evidence_summary": {
                        "source_count": 0,
                        "article_count": 0,
                        "has_formula_evidence": False,
                        "has_definition_evidence": False,
                        "has_answerable_evidence": False,
                        "source_schema_valid": True,
                        "unsupported_or_out_of_scope": False,
                        "refusal_reason": "no_relevant_source",
                    },
                }

        if mode == "research":
            return {
                "answer": "Research synthesis from local corpus only.\n\n资料缺口：没有外部或最新文献覆盖。",
                "mode": "research",
                "sources": [
                    {
                        "source_type": "article_chunk",
                        "source_id": "attention-001:0",
                        "title": "Attention",
                        "url": "https://spaces.ac.cn/archives/6508",
                        "section_title": "Background",
                        "chunk_index": 0,
                        "evidence": "definition",
                        "metadata": {"article_id": "attention-001"},
                    },
                    {
                        "source_type": "article_chunk",
                        "source_id": "attention-002:0",
                        "title": "Applications",
                        "url": "https://example.com/article",
                        "section_title": "Applications",
                        "chunk_index": 0,
                        "evidence": "synthesis",
                        "metadata": {"article_id": "attention-002"},
                    },
                ],
                "graph_context": {"nodes": [{"node_id": "concept:attention"}], "edges": []},
                "zotero_context": [],
                "follow_up_questions": ["可否给出研究方向？"],
                "refusal_reason": None,
                "selection_summary": {
                    "candidate_count": 22,
                    "selected_article_count": 2,
                    "selected_chunk_count": 2,
                    "graph_node_count": 1,
                    "graph_edge_count": 0,
                    "graph_latency_ms": 1.2,
                    "graph_error_code": None,
                    "context_character_count": 1100,
                    "estimated_token_count": 275,
                    "truncated": False,
                    "supplement_omitted_count": 0,
                },
                "evidence_summary": {
                    "source_count": 2,
                    "article_count": 2,
                    "has_formula_evidence": False,
                    "has_definition_evidence": True,
                    "has_answerable_evidence": True,
                    "source_schema_valid": True,
                    "unsupported_or_out_of_scope": False,
                    "refusal_reason": None,
                },
            }

        return {
            "answer": "Explain mode answer with bounded evidence and citation-safe links.",
            "mode": "explain",
            "sources": [
                {
                    "source_type": "article_chunk",
                    "source_id": "attention-001:0",
                    "title": "Attention intro",
                    "url": "https://spaces.ac.cn/archives/6508",
                    "section_title": "Introduction",
                    "chunk_index": 0,
                    "evidence": "intro",
                    "metadata": {"article_id": "attention-001"},
                },
                {
                    "source_type": "article_chunk",
                    "source_id": "attention-001:0",
                    "title": "Attention duplicate",
                    "url": "file:///home/local/article.md",
                    "section_title": "Introduction",
                    "chunk_index": 0,
                    "evidence": "intro duplicate",
                    "metadata": {"article_id": "attention-001"},
                },
                {
                    "source_type": "article_chunk",
                    "source_id": "attention-002:0",
                    "title": "Attention detail",
                    "url": "https://example.com/article",
                    "section_title": "Overview",
                    "chunk_index": 0,
                    "evidence": "detail",
                    "metadata": {"article_id": "attention-002"},
                },
                {
                    "source_type": "graph_node",
                    "source_id": "concept:attention",
                    "title": "Attention graph",
                    "url": None,
                    "section_title": None,
                    "chunk_index": None,
                    "evidence": "graph",
                    "metadata": {},
                },
                {
                    "source_type": "graph_edge",
                    "source_id": "edge:attention-related",
                    "title": "mentions",
                    "url": None,
                    "section_title": None,
                    "chunk_index": None,
                    "evidence": "bounded relationship",
                    "metadata": {},
                },
            ],
            "graph_context": {"nodes": [{"node_id": "concept:attention"}], "edges": []},
            "zotero_context": [],
            "follow_up_questions": ["What is attention?”", "Can you compare with convolution?"],
            "refusal_reason": None,
            "selection_summary": {
                "candidate_count": 16,
                "selected_article_count": 2,
                "selected_chunk_count": 3,
                "graph_node_count": 1,
                "graph_edge_count": 1,
                "graph_latency_ms": 1.1,
                "graph_error_code": None,
                "context_character_count": 1100,
                "estimated_token_count": 275,
                "truncated": True,
                "supplement_omitted_count": 2,
            },
            "evidence_summary": {
                "source_count": 3,
                "article_count": 2,
                "has_answerable_evidence": True,
                "has_formula_evidence": False,
                "has_definition_evidence": True,
                "source_schema_valid": True,
                "unsupported_or_out_of_scope": False,
                "refusal_reason": None,
            },
        }

    def tutor_quiz_payload() -> dict[str, object]:
        return {
            "questions": [
                {
                    "question": "What is attention?",
                    "options": ["Memory", "Attention", "Convolution", "Pool"],
                    "correct_answer": "Attention",
                    "explanation": "Attention assigns weights by relevance.",
                    "sources": [
                        {
                            "source_type": "article_chunk",
                            "source_id": "attention-001:0",
                            "title": "Attention quiz source",
                            "url": "https://spaces.ac.cn/archives/6508",
                            "section_title": "Definition",
                            "chunk_index": 0,
                            "evidence": "quiz evidence",
                            "metadata": {"article_id": "attention-001"},
                        }
                    ],
                },
                {
                    "question": "Which operation normalizes alignment scores?",
                    "options": ["ReLU", "Softmax", "LayerNorm", "Dropout"],
                    "correct_answer": "Softmax",
                    "explanation": "Softmax is used in alignment normalization.",
                    "sources": [
                        {
                            "source_type": "article_chunk",
                            "source_id": "attention-002:1",
                            "title": "Attention math source",
                            "url": "https://example.com/article",
                            "section_title": "Formulas",
                            "chunk_index": 1,
                            "evidence": "quiz evidence",
                            "metadata": {"article_id": "attention-002"},
                        }
                    ],
                },
            ],
            "total": 2,
        }

    def route_handler(route: Route) -> None:
        request = route.request
        if request.resource_type == "image" and request.url.startswith("data:"):
            route.continue_()
            return

        parsed = urlparse(request.url)
        if parsed.hostname not in allowed_hosts:
            blocked_requests.append(request.url)
            route.abort("blockedbyclient")
            return

        path = parsed.path or ""

        if path == "/tutor/ask":
            route_calls.append(request.url)
            state["ask_calls"] = int(state.get("ask_calls", 0)) + 1
            if state.get("fail_next_ask"):
                state["fail_next_ask"] = False
                route.fulfill(
                    status=500,
                    content_type="application/json",
                    body=json.dumps({"detail": "simulated failure"}),
                )
                return

            body = request.post_data_json or {}
            payload = tutor_ask_payload(body)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
            return

        if path == "/tutor/quiz":
            route_calls.append(request.url)
            state["quiz_calls"] = int(state.get("quiz_calls", 0)) + 1
            body = request.post_data_json or {}
            state["quiz_topic"] = body.get("topic")
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(tutor_quiz_payload()),
            )
            return

        if path == "/tutor/sessions":
            state["sessions_calls"] = int(state.get("sessions_calls", 0)) + 1
            route_calls.append(request.url)
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"items": [], "total": 0}),
            )
            return

        route.continue_()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.route("**/*", route_handler)

        page.goto(f"{frontend_url.rstrip('/')}/tutor", wait_until="domcontentloaded")

        checks["five_modes_present"] = (
            page.get_by_role("button", name=re.compile(r"^(explain|derive|qa|quiz|research)$")).count() == 5
        )

        page.get_by_placeholder("Optional Article ID").wait_for()
        checks["article_and_node_blank_default"] = (
            page.get_by_placeholder("Optional Article ID").input_value() == ""
            and page.get_by_placeholder("Optional concept:attention").input_value() == ""
        )

        checks["loading_and_retry_state"] = _run_loading_and_retry(page)

        # Derive success and derive refusal path.
        page.get_by_role("button", name="derive").click()
        page.get_by_placeholder("Ask a question").fill("Show a complete derivation")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_text("Derive mode completed").wait_for(timeout=30_000)
        checks["derive_success"] = page.get_by_text("Derive mode completed").is_visible()

        page.get_by_placeholder("Ask a question").fill("Please refuse derivation")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Refusal").wait_for(timeout=30_000)
        checks["derive_refusal"] = page.get_by_text("当前资料不足以完整推导。").is_visible()

        # QA path with empty source edge case.
        page.get_by_role("button", name="qa").click()
        page.get_by_placeholder("Ask a question").fill("Need empty response")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_text("未返回来源。").wait_for(timeout=30_000)
        checks["qa_empty_state"] = page.get_by_text("未返回来源。").is_visible()

        # Quiz path: per-question sources.
        page.get_by_role("button", name="quiz").click()
        quiz_prompt = "attention prompt submitted as quiz topic"
        quiz_prompt_input = page.get_by_placeholder("Prompt for quiz topic")
        checks["single_quiz_prompt_control"] = (
            quiz_prompt_input.count() == 1
            and page.get_by_placeholder("Optional: e.g., attention").count() == 0
        )
        quiz_prompt_input.fill(quiz_prompt)
        page.get_by_role("button", name="Generate quiz").click()
        page.get_by_role("heading", name="Quiz").wait_for(timeout=30_000)
        page.get_by_text("题目来源").first.wait_for(timeout=30_000)
        checks["quiz_with_per_question_sources"] = page.get_by_text("题目来源").count() >= 2
        checks["quiz_prompt_submitted_as_topic"] = state.get("quiz_topic") == quiz_prompt

        # Research path and evidence gap callouts.
        page.get_by_role("button", name="research").click()
        page.get_by_placeholder("Ask a question").fill("attention synthesis")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_text(re.compile(r"Research synthesis from local corpus only")).wait_for(timeout=30_000)
        checks["research_local_only_state"] = page.get_by_text(
            "Research 结果仅基于本地语料证据，不能据此推断外部文献覆盖情况。"
        ).is_visible()
        checks["research_evidence_gap_state"] = page.get_by_text(re.compile(r"资料缺口：没有外部或最新文献覆盖")).is_visible()

        # Explain path: bounded source rendering and safe links.
        page.get_by_role("button", name="explain").click()
        page.get_by_placeholder("Ask a question").fill("What is attention?")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_text("Explain mode answer with bounded evidence and citation-safe links.").wait_for(timeout=30_000)

        source_rows = page.get_by_text("Open original source")
        safe_link_count = source_rows.count()
        checks["safe_links"] = safe_link_count >= 1

        visible_body = page.locator("body").inner_text()
        checks["no_file_or_local_path_text"] = not re.search(
            r"file://|/home/|/tmp/|C:\\\\",
            visible_body,
            re.I,
        )

        # Bound preview + expand and overflow checks.
        expand = page.get_by_role("button", name=re.compile(r"展开另外 \d+ 条已返回来源"))
        checks["bounded_source_expandable"] = expand.count() == 1
        if checks["bounded_source_expandable"]:
            expand.click()
            collapse = page.get_by_role("button", name=re.compile(r"收起来源"))
            checks["bounded_source_collapsible"] = collapse.count() == 1
            if checks["bounded_source_collapsible"]:
                collapse.click()
                checks["bounded_source_collapses"] = expand.count() == 1
        else:
            checks["bounded_source_collapsible"] = False
            checks["bounded_source_collapses"] = False
        checks["no_external_network_requests"] = len(blocked_requests) == 0
        checks["desktop_no_overflow"] = _no_horizontal_overflow(page)

        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_text("Explain mode answer with bounded evidence and citation-safe links.").wait_for()
        checks["mobile_no_overflow"] = _no_horizontal_overflow(page)
        checks["requests_hit_api_boundaries"] = (
            state.get("ask_calls", 0) >= 1
            and state.get("quiz_calls", 0) >= 1
            and state.get("sessions_calls", 0) >= 1
        )

        browser_version = browser.version
        console_version = _unexpected_console_errors(console_errors)
        browser.close()

    return {
        "status": "PASS" if all(checks.values()) and len(blocked_requests) == 0 and not console_version else "BLOCKED",
        "mode": "fixture",
        "browser_version": browser_version,
        "checks": checks,
        "blocked_external_requests": blocked_requests,
        "api_request_count": int(state.get("ask_calls", 0)) + int(state.get("quiz_calls", 0)) + int(state.get("sessions_calls", 0)),
        "external_network_request_count": len(blocked_requests),
        "console_error_count": len(console_version),
        "console_errors": console_version,
        "route_error_count": len(route_calls),
    }


def _run_live_smoke(frontend_url: str, api_url: str) -> dict[str, object]:
    parsed_frontend = urlparse(frontend_url)
    parsed_api = urlparse(api_url)
    allowed_hosts = {"localhost", "127.0.0.1", "::1", parsed_frontend.hostname, parsed_api.hostname}
    blocked_requests: list[str] = []
    console_errors: list[str] = []
    checks: dict[str, bool] = {}

    def local_only(route: Route) -> None:
        request = route.request
        parsed = urlparse(request.url)
        if parsed.hostname not in allowed_hosts:
            blocked_requests.append(request.url)
            route.abort("blockedbyclient")
            return
        route.continue_()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.route("**/*", local_only)

        health = page.request.get(f"{api_url.rstrip('/')}/health")
        checks["backend_health"] = health.status == 200 and health.json().get("status") == "ok"
        page.goto(f"{frontend_url.rstrip('/')}/tutor", wait_until="domcontentloaded")
        checks["five_modes_present"] = (
            page.get_by_role("button", name=re.compile(r"^(explain|derive|qa|quiz|research)$")).count() == 5
        )

        article_input = page.get_by_placeholder("Optional Article ID")
        node_input = page.get_by_placeholder("Optional concept:attention")
        question_input = page.get_by_placeholder("Ask a question")
        article_input.wait_for()
        checks["blank_defaults"] = article_input.input_value() == "" and node_input.input_value() == ""

        node_input.fill("concept:attention")
        question_input.fill("Attention query key value")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Answer").wait_for(timeout=60_000)
        checks["explain_grounded"] = page.get_by_text("Open local article").count() >= 1
        checks["selection_summary_visible"] = page.get_by_role("heading", name="来源选择摘要").is_visible()
        context_text = page.get_by_role("heading", name="Context").locator("..").inner_text()
        checks["explicit_graph_context"] = bool(re.search(r"Graph nodes\s+[1-9]\d*", context_text))

        page.get_by_role("button", name="derive").click()
        article_input.fill("69e708f3cca249cf")
        node_input.fill("")
        question_input.fill("Attention query key value 公式推导")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Answer").wait_for(timeout=60_000)
        checks["derive_success"] = page.get_by_text(re.compile(r"分步推导说明")).is_visible()

        article_input.fill("cdfd28f5259b0436")
        question_input.fill("树莓派 Zero2W 旁路由 公式推导")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Refusal").first.wait_for(timeout=60_000)
        checks["derive_refusal"] = page.get_by_text("当前资料不足以完整推导。").is_visible()

        page.get_by_role("button", name="qa").click()
        article_input.fill("")
        question_input.fill("Transformer 为什么需要 Attention？")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Answer").wait_for(timeout=60_000)
        checks["qa_grounded"] = page.get_by_text("Open local article").count() >= 1

        page.get_by_role("button", name="quiz").click()
        page.get_by_placeholder("Prompt for quiz topic").fill("Attention")
        page.get_by_role("button", name="Generate quiz").click()
        page.get_by_role("heading", name="Quiz").wait_for(timeout=60_000)
        checks["quiz_sources"] = page.get_by_text("题目来源").count() >= 1

        page.get_by_role("button", name="research").click()
        node_input.fill("concept:attention")
        page.get_by_placeholder("Ask a question").fill("Attention Transformer 研究路线")
        page.get_by_role("button", name="Ask tutor").click()
        page.get_by_role("heading", name="Answer").wait_for(timeout=60_000)
        checks["research_local_only"] = page.get_by_text(
            "Research 结果仅基于本地语料证据，不能据此推断外部文献覆盖情况。"
        ).is_visible()
        checks["research_gap_statement"] = page.get_by_text(re.compile(r"资料缺口")).count() >= 1
        checks["safe_original_link"] = page.get_by_text("Open original source").count() >= 1

        visible_body = page.locator("body").inner_text()
        checks["no_local_path_text"] = not re.search(r"file://|/home/|/tmp/|[A-Za-z]:\\\\|\\\\\\\\", visible_body, re.I)
        checks["desktop_no_overflow"] = _no_horizontal_overflow(page)
        page.set_viewport_size({"width": 390, "height": 844})
        checks["mobile_no_overflow"] = _no_horizontal_overflow(page)
        checks["no_external_network_requests"] = not blocked_requests

        browser_version = browser.version
        unexpected_console_errors = _unexpected_console_errors(console_errors, expected_failed_requests=0)
        browser.close()

    return {
        "status": "PASS" if all(checks.values()) and not unexpected_console_errors else "BLOCKED",
        "mode": "live",
        "browser_version": browser_version,
        "checks": checks,
        "blocked_external_requests": blocked_requests,
        "external_network_request_count": len(blocked_requests),
        "console_error_count": len(unexpected_console_errors),
        "console_errors": unexpected_console_errors,
    }


def _run_loading_and_retry(page) -> bool:
    page.get_by_role("button", name="explain").click()
    page.get_by_placeholder("Ask a question").fill("Trigger retry behavior")
    page.get_by_role("button", name="Ask tutor").click()
    page.get_by_text(re.compile(r"Tutor request failed: 500")).wait_for(timeout=20_000)
    page.get_by_role("button", name="Retry").click()
    page.get_by_text("Explain mode answer with bounded evidence and citation-safe links.").wait_for(timeout=20_000)
    return True


def _no_horizontal_overflow(page) -> bool:
    return bool(
        page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth"
        )
    )


def _unexpected_console_errors(messages: list[str], *, expected_failed_requests: int = 1) -> list[str]:
    remaining_expected = expected_failed_requests
    unexpected: list[str] = []
    for message in messages:
        if remaining_expected and (
            "net::ERR_FAILED" in message
            or "status of 500" in message
        ):
            remaining_expected -= 1
            continue
        unexpected.append(message)
    return unexpected


if __name__ == "__main__":
    raise SystemExit(main())
