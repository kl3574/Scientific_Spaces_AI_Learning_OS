from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.rag.vector_store import SearchResult
from app.tutor.models import TutorMode, TutorSource

MAX_TUTOR_GRAPH_NODES = 20
MAX_TUTOR_GRAPH_EDGES = 30
MAX_TUTOR_GRAPH_DEPTH = 2
MAX_SUPPLEMENT_TEXT_CHARS = 1_000
MAX_SUPPLEMENT_URL_CHARS = 2_048
MAX_SUPPLEMENT_COLLECTION_ITEMS = 20
MAX_SUPPLEMENT_MAPPING_ITEMS = 20
MAX_SUPPLEMENT_NESTING_DEPTH = 4
MAX_SUPPLEMENT_PAYLOAD_CHARS = 8_192
MAX_GRAPH_METADATA_PAYLOAD_CHARS = 4_096
MAX_GRAPH_PROVENANCE_PAYLOAD_CHARS = 1_500
MAX_TUTOR_GRAPH_SUPPLEMENT_CHARS = 31_500
MAX_TUTOR_ZOTERO_SUPPLEMENT_CHARS = 16_000
MAX_TUTOR_SUPPLEMENT_RESPONSE_CHARS = 48_000


class TutorSourceConfigurationError(ValueError):
    """Raised when a local selector limit is invalid."""


class GraphContextDataError(ValueError):
    """Raised when Graph context does not match the persisted Graph contract."""


@dataclass(frozen=True)
class SourceSelectionPolicy:
    candidate_chunk_limit: int = 20
    max_source_articles: int = 6
    max_final_chunks: int = 10
    max_chunks_per_article: int = 2
    max_graph_nodes: int = 20
    max_graph_edges: int = 30
    max_graph_depth: int = 2
    max_context_chars: int = 24_000

    def __post_init__(self) -> None:
        _validate_limit("candidate_chunk_limit", self.candidate_chunk_limit, 20)
        _validate_limit("max_source_articles", self.max_source_articles, 12)
        _validate_limit("max_final_chunks", self.max_final_chunks, 20)
        _validate_limit("max_chunks_per_article", self.max_chunks_per_article, 2)
        _validate_limit("max_graph_nodes", self.max_graph_nodes, MAX_TUTOR_GRAPH_NODES)
        _validate_limit("max_graph_edges", self.max_graph_edges, MAX_TUTOR_GRAPH_EDGES)
        _validate_limit("max_graph_depth", self.max_graph_depth, MAX_TUTOR_GRAPH_DEPTH)
        _validate_limit("max_context_chars", self.max_context_chars, 100_000)

    @classmethod
    def from_env(cls) -> "SourceSelectionPolicy":
        return cls(
            max_source_articles=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_SOURCE_ARTICLES", 6, 1, 12),
            max_final_chunks=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_CHUNKS", 10, 1, 20),
            max_graph_nodes=_bounded_env(
                "SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_NODES", 20, 1, MAX_TUTOR_GRAPH_NODES
            ),
            max_graph_edges=_bounded_env(
                "SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES", 30, 1, MAX_TUTOR_GRAPH_EDGES
            ),
            max_context_chars=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_CONTEXT_CHARS", 24_000, 1_000, 100_000),
        )


@dataclass(frozen=True)
class EvidenceSufficiencyResult:
    source_count: int
    article_count: int
    has_formula_evidence: bool
    has_definition_evidence: bool
    has_answerable_evidence: bool
    source_schema_valid: bool
    unsupported_or_out_of_scope: bool
    refusal_reason: str | None


@dataclass(frozen=True)
class SourceCandidate:
    chunk_id: str
    result: SearchResult
    relevance_score: float
    query_overlap: float
    score: float


@dataclass(frozen=True)
class SelectedSource:
    chunk_id: str
    result: SearchResult
    source: TutorSource
    excerpt: str
    score: float


@dataclass(frozen=True)
class SourceSelectionSummary:
    candidate_count: int
    unique_candidate_count: int
    selected_article_count: int
    selected_chunk_count: int
    duplicate_chunk_count: int
    graph_node_count: int
    graph_edge_count: int
    graph_truncated: bool
    context_char_count: int
    estimated_token_count: int
    context_truncated: bool
    source_truncation_count: int
    budget_violation: bool


