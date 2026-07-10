from app.rag.chunking import ArticleChunk
from app.rag.vector_store import SearchResult
from app.tutor.source_selection import (
    SourceSelectionPolicy,
    SourceSelector,
    TutorSourceConfigurationError,
)


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
    assert policy.max_graph_nodes == 100
    assert policy.max_graph_edges == 200


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


def test_graph_context_requires_explicit_node_id_and_is_bounded() -> None:
    selector = SourceSelector(SourceSelectionPolicy(max_graph_nodes=1, max_graph_edges=1))
    graph_context = {
        "nodes": [
            {"node_id": "concept:attention", "node_type": "concept", "label": "Attention", "provenance": [1, 2, 3]},
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
    assert len(explicit.graph_context["nodes"][0]["provenance"]) == 2


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
