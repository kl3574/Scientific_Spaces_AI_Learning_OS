from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.graph.models import GraphDocument, GraphEdge, GraphNode
from app.storage.article_store import StoredArticle


def _article(index: int, *, content: str | None = None, category: str = "机器学习") -> StoredArticle:
    return StoredArticle(
        id=f"article-{index:03d}",
        title=f"Attention study {index}",
        url=f"https://spaces.ac.cn/archives/{7000 + index}",
        content=content
        or (
            f"# Attention section {index}\n\n"
            f"Attention and Transformer evidence for article {index}.\n\n"
            "$$\nQK^T\n$$\n"
        ),
        metadata={
            "date": "2020-01-01",
            "category": category,
            "references": [],
            "images": [],
        },
    )


def _write_store(path: Path, articles: list[StoredArticle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([article.to_dict() for article in articles], ensure_ascii=False),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_full_corpus_graph_fingerprint_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.graph.full_corpus import GRAPH_EXTRACTION_RULE_VERSION, compute_graph_fingerprint
    from app.zotero.store import ZoteroLinkStore

    articles = [_article(1), _article(2)]
    empty_zotero = ZoteroLinkStore(tmp_path / "zotero.json")
    first = KnowledgeGraphBuilder(
        articles=articles,
        zotero_store=empty_zotero,
        include_personalization=False,
    ).build()
    second = KnowledgeGraphBuilder(
        articles=list(reversed(articles)),
        zotero_store=empty_zotero,
        include_personalization=False,
    ).build()
    changed = KnowledgeGraphBuilder(
        articles=[_article(1), _article(2, content="# UniqueQuantumConcept\n\nUniqueQuantumConcept evidence.")],
        zotero_store=empty_zotero,
        include_personalization=False,
    ).build()

    first_fingerprint = compute_graph_fingerprint(first)
    assert first_fingerprint == compute_graph_fingerprint(second)
    assert first_fingerprint != compute_graph_fingerprint(changed)
    assert compute_graph_fingerprint(first, corpus_fingerprint="corpus-a") != compute_graph_fingerprint(
        first,
        corpus_fingerprint="corpus-b",
    )
    assert first_fingerprint != compute_graph_fingerprint(
        first,
        extraction_rule_version=f"{GRAPH_EXTRACTION_RULE_VERSION}-changed",
    )


def test_graph_integrity_audit_detects_duplicate_and_dangling_records() -> None:
    from app.graph.full_corpus import audit_graph

    article = _article(1)
    duplicate = GraphNode(
        node_id="article:article-001",
        node_type="article",
        label=article.title,
        source_id=article.id,
        source_url=article.url,
        metadata={"article_id": article.id},
    )
    graph = GraphDocument(
        nodes=[
            duplicate,
            duplicate,
            GraphNode(
                node_id="concept:private",
                node_type="concept",
                label="private",
                source_id="private",
                metadata={
                    "normalized": "private",
                    "source_count": 1,
                    "truncated": False,
                    "sources": [
                        {
                            "article_id": article.id,
                            "article_title": article.title,
                            "article_url": article.url,
                            "source_type": "section_content",
                            "source_context": "/home/private/article.md",
                            "evidence": "private",
                        }
                    ],
                },
            ),
        ],
        edges=[
            GraphEdge(
                edge_id="edge:duplicate",
                source_node_id=duplicate.node_id,
                target_node_id="concept:missing",
                edge_type="mentions",
                evidence={"article_id": article.id},
            ),
            GraphEdge(
                edge_id="edge:duplicate",
                source_node_id=duplicate.node_id,
                target_node_id=duplicate.node_id,
                edge_type="mentions",
                evidence={},
            ),
        ],
    )

    audit = audit_graph([article], graph)

    assert audit["duplicate_node_id_count"] == 1
    assert audit["duplicate_edge_id_count"] == 1
    assert audit["dangling_edge_count"] == 1
    assert audit["self_loop_count"] == 1
    assert audit["missing_edge_evidence_count"] == 1
    assert audit["local_path_provenance_count"] == 1
    assert audit["article_metadata_mismatch_count"] == 1
    assert audit["status"] == "BLOCKED"


def test_full_corpus_builder_preserves_complete_bounded_concept_provenance(tmp_path: Path) -> None:
    from app.graph.builder import MAX_CONCEPT_SOURCES, KnowledgeGraphBuilder
    from app.graph.full_corpus import audit_graph
    from app.zotero.store import ZoteroLinkStore

    articles = [_article(index, category="") for index in range(12)]
    graph = KnowledgeGraphBuilder(
        articles=articles,
        zotero_store=ZoteroLinkStore(tmp_path / "zotero.json"),
        include_personalization=False,
    ).build()
    concept = next(node for node in graph.nodes if node.node_type == "concept" and node.label.lower() == "attention")
    sources = concept.metadata["sources"]

    assert concept.metadata["source_count"] == len(articles) * 3
    assert concept.metadata["source_count"] > MAX_CONCEPT_SOURCES
    assert len(sources) == MAX_CONCEPT_SOURCES
    assert concept.metadata["truncated"] is True
    assert len({json.dumps(source, sort_keys=True) for source in sources}) == len(sources)
    assert all(source["article_id"] in {article.id for article in articles} for source in sources)
    assert all(source.get("section_node_id") or source["source_type"] == "article_title" for source in sources)
    assert all("content" not in source for source in sources)
    assert all(".local_data" not in json.dumps(source) for source in sources)

    audit = audit_graph(articles, graph)
    assert audit["article_coverage_rate"] == 1.0
    assert audit["missing_provenance_count"] == 0
    assert audit["concepts_without_sources_count"] == 0
    assert audit["formulas_without_sources_count"] == 0
    assert audit["sections_without_parent_article_count"] == 0
    assert audit["invalid_article_reference_count"] == 0
    assert audit["edges_per_article_min"] == audit["edges_per_article_max"]
    assert audit["nodes_per_article_min"] == audit["nodes_per_article_max"]
    assert (
        audit["concepts_per_article_distribution"]["min"]
        == audit["concepts_per_article_distribution"]["max"]
    )
    assert audit["status"] == "PASS"


def test_graph_integrity_audit_detects_incorrect_complete_concept_source_count(tmp_path: Path) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.graph.full_corpus import audit_graph
    from app.zotero.store import ZoteroLinkStore

    articles = [_article(1)]
    graph = KnowledgeGraphBuilder(
        articles=articles,
        zotero_store=ZoteroLinkStore(tmp_path / "zotero.json"),
        include_personalization=False,
    ).build()
    concept = next(node for node in graph.nodes if node.node_type == "concept" and node.label == "attention")
    concept.metadata["source_count"] = int(concept.metadata["source_count"]) + 1
    concept.metadata["truncated"] = True

    audit = audit_graph(articles, graph)

    assert audit["concept_source_count_mismatch_count"] == 1
    assert "concept_source_count_mismatch_count" in audit["blocking_metrics"]
    assert audit["status"] == "BLOCKED"


def test_graph_builder_merges_concept_aliases_that_share_a_stable_node_id(tmp_path: Path) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.graph.full_corpus import audit_graph
    from app.graph.models import make_node_id
    from app.graph.service import GraphService
    from app.graph.store import GraphStore
    from app.zotero.store import ZoteroLinkStore

    article = _article(
        1,
        content="# Divergence\n\nKullback- Leibler divergence compares Kullback distributions.",
        category="",
    )
    graph = KnowledgeGraphBuilder(
        articles=[article],
        zotero_store=ZoteroLinkStore(tmp_path / "zotero.json"),
        include_personalization=False,
    ).build()
    node_id = make_node_id("concept", "kullback")
    concepts = [node for node in graph.nodes if node.node_id == node_id]

    assert len(concepts) == 1
    assert concepts[0].metadata["normalized"] == "kullback"
    assert concepts[0].metadata["aliases"] == ["kullback", "kullback-"]
    assert concepts[0].metadata["source_count"] == 2
    assert audit_graph([article], graph)["concept_source_count_mismatch_count"] == 0
    store = GraphStore(tmp_path / "graph.json")
    store.save(graph)
    alias_result = GraphService(store=store).list_nodes(
        node_type="concept",
        concept="kullback-",
        page=1,
        page_size=10,
    )
    assert [item["node_id"] for item in alias_result["items"]] == [node_id]


def test_article_node_filter_uses_complete_edge_evidence_beyond_bounded_provenance(tmp_path: Path) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.graph.service import GraphService
    from app.graph.store import GraphStore
    from app.zotero.store import ZoteroLinkStore

    articles = [_article(index, category="") for index in range(12)]
    graph = KnowledgeGraphBuilder(
        articles=articles,
        zotero_store=ZoteroLinkStore(tmp_path / "zotero.json"),
        include_personalization=False,
    ).build()
    service = GraphService(store=GraphStore(tmp_path / "graph.json"))
    service.store.save(graph)

    response = service.list_nodes(
        node_type="concept",
        article_id=articles[-1].id,
        page=1,
        page_size=100,
    )

    assert any(item["node_id"] == "concept:attention" for item in response["items"])


def test_graph_builder_keeps_code_comment_concepts_connected(tmp_path: Path) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.graph.full_corpus import audit_graph
    from app.zotero.store import ZoteroLinkStore

    article = _article(
        1,
        content=(
            "# Code sample\n\n"
            "```c\n"
            "#include<stdio.h>\n"
            "int main(void) { return 0; }\n"
            "```\n"
        ),
    )
    graph = KnowledgeGraphBuilder(
        articles=[article],
        zotero_store=ZoteroLinkStore(tmp_path / "zotero.json"),
        include_personalization=False,
    ).build()
    node_ids = {node.node_id for node in graph.nodes}

    assert "concept:include" in node_ids
    assert "concept:stdio" in node_ids
    assert all(edge.source_node_id in node_ids and edge.target_node_id in node_ids for edge in graph.edges)
    assert audit_graph([article], graph)["dangling_edge_count"] == 0


def test_full_corpus_build_is_atomic_offline_and_idempotent(tmp_path: Path, monkeypatch) -> None:
    import app.graph.builder as builder_module
    import app.graph.full_corpus as full_corpus_module
    from app.graph.full_corpus import (
        GRAPH_AUDIT_RULE_VERSION,
        GRAPH_FINGERPRINT_VERSION,
        build_full_corpus_graph,
    )

    article_store = tmp_path / "articles.json"
    output_dir = tmp_path / "graph-output"
    _write_store(article_store, [_article(1), _article(2), _article(3)])

    def fail_if_provider_is_requested():
        raise AssertionError("full-corpus graph build must not initialize an external provider without links")

    monkeypatch.setattr(builder_module, "get_zotero_provider", fail_if_provider_is_requested)

    first = build_full_corpus_graph(
        article_store_path=article_store,
        output_dir=output_dir,
        expected_article_count=3,
        rebuild=True,
    )
    graph_file = output_dir / "graph.json"
    manifest_file = output_dir / "manifest.json"
    first_graph_hash = _sha256(graph_file)
    second = build_full_corpus_graph(
        article_store_path=article_store,
        output_dir=output_dir,
        expected_article_count=3,
        rebuild=True,
    )

    assert first["status"] == "PASS"
    assert first["action"] == "rebuilt"
    assert first["atomic_replace"] is True
    assert graph_file.is_file()
    assert manifest_file.is_file()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["audit_rule_version"] == GRAPH_AUDIT_RULE_VERSION
    assert manifest["graph_fingerprint_version"] == GRAPH_FINGERPRINT_VERSION
    assert (output_dir / "reports" / "build_summary.json").is_file()
    assert (output_dir / "reports" / "integrity_audit.json").is_file()
    assert second["status"] == "PASS"
    assert second["action"] == "no_op"
    assert second["corpus_fingerprint_unchanged"] is True
    assert second["graph_fingerprint_unchanged"] is True
    assert second["node_count_unchanged"] is True
    assert second["edge_count_unchanged"] is True
    assert _sha256(graph_file) == first_graph_hash

    _write_store(
        article_store,
        [_article(1), _article(2), _article(3, content="# Changed\n\nChanged corpus content.")],
    )

    def fail_atomic_publish(staging: Path, target: Path) -> None:
        raise OSError("simulated graph publish failure")

    monkeypatch.setattr(full_corpus_module, "_atomic_replace_directory", fail_atomic_publish)
    with pytest.raises(OSError, match="simulated graph publish failure"):
        build_full_corpus_graph(
            article_store_path=article_store,
            output_dir=output_dir,
            expected_article_count=3,
            rebuild=True,
        )
    assert _sha256(graph_file) == first_graph_hash


def test_graph_store_atomic_failure_preserves_previous_graph(tmp_path: Path, monkeypatch) -> None:
    import app.graph.store as store_module
    from app.graph.store import GraphStore

    store = GraphStore(tmp_path / "graph.json")
    original = GraphDocument(
        nodes=[GraphNode(node_id="concept:old", node_type="concept", label="old")],
    )
    store.save(original)
    original_hash = _sha256(store.path)

    def fail_replace(source: Path | str, target: Path | str) -> None:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(store_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        store.save(
            GraphDocument(nodes=[GraphNode(node_id="concept:new", node_type="concept", label="new")])
        )

    assert _sha256(store.path) == original_hash
    assert store.load().nodes[0].node_id == "concept:old"


def test_atomic_directory_publish_restores_previous_target_on_install_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import app.graph.full_corpus as full_corpus_module

    target = tmp_path / "graph-output"
    staging = tmp_path / ".graph-output.staging"
    target.mkdir()
    staging.mkdir()
    (target / "graph.json").write_text("old", encoding="utf-8")
    (staging / "graph.json").write_text("new", encoding="utf-8")
    real_replace = full_corpus_module.os.replace

    def fail_staging_install(source: Path | str, destination: Path | str) -> None:
        if Path(source) == staging and Path(destination) == target:
            raise OSError("simulated staged directory install failure")
        real_replace(source, destination)

    monkeypatch.setattr(full_corpus_module.os, "replace", fail_staging_install)

    with pytest.raises(OSError, match="simulated staged directory install failure"):
        full_corpus_module._atomic_replace_directory(staging, target)

    assert (target / "graph.json").read_text(encoding="utf-8") == "old"
    assert (staging / "graph.json").read_text(encoding="utf-8") == "new"
    assert list(tmp_path.glob(".graph-output.backup-*")) == []
