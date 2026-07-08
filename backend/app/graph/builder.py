from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.graph.extractors import display_concept, extract_concepts, extract_formulas, normalize_concept
from app.graph.models import GraphDocument, GraphEdge, GraphNode, make_edge_id, make_node_id, utc_now
from app.learning.store import LearningStore, learning_store_path
from app.rag.chunking import chunk_article
from app.services.article_reader import list_articles
from app.zotero.provider import get_zotero_provider
from app.zotero.store import ZoteroLinkStore, zotero_store_path

MAX_CONCEPT_SOURCES = 10


class KnowledgeGraphBuilder:
    def __init__(
        self,
        *,
        zotero_store: ZoteroLinkStore | None = None,
    ) -> None:
        self.zotero_store = zotero_store or ZoteroLinkStore(zotero_store_path())

    def build(self) -> GraphDocument:
        articles = list_articles()
        if not articles:
            return GraphDocument(
                nodes=[],
                edges=[],
                built_at=utc_now(),
                source_counts={"articles": 0, "sections": 0, "concepts": 0, "formulas": 0, "zotero_links": 0},
            )

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        category_articles: dict[str, list[str]] = defaultdict(list)
        concept_sources: dict[str, dict[tuple[str, str, str, str, str], dict[str, Any]]] = defaultdict(dict)
        source_counts = {"articles": len(articles), "sections": 0, "concepts": 0, "formulas": 0, "zotero_links": 0}
        provider = get_zotero_provider()
        learning_store = LearningStore(learning_store_path())
        bookmarked_articles = {bookmark.article_id for bookmark in learning_store.list_bookmarks()}

        for article in articles:
            article_node_id = make_node_id("article", article.id)
            learning_state = learning_store.get_state(article.id)
            article_node = GraphNode(
                node_id=article_node_id,
                node_type="article",
                label=article.title,
                source_id=article.id,
                source_url=article.url,
                metadata={
                    "article_id": article.id,
                    **article.metadata,
                    "learning": {
                        **learning_state.to_dict(),
                        "bookmarked": article.id in bookmarked_articles,
                    },
                },
            )
            _add_node(nodes, article_node)

            category = str(article.metadata.get("category") or "").strip()
            if category:
                category_articles[category].append(article_node_id)

            title_concepts = _concepts_by_normalized(article.title)
            category_concepts = _concepts_by_normalized(category)
            for concept in extract_concepts(article.title, category):
                normalized = normalize_concept(concept)
                concept_node_id = make_node_id("concept", normalized)
                if normalized in title_concepts:
                    _record_concept_source(
                        concept_sources,
                        concept=concept,
                        article_id=article.id,
                        article_title=article.title,
                        article_url=article.url,
                        source_type="article_title",
                        source_context=article.title,
                        evidence=title_concepts[normalized],
                    )
                if normalized in category_concepts:
                    _record_concept_source(
                        concept_sources,
                        concept=concept,
                        article_id=article.id,
                        article_title=article.title,
                        article_url=article.url,
                        source_type="metadata_category",
                        source_context=category,
                        evidence=category_concepts[normalized],
                    )
                _add_edge(
                    edges,
                    article_node_id,
                    concept_node_id,
                    "mentions",
                    evidence={"source": "article_metadata", "article_id": article.id, "text": concept},
                )

            chunks = chunk_article(
                article_id=article.id,
                article_title=article.title,
                article_url=article.url,
                content=article.content,
            )
            source_counts["sections"] += len(chunks)
            for chunk in chunks:
                section_key = f"{article.id}:{chunk.chunk_index}:{chunk.section_title}"
                section_node_id = make_node_id("section", section_key)
                section_node = GraphNode(
                    node_id=section_node_id,
                    node_type="section",
                    label=chunk.section_title,
                    source_id=article.id,
                    source_url=article.url,
                    metadata={"article_id": article.id, "chunk_index": chunk.chunk_index},
                )
                _add_node(nodes, section_node)
                _add_edge(
                    edges,
                    article_node_id,
                    section_node_id,
                    "has_section",
                    evidence=chunk.source(),
                )

                section_heading_concepts = _concepts_by_normalized(chunk.section_title)
                section_content_concepts = _concepts_by_normalized(_section_body(chunk.content))
                for concept in extract_concepts(chunk.section_title, chunk.content):
                    normalized = normalize_concept(concept)
                    concept_node_id = make_node_id("concept", normalized)
                    if normalized in section_heading_concepts:
                        _record_concept_source(
                            concept_sources,
                            concept=concept,
                            article_id=article.id,
                            article_title=article.title,
                            article_url=article.url,
                            source_type="section_heading",
                            source_context=chunk.section_title,
                            evidence=section_heading_concepts[normalized],
                            section_title=chunk.section_title,
                            section_node_id=section_node_id,
                            chunk_index=chunk.chunk_index,
                        )
                    if normalized in section_content_concepts:
                        _record_concept_source(
                            concept_sources,
                            concept=concept,
                            article_id=article.id,
                            article_title=article.title,
                            article_url=article.url,
                            source_type="section_content",
                            source_context=chunk.section_title,
                            evidence=section_content_concepts[normalized],
                            section_title=chunk.section_title,
                            section_node_id=section_node_id,
                            chunk_index=chunk.chunk_index,
                        )
                    _add_edge(
                        edges,
                        section_node_id,
                        concept_node_id,
                        "mentions",
                        evidence={**chunk.source(), "text": concept},
                    )

                for formula_index, formula in enumerate(extract_formulas(chunk.content)):
                    formula_node_id = make_node_id("formula", f"{article.id}:{chunk.chunk_index}:{formula_index}:{formula}")
                    formula_node = GraphNode(
                        node_id=formula_node_id,
                        node_type="formula",
                        label=_formula_label(formula),
                        source_id=article.id,
                        source_url=article.url,
                        metadata={"formula": formula, "article_id": article.id, "chunk_index": chunk.chunk_index},
                    )
                    _add_node(nodes, formula_node)
                    _add_edge(
                        edges,
                        section_node_id,
                        formula_node_id,
                        "has_formula",
                        evidence={**chunk.source(), "formula": formula},
                    )

            for link in self.zotero_store.list_links(article.id):
                source_counts["zotero_links"] += 1
                item = provider.get_item(link.zotero_item_key)
                zotero_node_id = make_node_id("zotero_item", link.zotero_item_key)
                zotero_node = GraphNode(
                    node_id=zotero_node_id,
                    node_type="zotero_item",
                    label=item.title if item else link.zotero_item_key,
                    source_id=link.zotero_item_key,
                    source_url=item.url if item else None,
                    metadata=item.to_dict() if item else {"item_key": link.zotero_item_key},
                )
                _add_node(nodes, zotero_node)
                _add_edge(
                    edges,
                    article_node_id,
                    zotero_node_id,
                    link.relation_type,
                    evidence=link.to_dict(),
                )

        for category, article_node_ids in category_articles.items():
            for left, right in zip(article_node_ids[:5], article_node_ids[1:6]):
                _add_edge(
                    edges,
                    left,
                    right,
                    "same_category",
                    evidence={"source": "article_metadata", "category": category},
                    weight=0.5,
                )

        for normalized, sources_by_key in concept_sources.items():
            _add_node(nodes, _concept_node(normalized, sources_by_key.values()))

        source_counts["concepts"] = sum(1 for node in nodes.values() if node.node_type == "concept")
        source_counts["formulas"] = sum(1 for node in nodes.values() if node.node_type == "formula")

        return GraphDocument(
            nodes=sorted(nodes.values(), key=lambda node: node.node_id),
            edges=sorted(edges.values(), key=lambda edge: edge.edge_id),
            built_at=utc_now(),
            source_counts=source_counts,
        )


