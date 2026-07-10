from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pytest

from app.rag.chunking import ArticleChunk
from app.rag.full_corpus import FullCorpusIndexError, FullCorpusRagService, build_full_corpus_index
from app.rag.service import NO_SOURCE_ANSWER
from app.rag.vector_store import SearchResult
from app.tutor import retrieval
from app.tutor.models import TutorRequest
from app.tutor.retrieval import ConfiguredTutorRetriever
from app.tutor.source_selection import (
    SourceSelectionPolicy,
    SourceSelector,
    TutorSourceConfigurationError,
    sanitize_graph_context,
)
from app.tutor.graph_context import collect_graph_context


def tutor_request(question: str, *, article_id: str | None = None) -> TutorRequest:
    return TutorRequest(question=question, mode="qa", article_id=article_id)


def _article(article_id: str, content: str) -> dict[str, object]:
    return {
        "id": article_id,
        "title": f"Article {article_id}",
        "url": f"https://spaces.ac.cn/archives/{article_id}",
        "content": content,
        "metadata": {"date": "2024-01-01", "category": "math", "references": [], "images": []},
    }


@pytest.fixture
def built_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    store.write_text(
        json.dumps(
            [
                _article("attention", "# Attention\n\nattention transformer query key value"),
                _article("matrix", "# Matrix\n\nmatrix singular value decomposition"),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    build_full_corpus_index(article_store_path=store, output_dir=output, provider_name="fake", rebuild=True)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(store))
    monkeypatch.setenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", str(output))
    retrieval.reset_configured_retriever_cache()
    return store, output


@pytest.mark.parametrize("direct_index_dir", [False, True], ids=["root-directory", "direct-index-directory"])
def test_configured_retriever_reuses_loaded_full_corpus_index(
    monkeypatch: pytest.MonkeyPatch,
    built_index: tuple[Path, Path],
    direct_index_dir: bool,
) -> None:
    _, output = built_index
    monkeypatch.setenv(
        "SCIENTIFIC_SPACES_RAG_INDEX_DIR",
        str(output / "index" if direct_index_dir else output),
    )
    loads = 0
    original_load = retrieval.FullCorpusRagService.load

    def counting_loader(*args, **kwargs):
        nonlocal loads
        loads += 1
        return original_load(*args, **kwargs)

    monkeypatch.setattr(retrieval.FullCorpusRagService, "load", counting_loader)
    retriever = ConfiguredTutorRetriever()

    first = retriever.retrieve(tutor_request("attention"), candidate_limit=20)
    second = retriever.retrieve(tutor_request("transformer"), candidate_limit=20)

    assert first.results and second.results
    assert loads == 1


def test_cache_root_resolution_ignores_non_file_manifest(
    monkeypatch: pytest.MonkeyPatch,
    built_index: tuple[Path, Path],
) -> None:
    _, output = built_index
    (output / "manifest.json").mkdir()
    nested_manifest = output / "index" / "manifest.json"
    loads = 0
    original_load = retrieval.FullCorpusRagService.load

    def counting_loader(*args, **kwargs):
        nonlocal loads
        loads += 1
        return original_load(*args, **kwargs)

    monkeypatch.setattr(retrieval.FullCorpusRagService, "load", counting_loader)
    retriever = ConfiguredTutorRetriever()

    first = retriever.retrieve(tutor_request("attention"), candidate_limit=20)
    stat = nested_manifest.stat()
    os.utime(nested_manifest, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
    second = retriever.retrieve(tutor_request("transformer"), candidate_limit=20)

    assert first.results and second.results
    assert loads == 2


def test_explicit_article_id_retrieval_never_returns_other_articles(built_index: tuple[Path, Path]) -> None:
    del built_index

    result = ConfiguredTutorRetriever().retrieve(tutor_request("matrix attention", article_id="attention"), candidate_limit=20)

    assert result.results
    assert {item.chunk.article_id for item in result.results} == {"attention"}


def test_configured_corrupt_index_fails_closed(built_index: tuple[Path, Path]) -> None:
    _, output = built_index
    (output / "index" / "faiss.index").write_bytes(b"corrupt")
    retrieval.reset_configured_retriever_cache()

    with pytest.raises(FullCorpusIndexError):
        ConfiguredTutorRetriever().retrieve(tutor_request("attention"), candidate_limit=20)


def test_full_corpus_rag_service_preserves_no_source_answer_for_zero_top_k(
    built_index: tuple[Path, Path],
) -> None:
    store, output = built_index
    service = FullCorpusRagService.load(article_store_path=store, index_dir=output)

    assert service.search(question="attention", top_k=0) == []
    assert service.answer(question="attention", top_k=0) == {
        "answer": NO_SOURCE_ANSWER,
        "sources": [],
    }


def test_unconfigured_retriever_uses_small_fixture_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = tmp_path / "articles.json"
    store.write_text(json.dumps([_article("attention", "# Attention\n\nattention transformer")]), encoding="utf-8")
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(store))
    monkeypatch.delenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", raising=False)
    retrieval.reset_configured_retriever_cache()

    result = ConfiguredTutorRetriever().retrieve(tutor_request("attention"), candidate_limit=20)

    assert [item.chunk.article_id for item in result.results] == ["attention"]


def test_unconfigured_retriever_rejects_query_without_local_token_support(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = tmp_path / "articles.json"
    store.write_text(json.dumps([_article("attention", "# Attention\n\nattention transformer")]), encoding="utf-8")
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(store))
    monkeypatch.delenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", raising=False)
    search_calls = 0
    original_search = retrieval.FaissVectorStore.search

    def counting_search(*args, **kwargs):
        nonlocal search_calls
        search_calls += 1
        return original_search(*args, **kwargs)

    monkeypatch.setattr(retrieval.FaissVectorStore, "search", counting_search)

    result = ConfiguredTutorRetriever().retrieve(tutor_request("zxqv_unsupported_7f3c9a"), candidate_limit=20)

    assert result.results == []
    assert result.locally_supported is False
    assert search_calls == 0


def test_explicit_article_retriever_rejects_query_without_local_token_support(
    monkeypatch: pytest.MonkeyPatch,
    built_index: tuple[Path, Path],
) -> None:
    del built_index
    search_calls = 0
    original_search = retrieval.FaissVectorStore.search

    def counting_search(*args, **kwargs):
        nonlocal search_calls
        search_calls += 1
        return original_search(*args, **kwargs)

    monkeypatch.setattr(retrieval.FaissVectorStore, "search", counting_search)

    result = ConfiguredTutorRetriever().retrieve(
        tutor_request("zxqv_unsupported_7f3c9a", article_id="attention"),
        candidate_limit=20,
    )

    assert result.results == []
    assert result.locally_supported is False
    assert search_calls == 0


def test_fake_provider_retrieval_never_accesses_network(
    monkeypatch: pytest.MonkeyPatch,
    built_index: tuple[Path, Path],
) -> None:
    del built_index

    def reject_network(*_args, **_kwargs):
        raise AssertionError("fake provider must not access the network")

    monkeypatch.setattr(urllib.request, "urlopen", reject_network)

    result = ConfiguredTutorRetriever().retrieve(tutor_request("attention"), candidate_limit=20)

    assert result.results


def result(article_id: str, chunk_index: int, score: float) -> SearchResult:
    return SearchResult(
        chunk=ArticleChunk(
            article_id=article_id,
            article_title=f"Article {article_id}",
            article_url=f"https://spaces.ac.cn/archives/{article_id}",
            section_title=f"Section {chunk_index}",
            chunk_index=chunk_index,
            content=f"attention evidence {article_id} {chunk_index}",
        ),
        score=score,
    )


def custom_result(
    *,
    article_id: str = "attention",
    article_title: str = "Attention foundations",
    article_url: str = "https://spaces.ac.cn/archives/attention",
    section_title: str = "Definition",
    chunk_index: int = 0,
    content: str = "Attention is a mechanism that assigns weights to evidence.",
    score: float = 0.1,
) -> SearchResult:
    return SearchResult(
        chunk=ArticleChunk(
            article_id=article_id,
            article_title=article_title,
            article_url=article_url,
            section_title=section_title,
            chunk_index=chunk_index,
            content=content,
        ),
        score=score,
    )


def test_selector_deduplicates_groups_and_caps_chunks_per_article() -> None:
    policy = SourceSelectionPolicy(
        candidate_chunk_limit=20,
        max_source_articles=2,
        max_final_chunks=3,
        max_chunks_per_article=2,
    )
    results = [
        result("a", 0, 0.1),
        result("a", 0, 0.1),
        result("a", 1, 0.2),
        result("a", 2, 0.3),
        result("b", 0, 0.4),
    ]

    selected = SourceSelector(policy).select(query="attention", mode="qa", results=results, requested_chunks=10)

    assert [item.chunk_id for item in selected.selected] == ["a:0", "a:1", "b:0"]
    assert selected.summary.duplicate_chunk_count == 1
    assert selected.summary.budget_violation is False


def test_policy_from_env_clamps_values_and_rejects_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_SOURCE_ARTICLES", "99")
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_CHUNKS", "19")
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_NODES", "101")
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES", "0")

    try:
        SourceSelectionPolicy.from_env()
    except TutorSourceConfigurationError as error:
        assert "SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES" in str(error)
    else:
        raise AssertionError("non-positive environment values must fail closed")

    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES", "999")
    policy = SourceSelectionPolicy.from_env()

    assert policy.max_source_articles == 12
    assert policy.max_final_chunks == 19
    assert policy.max_graph_nodes == 20
    assert policy.max_graph_edges == 30


@pytest.mark.parametrize(
    ("override", "value"),
    [("max_graph_nodes", 21), ("max_graph_edges", 31), ("max_graph_depth", 3)],
)
def test_policy_rejects_graph_limits_above_hard_maxima(override: str, value: int) -> None:
    with pytest.raises(TutorSourceConfigurationError, match=override):
        SourceSelectionPolicy(**{override: value})


def test_derive_requires_article_formula_evidence() -> None:
    selector = SourceSelector(SourceSelectionPolicy())

    accepted = selector.select(
        query="derive attention",
        mode="derive",
        results=[custom_result(content="The derivation is $$QK^T / sqrt(d)$$.")],
        requested_chunks=1,
    )
    refused = selector.select(
        query="derive attention",
        mode="derive",
        results=[custom_result(content="Attention has useful applications.")],
        requested_chunks=1,
    )

    assert accepted.evidence.has_formula_evidence is True
    assert accepted.evidence.refusal_reason is None
    assert refused.evidence.has_formula_evidence is False
    assert refused.evidence.refusal_reason == "insufficient_formula_evidence"


def test_selector_marks_definition_and_unsupported_local_scope() -> None:
    selector = SourceSelector(SourceSelectionPolicy())

    defined = selector.select(
        query="what is attention",
        mode="explain",
        results=[custom_result()],
        requested_chunks=1,
    )
    unsupported = selector.select(
        query="latest weather in Beijing",
        mode="qa",
        results=[custom_result()],
        requested_chunks=1,
        locally_supported=False,
    )

    assert defined.evidence.has_definition_evidence is True
    assert defined.evidence.has_answerable_evidence is True
    assert unsupported.evidence.unsupported_or_out_of_scope is True
    assert unsupported.evidence.refusal_reason == "unsupported_query"


def test_selector_recognizes_chinese_query_overlap() -> None:
    selected = SourceSelector(SourceSelectionPolicy()).select(
        query="什么是注意力机制",
        mode="explain",
        results=[
            custom_result(
                article_title="注意力机制基础",
                content="注意力机制是为不同证据分配权重的方法。",
            )
        ],
        requested_chunks=1,
    )

    assert selected.evidence.has_answerable_evidence is True
    assert selected.evidence.refusal_reason is None


def test_selector_rejects_invalid_source_metadata() -> None:
    selected = SourceSelector(SourceSelectionPolicy()).select(
        query="attention",
        mode="qa",
        results=[custom_result(article_url="file:///private/article.md")],
        requested_chunks=1,
    )

    assert selected.evidence.source_schema_valid is False
    assert selected.evidence.refusal_reason == "invalid_source_schema"


def test_research_selection_is_deterministic_and_uses_distinct_articles() -> None:
    selector = SourceSelector(SourceSelectionPolicy(max_source_articles=3, max_final_chunks=4))
    results = [
        custom_result(article_id="a", article_title="Attention mechanisms", section_title="Overview", score=0.1),
        custom_result(article_id="a", article_title="Attention mechanisms", section_title="Details", chunk_index=1, score=0.2),
        custom_result(article_id="b", article_title="Transformer position encoding", score=0.3),
        custom_result(article_id="c", article_title="Optimization geometry", score=0.4),
    ]

    first = selector.select(query="attention", mode="research", results=results, requested_chunks=4)
    second = selector.select(query="attention", mode="research", results=results, requested_chunks=4)

    assert [item.chunk_id for item in first.selected] == [item.chunk_id for item in second.selected]
    assert len({item.source.metadata["article_id"] for item in first.selected}) >= 2
    assert first.evidence.refusal_reason is None


def test_research_selects_distinct_articles_before_second_chunks() -> None:
    selector = SourceSelector(SourceSelectionPolicy())
    results = [
        custom_result(article_id="a", chunk_index=0, score=0.1),
        custom_result(article_id="a", chunk_index=1, score=0.2),
        custom_result(article_id="b", chunk_index=0, score=0.3),
    ]

    selected = selector.select(query="attention", mode="research", results=results, requested_chunks=2)

    article_ids = {item.result.chunk.article_id for item in selected.selected}
    assert article_ids == {"a", "b"}
    assert selected.evidence.refusal_reason is None


def test_graph_context_requires_explicit_node_id_and_is_bounded() -> None:
    selector = SourceSelector(SourceSelectionPolicy(max_graph_nodes=1, max_graph_edges=1))
    graph_context = {
        "nodes": [
            {
                "node_id": "concept:attention",
                "node_type": "concept",
                "label": "Attention",
                "metadata": {
                    "normalized": "attention",
                    "source_count": 3,
                    "truncated": True,
                    "sources": [
                        {"article_id": "attention", "article_url": "https://spaces.ac.cn/archives/attention"},
                        {"article_id": "query", "article_url": "https://spaces.ac.cn/archives/query"},
                        {"article_id": "value", "article_url": "https://spaces.ac.cn/archives/value"},
                    ],
                },
            },
            {"node_id": "concept:query", "node_type": "concept", "label": "Query"},
        ],
        "edges": [
            {"edge_id": "edge:1", "edge_type": "related_to", "source_node_id": "concept:attention", "target_node_id": "concept:query"},
            {"edge_id": "edge:2", "edge_type": "related_to", "source_node_id": "concept:query", "target_node_id": "concept:attention"},
        ],
    }

    implicit = selector.select(query="attention", mode="qa", results=[custom_result()], requested_chunks=1, graph_context=graph_context)
    explicit = selector.select(
        query="attention",
        mode="qa",
        results=[custom_result()],
        requested_chunks=1,
        graph_context={**graph_context, "node_id": "concept:attention"},
    )

    assert implicit.graph_context == {"nodes": (), "edges": ()}
    assert len(explicit.graph_context["nodes"]) == 1
    assert len(explicit.graph_context["edges"]) == 1
    assert len(explicit.graph_context["nodes"][0]["metadata"]["sources"]) == 2


class SpyGraphService:
    def __init__(self, subgraph: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self.calls = 0
        self.subgraph = subgraph or {"nodes": [], "edges": []}
        self.error = error
        self.call_args: dict[str, object] | None = None

    def get_subgraph(self, node_id: str, **kwargs: object) -> dict[str, object]:
        self.calls += 1
        self.call_args = {"node_id": node_id, **kwargs}
        if self.error:
            raise self.error
        return self.subgraph


def test_graph_context_is_not_loaded_without_explicit_node_id() -> None:
    graph = SpyGraphService()

    result = collect_graph_context(graph, node_id=None, policy=SourceSelectionPolicy())

    assert graph.calls == 0
    assert result.context == {"nodes": [], "edges": []}
    assert result.supplemental_sources == ()
    assert result.error_code is None


def test_high_degree_graph_concept_context_is_bounded_and_sanitized() -> None:
    root = {
        "node_id": "concept:attention",
        "node_type": "concept",
        "label": "Attention",
        "source_url": "file:///private/graph.json",
        "metadata": {
            "normalized": "attention",
            "source_count": 255,
            "truncated": True,
            "sources": [
                {
                    "article_id": "unsafe-first",
                    "article_title": "Unsafe",
                    "article_url": "file:///private/attention.md",
                    "source_context": "/home/private/attention.md",
                    "evidence": "unsafe",
                },
                {
                    "article_id": "safe-first",
                    "article_title": "Attention",
                    "article_url": "https://spaces.ac.cn/archives/6508",
                    "source_context": "Transformer attention",
                    "evidence": "query and key",
                },
                {"article_id": "unsafe-second", "article_url": "ftp://localhost/private.txt"},
                {
                    "article_id": "safe-second",
                    "article_title": "Transformer",
                    "article_url": "https://spaces.ac.cn/archives/6509",
                    "evidence": "safe evidence",
                },
                {"article_id": "safe-third", "article_url": "https://spaces.ac.cn/archives/6510"},
            ],
        },
    }
    nodes = [root, *[
        {"node_id": f"concept:neighbor-{index}", "node_type": "concept", "label": f"Neighbor {index}"}
        for index in range(25)
    ]]
    edges = [
        {
            "edge_id": f"edge:{index}",
            "edge_type": "related_to",
            "source_node_id": "concept:attention",
            "target_node_id": f"concept:neighbor-{index}",
            "evidence": {"article_url": "file:///private/evidence.md", "excerpt": "safe evidence"},
        }
        for index in range(35)
    ]
    graph = SpyGraphService({"nodes": nodes, "edges": edges})

    result = collect_graph_context(graph, node_id="concept:attention", policy=SourceSelectionPolicy())

    assert graph.call_args == {
        "node_id": "concept:attention",
        "depth": 2,
        "node_limit": 20,
        "edge_limit": 30,
    }
    assert len(result.context["nodes"]) <= 20
    assert len(result.context["edges"]) <= 30
    assert len(result.context["nodes"][0]["metadata"]["sources"]) <= 2
    assert result.context["nodes"][0]["metadata"]["source_count"] == 255
    assert result.context["nodes"][0]["metadata"]["truncated"] is True
    assert "source_url" not in result.context["nodes"][0]
    assert [
        source["article_id"] for source in result.context["nodes"][0]["metadata"]["sources"]
    ] == ["safe-first", "safe-second"]
    assert "article_url" not in result.context["edges"][0]["evidence"]
    assert len(result.supplemental_sources) == 50
    assert {source.source_type for source in result.supplemental_sources} == {"graph_node", "graph_edge"}


def test_graph_context_missing_node_degrades_to_article_only() -> None:
    from app.graph.service import NodeNotFoundError

    result = collect_graph_context(
        SpyGraphService(error=NodeNotFoundError("Graph node not found: concept:missing")),
        node_id="concept:missing",
        policy=SourceSelectionPolicy(),
    )

    assert result.context == {"nodes": [], "edges": []}
    assert result.supplemental_sources == ()
    assert result.error_code == "graph_node_not_found"


def test_graph_context_corrupt_store_degrades_to_article_only() -> None:
    result = collect_graph_context(
        SpyGraphService(error=json.JSONDecodeError("bad graph", "{", 1)),
        node_id="concept:attention",
        policy=SourceSelectionPolicy(),
    )

    assert result.context == {"nodes": [], "edges": []}
    assert result.supplemental_sources == ()
    assert result.error_code == "graph_unavailable"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"nodes": [{"node_id": "concept:attention", "node_type": "concept"}], "edges": []},
        {
            "nodes": [
                {"node_id": "concept:attention", "node_type": "concept", "label": "Attention"}
            ],
            "edges": [
                {
                    "edge_id": "edge:bad",
                    "source_node_id": "concept:attention",
                    "edge_type": "related_to",
                }
            ],
        },
    ],
    ids=["wrong-root", "malformed-node", "malformed-edge"],
)
def test_structurally_corrupt_graph_store_degrades_to_article_only(tmp_path: Path, payload: object) -> None:
    from app.graph.service import GraphService
    from app.graph.store import GraphStore

    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(payload), encoding="utf-8")

    result = collect_graph_context(
        GraphService(store=GraphStore(graph_file)),
        node_id="concept:attention",
        policy=SourceSelectionPolicy(),
    )

    assert result.context == {"nodes": [], "edges": []}
    assert result.supplemental_sources == ()
    assert result.error_code == "graph_unavailable"


