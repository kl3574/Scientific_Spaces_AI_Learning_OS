from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import time
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any
from urllib.parse import urlparse

from app.graph.builder import KnowledgeGraphBuilder, section_body_for_concept_extraction
from app.graph.extractors import extract_concepts, normalize_concept
from app.graph.models import GraphDocument, GraphEdge, GraphNode, make_node_id
from app.rag.chunking import chunk_article
from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles
from app.storage.article_store import StoredArticle
from app.zotero.store import ZoteroLinkStore

GRAPH_SCHEMA_VERSION = 1
GRAPH_CONTRACT_VERSION = "m6.1"
GRAPH_EXTRACTION_RULE_VERSION = "m6.1-deterministic-v2"
GRAPH_AUDIT_RULE_VERSION = "p2-003-integrity-v4"
GRAPH_FINGERPRINT_VERSION = 1


class FullCorpusGraphError(RuntimeError):
    pass


def compute_graph_fingerprint(
    graph: GraphDocument,
    *,
    extraction_rule_version: str = GRAPH_EXTRACTION_RULE_VERSION,
    corpus_fingerprint: str | None = None,
) -> str:
    payload = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "contract_version": GRAPH_CONTRACT_VERSION,
        "extraction_rule_version": extraction_rule_version,
        "corpus_fingerprint": corpus_fingerprint,
        "nodes": [node.to_dict() for node in sorted(graph.nodes, key=lambda item: item.node_id)],
        "edges": [edge.to_dict() for edge in sorted(graph.edges, key=lambda item: item.edge_id)],
        "source_counts": dict(sorted(graph.source_counts.items())),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def audit_graph(articles: list[StoredArticle], graph: GraphDocument) -> dict[str, Any]:
    article_ids = {article.id for article in articles}
    articles_by_id = {article.id: article for article in articles}
    article_urls = {article.url for article in articles}
    node_ids = [node.node_id for node in graph.nodes]
    edge_ids = [edge.edge_id for edge in graph.edges]
    unique_nodes = {node.node_id: node for node in graph.nodes}
    node_type_counts = Counter(node.node_type for node in graph.nodes)
    edge_type_counts = Counter(edge.edge_type for edge in graph.edges)
    article_nodes = [node for node in graph.nodes if node.node_type == "article"]
    graph_article_ids = {str(node.source_id or node.metadata.get("article_id") or "") for node in article_nodes}

    incident: Counter[str] = Counter()
    adjacency: dict[str, set[str]] = defaultdict(set)
    incoming_by_target: dict[str, list[GraphEdge]] = defaultdict(list)
    outgoing_by_source: dict[str, list[GraphEdge]] = defaultdict(list)
    dangling_edge_count = 0
    self_loop_count = 0
    missing_edge_evidence_count = 0
    invalid_article_references: set[str] = set()
    for edge in graph.edges:
        if edge.source_node_id not in unique_nodes or edge.target_node_id not in unique_nodes:
            dangling_edge_count += 1
        else:
            incident[edge.source_node_id] += 1
            incident[edge.target_node_id] += 1
            adjacency[edge.source_node_id].add(edge.target_node_id)
            adjacency[edge.target_node_id].add(edge.source_node_id)
        if edge.source_node_id == edge.target_node_id:
            self_loop_count += 1
        if not edge.evidence:
            missing_edge_evidence_count += 1
        evidence_article_id = str(edge.evidence.get("article_id") or "")
        if evidence_article_id and evidence_article_id not in article_ids:
            invalid_article_references.add(evidence_article_id)
        incoming_by_target[edge.target_node_id].append(edge)
        outgoing_by_source[edge.source_node_id].append(edge)

    missing_provenance_count = 0
    concepts_without_sources_count = 0
    formulas_without_sources_count = 0
    invalid_source_url_count = 0
    local_path_provenance_count = 0
    duplicate_concept_source_count = 0
    for node in graph.nodes:
        if node.source_url and not _valid_http_url(node.source_url):
            invalid_source_url_count += 1
        referenced_article_id = _node_article_id(node)
        if referenced_article_id and node.node_type in {"article", "section", "formula"}:
            if referenced_article_id not in article_ids:
                invalid_article_references.add(referenced_article_id)
        if node.node_type in {"article", "section", "formula"} and (not node.source_id or not node.source_url):
            missing_provenance_count += 1
        if node.node_type == "zotero_item" and not node.source_id:
            missing_provenance_count += 1
        if node.node_type == "formula":
            has_parent = any(edge.edge_type == "has_formula" for edge in incoming_by_target[node.node_id])
            if not node.metadata.get("formula") or not referenced_article_id or not has_parent:
                formulas_without_sources_count += 1
        if node.node_type != "concept":
            continue

        metadata = node.metadata
        sources = metadata.get("sources")
        source_count = metadata.get("source_count")
        truncated = metadata.get("truncated")
        required_keys_present = all(key in metadata for key in ("normalized", "source_count", "sources", "truncated"))
        if not required_keys_present or not isinstance(sources, list) or not sources:
            concepts_without_sources_count += 1
            missing_provenance_count += 1
            continue
        serialized_sources = [_canonical_json(source) for source in sources if isinstance(source, dict)]
        duplicate_concept_source_count += len(serialized_sources) - len(set(serialized_sources))
        source_records_valid = True
        for source in sources:
            if not isinstance(source, dict):
                source_records_valid = False
                continue
            source_article_id = str(source.get("article_id") or "")
            source_url = str(source.get("article_url") or "")
            if source_article_id not in article_ids:
                invalid_article_references.add(source_article_id or "<missing>")
                source_records_valid = False
            if not source.get("article_title") or not source_url or not source.get("source_type"):
                source_records_valid = False
            if not source.get("section_node_id") and not source.get("source_context"):
                source_records_valid = False
            if source_url and not _valid_http_url(source_url):
                invalid_source_url_count += 1
            serialized = _canonical_json(source)
            if ".local_data" in serialized or _contains_absolute_local_path(serialized):
                local_path_provenance_count += 1
            if "content" in source:
                source_records_valid = False
        count_valid = (
            isinstance(source_count, int)
            and source_count >= len(sources)
            and isinstance(truncated, bool)
            and truncated == (source_count > len(sources))
        )
        if not source_records_valid or not count_valid:
            missing_provenance_count += 1

    sections = [node for node in graph.nodes if node.node_type == "section"]
    section_parent_ids = {
        edge.target_node_id
        for edge in graph.edges
        if edge.edge_type == "has_section"
        and unique_nodes.get(edge.source_node_id, GraphNode("", "article", "")).node_type == "article"
    }
    sections_without_parent_article_count = sum(node.node_id not in section_parent_ids for node in sections)
    article_nodes_with_sections = {
        edge.source_node_id for edge in graph.edges if edge.edge_type == "has_section" and edge.target_node_id in unique_nodes
    }
    articles_without_sections_count = sum(node.node_id not in article_nodes_with_sections for node in article_nodes)

    per_article = _per_article_metrics(articles, graph)
    component_sizes = _component_sizes(unique_nodes, adjacency)
    largest_concepts = sorted(
        (
            {
                "node_id": node.node_id,
                "label": node.label,
                "source_count": int(node.metadata.get("source_count") or 0),
            }
            for node in graph.nodes
            if node.node_type == "concept"
        ),
        key=lambda item: (-item["source_count"], item["node_id"]),
    )[:20]

    article_coverage_rate = len(graph_article_ids & article_ids) / len(article_ids) if article_ids else 1.0
    duplicate_node_id_count = len(node_ids) - len(set(node_ids))
    duplicate_edge_id_count = len(edge_ids) - len(set(edge_ids))
    missing_node_type_count = sum(not str(node.node_type).strip() for node in graph.nodes)
    missing_edge_type_count = sum(not str(edge.edge_type).strip() for edge in graph.edges)
    isolated_node_count = sum(incident[node_id] == 0 for node_id in unique_nodes)
    invalid_article_reference_count = len(invalid_article_references)
    article_metadata_mismatch_count = 0
    for node in unique_nodes.values():
        if node.node_type != "article":
            continue
        article_id = str(node.source_id or node.metadata.get("article_id") or "")
        expected = articles_by_id.get(article_id)
        if expected is None:
            article_metadata_mismatch_count += 1
            continue
        if node.label != expected.title or node.source_url != expected.url:
            article_metadata_mismatch_count += 1
            continue
        if any(
            node.metadata.get(key) != expected.metadata.get(key)
            for key in ("date", "category", "references", "images")
        ):
            article_metadata_mismatch_count += 1

    expected_concept_source_counts = _expected_concept_source_counts(articles)
    actual_concept_source_counts = {
        node.node_id: node.metadata.get("source_count")
        for node in graph.nodes
        if node.node_type == "concept"
    }
    concept_source_count_mismatch_count = sum(
        type(actual_concept_source_counts.get(normalized)) is not int
        or actual_concept_source_counts.get(normalized) != expected_concept_source_counts.get(normalized, 0)
        for normalized in set(expected_concept_source_counts) | set(actual_concept_source_counts)
    )

    blockers = {
        "article_coverage_rate": article_coverage_rate != 1.0,
        "duplicate_node_id_count": duplicate_node_id_count != 0,
        "duplicate_edge_id_count": duplicate_edge_id_count != 0,
        "dangling_edge_count": dangling_edge_count != 0,
        "missing_provenance_count": missing_provenance_count != 0,
        "missing_edge_evidence_count": missing_edge_evidence_count != 0,
        "concepts_without_sources_count": concepts_without_sources_count != 0,
        "formulas_without_sources_count": formulas_without_sources_count != 0,
        "sections_without_parent_article_count": sections_without_parent_article_count != 0,
        "invalid_article_reference_count": invalid_article_reference_count != 0,
        "duplicate_concept_source_count": duplicate_concept_source_count != 0,
        "local_path_provenance_count": local_path_provenance_count != 0,
        "article_metadata_mismatch_count": article_metadata_mismatch_count != 0,
        "concept_source_count_mismatch_count": concept_source_count_mismatch_count != 0,
    }
    return {
        "status": "BLOCKED" if any(blockers.values()) else "PASS",
        "blocking_metrics": sorted(key for key, blocked in blockers.items() if blocked),
        "input_article_count": len(articles),
        "graph_article_node_count": len(article_nodes),
        "article_coverage_rate": article_coverage_rate,
        "total_node_count": len(graph.nodes),
        "total_edge_count": len(graph.edges),
        "node_count_by_type": dict(sorted(node_type_counts.items())),
        "edge_count_by_type": dict(sorted(edge_type_counts.items())),
        "isolated_node_count": isolated_node_count,
        "duplicate_node_id_count": duplicate_node_id_count,
        "duplicate_edge_id_count": duplicate_edge_id_count,
        "dangling_edge_count": dangling_edge_count,
        "self_loop_count": self_loop_count,
        "missing_node_type_count": missing_node_type_count,
        "missing_edge_type_count": missing_edge_type_count,
        "missing_provenance_count": missing_provenance_count,
        "missing_edge_evidence_count": missing_edge_evidence_count,
        "concepts_without_sources_count": concepts_without_sources_count,
        "formulas_without_sources_count": formulas_without_sources_count,
        "sections_without_parent_article_count": sections_without_parent_article_count,
        "articles_without_sections_count": articles_without_sections_count,
        "invalid_source_url_count": invalid_source_url_count,
        "invalid_article_reference_count": invalid_article_reference_count,
        "article_metadata_mismatch_count": article_metadata_mismatch_count,
        "concept_source_count_mismatch_count": concept_source_count_mismatch_count,
        "duplicate_concept_source_count": duplicate_concept_source_count,
        "local_path_provenance_count": local_path_provenance_count,
        **per_article,
        "largest_concepts_by_source_count": largest_concepts,
        "connected_component_count": len(component_sizes),
        "largest_connected_components": component_sizes[:20],
        "article_store_url_count": len(article_urls),
    }


