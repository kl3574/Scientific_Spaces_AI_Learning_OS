import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class RecordingGraphService:
    def __init__(self) -> None:
        from app.graph.models import GraphDocument, GraphEdge, GraphNode

        self.calls: list[tuple[str, dict[str, object]]] = []
        self.node = GraphNode(
            node_id="concept:attention",
            node_type="concept",
            label="Attention",
            source_id="attention",
            source_url="https://spaces.ac.cn/archives/6508",
            metadata={"normalized": "attention", "source_count": 1, "sources": [], "truncated": False},
        )
        self.edge = GraphEdge(
            edge_id="edge:attention",
            source_node_id="concept:attention",
            target_node_id="article:attention-001",
            edge_type="mentions",
            evidence={"article_id": "attention-001"},
        )
        self.graph = GraphDocument(nodes=[self.node], edges=[self.edge])

    def get_graph(self):
        self.calls.append(("get_graph", {}))
        return self.graph

    def build_graph(self):
        self.calls.append(("build_graph", {}))
        return self.graph

    def get_node(self, node_id: str):
        self.calls.append(("get_node", {"node_id": node_id}))
        return self.node

    def get_neighbors(self, node_id: str, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_neighbors", {"node_id": node_id, **kwargs}))
        return {"nodes": [], "edges": [self.edge.to_dict()]}

    def get_subgraph(self, node_id: str, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_subgraph", {"node_id": node_id, **kwargs}))
        return {
            "nodes": [self.node.to_dict()],
            "edges": [self.edge.to_dict()],
            "built_at": None,
            "source_counts": {"concepts": 1},
            "limits": {
                "depth": kwargs["depth"],
                "node_limit": kwargs["node_limit"],
                "edge_limit": kwargs["edge_limit"],
            },
        }


def write_articles(path: Path, *, include_formula: bool = True) -> None:
    formula_section = "\n\n## 数学形式\n\n$$\nQK^T\n$$\n" if include_formula else ""
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
                        "Attention 用 query 和 key 计算相关性，Transformer 使用 self-attention。"
                        f"{formula_section}"
                    ),
                    "metadata": {
                        "date": "2018-06-01",
                        "category": "信息时代",
                        "references": [],
                        "images": [],
                    },
                },
                {
                    "id": "transformer-001",
                    "title": "Transformer中的位置编码",
                    "url": "https://spaces.ac.cn/archives/6509",
                    "content": "# 位置编码\n\nTransformer 需要位置编码来补充序列信息。Attention 也需要位置信息。",
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


def configure_files(tmp_path: Path, monkeypatch, *, include_formula: bool = True) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file, include_formula=include_formula)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(tmp_path / "learning.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(tmp_path / "zotero_links.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_GRAPH_FILE", str(tmp_path / "knowledge_graph.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_FILE", str(tmp_path / "tutor_sessions.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "fake")


def _tutor_service_with_graph(graph_service: RecordingGraphService, tmp_path: Path):
    from app.tutor.service import TutorService
    from app.zotero.store import ZoteroLinkStore

    return TutorService(
        graph_service=graph_service,
        zotero_store=ZoteroLinkStore(tmp_path / "zotero_links.json"),
    )


def test_tutor_service_does_not_load_graph_without_enabled_explicit_node(tmp_path: Path) -> None:
    from app.tutor.models import TutorRequest

    for include_graph_context, node_id in ((False, "concept:attention"), (True, None), (True, "   ")):
        graph = RecordingGraphService()
        service = _tutor_service_with_graph(graph, tmp_path)
        request = TutorRequest(
            question="attention",
            mode="qa",
            node_id=node_id,
            include_graph_context=include_graph_context,
        )

        context, sources = service._graph_context(request)

        assert graph.calls == []
        assert context == {"nodes": [], "edges": []}
        assert sources == []