def test_graph_context_sanitizer_is_idempotent() -> None:
    policy = SourceSelectionPolicy()
    context = {
        "nodes": [
            {
                "node_id": "concept:attention",
                "node_type": "concept",
                "label": "Attention",
                "metadata": {
                    "source_count": 1,
                    "truncated": False,
                    "sources": [{"article_url": "https://spaces.ac.cn/archives/6508", "path": "/tmp/secret"}],
                },
            }
        ],
        "edges": [],
    }

    once, _ = sanitize_graph_context(context, policy)
    twice, _ = sanitize_graph_context(once, policy)

    assert twice == once


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
def test_graph_context_does_not_swallow_programming_errors(error_type: type[Exception]) -> None:
    with pytest.raises(error_type, match="programming error"):
        collect_graph_context(
            SpyGraphService(error=error_type("programming error")),
            node_id="concept:attention",
            policy=SourceSelectionPolicy(),
        )


@pytest.mark.parametrize(
    ("source_url", "expected"),
    [
        ("https://spaces.ac.cn/archives/6508", "https://spaces.ac.cn/archives/6508"),
        ("http://example.test/article", "http://example.test/article"),
        ("file:///private/article.md", None),
        ("ftp://example.test/article", None),
        ("/workspace/article.md", None),
        (r"C:\private\article.md", None),
    ],
)
def test_graph_context_keeps_only_http_source_urls(source_url: str, expected: str | None) -> None:
    context, _ = sanitize_graph_context(
        {
            "nodes": [
                {
                    "node_id": "concept:attention",
                    "node_type": "concept",
                    "label": "Attention",
                    "source_url": source_url,
                    "metadata": {},
                }
            ],
            "edges": [],
        },
        SourceSelectionPolicy(),
    )

    assert context["nodes"][0].get("source_url") == expected


