import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.graph.service import NodeNotFoundError
from app.main import app
from app.rag.chunking import ArticleChunk
from app.rag.vector_store import SearchResult
from app.tutor.models import TutorRequest
from app.tutor.retrieval import RetrievalResult
from app.tutor.service import TutorService
from app.tutor.source_selection import SourceSelectionPolicy
from app.zotero.models import ZoteroArticleLink
from test_tutor import configure_files


class EmptyRetriever:
    def __init__(self) -> None:
        self.calls = 0

    def retrieve(self, request: TutorRequest, candidate_limit: int) -> RetrievalResult:
        self.calls += 1
        return RetrievalResult(results=[], locally_supported=True)


class StaticRetriever:
    def __init__(self, results: list[SearchResult], *, locally_supported: bool = True) -> None:
        self.results = results
        self.locally_supported = locally_supported
        self.calls = 0

    def retrieve(self, request: TutorRequest, candidate_limit: int) -> RetrievalResult:
        self.calls += 1
        return RetrievalResult(
            results=self.results[:candidate_limit],
            locally_supported=self.locally_supported,
        )


def article_result(
    *,
    article_id: str = "attention-001",
    chunk_index: int = 0,
    section_title: str = "Attention",
    content: str = "Attention assigns weights to relevant evidence.",
) -> SearchResult:
    return SearchResult(
        chunk=ArticleChunk(
            article_id=article_id,
            article_title="Attention foundations",
            article_url=f"https://example.test/{article_id}",
            section_title=section_title,
            chunk_index=chunk_index,
            content=content,
        ),
        score=0.1 + chunk_index,
    )


class ExplicitNodeGraphService:
    def get_subgraph(self, node_id: str, **kwargs: object) -> dict[str, object]:
        return {
            "nodes": [
                {
                    "node_id": node_id,
                    "node_type": "concept",
                    "label": "Attention",
                    "source_id": "attention",
                    "source_url": "https://spaces.ac.cn/archives/6508",
                    "metadata": {"source_count": 1, "truncated": False, "sources": []},
                }
            ],
            "edges": [
                {
                    "edge_id": "attention-edge",
                    "edge_type": "mentions",
                    "source_node_id": node_id,
                    "target_node_id": "attention-001",
                    "evidence": {"score": 0.9},
                }
            ],
            **{k: v for k, v in kwargs.items()},
        }


class FailingGraphService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def get_subgraph(self, node_id: str, **kwargs: object) -> dict[str, object]:
        raise self.error


class OversizedGraphService:
    def get_subgraph(self, node_id: str, **kwargs: object) -> dict[str, object]:
        nodes = [
            {
                "node_id": node_id if index == 0 else f"concept:neighbor-{index}",
                "node_type": "concept",
                "label": "Attention" if index == 0 else f"Neighbor {index}",
            }
            for index in range(25)
        ]
        edges = [
            {
                "edge_id": f"edge:{index}",
                "edge_type": "related_to",
                "source_node_id": node_id,
                "target_node_id": f"concept:neighbor-{index + 1}",
            }
            for index in range(35)
        ]
        return {"nodes": nodes, "edges": edges}


class PayloadHeavyGraphService:
    def get_subgraph(self, node_id: str, **_kwargs: object) -> dict[str, object]:
        nodes = [
            {
                "node_id": node_id if index == 0 else f"concept:neighbor-{index}",
                "node_type": "concept",
                "label": "Attention" if index == 0 else f"Neighbor {index}",
                "evidence": {"detail": f"node-{index}-" + ("x" * 1000)},
                "metadata": {
                    "description": f"metadata-{index}-" + ("y" * 1000),
                    "source_count": 255 if index == 0 else 1,
                    "truncated": index == 0,
                    "sources": [
                        {
                            "article_id": f"article-{source_index}",
                            "article_url": f"https://spaces.ac.cn/archives/{6500 + source_index}",
                            "evidence": "z" * 500,
                        }
                        for source_index in range(10)
                    ],
                },
            }
            for index in range(25)
        ]
        edges = [
            {
                "edge_id": f"edge:{index}",
                "edge_type": "related_to",
                "source_node_id": node_id,
                "target_node_id": f"concept:neighbor-{index + 1}",
                "evidence": {"detail": f"edge-{index}-" + ("q" * 1000)},
            }
            for index in range(35)
        ]
        return {"nodes": nodes, "edges": edges}


