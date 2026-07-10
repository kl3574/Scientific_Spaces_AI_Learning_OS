from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from typing import Any

from app.graph.service import GraphService
from app.learning.store import LearningStore, learning_store_path
from app.llm.fake import FakeLLMProvider
from app.llm.provider import LLMProvider, OpenAICompatibleLLMProvider
from app.tutor.graph_context import GraphContextResult, collect_graph_context
from app.tutor.models import (
    EvidenceSummary,
    QuizQuestion,
    SelectionSummary,
    TutorMode,
    TutorRequest,
    TutorResponse,
    TutorSource,
)
from app.tutor.policy import enforce_grounding, refusal_response
from app.tutor.retrieval import ConfiguredTutorRetriever, RetrievalResult, TutorRetriever
from app.tutor.source_selection import (
    MAX_TUTOR_SUPPLEMENT_RESPONSE_CHARS,
    MAX_TUTOR_ZOTERO_SUPPLEMENT_CHARS,
    SourceSelectionPolicy,
    SourceSelector,
    sanitize_http_url,
    sanitize_supplement_identity,
    sanitize_supplement_payload,
)
from app.rag.embeddings import EmbeddingProvider, FakeEmbeddingProvider
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
    selection_summary: SelectionSummary
    evidence_summary: EvidenceSummary
    learning_source: TutorSource | None


class TutorIndexUnavailable(RuntimeError):
    """Raised when configured full-corpus retrieval resources cannot be loaded."""


