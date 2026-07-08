from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.graph.service import GraphService, NodeNotFoundError
from app.learning.store import LearningStore, learning_store_path
from app.llm.fake import FakeLLMProvider
from app.llm.provider import LLMProvider, OpenAICompatibleLLMProvider
from app.rag.chunking import ArticleChunk, chunk_article
from app.rag.embeddings import EmbeddingProvider, FakeEmbeddingProvider
from app.rag.vector_store import FaissVectorStore, SearchResult
from app.services.article_reader import article_store_path
from app.storage.article_store import ArticleStore, StoredArticle
from app.tutor.models import QuizQuestion, TutorMode, TutorRequest, TutorResponse, TutorSource
from app.tutor.policy import enforce_grounding, refusal_response
from app.zotero.provider import get_zotero_provider
from app.zotero.store import ZoteroLinkStore, zotero_store_path


@dataclass(frozen=True)
class TutorContext:
    article_sources: list[TutorSource]
    rag_contexts: list[dict[str, str]]
    graph_context: dict[str, Any]
    graph_sources: list[TutorSource]
    zotero_context: list[dict[str, Any]]
    zotero_sources: list[TutorSource]
    learning_source: TutorSource | None
    retrieved_chunks: list[ArticleChunk]


class TutorService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: LLMProvider | None = None,
        graph_service: GraphService | None = None,
        zotero_store: ZoteroLinkStore | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()
        self.llm_provider = llm_provider or _default_llm_provider()
        self.graph_service = graph_service or GraphService()
        self.zotero_store = zotero_store or ZoteroLinkStore(zotero_store_path())

    def answer(self, request: TutorRequest) -> TutorResponse:
        context = self._collect_context(request)
        if not context.article_sources:
            if request.mode == "research":
                answer, refusal = refusal_response(
                    request.mode,
                    "no_sources",
                    "无法基于当前资料形成可靠研究建议。",
                )
            else:
                answer, refusal = refusal_response(request.mode, "no_sources")
            return TutorResponse(
                answer=answer,
                mode=request.mode,
                sources=[],
                graph_context=context.graph_context,
                zotero_context=context.zotero_context,
                follow_up_questions=[],
                refusal_reason=refusal,
            )

        if request.mode == "derive" and not _has_formula_context(context.retrieved_chunks, context.graph_context):
            answer, refusal = refusal_response(
                request.mode,
                "insufficient_formula_sources",
                "当前资料不足以完整推导。",
            )
            return TutorResponse(
                answer=answer,
                mode=request.mode,
                sources=context.article_sources + context.graph_sources + context.zotero_sources,
                graph_context=context.graph_context,
                zotero_context=context.zotero_context,
                follow_up_questions=_follow_ups(request),
                refusal_reason=refusal,
            )

        answer = self._mode_answer(request, context)
        sources = context.article_sources + context.graph_sources + context.zotero_sources
        answer, refusal = enforce_grounding(mode=request.mode, answer=answer, sources=sources)
        return TutorResponse(
            answer=answer,
            mode=request.mode,
            sources=[] if refusal else sources,
            graph_context=context.graph_context,
            zotero_context=context.zotero_context,
            follow_up_questions=[] if refusal else _follow_ups(request),
            refusal_reason=refusal,
        )

    def quiz(self, *, article_id: str | None = None, node_id: str | None = None, num_questions: int = 3) -> list[QuizQuestion]:
        request = TutorRequest(
            question="生成基于当前资料的概念检查题。",
            mode="quiz",
            article_id=article_id,
            node_id=node_id,
            top_k=max(1, min(num_questions, 10)),
            include_graph_context=True,
            include_zotero_context=False,
        )
        context = self._collect_context(request)
        if not context.article_sources:
            return []

        questions: list[QuizQuestion] = []
        for index, source in enumerate(context.article_sources[: max(1, min(num_questions, 10))], start=1):
            section = source.section_title or source.title
            questions.append(
                QuizQuestion(
                    question=f"概念检查 {index}: {section} 中的核心观点是什么？",
                    options=None,
                    correct_answer=f"请依据《{source.title}》的“{section}”章节回答。",
                    explanation="该题只基于已检索到的文章片段生成，答案需要回到对应来源核对。",
                    sources=[source],
                )
            )
        return questions

    def _collect_context(self, request: TutorRequest) -> TutorContext:
        results = self._retrieve_article_chunks(request)
        article_sources = [_source_from_result(result) for result in results]
        rag_contexts = [
            {
                "content": result.chunk.content,
                "article_title": result.chunk.article_title,
                "section_title": result.chunk.section_title,
            }
            for result in results
        ]
        chunks = [result.chunk for result in results]
        graph_context, graph_sources = self._graph_context(request)
        zotero_context, zotero_sources = self._zotero_context(request.article_id)
        learning_source = _learning_source(request.article_id)
        if learning_source:
            graph_context = {**graph_context, "learning_state": learning_source.to_dict()}
        return TutorContext(
            article_sources=article_sources,
            rag_contexts=rag_contexts,
            graph_context=graph_context,
            graph_sources=graph_sources,
            zotero_context=zotero_context,
            zotero_sources=zotero_sources,
            learning_source=learning_source,
            retrieved_chunks=chunks,
        )

    def _retrieve_article_chunks(self, request: TutorRequest) -> list[SearchResult]:
        articles = ArticleStore(article_store_path()).list_articles()
        if request.article_id:
            articles = [article for article in articles if article.id == request.article_id]
        chunks = _chunks_from_articles(articles)
        if not chunks:
            return []
        vector_store = FaissVectorStore.from_chunks(chunks, self.embedding_provider)
        return vector_store.search(request.question, top_k=max(1, min(request.top_k, 20)), embedding_provider=self.embedding_provider)

    def _graph_context(self, request: TutorRequest) -> tuple[dict[str, Any], list[TutorSource]]:
        if not request.include_graph_context:
            return {"nodes": [], "edges": []}, []
        try:
            graph = self.graph_service.get_graph()
            if request.node_id and not graph.nodes:
                self.graph_service.build_graph()
            if request.node_id:
                node = self.graph_service.get_node(request.node_id)
                neighbors = self.graph_service.get_neighbors(request.node_id, depth=1, limit=20)
                nodes = [node.to_dict(), *neighbors["nodes"]]
                edges = neighbors["edges"]
            else:
                nodes = []
                edges = []
        except NodeNotFoundError:
            return {"nodes": [], "edges": []}, []

        sources: list[TutorSource] = []
        for node in nodes[:10]:
            sources.append(
                TutorSource(
                    source_type="graph_node",
                    source_id=str(node["node_id"]),
                    title=str(node["label"]),
                    url=node.get("source_url"),
                    evidence=node.get("metadata"),
                    metadata={"node_type": node.get("node_type"), "source_id": node.get("source_id")},
                )
            )
        for edge in edges[:10]:
            sources.append(
                TutorSource(
                    source_type="graph_edge",
                    source_id=str(edge["edge_id"]),
                    title=str(edge["edge_type"]),
                    evidence=edge.get("evidence"),
                    metadata={
                        "source_node_id": edge.get("source_node_id"),
                        "target_node_id": edge.get("target_node_id"),
                    },
                )
            )
        return {"nodes": nodes, "edges": edges}, sources

    def _zotero_context(self, article_id: str | None) -> tuple[list[dict[str, Any]], list[TutorSource]]:
        if not article_id:
            return [], []
        provider = get_zotero_provider()
        context: list[dict[str, Any]] = []
        sources: list[TutorSource] = []
        for link in self.zotero_store.list_links(article_id):
            item = provider.get_item(link.zotero_item_key)
            item_data = item.to_dict() if item else {"item_key": link.zotero_item_key}
            context_item = {"link": link.to_dict(), "item": item_data}
            context.append(context_item)
            sources.append(
                TutorSource(
                    source_type="zotero_item",
                    source_id=link.zotero_item_key,
                    title=str(item_data.get("title") or link.zotero_item_key),
                    url=item_data.get("url"),
                    evidence=link.to_dict(),
                    metadata=item_data,
                )
            )
        return context, sources

    def _mode_answer(self, request: TutorRequest, context: TutorContext) -> str:
        base = self.llm_provider.chat(question=request.question, contexts=context.rag_contexts)
        if request.mode == "explain":
            return f"解释：{base}\n\n要点：\n- 回到引用章节核对定义。\n- 结合图谱邻居查看相关概念。"
        if request.mode == "derive":
            return f"分步推导说明：{base}\n\n假设：只使用已检索到的公式和文章片段；未在资料中出现的推导不补全。"
        if request.mode == "qa":
            return f"直接回答：{base}\n\n为什么重要：该问题连接了当前文章片段与后续学习路径。"
        if request.mode == "research":
            readings = [item["item"].get("title") for item in context.zotero_context if item.get("item")]
            reading_text = "；".join(str(item) for item in readings if item) or "优先复读已引用文章片段。"
            return f"研究建议：{base}\n\n下一步阅读：{reading_text}\n资料缺口：仅基于本地文章、图谱和Zotero链接，不能视为完整文献综述。"
        if request.mode == "quiz":
            return f"测验引导：{base}"
        return base