def build_full_corpus_graph(
    *,
    article_store_path: Path | str,
    output_dir: Path | str,
    rebuild: bool = False,
    expected_article_count: int | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    source_path = Path(article_store_path).expanduser().resolve()
    target = Path(output_dir).expanduser().resolve()
    articles = load_full_corpus_articles(source_path)
    if expected_article_count is not None and len(articles) != expected_article_count:
        raise FullCorpusGraphError(
            f"Expected {expected_article_count} Articles but loaded {len(articles)} from {source_path}"
        )
    corpus_fingerprint = compute_corpus_fingerprint(articles)
    existing_manifest = _read_json(target / "manifest.json")
    if _existing_graph_matches(target, existing_manifest, corpus_fingerprint):
        elapsed = time.perf_counter() - started
        result = _no_op_result(existing_manifest or {}, elapsed)
        _write_json_atomic(target / "reports" / "build_summary.json", result)
        return result
    if target.exists() and not rebuild:
        raise FullCorpusGraphError("Existing graph is stale or incomplete; pass rebuild=True to replace it")

    staging = target.with_name(f".{target.name}.staging-{uuid.uuid4().hex}")
    try:
        staging.mkdir(parents=True)
        graph = KnowledgeGraphBuilder(
            articles=articles,
            zotero_store=ZoteroLinkStore(staging / "empty-zotero-links.json"),
            include_personalization=False,
        ).build()
        graph_fingerprint = compute_graph_fingerprint(graph, corpus_fingerprint=corpus_fingerprint)
        audit = audit_graph(articles, graph)
        if audit["status"] != "PASS":
            raise FullCorpusGraphError(
                "Graph integrity audit failed: " + ", ".join(audit["blocking_metrics"])
            )

        graph_path = staging / "graph.json"
        _write_json(graph_path, graph.to_dict(), compact=True)
        graph_file_size = graph_path.stat().st_size
        graph_file_sha256 = _file_sha256(graph_path)
        elapsed = time.perf_counter() - started
        manifest = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "graph_contract_version": GRAPH_CONTRACT_VERSION,
            "extraction_rule_version": GRAPH_EXTRACTION_RULE_VERSION,
            "audit_rule_version": GRAPH_AUDIT_RULE_VERSION,
            "graph_fingerprint_version": GRAPH_FINGERPRINT_VERSION,
            "article_count": len(articles),
            "unique_url_count": len({article.url for article in articles}),
            "corpus_fingerprint": corpus_fingerprint,
            "graph_fingerprint": graph_fingerprint,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "node_count_by_type": audit["node_count_by_type"],
            "edge_count_by_type": audit["edge_count_by_type"],
            "build_timestamp": datetime.now(UTC).isoformat(),
            "build_elapsed_seconds": elapsed,
            "graph_file": "graph.json",
            "graph_file_size_bytes": graph_file_size,
            "graph_file_sha256": graph_file_sha256,
            "source_store_path": str(source_path),
            "atomic_replace": True,
        }
        result = {
            "status": "PASS",
            "action": "rebuilt",
            "second_run_action": None,
            **manifest,
            "manifest_path": str(target / "manifest.json"),
            "corpus_fingerprint_unchanged": bool(
                existing_manifest and existing_manifest.get("corpus_fingerprint") == corpus_fingerprint
            ),
            "graph_fingerprint_unchanged": bool(
                existing_manifest and existing_manifest.get("graph_fingerprint") == graph_fingerprint
            ),
            "node_count_unchanged": bool(
                existing_manifest and existing_manifest.get("node_count") == len(graph.nodes)
            ),
            "edge_count_unchanged": bool(
                existing_manifest and existing_manifest.get("edge_count") == len(graph.edges)
            ),
        }
        _write_json(staging / "manifest.json", manifest)
        _write_json(staging / "reports" / "integrity_audit.json", audit)
        _write_json(staging / "reports" / "build_summary.json", result)
        (staging / "logs").mkdir()
        (staging / "empty-zotero-links.json").unlink(missing_ok=True)
        _atomic_replace_directory(staging, target)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _per_article_metrics(articles: list[StoredArticle], graph: GraphDocument) -> dict[str, Any]:
    article_ids = [article.id for article in articles]
    nodes: dict[str, set[str]] = {article_id: set() for article_id in article_ids}
    edges: dict[str, set[str]] = {article_id: set() for article_id in article_ids}
    concepts: dict[str, set[str]] = {article_id: set() for article_id in article_ids}
    formulas: dict[str, set[str]] = {article_id: set() for article_id in article_ids}
    direct_node_article_ids: dict[str, set[str]] = defaultdict(set)
    node_types = {node.node_id: node.node_type for node in graph.nodes}

    for node in graph.nodes:
        if node.node_type == "concept":
            continue
        article_id = _node_article_id(node)
        if article_id in nodes:
            nodes[article_id].add(node.node_id)
            direct_node_article_ids[node.node_id].add(article_id)
            if node.node_type == "formula":
                formulas[article_id].add(node.node_id)

    for edge in graph.edges:
        evidence_article_id = str(edge.evidence.get("article_id") or "")
        if evidence_article_id in edges:
            edge_articles = {evidence_article_id}
        else:
            edge_articles = set(direct_node_article_ids.get(edge.source_node_id, set())) | set(
                direct_node_article_ids.get(edge.target_node_id, set())
            )
        for article_id in edge_articles:
            edges[article_id].add(edge.edge_id)
            if edge.edge_type == "mentions" and node_types.get(edge.target_node_id) == "concept":
                concepts[article_id].add(edge.target_node_id)
                nodes[article_id].add(edge.target_node_id)

    node_values = [len(nodes[article_id]) for article_id in article_ids]
    edge_values = [len(edges[article_id]) for article_id in article_ids]
    concept_values = [len(concepts[article_id]) for article_id in article_ids]
    formula_values = [len(formulas[article_id]) for article_id in article_ids]
    return {
        **_distribution("nodes_per_article", node_values),
        **_distribution("edges_per_article", edge_values),
        "concepts_per_article_distribution": _distribution_values(concept_values),
        "formulas_per_article_distribution": _distribution_values(formula_values),
    }