def test_graph_context_sanitizes_identity_evidence_and_metadata_strings() -> None:
    context, _ = sanitize_graph_context(
        {
            "nodes": [
                {
                    "node_id": "/workspace/concept",
                    "node_type": r"C:\private\concept",
                    "label": "../private/label.txt",
                    "source_id": "ftp://localhost/source",
                    "metadata": {
                        "safe": "attention",
                        "workspace": "/workspace/graph.json",
                        "private": "/private/graph.json",
                        "windows": r"C:\private\graph.json",
                        "fragment": "../private/graph.json",
                        "nested": {"unsafe": r"..\private\graph.json", "safe": "evidence"},
                    },
                    "evidence": {"unsafe": "file:///private/evidence", "safe": "weighted lookup"},
                }
            ],
            "edges": [
                {
                    "edge_id": "edge:safe",
                    "edge_type": "related_to",
                    "source_node_id": "/workspace/source",
                    "target_node_id": r"C:\private\target",
                    "evidence": {"unsafe": "ftp://localhost/evidence", "safe": "related"},
                }
            ],
        },
        SourceSelectionPolicy(),
    )

    node = context["nodes"][0]
    edge = context["edges"][0]
    assert node["node_id"] == ""
    assert node["node_type"] == ""
    assert node["label"] == ""
    assert "source_id" not in node
    assert node["metadata"] == {"safe": "attention", "nested": {"safe": "evidence"}}
    assert node["evidence"] == {"safe": "weighted lookup"}
    assert edge["source_node_id"] == ""
    assert edge["target_node_id"] == ""
    assert edge["evidence"] == {"safe": "related"}