class OversizedZoteroStore:
    def list_links(self, article_id: str) -> list[ZoteroArticleLink]:
        return [
            ZoteroArticleLink(
                article_id=article_id,
                zotero_item_key=f"ITEM{index:02d}",
                relation_type="cites",
                created_at="2026-07-10T00:00:00Z",
                note="/home/user/private/zotero-note.txt",
            )
            for index in range(20)
        ]


class OversizedZoteroProvider:
    def get_item(self, item_key: str) -> SimpleNamespace:
        return SimpleNamespace(
            to_dict=lambda: {
                "item_key": item_key,
                "title": "Attention " * 1000,
                "url": "https://example.test/papers/attention",
                "abstract_note": "bounded evidence " * 1000,
                "creators": [f"Creator {index}" for index in range(100)],
                "tags": [f"tag-{index}" for index in range(100)],
                "collections": [f"collection-{index}" for index in range(100)],
                "attachment_path": "/home/user/private/paper.pdf",
            }
        )


class UnsafeIdentityZoteroStore:
    def list_links(self, article_id: str) -> list[ZoteroArticleLink]:
        return [
            ZoteroArticleLink(
                article_id=article_id,
                zotero_item_key="/home/user/private/item-key",
                relation_type="cites",
                created_at="2026-07-10T00:00:00Z",
            ),
            ZoteroArticleLink(
                article_id=article_id,
                zotero_item_key="X" * 1000,
                relation_type="cites",
                created_at="2026-07-10T00:00:00Z",
            ),
            ZoteroArticleLink(
                article_id=article_id,
                zotero_item_key="SAFE_ITEM_01",
                relation_type="cites",
                created_at="2026-07-10T00:00:00Z",
            ),
        ]


class MissingZoteroProvider:
    def get_item(self, _item_key: str):
        return None


def test_derive_internal_reason_preserves_m7_api_alias(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch, include_formula=False)
    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "derive Attention prose only", "mode": "derive", "article_id": "attention-001", "top_k": 3},
    ).json()

    assert payload["refusal_reason"] == "insufficient_formula_sources"
    assert payload["evidence_summary"]["refusal_reason"] == "insufficient_formula_evidence"
    assert [source["source_type"] for source in payload["sources"]] == ["article_chunk"]


def test_tutor_refuses_article_chunks_that_do_not_answer_the_question(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "zxqv_unrelated_topic_7f3c9a", "mode": "qa", "article_id": "attention-001", "top_k": 3},
    ).json()

    assert payload["refusal_reason"] == "no_sources"
    assert payload["sources"] == []
    assert payload["evidence_summary"]["refusal_reason"] == "no_relevant_source"


def test_tutor_ask_adds_selection_and_evidence_summaries(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "attention", "mode": "explain", "article_id": "attention-001", "top_k": 3},
    ).json()

    assert payload["selection_summary"]["candidate_count"] >= 1
    assert payload["selection_summary"]["selected_article_count"] >= 1
    assert payload["selection_summary"]["context_character_count"] > 0
    assert payload["selection_summary"]["selected_chunk_count"] == len(
        [source for source in payload["sources"] if source["source_type"] == "article_chunk"]
    )
    assert payload["evidence_summary"]["source_count"] >= 1
    assert payload["evidence_summary"]["article_count"] >= 1
    assert payload["evidence_summary"]["refusal_reason"] is None