@dataclass
class TutorService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: LLMProvider | None = None,
        graph_service: GraphService | None = None,
        zotero_store: ZoteroLinkStore | None = None,
        source_selection_policy: SourceSelectionPolicy | None = None,
        source_selector: SourceSelector | None = None,
        retriever: TutorRetriever | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()
        self.llm_provider = llm_provider or _default_llm_provider()
        self.graph_service = graph_service or GraphService()
        self.zotero_store = zotero_store or ZoteroLinkStore(zotero_store_path())
        self.source_selection_policy = source_selection_policy or SourceSelectionPolicy.from_env()
        self.source_selector = source_selector or SourceSelector(self.source_selection_policy)
        self.retriever = retriever or ConfiguredTutorRetriever(embedding_provider=self.embedding_provider)

    def answer(self, request: TutorRequest) -> TutorResponse:
        context = self._collect_context(request)

        internal_refusal_reason = context.evidence_summary.refusal_reason
        if internal_refusal_reason == "no_relevant_source" and request.mode == "research":
            internal_refusal_reason = "insufficient_local_corpus_evidence"

        refusal_reason = _to_m7_refusal(internal_refusal_reason)
        evidence_summary = replace(context.evidence_summary, refusal_reason=internal_refusal_reason)
        if refusal_reason is not None:
            retain_evidence = internal_refusal_reason == "insufficient_formula_evidence"
            if request.mode == "research":
                answer, _ = refusal_response(
                    request.mode,
                    refusal_reason,
                    "无法基于当前资料形成可靠研究建议。",
                )
            elif request.mode == "derive":
                answer, _ = refusal_response(request.mode, refusal_reason, "当前资料不足以完整推导。")
            else:
                answer, _ = refusal_response(request.mode, refusal_reason)
            return TutorResponse(
                answer=answer,
                mode=request.mode,
                sources=(context.article_sources + context.graph_sources + context.zotero_sources) if retain_evidence else [],
                graph_context=context.graph_context,
                zotero_context=context.zotero_context,
                follow_up_questions=_follow_ups(request) if retain_evidence else [],
                refusal_reason=refusal_reason,
                selection_summary=context.selection_summary,
                evidence_summary=evidence_summary,
            )

        answer = self._mode_answer(request, context)
        sources = context.article_sources + context.graph_sources + context.zotero_sources
        answer, refusal = enforce_grounding(mode=request.mode, answer=answer, sources=sources)
        refusal = _to_m7_refusal(refusal)
        if refusal is not None:
            return TutorResponse(
                answer=answer,
                mode=request.mode,
                sources=[],
                graph_context=context.graph_context,
                zotero_context=context.zotero_context,
                follow_up_questions=[],
                refusal_reason=refusal,
                selection_summary=context.selection_summary,
                evidence_summary=evidence_summary,
            )

        return TutorResponse(
            answer=answer,
            mode=request.mode,
            sources=sources,
            graph_context=context.graph_context,
            zotero_context=context.zotero_context,
            follow_up_questions=_follow_ups(request),
            refusal_reason=None,
            selection_summary=context.selection_summary,
            evidence_summary=evidence_summary,
        )

    def quiz(
        self,
        *,
        article_id: str | None = None,
        node_id: str | None = None,
        topic: str | None = None,
        num_questions: int = 3,
    ) -> list[QuizQuestion]:
        normalized_topic = (topic or "").strip()
        request = TutorRequest(
            question=normalized_topic or (article_id or "").strip() or "生成基于当前资料的概念检查题。",
            mode="quiz",
            article_id=article_id,
            node_id=node_id,
            top_k=max(1, min(num_questions, 10)),
            include_graph_context=False,
            include_zotero_context=False,
        )
        context = self._collect_context(request)
        if (
            not context.article_sources
            or context.evidence_summary.refusal_reason is not None
            or not context.evidence_summary.has_answerable_evidence
        ):
            return []

        questions: list[QuizQuestion] = []
        seen_evidence_units: set[str] = set()
        seen_questions: set[str] = set()
        requested = max(1, min(num_questions, 10))
        for source, rag_context in zip(context.article_sources, context.rag_contexts):
            if len(questions) >= requested:
                break
            evidence_unit = " ".join(rag_context["content"].split())
            evidence_key = evidence_unit.casefold()
            if not evidence_key or evidence_key in seen_evidence_units:
                continue
            seen_evidence_units.add(evidence_key)
            section = source.section_title or source.title
            focus = _quiz_evidence_focus(evidence_unit)
            task = f"围绕“{normalized_topic}”，该证据说明了什么？" if normalized_topic else "该证据的核心观点是什么？"
            question_text = f"根据「{section}」中的证据“{focus}”，{task}"
            if question_text in seen_questions:
                continue
            seen_questions.add(question_text)
            questions.append(
                QuizQuestion(
                    question=question_text,
                    options=None,
                    correct_answer=f"{focus}（依据《{source.title}》中的“{section}”章节。）",
                    explanation="该题只基于已选文章片段生成，答案必须对应来源内容。",
                    sources=[source],
                )
            )
        return questions

    def _collect_context(self, request: TutorRequest) -> TutorContext:
        graph_result = self._collect_graph_context(request)
        graph_context = graph_result.context
        graph_sources = list(graph_result.supplemental_sources)
        retrieval = self._retrieve_results(request)
        locally_supported = retrieval.locally_supported
        if request.article_id:
            locally_supported = True
        selector_graph_context = (
            {**graph_context, "node_id": request.node_id}
            if request.include_graph_context and request.node_id and request.node_id.strip()
            else None
        )
        selection = self.source_selector.select(
            query=request.question,
            mode=request.mode,
            results=retrieval.results,
            requested_chunks=request.top_k,
            graph_context=selector_graph_context,
            locally_supported=locally_supported,
        )
        article_sources = [item.source for item in selection.selected]
        rag_contexts = [
            {
                "content": item.excerpt,
                "article_title": item.result.chunk.article_title,
                "section_title": item.result.chunk.section_title,
            }
            for item in selection.selected
        ]
        zotero_context, zotero_sources, zotero_omitted_count = self._zotero_context(
            request.article_id if request.include_zotero_context else None
        )
        (
            graph_context,
            graph_sources,
            zotero_context,
            zotero_sources,
            aggregate_omitted_count,
        ) = _bound_supplement_response(
            graph_context=graph_context,
            graph_sources=graph_sources,
            zotero_context=zotero_context,
            zotero_sources=zotero_sources,
        )
        learning_source = _learning_source(request.article_id)
        if learning_source:
            graph_context = {**graph_context, "learning_state": learning_source.to_dict()}
        return TutorContext(
            article_sources=article_sources,
            rag_contexts=rag_contexts,
            graph_context=graph_context,
            graph_sources=list(graph_sources),
            zotero_context=zotero_context,
            zotero_sources=zotero_sources,
            selection_summary=_selection_summary(
                selection,
                graph_latency_ms=graph_result.latency_ms,
                graph_error_code=graph_result.error_code,
                graph_node_count=len(graph_context["nodes"]),
                graph_edge_count=len(graph_context["edges"]),
                supplement_truncated=(
                    graph_result.truncated
                    or zotero_omitted_count > 0
                    or aggregate_omitted_count > 0
                ),
                supplement_omitted_count=(
                    graph_result.omitted_count
                    + zotero_omitted_count
                    + aggregate_omitted_count
                ),
            ),
            evidence_summary=_evidence_summary(selection),
            learning_source=learning_source,
        )

    def _retrieve_results(self, request: TutorRequest) -> RetrievalResult:
        try:
            retrieval = self.retriever.retrieve(
                request=request,
                candidate_limit=self.source_selection_policy.candidate_chunk_limit,
            )
            return retrieval
        except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise TutorIndexUnavailable("Configured full-corpus Tutor index is unavailable") from error
        except Exception as error:
            if os.getenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR"):
                raise TutorIndexUnavailable("Configured full-corpus Tutor index is unavailable") from error
            raise

    def _graph_context(self, request: TutorRequest) -> tuple[dict[str, Any], list[TutorSource]]:
        result = self._collect_graph_context(request)
        return result.context, list(result.supplemental_sources)

    def _collect_graph_context(self, request: TutorRequest) -> GraphContextResult:
        if not request.include_graph_context or not request.node_id or not request.node_id.strip():
            return GraphContextResult(context={"nodes": [], "edges": []}, supplemental_sources=(), latency_ms=0.0)
        return collect_graph_context(
            self.graph_service,
            node_id=request.node_id,
            policy=self.source_selection_policy,
        )

    def _zotero_context(
        self,
        article_id: str | None,
    ) -> tuple[list[dict[str, Any]], list[TutorSource], int]:
        if not article_id:
            return [], [], 0
        provider = get_zotero_provider()
        context: list[dict[str, Any]] = []
        sources: list[TutorSource] = []
        all_links = self.zotero_store.list_links(article_id)
        bounded_links = all_links[: self.source_selection_policy.max_source_articles]
        omitted_count = len(all_links) - len(bounded_links)
        for index, link in enumerate(bounded_links):
            safe_item_key = sanitize_supplement_identity(link.zotero_item_key)
            if safe_item_key is None:
                omitted_count += 1
                continue
            item = provider.get_item(link.zotero_item_key)
            item_data = _safe_zotero_mapping(
                item.to_dict() if item else {"item_key": safe_item_key}
            )
            link_data = _safe_zotero_mapping(link.to_dict())
            context_item = {"link": link_data, "item": item_data}
            source = TutorSource(
                source_type="zotero_item",
                source_id=safe_item_key,
                title=str(item_data.get("title") or safe_item_key),
                url=sanitize_http_url(item_data.get("url")),
                evidence=link_data,
                metadata=_zotero_source_metadata(item_data),
            )
            candidate_payload = {
                "context": [*context, context_item],
                "sources": [*[existing.to_dict() for existing in sources], source.to_dict()],
            }
            if _serialized_chars(candidate_payload) > MAX_TUTOR_ZOTERO_SUPPLEMENT_CHARS:
                omitted_count += len(bounded_links) - index
                break
            context.append(context_item)
            sources.append(source)
        return context, sources, omitted_count

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