@dataclass(frozen=True)
class SourceSelectionResult:
    candidates: tuple[SourceCandidate, ...]
    selected: tuple[SelectedSource, ...]
    graph_context: Mapping[str, tuple[Mapping[str, Any], ...]]
    generation_context: str
    summary: SourceSelectionSummary
    evidence: EvidenceSufficiencyResult

    @property
    def evidence_sufficiency(self) -> EvidenceSufficiencyResult:
        return self.evidence


class SourceSelector:
    def __init__(self, policy: SourceSelectionPolicy | None = None) -> None:
        self.policy = policy or SourceSelectionPolicy()

    def select(
        self,
        *,
        query: str,
        mode: TutorMode,
        results: Sequence[SearchResult],
        requested_chunks: int,
        graph_context: Mapping[str, Any] | None = None,
        locally_supported: bool = True,
    ) -> SourceSelectionResult:
        bounded_results = results[: self.policy.candidate_chunk_limit]
        unique_results, duplicate_count = self._deduplicate_results(bounded_results)
        candidates = self._score_candidates(query=query, mode=mode, results=unique_results)
        grouped = self._group_by_article(candidates)
        selected_candidates = self._select_diverse_articles(
            mode=mode,
            grouped=grouped,
            requested_chunks=requested_chunks,
        )
        selected_candidates = self._preserve_relevant_formula_candidate(
            query=query,
            mode=mode,
            candidates=candidates,
            selected=selected_candidates,
        )
        selected, generation_context, context_truncated, source_truncation_count = self._assemble_context(selected_candidates)
        safe_graph_context, graph_truncated = self._bounded_graph_context(graph_context)
        source_schema_valid = all(_valid_source(candidate.result) for candidate in selected_candidates)
        evidence = self._evaluate_evidence(
            query=query,
            mode=mode,
            selected=selected,
            source_schema_valid=source_schema_valid,
            locally_supported=locally_supported,
        )
        article_ids = {item.result.chunk.article_id for item in selected}
        summary = SourceSelectionSummary(
            candidate_count=len(bounded_results),
            unique_candidate_count=len(candidates),
            selected_article_count=len(article_ids),
            selected_chunk_count=len(selected),
            duplicate_chunk_count=duplicate_count,
            graph_node_count=len(safe_graph_context["nodes"]),
            graph_edge_count=len(safe_graph_context["edges"]),
            graph_truncated=graph_truncated,
            context_char_count=len(generation_context),
            estimated_token_count=_estimate_tokens(generation_context),
            context_truncated=context_truncated,
            source_truncation_count=source_truncation_count,
            budget_violation=_budget_violation(selected, self.policy, mode),
        )
        return SourceSelectionResult(
            candidates=tuple(candidates),
            selected=tuple(selected),
            graph_context=safe_graph_context,
            generation_context=generation_context,
            summary=summary,
            evidence=evidence,
        )

    @staticmethod
    def _deduplicate_results(results: Sequence[SearchResult]) -> tuple[list[SearchResult], int]:
        unique: list[SearchResult] = []
        seen: set[str] = set()
        duplicate_count = 0
        for result in results:
            chunk_id = _chunk_id(result)
            if chunk_id in seen:
                duplicate_count += 1
                continue
            seen.add(chunk_id)
            unique.append(result)
        return unique, duplicate_count

    def _score_candidates(
        self,
        *,
        query: str,
        mode: TutorMode,
        results: Sequence[SearchResult],
    ) -> list[SourceCandidate]:
        query_tokens = _tokens(query)
        candidates: list[SourceCandidate] = []
        for rank, result in enumerate(results, start=1):
            chunk = result.chunk
            evidence_text = " ".join((chunk.article_title, chunk.section_title, chunk.content))
            overlap = _jaccard(query_tokens, _tokens(evidence_text))
            relevance = 1.0 / (1.0 + max(0.0, result.score))
            evidence_bonus = _mode_evidence_bonus(mode, chunk.content)
            score = (0.70 * relevance) + (0.25 * overlap) + (0.05 / rank) + evidence_bonus
            candidates.append(
                SourceCandidate(
                    chunk_id=_chunk_id(result),
                    result=result,
                    relevance_score=relevance,
                    query_overlap=overlap,
                    score=score,
                )
            )
        return sorted(candidates, key=lambda item: (-item.score, item.result.chunk.article_id, item.chunk_id))

    @staticmethod
    def _group_by_article(candidates: Sequence[SourceCandidate]) -> dict[str, tuple[SourceCandidate, ...]]:
        grouped: dict[str, list[SourceCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.result.chunk.article_id, []).append(candidate)
        return {
            article_id: tuple(sorted(items, key=lambda item: (-item.score, item.chunk_id)))
            for article_id, items in grouped.items()
        }

    def _select_diverse_articles(
        self,
        *,
        mode: TutorMode,
        grouped: Mapping[str, tuple[SourceCandidate, ...]],
        requested_chunks: int,
    ) -> list[SourceCandidate]:
        article_limit, chunk_limit = _mode_limits(mode, self.policy, requested_chunks)
        ordered_article_ids = self._rank_articles(mode=mode, grouped=grouped, article_limit=article_limit)
        selected: list[SourceCandidate] = []
        if mode == "research":
            for chunk_index in range(self.policy.max_chunks_per_article):
                for article_id in ordered_article_ids:
                    article_candidates = grouped[article_id]
                    if chunk_index >= len(article_candidates):
                        continue
                    if len(selected) >= chunk_limit:
                        return selected
                    selected.append(article_candidates[chunk_index])
            return selected
        for article_id in ordered_article_ids:
            for candidate in grouped[article_id][: self.policy.max_chunks_per_article]:
                if len(selected) >= chunk_limit:
                    return selected
                selected.append(candidate)
        return selected

    @staticmethod
    def _preserve_relevant_formula_candidate(
        *,
        query: str,
        mode: TutorMode,
        candidates: Sequence[SourceCandidate],
        selected: Sequence[SourceCandidate],
    ) -> list[SourceCandidate]:
        selected_candidates = list(selected)
        if (
            mode not in {"explain", "qa", "quiz"}
            or len(selected_candidates) < 2
            or any(_has_formula_or_derivation(item.result.chunk.content) for item in selected_candidates)
        ):
            return selected_candidates

        selected_article_ids = {
            item.result.chunk.article_id
            for item in selected_candidates
        }
        query_tokens = _tokens(query)
        formula_candidate = next(
            (
                item
                for item in candidates
                if item.result.chunk.article_id in selected_article_ids
                and _valid_source(item.result)
                and _jaccard(
                    query_tokens,
                    _tokens(f"{item.result.chunk.section_title} {item.result.chunk.content}"),
                )
                > 0
                and _has_formula_or_derivation(item.result.chunk.content)
            ),
            None,
        )
        if formula_candidate is None:
            return selected_candidates

        for index in range(len(selected_candidates) - 1, -1, -1):
            selected_item = selected_candidates[index]
            if selected_item.result.chunk.article_id != formula_candidate.result.chunk.article_id:
                continue
            selected_candidates[index] = formula_candidate
            break
        return selected_candidates

    @staticmethod
    def _rank_articles(
        *,
        mode: TutorMode,
        grouped: Mapping[str, tuple[SourceCandidate, ...]],
        article_limit: int,
    ) -> list[str]:
        remaining = set(grouped)
        selected: list[str] = []
        selected_terms: list[set[str]] = []
        while remaining and len(selected) < article_limit:
            ranked: list[tuple[float, str]] = []
            for article_id in remaining:
                best = grouped[article_id][0]
                score = best.score
                if mode == "research" and selected_terms:
                    article_terms = _article_terms(best)
                    score -= 0.25 * max(_jaccard(article_terms, terms) for terms in selected_terms)
                ranked.append((score, article_id))
            _, article_id = min(ranked, key=lambda item: (-item[0], item[1]))
            selected.append(article_id)
            selected_terms.append(_article_terms(grouped[article_id][0]))
            remaining.remove(article_id)
        return selected

    def _assemble_context(
        self,
        candidates: Sequence[SourceCandidate],
    ) -> tuple[list[SelectedSource], str, bool, int]:
        selected: list[SelectedSource] = []
        blocks: list[str] = []
        context_truncated = False
        source_truncation_count = 0
        for candidate in candidates:
            if not _valid_source(candidate.result):
                source_truncation_count += 1
                continue
            chunk = candidate.result.chunk
            header = f"[{candidate.chunk_id}]\n{chunk.article_title} | {chunk.section_title}\n"
            separator = "\n\n" if blocks else ""
            available = self.policy.max_context_chars - len("".join(blocks)) - len(separator) - len(header)
            excerpt = _bounded_excerpt(chunk.content, available)
            if not excerpt:
                context_truncated = True
                source_truncation_count += 1
                continue
            if excerpt != chunk.content.strip():
                context_truncated = True
            block = f"{header}{excerpt}"
            blocks.append(f"{separator}{block}")
            selected.append(
                SelectedSource(
                    chunk_id=candidate.chunk_id,
                    result=candidate.result,
                    source=_source_from_candidate(candidate),
                    excerpt=excerpt,
                    score=candidate.score,
                )
            )
        return selected, "".join(blocks), context_truncated, source_truncation_count

    def _bounded_graph_context(
        self,
        graph_context: Mapping[str, Any] | None,
    ) -> tuple[Mapping[str, tuple[Mapping[str, Any], ...]], bool]:
        if not graph_context or not str(graph_context.get("node_id") or "").strip():
            return {"nodes": (), "edges": ()}, False
        return sanitize_graph_context(graph_context, self.policy)

    @staticmethod
    def _evaluate_evidence(
        *,
        query: str,
        mode: TutorMode,
        selected: Sequence[SelectedSource],
        source_schema_valid: bool,
        locally_supported: bool,
    ) -> EvidenceSufficiencyResult:
        chunks = [item.result.chunk for item in selected]
        combined_content = "\n".join(
            f"{chunk.article_title} {chunk.section_title} {chunk.content}" for chunk in chunks
        )
        has_formula = any(_has_formula_or_derivation(chunk.content) for chunk in chunks)
        has_definition = any(_has_definition(chunk.content) for chunk in chunks)
        has_answerable = bool(_tokens(query) & _tokens(combined_content))
        unsupported = (not locally_supported) or _is_explicitly_unsupported(query)
        article_count = len({chunk.article_id for chunk in chunks})
        refusal_reason: str | None = None
        if unsupported:
            refusal_reason = "unsupported_query"
        elif not source_schema_valid:
            refusal_reason = "invalid_source_schema"
        elif not chunks or not has_answerable:
            refusal_reason = "no_relevant_source"
        elif mode == "derive" and not has_formula:
            refusal_reason = "insufficient_formula_evidence"
        elif mode == "research" and article_count < 2:
            refusal_reason = "insufficient_local_corpus_evidence"
        return EvidenceSufficiencyResult(
            source_count=len(chunks),
            article_count=article_count,
            has_formula_evidence=has_formula,
            has_definition_evidence=has_definition,
            has_answerable_evidence=has_answerable,
            source_schema_valid=source_schema_valid,
            unsupported_or_out_of_scope=unsupported,
            refusal_reason=refusal_reason,
        )


def _bounded_env(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise TutorSourceConfigurationError(f"{name} must be a positive integer") from error
    if parsed <= 0:
        raise TutorSourceConfigurationError(f"{name} must be a positive integer")
    return min(maximum, max(minimum, parsed))


def _validate_limit(name: str, value: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > maximum:
        raise TutorSourceConfigurationError(f"{name} must be an integer between 1 and {maximum}")


def _mode_limits(mode: TutorMode, policy: SourceSelectionPolicy, requested_chunks: int) -> tuple[int, int]:
    mode_limits: dict[TutorMode, tuple[int, int]] = {
        "explain": (5, 10),
        "derive": (4, 8),
        "qa": (4, 6),
        "quiz": (6, 10),
        "research": (6, 10),
    }
    article_limit, chunk_limit = mode_limits[mode]
    return min(policy.max_source_articles, article_limit), min(policy.max_final_chunks, chunk_limit, max(0, requested_chunks))


def _chunk_id(result: SearchResult) -> str:
    return f"{result.chunk.article_id}:{result.chunk.chunk_index}"


def _tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for part in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", value.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.update(part[index : index + 2] for index in range(len(part) - 1))
        elif len(part) > 1:
            tokens.add(part)
    return tokens


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _article_terms(candidate: SourceCandidate) -> set[str]:
    chunk = candidate.result.chunk
    return _tokens(f"{chunk.article_title} {chunk.section_title}")


def _mode_evidence_bonus(mode: TutorMode, content: str) -> float:
    if mode == "derive" and _has_formula_or_derivation(content):
        return 0.10
    if mode == "explain" and _has_definition(content):
        return 0.05
    return 0.0


def _has_formula_or_derivation(content: str) -> bool:
    normalized = content.lower()
    return (
        (normalized.count("$$") >= 2 and normalized.count("$$") % 2 == 0)
        or (normalized.count("\\[") >= 1 and normalized.count("\\[") == normalized.count("\\]"))
        or ("\\begin{equation" in normalized and "\\end{equation" in normalized)
        or bool(re.search(r"\b(theorem|proof|derive|derivation)\b|推导|定理|证明", normalized))
    )


def _has_definition(content: str) -> bool:
    return bool(re.search(r"\b(is|are|means|defined as|refers to)\b|定义|是指", content.lower()))


def _is_explicitly_unsupported(query: str) -> bool:
    normalized = query.lower()
    external_access = (
        "search the web",
        "browse the web",
        "search the internet",
        "access the internet",
        "联网检索",
        "联网搜索",
        "上网搜索",
        "访问互联网",
        "浏览网页",
    )
    private_actions = ("access my", "read my", "log into my", "open my", "retrieve my", "读取我的", "访问我的", "登录我的", "打开我的")
    private_targets = ("email", "inbox", "account", "private record", "private data", "personal file", "电子邮件", "收件箱", "邮箱", "账户", "账号", "私人记录", "私有数据", "个人文件")
    diagnosis = ("diagnose me", "diagnose my", "诊断疾病", "直接诊断", "为我诊断")
    prescription = ("prescribe", "prescription", "dosage", "处方", "剂量")
    missing_records = ("without medical records", "without records", "没有提供的病历", "未提供病历", "无病历")
    current_scope = ("latest", "current", "today", "real-time", "现在", "今天", "实时", "未来两小时")
    dynamic_targets = ("weather", "news", "stock price", "market price", "气温", "降雨", "预报", "新闻", "股价")
    return (
        any(marker in normalized for marker in external_access)
        or (
            any(marker in normalized for marker in private_actions)
            and any(marker in normalized for marker in private_targets)
        )
        or (
            any(marker in normalized for marker in diagnosis)
            and any(marker in normalized for marker in prescription)
            and any(marker in normalized for marker in missing_records)
        )
        or (
            any(marker in normalized for marker in current_scope)
            and any(marker in normalized for marker in dynamic_targets)
        )
    )


def _valid_source(result: SearchResult) -> bool:
    chunk = result.chunk
    return bool(
        chunk.article_id.strip()
        and chunk.article_title.strip()
        and chunk.section_title.strip()
        and chunk.content.strip()
        and chunk.chunk_index >= 0
        and re.match(r"^https?://", chunk.article_url.strip())
    )


def _source_from_candidate(candidate: SourceCandidate) -> TutorSource:
    chunk = candidate.result.chunk
    return TutorSource(
        source_type="article_chunk",
        source_id=candidate.chunk_id,
        title=chunk.article_title,
        url=chunk.article_url,
        section_title=chunk.section_title,
        chunk_index=chunk.chunk_index,
        evidence=None,
        metadata={"article_id": chunk.article_id, "retrieval_score": candidate.result.score, "selection_score": candidate.score},
    )


def _bounded_excerpt(content: str, available: int) -> str:
    normalized = content.strip()
    if available <= 0 or not normalized:
        return ""
    if len(normalized) <= available:
        return normalized
    paragraph_end = normalized.rfind("\n\n", 0, available + 1)
    line_end = normalized.rfind("\n", 0, available + 1)
    boundary = max(paragraph_end, line_end)
    return normalized[:boundary].strip() if boundary > 0 else ""


def sanitize_graph_context(
    graph_context: Mapping[str, Any] | None,
    policy: SourceSelectionPolicy,
) -> tuple[Mapping[str, tuple[Mapping[str, Any], ...]], bool]:
    """Return a bounded, path-safe graph view without changing valid output on repeat calls."""
    if not isinstance(graph_context, Mapping):
        raise GraphContextDataError("Graph context root must be a mapping")
    if "nodes" not in graph_context or "edges" not in graph_context:
        raise GraphContextDataError("Graph context must contain nodes and edges")
    raw_nodes = _graph_records(
        graph_context["nodes"],
        record_type="node",
        required_fields=("node_id", "node_type", "label"),
    )
    raw_edges = _graph_records(
        graph_context["edges"],
        record_type="edge",
        required_fields=("edge_id", "edge_type", "source_node_id", "target_node_id"),
    )
    node_limit = min(policy.max_graph_nodes, MAX_TUTOR_GRAPH_NODES)
    edge_limit = min(policy.max_graph_edges, MAX_TUTOR_GRAPH_EDGES)
    nodes = tuple(_safe_graph_node(item) for item in raw_nodes[:node_limit])
    edges = tuple(_safe_graph_edge(item) for item in raw_edges[:edge_limit])
    graph_truncated = (
        len(raw_nodes) > len(nodes)
        or len(raw_edges) > len(edges)
        or any(
            isinstance(node.get("metadata"), Mapping)
            and node["metadata"].get("truncated") is True
            for node in nodes
        )
    )
    return {"nodes": nodes, "edges": edges}, graph_truncated


def _graph_records(
    value: Any,
    *,
    record_type: str,
    required_fields: tuple[str, ...] = (),
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise GraphContextDataError(f"Graph {record_type} records must be a sequence")
    records: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise GraphContextDataError(f"Graph {record_type} record must be a mapping")
        if any(field not in item or not isinstance(item[field], str) for field in required_fields):
            raise GraphContextDataError(f"Graph {record_type} record has malformed identity")
        records.append(item)
    return tuple(records)


def _safe_graph_node(node: Mapping[str, Any]) -> Mapping[str, Any]:
    safe: dict[str, Any] = {
        "node_id": _safe_identity(node["node_id"]),
        "node_type": _safe_identity(node["node_type"]),
        "label": _safe_identity(node["label"]),
    }
    source_id = (
        _safe_graph_value(node.get("source_id"), max_chars=MAX_SUPPLEMENT_TEXT_CHARS)
        if "source_id" in node
        else _REMOVED
    )
    source_url = _safe_http_url(node.get("source_url")) if "source_url" in node else _REMOVED
    evidence = (
        _safe_graph_value(node.get("evidence"), max_chars=2 * MAX_SUPPLEMENT_TEXT_CHARS)
        if "evidence" in node
        else _REMOVED
    )
    metadata = node.get("metadata")
    if source_id is not _REMOVED and source_id is not None:
        safe["source_id"] = source_id
    if source_url is not _REMOVED and source_url is not None:
        safe["source_url"] = source_url
    if evidence is not _REMOVED and evidence is not None:
        safe["evidence"] = evidence
    if metadata is not None and not isinstance(metadata, Mapping):
        raise GraphContextDataError("Graph node metadata must be a mapping")
    if isinstance(metadata, Mapping):
        safe_metadata = _safe_graph_metadata(metadata)
        if safe_metadata:
            safe["metadata"] = safe_metadata
    bounded = _fit_payload(safe, MAX_SUPPLEMENT_PAYLOAD_CHARS)
    if not isinstance(bounded, Mapping):
        raise GraphContextDataError("Graph node could not be bounded")
    return bounded


def _safe_graph_edge(edge: Mapping[str, Any]) -> Mapping[str, Any]:
    safe: dict[str, Any] = {
        "edge_id": _safe_identity(edge["edge_id"]),
        "edge_type": _safe_identity(edge["edge_type"]),
        "source_node_id": _safe_identity(edge["source_node_id"]),
        "target_node_id": _safe_identity(edge["target_node_id"]),
    }
    evidence = (
        _safe_graph_value(edge.get("evidence"), max_chars=2 * MAX_SUPPLEMENT_TEXT_CHARS)
        if "evidence" in edge
        else _REMOVED
    )
    if evidence is not _REMOVED and evidence is not None:
        safe["evidence"] = evidence
    bounded = _fit_payload(safe, MAX_SUPPLEMENT_PAYLOAD_CHARS)
    if not isinstance(bounded, Mapping):
        raise GraphContextDataError("Graph edge could not be bounded")
    return bounded


def _safe_graph_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    safe_metadata: dict[str, Any] = {}
    for key in ("source_count", "truncated"):
        if key not in metadata:
            continue
        value = _safe_graph_value(metadata[key], max_chars=MAX_SUPPLEMENT_TEXT_CHARS)
        if value is not _REMOVED:
            safe_metadata[key] = value

    if "sources" in metadata:
        sources = _graph_records(metadata["sources"], record_type="provenance")
        safe_sources: list[Mapping[str, Any]] = []
        for source in sources:
            if _contains_unsafe_graph_value(source):
                continue
            sanitized = _safe_graph_value(
                source,
                max_chars=MAX_GRAPH_PROVENANCE_PAYLOAD_CHARS,
            )
            if isinstance(sanitized, Mapping) and sanitized:
                safe_sources.append(sanitized)
            if len(safe_sources) == 2:
                break
        safe_metadata["sources"] = tuple(safe_sources)

    remaining = {
        key: value
        for key, value in metadata.items()
        if key not in {"source_count", "truncated", "sources"}
    }
    safe_remaining = _safe_graph_value(
        remaining,
        max_chars=MAX_GRAPH_METADATA_PAYLOAD_CHARS,
    )
    if isinstance(safe_remaining, Mapping):
        safe_metadata.update(safe_remaining)

    bounded = _fit_payload(safe_metadata, MAX_GRAPH_METADATA_PAYLOAD_CHARS)
    if not isinstance(bounded, Mapping):
        raise GraphContextDataError("Graph node metadata could not be bounded")
    return dict(bounded)


_REMOVED = object()
_UNSAFE_URI = re.compile(r"\b(?:data|file|ftp|javascript|mailto|sftp|ssh|vbscript):", re.IGNORECASE)
_ABSOLUTE_POSIX_PATH = re.compile(r"(?:^|[\s\"'(<>=:])/(?!/)")
_WINDOWS_PATH = re.compile(r"(?:^|[\s\"'(<>=:])[A-Za-z]:[\\/]")
_RELATIVE_LOCAL_PATH = re.compile(
    r"(?:^|[\s\"'(<>=:])(?:(?:\.{1,2}|~)[\\/]|(?:\.local_data|workspace|private|home|users|root|tmp|var|etc|opt|mnt|srv|data)[\\/])",
    re.IGNORECASE,
)
_UNC_PATH = re.compile(r"^(?:\\\\|//)")
_HTTP_URL = re.compile(r"^https?://[^\s/]+(?:[/?#].*)?$", re.IGNORECASE)
_PATH_KEYS = {"path", "file_path", "store_path", "local_path"}
_URL_KEYS = {"url", "article_url", "source_url"}
_MAX_SUPPLEMENT_KEY_CHARS = 128
_MAX_SUPPLEMENT_IDENTITY_CHARS = 256


def _safe_identity(value: str) -> str:
    normalized = value.strip()
    if len(normalized) > _MAX_SUPPLEMENT_IDENTITY_CHARS or _is_unsafe_graph_string(normalized):
        return ""
    return normalized


def sanitize_supplement_identity(value: Any) -> str | None:
    """Return a bounded, path-safe identity for supplemental response sources."""
    if not isinstance(value, str):
        return None
    sanitized = _safe_identity(value)
    return sanitized or None


def _safe_http_url(value: Any) -> str | object | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return _REMOVED
    normalized = value.strip()
    if len(normalized) > MAX_SUPPLEMENT_URL_CHARS or not _HTTP_URL.fullmatch(normalized):
        return _REMOVED
    return normalized


def sanitize_http_url(value: Any) -> str | None:
    """Return a bounded HTTP(S) identity for supplemental response payloads."""
    sanitized = _safe_http_url(value)
    return sanitized if isinstance(sanitized, str) else None


def sanitize_supplement_payload(
    value: Any,
    *,
    max_chars: int = MAX_SUPPLEMENT_PAYLOAD_CHARS,
) -> Any:
    """Sanitize and structurally bound a Graph/Zotero supplemental value."""
    sanitized = _safe_graph_value(value, max_chars=max_chars)
    return None if sanitized is _REMOVED else sanitized


def _is_unsafe_graph_string(value: str) -> bool:
    value = value.strip()
    return bool(
        _UNSAFE_URI.search(value)
        or _ABSOLUTE_POSIX_PATH.search(value)
        or _WINDOWS_PATH.search(value)
        or _UNC_PATH.match(value)
        or _RELATIVE_LOCAL_PATH.search(value)
    )


def _is_path_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
    return normalized in _PATH_KEYS or normalized.endswith("path")


def _is_url_key(key: Any) -> bool:
    normalized = str(key).lower()
    return normalized in _URL_KEYS or normalized.endswith("_url")


def _contains_unsafe_graph_value(value: Any) -> bool:
    if isinstance(value, str):
        return _is_unsafe_graph_string(value)
    if isinstance(value, Mapping):
        return any(_is_path_key(key) or _contains_unsafe_graph_value(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_unsafe_graph_value(item) for item in value)
    return False


def _safe_graph_value(value: Any, *, max_chars: int = MAX_SUPPLEMENT_PAYLOAD_CHARS) -> Any:
    sanitized = _sanitize_graph_value(value, depth=0)
    if sanitized is _REMOVED:
        return _REMOVED
    return _fit_payload(sanitized, max_chars)


def _sanitize_graph_value(value: Any, *, depth: int) -> Any:
    if isinstance(value, str):
        normalized = value.strip()
        if _is_unsafe_graph_string(normalized):
            return _REMOVED
        return normalized[:MAX_SUPPLEMENT_TEXT_CHARS]
    if isinstance(value, Mapping):
        if depth >= MAX_SUPPLEMENT_NESTING_DEPTH:
            return _REMOVED
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in {"content", "body"} or _is_path_key(key_text):
                continue
            bounded_key = key_text[:_MAX_SUPPLEMENT_KEY_CHARS]
            sanitized = (
                _safe_http_url(item)
                if _is_url_key(key_text)
                else _sanitize_graph_value(item, depth=depth + 1)
            )
            if sanitized is _REMOVED:
                continue
            safe[bounded_key] = sanitized
            if len(safe) >= MAX_SUPPLEMENT_MAPPING_ITEMS:
                break
        return safe
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if depth >= MAX_SUPPLEMENT_NESTING_DEPTH:
            return _REMOVED
        safe_items: list[Any] = []
        for item in value:
            sanitized = _sanitize_graph_value(item, depth=depth + 1)
            if sanitized is not _REMOVED:
                safe_items.append(sanitized)
            if len(safe_items) >= MAX_SUPPLEMENT_COLLECTION_ITEMS:
                break
        return tuple(safe_items)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _REMOVED


def _fit_payload(value: Any, max_chars: int) -> Any:
    if max_chars <= 0:
        return _REMOVED
    if _json_size(value) <= max_chars:
        return value
    if isinstance(value, str):
        low = 0
        high = min(len(value), max_chars)
        while low < high:
            middle = (low + high + 1) // 2
            if _json_size(value[:middle]) <= max_chars:
                low = middle
            else:
                high = middle - 1
        return value[:low] if low else _REMOVED
    if isinstance(value, Mapping):
        bounded: dict[str, Any] = {}
        for key, item in value.items():
            available = max_chars - _json_size(bounded) - _json_size(str(key)) - 2
            fitted = _fit_payload(item, available)
            if fitted is _REMOVED:
                continue
            candidate = {**bounded, str(key): fitted}
            if _json_size(candidate) <= max_chars:
                bounded[str(key)] = fitted
        return bounded
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        bounded_items: list[Any] = []
        for item in value:
            available = max_chars - _json_size(bounded_items) - 1
            fitted = _fit_payload(item, available)
            if fitted is _REMOVED:
                continue
            candidate = [*bounded_items, fitted]
            if _json_size(candidate) <= max_chars:
                bounded_items.append(fitted)
        return tuple(bounded_items)
    return _REMOVED


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _estimate_tokens(context: str) -> int:
    return (len(context) + 3) // 4


def _budget_violation(selected: Sequence[SelectedSource], policy: SourceSelectionPolicy, mode: TutorMode) -> bool:
    mode_article_limit, mode_chunk_limit = _mode_limits(mode, policy, policy.max_final_chunks)
    article_ids = {item.result.chunk.article_id for item in selected}
    per_article: dict[str, int] = {}
    for item in selected:
        article_id = item.result.chunk.article_id
        per_article[article_id] = per_article.get(article_id, 0) + 1
    return (
        len(selected) > mode_chunk_limit
        or len(article_ids) > mode_article_limit
        or any(count > policy.max_chunks_per_article for count in per_article.values())
    )