def _expected_concept_source_counts(articles: list[StoredArticle]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for article in articles:
        category = str(article.metadata.get("category") or "").strip()
        title_concepts = _normalized_concepts(article.title)
        category_concepts = _normalized_concepts(category)
        for concept in extract_concepts(article.title, category):
            normalized = normalize_concept(concept)
            node_id = make_node_id("concept", normalized)
            if normalized in title_concepts:
                counts[node_id] += 1
            if normalized in category_concepts:
                counts[node_id] += 1

        chunks = chunk_article(
            article_id=article.id,
            article_title=article.title,
            article_url=article.url,
            content=article.content,
        )
        for chunk in chunks:
            heading_concepts = _normalized_concepts(chunk.section_title)
            body_concepts = _normalized_concepts(section_body_for_concept_extraction(chunk.content))
            for concept in extract_concepts(chunk.section_title, chunk.content):
                normalized = normalize_concept(concept)
                node_id = make_node_id("concept", normalized)
                if normalized in heading_concepts:
                    counts[node_id] += 1
                if normalized in body_concepts:
                    counts[node_id] += 1
    return counts


def _normalized_concepts(text: str | None) -> set[str]:
    return {normalize_concept(concept) for concept in extract_concepts(text)}


def _distribution(prefix: str, values: list[int]) -> dict[str, int | float]:
    summary = _distribution_values(values)
    return {f"{prefix}_{key}": value for key, value in summary.items()}


def _distribution_values(values: list[int]) -> dict[str, int | float]:
    if not values:
        return {"min": 0, "mean": 0.0, "median": 0.0, "p95": 0, "max": 0}
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "min": ordered[0],
        "mean": float(mean(ordered)),
        "median": float(median(ordered)),
        "p95": ordered[p95_index],
        "max": ordered[-1],
    }