def test_graph_context_skips_supplements_with_empty_required_identity() -> None:
    result = collect_graph_context(
        SpyGraphService(
            {
                "nodes": [
                    {"node_id": "", "node_type": "concept", "label": "Missing ID"},
                    {"node_id": "concept:missing-title", "node_type": "concept", "label": ""},
                    {"node_id": "concept:attention", "node_type": "concept", "label": "Attention"},
                ],
                "edges": [
                    {
                        "edge_id": "",
                        "edge_type": "related_to",
                        "source_node_id": "concept:attention",
                        "target_node_id": "concept:query",
                    },
                    {
                        "edge_id": "edge:missing-title",
                        "edge_type": "",
                        "source_node_id": "concept:attention",
                        "target_node_id": "concept:query",
                    },
                    {
                        "edge_id": "edge:attention",
                        "edge_type": "related_to",
                        "source_node_id": "concept:attention",
                        "target_node_id": "concept:query",
                    },
                ],
            }
        ),
        node_id="concept:attention",
        policy=SourceSelectionPolicy(),
    )

    assert [(source.source_type, source.source_id) for source in result.supplemental_sources] == [
        ("graph_node", "concept:attention"),
        ("graph_edge", "edge:attention"),
    ]


def test_context_ceiling_truncates_content_without_losing_citation_identity() -> None:
    selector = SourceSelector(SourceSelectionPolicy(max_context_chars=180))
    content = "Attention is a definition.\n\n" + ("This paragraph is evidence. " * 30)

    selected = selector.select(
        query="attention",
        mode="qa",
        results=[custom_result(content=content)],
        requested_chunks=1,
    )

    assert len(selected.generation_context) <= 180
    assert selected.summary.context_truncated is True
    assert selected.selected[0].source.source_id == "attention:0"
    assert selected.selected[0].source.url == "https://spaces.ac.cn/archives/attention"
    assert selected.selected[0].excerpt
    assert selected.selected[0].excerpt in selected.generation_context