def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
    nodes.setdefault(node.node_id, node)


def _add_edge(
    edges: dict[str, GraphEdge],
    source_node_id: str,
    target_node_id: str,
    edge_type: str,
    *,
    evidence: dict[str, Any],
    weight: float = 1.0,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not evidence:
        raise ValueError("Graph edges require evidence")
    evidence_key = str(sorted(evidence.items()))
    edge = GraphEdge(
        edge_id=make_edge_id(source_node_id, target_node_id, edge_type, evidence_key),
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        edge_type=edge_type,
        weight=weight,
        evidence=evidence,
        metadata=metadata or {},
    )
    edges.setdefault(edge.edge_id, edge)


def _concept_node(concept: str, sources: Any) -> GraphNode:
    normalized = normalize_concept(concept)
    sorted_sources = sorted(
        sources,
        key=lambda source: (
            str(source["article_id"]),
            str(source["source_type"]),
            str(source.get("section_node_id") or ""),
            str(source["source_context"]),
            str(source["evidence"]),
        ),
    )
    source_count = len(sorted_sources)
    return GraphNode(
        node_id=make_node_id("concept", normalized),
        node_type="concept",
        label=display_concept(concept),
        source_id=normalized,
        metadata={
            "normalized": normalized,
            "source_count": source_count,
            "sources": sorted_sources[:MAX_CONCEPT_SOURCES],
            "truncated": source_count > MAX_CONCEPT_SOURCES,
        },
    )


def _concepts_by_normalized(text: str | None) -> dict[str, str]:
    return {normalize_concept(concept): concept for concept in extract_concepts(text)}


def _record_concept_source(
    concept_sources: dict[str, dict[tuple[str, str, str, str, str], dict[str, Any]]],
    *,
    concept: str,
    article_id: str,
    article_title: str,
    article_url: str,
    source_type: str,
    source_context: str,
    evidence: str,
    section_title: str | None = None,
    section_node_id: str | None = None,
    chunk_index: int | None = None,
) -> None:
    normalized = normalize_concept(concept)
    source = {
        "article_id": article_id,
        "article_title": article_title,
        "article_url": article_url,
        "source_type": source_type,
        "source_context": source_context,
        "evidence": evidence,
    }
    if section_title is not None:
        source["section_title"] = section_title
    if section_node_id is not None:
        source["section_node_id"] = section_node_id
    if chunk_index is not None:
        source["chunk_index"] = chunk_index

    key = (
        article_id,
        source_type,
        section_node_id or "",
        source_context,
        evidence,
    )
    concept_sources[normalized].setdefault(key, source)


def _section_body(content: str) -> str:
    return "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("#")).strip()


def _formula_label(formula: str) -> str:
    collapsed = " ".join(line.strip() for line in formula.splitlines() if line.strip())
    return collapsed[:80] if collapsed else "Formula"