def _selection_summary(
    selection,
    *,
    graph_latency_ms: float | None = None,
    graph_error_code: str | None = None,
    graph_node_count: int | None = None,
    graph_edge_count: int | None = None,
    supplement_truncated: bool = False,
    supplement_omitted_count: int = 0,
) -> SelectionSummary:
    return SelectionSummary(
        candidate_count=selection.summary.candidate_count,
        selected_article_count=selection.summary.selected_article_count,
        selected_chunk_count=selection.summary.selected_chunk_count,
        graph_node_count=(
            selection.summary.graph_node_count
            if graph_node_count is None
            else graph_node_count
        ),
        graph_edge_count=(
            selection.summary.graph_edge_count
            if graph_edge_count is None
            else graph_edge_count
        ),
        graph_latency_ms=graph_latency_ms,
        graph_error_code=graph_error_code,
        context_character_count=selection.summary.context_char_count,
        estimated_token_count=selection.summary.estimated_token_count,
        truncated=(
            selection.summary.context_truncated
            or selection.summary.source_truncation_count > 0
            or selection.summary.graph_truncated
            or supplement_truncated
        ),
        supplement_omitted_count=supplement_omitted_count,
    )


def _evidence_summary(selection) -> EvidenceSummary:
    return EvidenceSummary(
        source_count=selection.evidence.source_count,
        article_count=selection.evidence.article_count,
        has_formula_evidence=selection.evidence.has_formula_evidence,
        has_definition_evidence=selection.evidence.has_definition_evidence,
        has_answerable_evidence=selection.evidence.has_answerable_evidence,
        source_schema_valid=selection.evidence.source_schema_valid,
        unsupported_or_out_of_scope=selection.evidence.unsupported_or_out_of_scope,
        refusal_reason=selection.evidence.refusal_reason,
    )


