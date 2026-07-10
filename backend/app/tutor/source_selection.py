from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.rag.vector_store import SearchResult
from app.tutor.models import TutorMode, TutorSource


class TutorSourceConfigurationError(ValueError):
    """Raised when a local selector limit is invalid."""


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
        _validate_limit("max_graph_nodes", self.max_graph_nodes, 100)
        _validate_limit("max_graph_edges", self.max_graph_edges, 200)
        _validate_limit("max_graph_depth", self.max_graph_depth, 2)
        _validate_limit("max_context_chars", self.max_context_chars, 100_000)

    @classmethod
    def from_env(cls) -> "SourceSelectionPolicy":
        return cls(
            max_source_articles=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_SOURCE_ARTICLES", 6, 1, 12),
            max_final_chunks=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_CHUNKS", 10, 1, 20),
            max_graph_nodes=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_NODES", 20, 1, 100),
            max_graph_edges=_bounded_env("SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES", 30, 1, 200),
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
        raw_nodes = graph_context.get("nodes") if isinstance(graph_context.get("nodes"), Sequence) else ()
        raw_edges = graph_context.get("edges") if isinstance(graph_context.get("edges"), Sequence) else ()
        nodes = tuple(_safe_graph_node(item) for item in raw_nodes[: self.policy.max_graph_nodes] if isinstance(item, Mapping))
        edges = tuple(_safe_graph_edge(item) for item in raw_edges[: self.policy.max_graph_edges] if isinstance(item, Mapping))
        return {"nodes": nodes, "edges": edges}, len(raw_nodes) > len(nodes) or len(raw_edges) > len(edges)

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
    unsupported_markers = ("weather", "current news", "latest news", "stock price", "market price", "real-time", "实时", "天气", "新闻", "股价")
    return any(marker in normalized for marker in unsupported_markers)


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


def _safe_graph_node(node: Mapping[str, Any]) -> Mapping[str, Any]:
    safe = {
        "node_id": str(node.get("node_id") or ""),
        "node_type": str(node.get("node_type") or ""),
        "label": str(node.get("label") or ""),
    }
    if "evidence" in node:
        safe["evidence"] = node["evidence"]
    if "source_count" in node:
        safe["source_count"] = node["source_count"]
    if "truncated" in node:
        safe["truncated"] = bool(node["truncated"])
    provenance = node.get("provenance")
    if isinstance(provenance, Sequence) and not isinstance(provenance, (str, bytes)):
        safe["provenance"] = tuple(provenance[:2])
    return safe


def _safe_graph_edge(edge: Mapping[str, Any]) -> Mapping[str, Any]:
    safe = {
        "edge_id": str(edge.get("edge_id") or ""),
        "edge_type": str(edge.get("edge_type") or ""),
        "source_node_id": str(edge.get("source_node_id") or ""),
        "target_node_id": str(edge.get("target_node_id") or ""),
    }
    if "evidence" in edge:
        safe["evidence"] = edge["evidence"]
    return safe


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