def test_tutor_service_uses_bounded_graph_collector_for_explicit_node(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.tutor.models import TutorRequest

    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_NODES", "999")
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES", "999")
    graph = RecordingGraphService()
    service = _tutor_service_with_graph(graph, tmp_path)

    context, sources = service._graph_context(
        TutorRequest(question="attention", mode="qa", node_id="concept:attention")
    )

    assert graph.calls == [
        (
            "get_subgraph",
            {"node_id": "concept:attention", "depth": 2, "node_limit": 20, "edge_limit": 30},
        )
    ]
    assert context["nodes"][0]["node_id"] == "concept:attention"
    assert {source.source_type for source in sources} == {"graph_node", "graph_edge"}


def test_tutor_models_and_citation_policy_require_sources() -> None:
    from app.tutor.models import TutorRequest, TutorSource
    from app.tutor.policy import enforce_grounding

    source = TutorSource(
        source_type="article_chunk",
        source_id="attention-001:0",
        title="Attention机制的一个直观解释",
        url="https://spaces.ac.cn/archives/6508",
        section_title="Attention机制",
        chunk_index=0,
    )
    request = TutorRequest(question="什么是Attention？", mode="explain", top_k=3)

    accepted_answer, refusal = enforce_grounding(mode=request.mode, answer="基于来源的解释", sources=[source])
    refused_answer, refused_reason = enforce_grounding(mode="qa", answer="无来源回答", sources=[])

    assert request.mode == "explain"
    assert source.to_dict()["source_type"] == "article_chunk"
    assert accepted_answer == "基于来源的解释"
    assert refusal is None
    assert "无法基于当前资料回答" in refused_answer
    assert refused_reason == "no_sources"


def test_tutor_ask_modes_are_grounded_and_include_context(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    client.post(
        "/zotero/links/attention-001",
        json={"item_key": "ABCD1234", "relation_type": "cites", "note": "Core attention paper"},
    )
    client.put("/learning/state/attention-001", json={"status": "reading"})
    client.post("/graph/build")

    for mode in ["explain", "derive", "qa", "research"]:
        response = client.post(
            "/tutor/ask",
            json={
                "question": "什么是Attention？",
                "mode": mode,
                "article_id": "attention-001",
                "node_id": "concept:attention",
                "top_k": 3,
                "include_graph_context": True,
                "include_zotero_context": True,
            },
        )
        payload = response.json()

        assert response.status_code == 200
        assert payload["mode"] == mode
        assert payload["refusal_reason"] is None
        assert payload["answer"]
        assert payload["sources"]
        assert any(source["source_type"] == "article_chunk" for source in payload["sources"])
        assert not any(source["source_type"] == "learning_state" for source in payload["sources"])
        assert payload["graph_context"]["nodes"]
        assert payload["graph_context"]["learning_state"]["source_type"] == "learning_state"
        assert payload["graph_context"]["learning_state"]["metadata"]["usage"] == "personalization_only"
        assert payload["zotero_context"]
        assert payload["follow_up_questions"]


def test_tutor_derive_refuses_when_formula_source_is_missing(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch, include_formula=False)
    client = TestClient(app)

    response = client.post(
        "/tutor/ask",
        json={"question": "推导Attention公式", "mode": "derive", "article_id": "attention-001", "top_k": 3},
    )
    payload = response.json()

    assert response.status_code == 200
    assert "当前资料不足以完整推导" in payload["answer"]
    assert payload["refusal_reason"] == "insufficient_formula_sources"


def test_tutor_no_source_refuses_without_fabricating_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(tmp_path / "learning.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(tmp_path / "zotero_links.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_GRAPH_FILE", str(tmp_path / "knowledge_graph.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_FILE", str(tmp_path / "tutor_sessions.json"))
    client = TestClient(app)

    response = client.post("/tutor/ask", json={"question": "什么是Attention？", "mode": "explain"})
    payload = response.json()

    assert response.status_code == 200
    assert "无法基于当前资料回答" in payload["answer"]
    assert payload["sources"] == []
    assert payload["refusal_reason"] == "no_sources"

    research_response = client.post("/tutor/ask", json={"question": "给出研究路线", "mode": "research"})
    research_payload = research_response.json()

    assert research_response.status_code == 200
    assert "无法基于当前资料形成可靠研究建议" in research_payload["answer"]
    assert research_payload["sources"] == []
    assert research_payload["refusal_reason"] == "no_sources"


def test_tutor_quiz_questions_have_sources(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.post("/tutor/quiz", json={"article_id": "attention-001", "num_questions": 2})
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["questions"]) == 2
    for question in payload["questions"]:
        assert question["question"]
        assert question["correct_answer"]
        assert question["explanation"]
        assert question["sources"]
        assert question["sources"][0]["source_type"] == "article_chunk"


def test_tutor_sessions_and_m2_to_m6_regressions(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    session_response = client.post(
        "/tutor/sessions",
        json={"mode": "qa", "article_id": "attention-001", "node_id": "concept:attention"},
    )
    session_id = session_response.json()["session_id"]
    list_response = client.get("/tutor/sessions")
    detail_response = client.get(f"/tutor/sessions/{session_id}")

    article_response = client.get("/articles")
    rag_index_response = client.post("/rag/index")
    rag_query_response = client.post("/rag/query", json={"question": "什么是Attention？"})
    learning_response = client.get("/learning/stats")
    zotero_response = client.get("/zotero/status")
    graph_build_response = client.post("/graph/build")
    graph_response = client.get("/graph")

    assert session_response.status_code == 200
    assert session_response.json()["mode"] == "qa"
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["session_id"] == session_id
    assert detail_response.status_code == 200
    assert detail_response.json()["session_id"] == session_id

    assert article_response.status_code == 200
    assert "attention-001" in {item["id"] for item in article_response.json()["items"]}
    assert rag_index_response.status_code == 200
    assert rag_query_response.status_code == 200
    assert rag_query_response.json()["sources"]
    assert learning_response.status_code == 200
    assert zotero_response.status_code == 200
    assert zotero_response.json()["read_only"] is True
    assert graph_build_response.status_code == 200
    assert graph_response.status_code == 200
    assert graph_response.json()["source_counts"]["articles"] == 2