def _quiz_evidence_focus(evidence_unit: str) -> str:
    return evidence_unit if len(evidence_unit) <= 160 else f"{evidence_unit[:157].rstrip()}..."


def _safe_zotero_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_supplement_payload(payload)
    return dict(sanitized) if isinstance(sanitized, dict) else {}


def _zotero_source_metadata(item_data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item_data[key]
        for key in ("item_type", "year", "publication_title", "doi")
        if item_data.get(key) is not None
    }


def _bound_supplement_response(
    *,
    graph_context: dict[str, Any],
    graph_sources: list[TutorSource],
    zotero_context: list[dict[str, Any]],
    zotero_sources: list[TutorSource],
) -> tuple[
    dict[str, Any],
    list[TutorSource],
    list[dict[str, Any]],
    list[TutorSource],
    int,
]:
    bounded_graph = {
        "nodes": list(graph_context.get("nodes") or []),
        "edges": list(graph_context.get("edges") or []),
    }
    bounded_graph_sources = list(graph_sources)
    bounded_zotero = list(zotero_context)
    bounded_zotero_sources = list(zotero_sources)
    omitted_count = 0

    while _serialized_chars(
        {
            "graph_context": bounded_graph,
            "zotero_context": bounded_zotero,
            "sources": [
                *[source.to_dict() for source in bounded_graph_sources],
                *[source.to_dict() for source in bounded_zotero_sources],
            ],
        }
    ) > MAX_TUTOR_SUPPLEMENT_RESPONSE_CHARS:
        if bounded_zotero:
            bounded_zotero.pop()
            if bounded_zotero_sources:
                bounded_zotero_sources.pop()
            omitted_count += 1
            continue
        if bounded_zotero_sources:
            bounded_zotero_sources.pop()
            omitted_count += 1
            continue
        if bounded_graph["edges"]:
            edge = bounded_graph["edges"].pop()
            _remove_supplement_source(
                bounded_graph_sources,
                source_type="graph_edge",
                source_id=str(edge.get("edge_id") or ""),
            )
            omitted_count += 1
            continue
        if bounded_graph["nodes"]:
            node = bounded_graph["nodes"].pop()
            _remove_supplement_source(
                bounded_graph_sources,
                source_type="graph_node",
                source_id=str(node.get("node_id") or ""),
            )
            omitted_count += 1
            continue
        if bounded_graph_sources:
            bounded_graph_sources.pop()
            omitted_count += 1
            continue
        break

    return (
        bounded_graph,
        bounded_graph_sources,
        bounded_zotero,
        bounded_zotero_sources,
        omitted_count,
    )


def _remove_supplement_source(
    sources: list[TutorSource],
    *,
    source_type: str,
    source_id: str,
) -> None:
    for index in range(len(sources) - 1, -1, -1):
        source = sources[index]
        if source.source_type == source_type and source.source_id == source_id:
            sources.pop(index)
            return


def _serialized_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


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


def _to_m7_refusal(refusal: str | None) -> str | None:
    if refusal == "insufficient_formula_evidence":
        return "insufficient_formula_sources"
    if refusal in {"no_relevant_source", "unsupported_query", "invalid_source_schema", "insufficient_local_corpus_evidence"}:
        return "no_sources"
    return refusal
