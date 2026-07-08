import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def write_articles(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "id": "attention-001",
                    "title": "Attention机制的一个直观解释",
                    "url": "https://spaces.ac.cn/archives/6508",
                    "content": (
                        "# Attention机制\n\n"
                        "Attention 用 query 和 key 计算相关性，Transformer 使用 self-attention。\n\n"
                        "## 数学形式\n\n"
                        "$$\nQK^T\n$$\n"
                    ),
                    "metadata": {
                        "date": "2018-06-01",
                        "category": "信息时代",
                        "references": [],
                        "images": [],
                    },
                },
                {
                    "id": "attention-002",
                    "title": "Transformer中的位置编码",
                    "url": "https://spaces.ac.cn/archives/6509",
                    "content": "# 位置编码\n\nTransformer 需要位置编码来补充序列信息。",
                    "metadata": {
                        "date": "2018-06-02",
                        "category": "信息时代",
                        "references": [],
                        "images": [],
                    },
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def configure_files(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    learning_file = tmp_path / "learning.json"
    zotero_file = tmp_path / "zotero_links.json"
    graph_file = tmp_path / "knowledge_graph.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(learning_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(zotero_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_GRAPH_FILE", str(graph_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "fake")


def test_graph_model_ids_are_deterministic() -> None:
    from app.graph.models import make_edge_id, make_node_id

    assert make_node_id("article", "attention-001") == make_node_id("article", "attention-001")
    assert make_node_id("article", "attention-001") != make_node_id("concept", "attention-001")
    assert make_edge_id("a", "b", "mentions", "source") == make_edge_id("a", "b", "mentions", "source")


def test_graph_builder_empty_corpus_returns_empty_graph(tmp_path: Path, monkeypatch) -> None:
    from app.graph.builder import KnowledgeGraphBuilder

    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(tmp_path / "zotero_links.json"))

    graph = KnowledgeGraphBuilder().build()

    assert graph.nodes == []
    assert graph.edges == []
    assert graph.source_counts["articles"] == 0


def test_graph_builder_creates_article_section_concept_formula_and_zotero_edges(tmp_path: Path, monkeypatch) -> None:
    from app.graph.builder import KnowledgeGraphBuilder
    from app.learning.store import LearningStore
    from app.zotero.store import ZoteroLinkStore

    configure_files(tmp_path, monkeypatch)
    learning_store = LearningStore(tmp_path / "learning.json")
    learning_store.update_state("attention-001", "completed")
    learning_store.add_bookmark(
        article_id="attention-001",
        title="Attention机制的一个直观解释",
        url="https://spaces.ac.cn/archives/6508",
    )
    ZoteroLinkStore(tmp_path / "zotero_links.json").upsert_link(
        article_id="attention-001",
        zotero_item_key="ABCD1234",
        relation_type="background",
        note="Background paper",
    )

    graph = KnowledgeGraphBuilder().build()
    node_types = {node.node_type for node in graph.nodes}
    edge_types = {edge.edge_type for edge in graph.edges}
    concept_labels = {node.label.lower() for node in graph.nodes if node.node_type == "concept"}

    assert {"article", "section", "concept", "formula", "zotero_item"}.issubset(node_types)
    assert {"has_section", "mentions", "has_formula", "background", "same_category"}.issubset(edge_types)
    assert "attention" in concept_labels
    assert "transformer" in concept_labels
    assert all(edge.evidence for edge in graph.edges)
    assert graph.source_counts["articles"] == 2
    assert graph.source_counts["zotero_links"] == 1
    article_node = next(node for node in graph.nodes if node.node_id == "article:attention-001")
    assert article_node.metadata["learning"]["status"] == "completed"
    assert article_node.metadata["learning"]["bookmarked"] is True


def test_graph_store_load_save_clear_and_missing_file(tmp_path: Path) -> None:
    from app.graph.models import GraphDocument, GraphNode
    from app.graph.store import GraphStore

    store = GraphStore(tmp_path / "knowledge_graph.json")

    assert store.load().nodes == []
    graph = GraphDocument(nodes=[GraphNode(node_id="concept:attention", node_type="concept", label="Attention")])
    store.save(graph)
    assert store.load().nodes[0].node_id == "concept:attention"
    store.clear()
    assert store.load().nodes == []


def test_graph_service_search_neighbors_and_subgraph(tmp_path: Path, monkeypatch) -> None:
    from app.graph.service import GraphService, NodeNotFoundError
    from app.zotero.store import ZoteroLinkStore

    configure_files(tmp_path, monkeypatch)
    ZoteroLinkStore(tmp_path / "zotero_links.json").upsert_link(
        article_id="attention-001",
        zotero_item_key="ABCD1234",
        relation_type="cites",
    )
    service = GraphService()
    graph = service.build_graph()
    concept = next(node for node in graph.nodes if node.node_type == "concept" and node.label.lower() == "attention")

    search_results = service.search_nodes("attention")
    concept_results = service.search_nodes("attention", node_type="concept")
    neighbors = service.get_neighbors(concept.node_id, depth=1, limit=20)
    subgraph = service.get_subgraph(concept.node_id, depth=1, limit=50)

    assert search_results
    assert all(node.node_type == "concept" for node in concept_results)
    assert neighbors["nodes"]
    assert neighbors["edges"]
    assert any(node["node_id"] == concept.node_id for node in subgraph["nodes"])
    try:
        service.get_node("missing")
    except NodeNotFoundError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("missing graph node should raise")


def test_graph_api_build_get_search_neighbors_and_regressions(tmp_path: Path, monkeypatch) -> None:
    from app.graph.models import make_node_id
    from app.zotero.store import ZoteroLinkStore

    configure_files(tmp_path, monkeypatch)
    ZoteroLinkStore(tmp_path / "zotero_links.json").upsert_link(
        article_id="attention-001",
        zotero_item_key="ABCD1234",
        relation_type="related",
    )
    client = TestClient(app)
    attention_concept_id = make_node_id("concept", "attention")

    build_response = client.post("/graph/build")
    graph_response = client.get("/graph")
    search_response = client.get("/graph/nodes", params={"q": "attention", "node_type": "concept"})
    node_response = client.get(f"/graph/nodes/{attention_concept_id}")
    neighbors_response = client.get(f"/graph/nodes/{attention_concept_id}/neighbors", params={"limit": 20})
    subgraph_response = client.get(f"/graph/subgraph/{attention_concept_id}", params={"limit": 50})
    missing_response = client.get("/graph/nodes/not-found")
    article_response = client.get("/articles")
    rag_response = client.post("/rag/query", json={"question": "什么是Attention？"})
    learning_response = client.get("/learning/stats")
    zotero_response = client.get("/zotero/status")

    assert build_response.status_code == 200
    assert build_response.json()["node_count"] > 0
    assert build_response.json()["edge_count"] > 0
    assert graph_response.status_code == 200
    assert graph_response.json()["source_counts"]["articles"] == 2
    assert search_response.status_code == 200
    assert search_response.json()["total"] >= 1
    assert node_response.status_code == 200
    assert node_response.json()["node_type"] == "concept"
    assert neighbors_response.status_code == 200
    assert neighbors_response.json()["nodes"]
    assert subgraph_response.status_code == 200
    assert subgraph_response.json()["edges"]
    assert missing_response.status_code == 404
    assert article_response.status_code == 200
    assert rag_response.status_code == 200
    assert learning_response.status_code == 200
    assert zotero_response.status_code == 200