def test_tutor_research_requires_two_articles_even_when_explicitly_scoped(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_files(tmp_path, monkeypatch)

    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "attention 研究路线", "mode": "research", "article_id": "attention-001", "top_k": 6},
    ).json()

    assert payload["refusal_reason"] == "no_sources"
    assert payload["sources"] == []
    assert payload["evidence_summary"]["article_count"] == 1
    assert payload["evidence_summary"]["refusal_reason"] == "insufficient_local_corpus_evidence"
    assert "无法基于当前资料形成可靠研究建议" in payload["answer"]


def test_tutor_research_enforces_diversity_when_multiple_articles_available(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "attention 和 位置编码 相关", "mode": "research", "top_k": 6},
    ).json()

    article_sources = [source for source in payload["sources"] if source["source_type"] == "article_chunk"]
    assert len(article_sources) >= 2
    article_ids = {source["metadata"].get("article_id") for source in article_sources}
    assert len(article_ids) >= 2
    assert "本地" in payload["answer"] or "本地文章" in payload["answer"]


def test_tutor_unsupported_query_maps_to_no_sources_alias(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    payload = client.post(
        "/tutor/ask",
        json={"question": "请给我今天的实时新闻", "mode": "explain", "top_k": 3},
    ).json()

    assert payload["refusal_reason"] == "no_sources"
    assert payload["evidence_summary"]["refusal_reason"] == "unsupported_query"


def test_tutor_respects_optional_and_bounded_zotero_context(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)
    for index in range(8):
        response = client.post(
            "/zotero/links/attention-001",
            json={"item_key": f"ZOTERO{index:02d}", "relation_type": "cites"},
        )
        assert response.status_code == 200

    excluded = client.post(
        "/tutor/ask",
        json={
            "question": "attention",
            "mode": "explain",
            "article_id": "attention-001",
            "include_zotero_context": False,
        },
    ).json()
    included = client.post(
        "/tutor/ask",
        json={"question": "attention", "mode": "explain", "article_id": "attention-001"},
    ).json()

    assert excluded["zotero_context"] == []
    assert not any(source["source_type"] == "zotero_item" for source in excluded["sources"])
    assert len(included["zotero_context"]) == 6
    assert len([source for source in included["sources"] if source["source_type"] == "zotero_item"]) == 6


def test_tutor_graph_only_cannot_answer_without_article_chunk_sources(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    service = TutorService(retriever=EmptyRetriever(), graph_service=ExplicitNodeGraphService())
    payload = service.answer(
        TutorRequest(
            question="attention 相关问题",
            mode="qa",
            node_id="concept:attention",
            top_k=3,
            include_graph_context=True,
        )
    ).to_dict()

    assert payload["refusal_reason"] == "no_sources"
    assert payload["sources"] == []
    assert payload["evidence_summary"]["refusal_reason"] == "no_relevant_source"


def test_derive_with_zero_article_evidence_preserves_no_source_compatibility(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_files(tmp_path, monkeypatch)
    service = TutorService(retriever=EmptyRetriever())

    payload = service.answer(
        TutorRequest(
            question="derive attention",
            mode="derive",
            article_id="missing-article",
        )
    ).to_dict()

    assert payload["refusal_reason"] == "no_sources"
    assert payload["sources"] == []
    assert payload["evidence_summary"]["refusal_reason"] == "no_relevant_source"


def test_tutor_article_miss_does_not_start_a_second_retrieval_route(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_files(tmp_path, monkeypatch)
    retriever = EmptyRetriever()
    service = TutorService(retriever=retriever)

    payload = service.answer(
        TutorRequest(
            question="attention",
            mode="qa",
            article_id="attention-001",
        )
    ).to_dict()

    assert retriever.calls == 1
    assert payload["refusal_reason"] == "no_sources"
    assert payload["sources"] == []


@pytest.mark.parametrize(
    ("topic", "locally_supported"),
    [
        ("quantum chromodynamics", True),
        ("latest weather", False),
    ],
)
def test_tutor_quiz_honors_evidence_refusal_and_topic_relevance(
    topic: str,
    locally_supported: bool,
) -> None:
    service = TutorService(
        retriever=StaticRetriever(
            [article_result(content="Attention assigns weights to token evidence.")],
            locally_supported=locally_supported,
        )
    )

    assert service.quiz(topic=topic, num_questions=1) == []


def test_tutor_quiz_uses_unique_auditable_evidence_units() -> None:
    sources = [
        article_result(
            chunk_index=0,
            section_title="Shared section",
            content="Attention query weights identify relevant tokens.",
        ),
        article_result(
            chunk_index=1,
            section_title="Shared section",
            content="Attention values combine the selected token representations.",
        ),
    ]
    service = TutorService(retriever=StaticRetriever(sources))

    questions = service.quiz(topic="attention", num_questions=2)

    assert len(questions) == 2
    assert len({question.question for question in questions}) == 2
    assert [question.sources[0].source_id for question in questions] == [
        "attention-001:0",
        "attention-001:1",
    ]


def test_tutor_selection_summary_counts_bounded_explicit_graph_context(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    service = TutorService(graph_service=ExplicitNodeGraphService())

    payload = service.answer(
        TutorRequest(
            question="attention",
            mode="qa",
            article_id="attention-001",
            node_id="concept:attention",
            include_graph_context=True,
        )
    ).to_dict()

    assert payload["selection_summary"]["graph_node_count"] == 1
    assert payload["selection_summary"]["graph_edge_count"] == 1


def test_tutor_selection_summary_includes_graph_truncation() -> None:
    service = TutorService(
        retriever=StaticRetriever([article_result()]),
        graph_service=OversizedGraphService(),
    )

    payload = service.answer(
        TutorRequest(
            question="attention",
            mode="qa",
            node_id="concept:attention",
            include_graph_context=True,
        )
    ).to_dict()

    assert payload["selection_summary"]["graph_node_count"] == 20
    assert payload["selection_summary"]["graph_edge_count"] == 30
    assert payload["selection_summary"]["truncated"] is True
    assert payload["selection_summary"]["supplement_omitted_count"] == 10


def test_tutor_zotero_supplements_are_count_and_payload_bounded_and_path_safe(monkeypatch) -> None:
    monkeypatch.setattr("app.tutor.service.get_zotero_provider", lambda: OversizedZoteroProvider())
    service = TutorService(
        zotero_store=OversizedZoteroStore(),
        source_selection_policy=SourceSelectionPolicy(max_source_articles=6),
    )

    context, sources, omitted_count = service._zotero_context("attention-001")
    serialized = json.dumps(
        {"context": context, "sources": [source.to_dict() for source in sources]},
        ensure_ascii=False,
    )

    assert 1 <= len(context) <= 6
    assert len(sources) == len(context)
    assert omitted_count == 20 - len(context)
    assert len(context[0]["item"]["abstract_note"]) <= 1000
    assert len(context[0]["item"]["creators"]) <= 20
    assert context[0]["item"]["url"] == "https://example.test/papers/attention"
    assert "/home/user/private" not in serialized
    assert "attachment_path" not in serialized


def test_tutor_skips_unsafe_or_oversized_zotero_source_identities(monkeypatch) -> None:
    monkeypatch.setattr("app.tutor.service.get_zotero_provider", lambda: MissingZoteroProvider())
    service = TutorService(zotero_store=UnsafeIdentityZoteroStore())

    context, sources, omitted_count = service._zotero_context("attention-001")
    serialized = json.dumps(
        {"context": context, "sources": [source.to_dict() for source in sources]},
        ensure_ascii=False,
    )

    assert [source.source_id for source in sources] == ["SAFE_ITEM_01"]
    assert omitted_count == 2
    assert context[0]["item"]["item_key"] == "SAFE_ITEM_01"
    assert "/home/user/private" not in serialized
    assert "X" * 257 not in serialized


def test_tutor_applies_one_aggregate_budget_to_all_supplemental_response_data(monkeypatch) -> None:
    monkeypatch.setattr("app.tutor.service.get_zotero_provider", lambda: OversizedZoteroProvider())
    monkeypatch.setattr("app.tutor.service.MAX_TUTOR_SUPPLEMENT_RESPONSE_CHARS", 20_000)
    service = TutorService(
        retriever=StaticRetriever([article_result()]),
        graph_service=PayloadHeavyGraphService(),
        zotero_store=OversizedZoteroStore(),
    )

    payload = service.answer(
        TutorRequest(
            question="attention",
            mode="qa",
            article_id="attention-001",
            node_id="concept:attention",
            include_graph_context=True,
            include_zotero_context=True,
        )
    ).to_dict()
    supplemental_sources = [
        source
        for source in payload["sources"]
        if source["source_type"] in {"graph_node", "graph_edge", "zotero_item"}
    ]
    supplemental_payload = {
        "graph_context": payload["graph_context"],
        "zotero_context": payload["zotero_context"],
        "sources": supplemental_sources,
    }
    serialized = json.dumps(supplemental_payload, ensure_ascii=False, separators=(",", ":"))

    assert len(serialized) <= 20_000
    assert payload["selection_summary"]["truncated"] is True
    assert payload["selection_summary"]["supplement_omitted_count"] > 0
    assert len(payload["graph_context"]["nodes"]) <= 20
    assert len(payload["graph_context"]["edges"]) <= 30
    assert len(payload["zotero_context"]) <= 6
    assert payload["selection_summary"]["graph_node_count"] == len(payload["graph_context"]["nodes"])
    assert payload["selection_summary"]["graph_edge_count"] == len(payload["graph_context"]["edges"])
    if payload["graph_context"]["nodes"]:
        assert payload["graph_context"]["nodes"][0]["node_id"] == "concept:attention"


@pytest.mark.parametrize(
    ("error", "expected_error_code"),
    [
        (NodeNotFoundError("Graph node not found: concept:missing"), "graph_node_not_found"),
        (OSError("graph store unavailable"), "graph_unavailable"),
    ],
)
def test_tutor_preserves_safe_graph_diagnostics_when_article_answer_continues(
    tmp_path: Path,
    monkeypatch,
    error: Exception,
    expected_error_code: str,
) -> None:
    configure_files(tmp_path, monkeypatch)
    service = TutorService(graph_service=FailingGraphService(error))

    payload = service.answer(
        TutorRequest(
            question="attention",
            mode="qa",
            article_id="attention-001",
            node_id="concept:missing",
            include_graph_context=True,
        )
    ).to_dict()

    assert payload["refusal_reason"] is None
    assert any(source["source_type"] == "article_chunk" for source in payload["sources"])
    assert not any(source["source_type"].startswith("graph_") for source in payload["sources"])
    assert payload["graph_context"]["nodes"] == []
    assert payload["graph_context"]["edges"] == []
    assert payload["selection_summary"]["graph_error_code"] == expected_error_code
    assert payload["selection_summary"]["graph_latency_ms"] >= 0


def test_tutor_api_returns_503_on_configured_index_failure(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    monkeypatch.setenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", str(tmp_path / "missing-full-corpus-index"))
    response = TestClient(app).post(
        "/tutor/ask",
        json={"question": "attention", "mode": "explain", "top_k": 3},
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_tutor_api_does_not_bypass_missing_configured_index_for_explicit_article(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_files(tmp_path, monkeypatch)
    monkeypatch.setenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", str(tmp_path / "missing-full-corpus-index"))

    response = TestClient(app).post(
        "/tutor/ask",
        json={
            "question": "attention",
            "mode": "explain",
            "article_id": "attention-001",
            "top_k": 3,
        },
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]