def _component_sizes(nodes: dict[str, GraphNode], adjacency: dict[str, set[str]]) -> list[int]:
    remaining = set(nodes)
    sizes: list[int] = []
    while remaining:
        root = min(remaining)
        pending = [root]
        remaining.remove(root)
        size = 0
        while pending:
            current = pending.pop()
            size += 1
            for neighbor in sorted(adjacency.get(current, set())):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def _node_article_id(node: GraphNode) -> str:
    if node.node_type == "article":
        return str(node.source_id or node.metadata.get("article_id") or "")
    return str(node.metadata.get("article_id") or node.source_id or "")


def _existing_graph_matches(
    target: Path,
    manifest: dict[str, Any] | None,
    corpus_fingerprint: str,
) -> bool:
    graph_path = target / "graph.json"
    if not manifest or not graph_path.is_file():
        return False
    return (
        manifest.get("schema_version") == GRAPH_SCHEMA_VERSION
        and manifest.get("graph_contract_version") == GRAPH_CONTRACT_VERSION
        and manifest.get("extraction_rule_version") == GRAPH_EXTRACTION_RULE_VERSION
        and manifest.get("audit_rule_version") == GRAPH_AUDIT_RULE_VERSION
        and manifest.get("graph_fingerprint_version") == GRAPH_FINGERPRINT_VERSION
        and manifest.get("corpus_fingerprint") == corpus_fingerprint
        and manifest.get("graph_file_size_bytes") == graph_path.stat().st_size
        and manifest.get("graph_file_sha256") == _file_sha256(graph_path)
    )


def _no_op_result(manifest: dict[str, Any], elapsed: float) -> dict[str, Any]:
    return {
        "status": "PASS",
        "action": "no_op",
        "second_run_action": "no_op",
        **manifest,
        "build_elapsed_seconds": elapsed,
        "second_run_elapsed_seconds": elapsed,
        "corpus_fingerprint_unchanged": True,
        "graph_fingerprint_unchanged": True,
        "node_count_unchanged": True,
        "edge_count_unchanged": True,
        "atomic_replace": True,
    }


def _atomic_replace_directory(staging: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.with_name(f".{target.name}.backup-{uuid.uuid4().hex}")
    had_target = target.exists()
    if had_target:
        os.replace(target, backup)
    try:
        os.replace(staging, target)
    except Exception:
        if had_target and backup.exists():
            os.replace(backup, target)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _contains_absolute_local_path(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)(?:file://|(?:^|[\"'\s:=])/(?:home|users|root|tmp|var|etc|opt|mnt|srv|data)/|(?:^|[\"'\s:=])[a-z]:[\\/])",
            value,
        )
    )


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if compact else None,
            indent=None if compact else 2,
        )


def _write_json_atomic(path: Path, payload: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        _write_json(temporary, payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
