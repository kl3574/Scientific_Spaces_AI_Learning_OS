#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark bounded full-corpus graph API queries.")
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--graph-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--max-warm-latency-ms", type=float, default=1000.0)
    parser.add_argument("--max-cold-latency-ms", type=float, default=5000.0)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    if args.max_warm_latency_ms <= 0 or args.max_cold_latency_ms <= 0:
        parser.error("latency smoke limits must be positive")

    os.environ["SCIENTIFIC_SPACES_ARTICLE_STORE"] = str(args.article_store.resolve())
    os.environ["SCIENTIFIC_SPACES_GRAPH_FILE"] = str(args.graph_file.resolve())

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    cold_started = time.perf_counter()
    summary = client.get("/graph/summary")
    cold_summary_latency_ms = (time.perf_counter() - cold_started) * 1000
    concepts = client.get("/graph/nodes", params={"node_type": "concept", "page_size": 1}).json()
    articles = client.get("/graph/nodes", params={"node_type": "article", "page_size": 1}).json()
    if not concepts.get("items") or not articles.get("items"):
        raise RuntimeError("Graph benchmark requires at least one Concept and Article node")
    concept = concepts["items"][0]
    article = articles["items"][0]
    middle_page = max(1, math.ceil(int(summary.json()["node_count"]) / 100 / 2))
    cases = [
        ("graph_summary", "/graph/summary", {}, 200),
        ("nodes_first_page", "/graph/nodes", {"page": 1, "page_size": 100}, 200),
        ("nodes_middle_page", "/graph/nodes", {"page": middle_page, "page_size": 100}, 200),
        ("filter_article_nodes", "/graph/nodes", {"node_type": "article", "page_size": 50}, 200),
        ("filter_concept_nodes", "/graph/nodes", {"node_type": "concept", "page_size": 50}, 200),
        ("concept_search", "/graph/nodes", {"q": concept["label"], "page_size": 50}, 200),
        (
            "concept_parameter_filter",
            "/graph/nodes",
            {"concept": concept["label"], "page_size": 50},
            200,
        ),
        (
            "article_specific_nodes",
            "/graph/nodes",
            {"article_id": article["source_id"], "page_size": 100},
            200,
        ),
        (
            "one_hop_subgraph",
            "/graph/subgraph",
            {"node_id": concept["node_id"], "depth": 1, "node_limit": 100, "edge_limit": 250},
            200,
        ),
        (
            "two_hop_subgraph",
            "/graph/subgraph",
            {"node_id": concept["node_id"], "depth": 2, "node_limit": 250, "edge_limit": 500},
            200,
        ),
        ("missing_node", "/graph/nodes/not-a-real-node", {}, 404),
        ("invalid_depth", "/graph/subgraph", {"node_id": concept["node_id"], "depth": 4}, 422),
        ("excessive_page_size", "/graph/nodes", {"page_size": 101}, 422),
    ]

    case_results = [
        _benchmark_case(client, name, path, params, expected_status, repetitions=args.repetitions)
        for name, path, params, expected_status in cases
    ]
    bounded = "nodes" not in summary.json() and "edges" not in summary.json()
    bounds_respected = _response_bounds_respected(case_results)
    warm_max_latency_ms = max(float(item["latency_ms"]["max"]) for item in case_results)
    latency_guard_passed = (
        warm_max_latency_ms <= args.max_warm_latency_ms
        and cold_summary_latency_ms <= args.max_cold_latency_ms
    )
    passed = (
        bounded
        and bounds_respected
        and latency_guard_passed
        and all(item["error_count"] == 0 for item in case_results)
    )
    result = {
        "status": "PASS" if passed else "BLOCKED",
        "repetitions": args.repetitions,
        "summary_is_bounded": bounded,
        "response_bounds_respected": bounds_respected,
        "cold_summary_latency_ms": cold_summary_latency_ms,
        "warm_max_latency_ms": warm_max_latency_ms,
        "latency_guard_passed": latency_guard_passed,
        "local_smoke_limits_ms": {
            "warm_max": args.max_warm_latency_ms,
            "cold_max": args.max_cold_latency_ms,
        },
        "cases": case_results,
        "error_count": sum(int(item["error_count"]) for item in case_results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


def _response_bounds_respected(case_results: list[dict[str, Any]]) -> bool:
    limits = {
        "graph_summary": (0, 0),
        "nodes_first_page": (100, 0),
        "nodes_middle_page": (100, 0),
        "filter_article_nodes": (50, 0),
        "filter_concept_nodes": (50, 0),
        "concept_search": (50, 0),
        "concept_parameter_filter": (50, 0),
        "article_specific_nodes": (100, 0),
        "one_hop_subgraph": (100, 250),
        "two_hop_subgraph": (250, 500),
        "missing_node": (0, 0),
        "invalid_depth": (0, 0),
        "excessive_page_size": (0, 0),
    }
    return all(
        int(item["response_node_count"]) <= limits[str(item["name"])][0]
        and int(item["response_edge_count"]) <= limits[str(item["name"])][1]
        for item in case_results
    )


def _benchmark_case(
    client: Any,
    name: str,
    path: str,
    params: dict[str, Any],
    expected_status: int,
    *,
    repetitions: int,
) -> dict[str, Any]:
    latencies: list[float] = []
    error_count = 0
    response_node_count = 0
    response_edge_count = 0
    for _ in range(repetitions):
        started = time.perf_counter()
        response = client.get(path, params=params)
        latencies.append((time.perf_counter() - started) * 1000)
        if response.status_code != expected_status:
            error_count += 1
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(payload, dict):
            if isinstance(payload.get("nodes"), list):
                response_node_count = max(response_node_count, len(payload["nodes"]))
            elif isinstance(payload.get("items"), list):
                response_node_count = max(response_node_count, len(payload["items"]))
            if isinstance(payload.get("edges"), list):
                response_edge_count = max(response_edge_count, len(payload["edges"]))
    ordered = sorted(latencies)
    p95 = ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]
    return {
        "name": name,
        "expected_status": expected_status,
        "latency_ms": {
            "min": min(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": p95,
            "max": max(latencies),
        },
        "response_node_count": response_node_count,
        "response_edge_count": response_edge_count,
        "error_count": error_count,
    }


if __name__ == "__main__":
    raise SystemExit(main())