def _default_llm_provider() -> LLMProvider:
    provider_name = os.getenv("SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER", "fake").strip().lower()
    if provider_name == "openai":
        return OpenAICompatibleLLMProvider()
    return FakeLLMProvider()


def _chunks_from_articles(articles: list[StoredArticle]) -> list[ArticleChunk]:
    chunks: list[ArticleChunk] = []
    for article in articles:
        chunks.extend(
            chunk_article(
                article_id=article.id,
                article_title=article.title,
                article_url=article.url,
                content=article.content,
            )
        )
    return chunks


def _source_from_result(result: SearchResult) -> TutorSource:
    chunk = result.chunk
    return TutorSource(
        source_type="article_chunk",
        source_id=f"{chunk.article_id}:{chunk.chunk_index}",
        title=chunk.article_title,
        url=chunk.article_url,
        section_title=chunk.section_title,
        chunk_index=chunk.chunk_index,
        evidence=chunk.content[:500],
        metadata={"score": result.score, "article_id": chunk.article_id},
    )


def _has_formula_context(chunks: list[ArticleChunk], graph_context: dict[str, Any]) -> bool:
    if any("$$" in chunk.content or "\\[" in chunk.content or "\\begin{equation" in chunk.content for chunk in chunks):
        return True
    return any(node.get("node_type") == "formula" for node in graph_context.get("nodes", []))


def _learning_source(article_id: str | None) -> TutorSource | None:
    if not article_id:
        return None
    state = LearningStore(learning_store_path()).get_state(article_id)
    return TutorSource(
        source_type="learning_state",
        source_id=article_id,
        title=f"Learning state for {article_id}",
        evidence=state.to_dict(),
        metadata={"usage": "personalization_only", "status": state.status},
    )


def _follow_ups(request: TutorRequest) -> list[str]:
    if request.mode == "derive":
        return ["哪些公式来源支持这个推导？", "当前资料缺少哪些推导步骤？"]
    if request.mode == "research":
        return ["哪些相关文章应该先读？", "哪些Zotero条目和当前文章相关？"]
    if request.mode == "quiz":
        return ["能否基于同一来源再出一道题？"]
    return ["这个概念和哪些图谱邻居相关？", "我应该继续阅读哪一节？"]
