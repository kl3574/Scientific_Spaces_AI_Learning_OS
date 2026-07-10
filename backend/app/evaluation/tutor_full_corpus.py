from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable, Iterator, Literal, Protocol

from app.llm.fake import FakeLLMProvider
from app.llm.provider import OpenAICompatibleLLMProvider
from app.graph.full_corpus import compute_graph_fingerprint
from app.graph.store import GraphStore
from app.rag.full_corpus import (
    FullCorpusIndexError,
    compute_corpus_fingerprint,
    load_full_corpus_articles,
    load_full_corpus_index,
)
from app.tutor.models import TutorRequest, TutorResponse, TutorSource

TutorEvaluationMode = Literal["explain", "derive", "qa", "quiz", "research", "unsupported"]
_EXPECTED_MODE_COUNTS = {"explain": 8, "derive": 8, "qa": 8, "quiz": 8, "research": 6, "unsupported": 4}
_MAX_FAILED_IDS = 50
_HIGH_DEGREE_SOURCE_COUNT = 20
_MAX_GRAPH_NODES = 20
_MAX_GRAPH_EDGES = 30
_EXPECTED_EVIDENCE_TYPES = {"article", "formula", "multi_article", "unsupported"}
_REQUIRED_CASE_FIELDS = {
    "case_id",
    "mode",
    "question",
    "expected_article_ids",
    "min_sources",
    "max_sources",
    "expected_evidence_type",
    "expected_refusal",
    "unsupported",
}
_OPTIONAL_CASE_FIELDS = {"article_id", "node_id", "expected_question_count"}
_URL_VALUE = re.compile(r"(?:\b[a-z][a-z0-9+.-]*://|\bwww\.)", re.IGNORECASE)
_ABSOLUTE_POSIX_PATH = re.compile(r"(?:^|[\s\"'(<>=])/(?!/)")
_WINDOWS_PATH = re.compile(r"(?:^|[\s\"'(<>=])[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"(?:^|[\s\"'(<>=])\\\\[^\\\s]+[\\/]")
_TRAVERSAL_PATH = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")

HARD_METRIC_THRESHOLDS: dict[str, float | int] = {
    "source_schema_valid_rate": 1.0,
    "source_title_present_rate": 1.0,
    "source_url_present_rate": 1.0,
    "supported_case_non_empty_source_rate": 1.0,
    "citation_required_pass_rate": 1.0,
    "no_source_refusal_rate": 1.0,
    "derive_insufficient_evidence_refusal_rate": 1.0,
    "unsupported_answer_fabrication_count": 0,
    "answer_without_sources_count": 0,
    "quiz_question_source_coverage": 1.0,
    "research_local_only_pass_rate": 1.0,
    "source_budget_violation_count": 0,
    "graph_budget_violation_count": 0,
    "high_degree_concept_overexpansion_count": 0,
    "expected_evidence_type_pass_rate": 1.0,
    "supported_derive_formula_evidence_rate": 1.0,
    "research_multi_article_evidence_rate": 1.0,
    "quiz_requested_question_count_pass_rate": 1.0,
    "quiz_normalized_unique_question_rate": 1.0,
    "quiz_topic_relevance_rate": 1.0,
    "quiz_source_mapping_rate": 1.0,
}


class FullCorpusTutorFixtureError(ValueError):
    """Raised when the committed full-corpus Tutor fixture is not exact."""


class RealProviderNotAllowed(ValueError):
    """Raised before a real provider can be initialized."""


@dataclass(frozen=True)
class FullCorpusTutorCase:
    case_id: str
    mode: TutorEvaluationMode
    question: str
    expected_article_ids: tuple[str, ...]
    min_sources: int
    max_sources: int
    expected_evidence_type: str
    expected_refusal: bool
    unsupported: bool
    article_id: str | None = None
    node_id: str | None = None
    expected_question_count: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FullCorpusTutorCase":
        missing = sorted(_REQUIRED_CASE_FIELDS - data.keys())
        if missing:
            raise FullCorpusTutorFixtureError(f"case is missing required fields: {', '.join(missing)}")
        unexpected = sorted(data.keys() - (_REQUIRED_CASE_FIELDS | _OPTIONAL_CASE_FIELDS))
        if unexpected:
            raise FullCorpusTutorFixtureError(
                f"metadata-only case contains unexpected fields: {', '.join(unexpected)}"
            )
        for field_name, value in data.items():
            _validate_metadata_only_value(field_name, value)
        if not isinstance(data["mode"], str):
            raise FullCorpusTutorFixtureError("case mode must be a string")
        mode = data["mode"].strip()
        if mode not in _EXPECTED_MODE_COUNTS:
            raise FullCorpusTutorFixtureError(f"unsupported case mode: {mode}")
        if not isinstance(data["case_id"], str) or not isinstance(data["question"], str):
            raise FullCorpusTutorFixtureError("case_id and question must be strings")
        case_id = data["case_id"].strip()
        question = data["question"].strip()
        raw_expected_ids = data["expected_article_ids"]
        if not isinstance(raw_expected_ids, list) or not all(isinstance(item, str) for item in raw_expected_ids):
            raise FullCorpusTutorFixtureError("expected_article_ids must be a list of strings")
        expected_article_ids = tuple(item.strip() for item in raw_expected_ids)
        if not case_id or not question or any(not item for item in expected_article_ids):
            raise FullCorpusTutorFixtureError("case_id, question, and expected article IDs must be non-empty")
        if (
            not isinstance(data["min_sources"], int)
            or isinstance(data["min_sources"], bool)
            or not isinstance(data["max_sources"], int)
            or isinstance(data["max_sources"], bool)
        ):
            raise FullCorpusTutorFixtureError("source bounds must be integers")
        min_sources = data["min_sources"]
        max_sources = data["max_sources"]
        if min_sources < 0 or max_sources < min_sources:
            raise FullCorpusTutorFixtureError(f"invalid source bounds for case {case_id}")
        if not isinstance(data["expected_refusal"], bool) or not isinstance(data["unsupported"], bool):
            raise FullCorpusTutorFixtureError("expected_refusal and unsupported must be booleans")
        expected_refusal = data["expected_refusal"]
        unsupported = data["unsupported"]
        evidence_type = data["expected_evidence_type"]
        if not isinstance(evidence_type, str) or evidence_type not in _EXPECTED_EVIDENCE_TYPES:
            raise FullCorpusTutorFixtureError(f"invalid expected evidence type for case {case_id}")
        if (mode == "unsupported") != unsupported:
            raise FullCorpusTutorFixtureError(f"unsupported flag must match mode for case {case_id}")
        if unsupported and not expected_refusal:
            raise FullCorpusTutorFixtureError(f"unsupported case must expect refusal for case {case_id}")
        if expected_refusal and mode not in {"derive", "unsupported"}:
            raise FullCorpusTutorFixtureError(f"only Derive and unsupported cases may expect refusal: {case_id}")
        article_id = _optional_identifier(data, "article_id")
        node_id = _optional_identifier(data, "node_id")
        expected_question_count = data.get("expected_question_count")
        if mode == "quiz":
            if "expected_question_count" not in data:
                raise FullCorpusTutorFixtureError(
                    f"Quiz case requires expected_question_count: {case_id}"
                )
            if (
                not isinstance(expected_question_count, int)
                or isinstance(expected_question_count, bool)
                or not 1 <= expected_question_count <= 10
            ):
                raise FullCorpusTutorFixtureError(
                    f"expected_question_count must be an integer between 1 and 10: {case_id}"
                )
        elif "expected_question_count" in data:
            raise FullCorpusTutorFixtureError(
                f"only Quiz cases may define expected_question_count: {case_id}"
            )
        else:
            expected_question_count = None
        if article_id is not None and article_id not in expected_article_ids:
            raise FullCorpusTutorFixtureError(f"article_id must be listed in expected_article_ids: {case_id}")
        if unsupported and (expected_article_ids or article_id is not None or node_id is not None):
            raise FullCorpusTutorFixtureError(f"unsupported case must not reference local resources: {case_id}")
        return cls(
            case_id=case_id,
            mode=mode,  # type: ignore[arg-type]
            question=question,
            expected_article_ids=expected_article_ids,
            min_sources=min_sources,
            max_sources=max_sources,
            expected_evidence_type=evidence_type,
            expected_refusal=expected_refusal,
            unsupported=unsupported,
            article_id=article_id,
            node_id=node_id,
            expected_question_count=expected_question_count,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "case_id": self.case_id,
            "mode": self.mode,
            "question": self.question,
            "expected_article_ids": list(self.expected_article_ids),
            "min_sources": self.min_sources,
            "max_sources": self.max_sources,
            "expected_evidence_type": self.expected_evidence_type,
            "expected_refusal": self.expected_refusal,
            "unsupported": self.unsupported,
        }
        if self.article_id is not None:
            payload["article_id"] = self.article_id
        if self.node_id is not None:
            payload["node_id"] = self.node_id
        if self.expected_question_count is not None:
            payload["expected_question_count"] = self.expected_question_count
        return payload


def load_full_corpus_tutor_cases(path: Path | str) -> list[FullCorpusTutorCase]:
    fixture_path = Path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FullCorpusTutorFixtureError(f"cannot read full-corpus Tutor fixture: {fixture_path.name}") from error
    if not isinstance(payload, list):
        raise FullCorpusTutorFixtureError("full-corpus Tutor fixture must be a JSON list")
    if len(payload) != 42:
        raise FullCorpusTutorFixtureError(f"expected 42 cases, found {len(payload)}")
    if not all(isinstance(item, dict) for item in payload):
        raise FullCorpusTutorFixtureError("full-corpus Tutor fixture entries must be objects")
    cases = [FullCorpusTutorCase.from_dict(item) for item in payload]
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise FullCorpusTutorFixtureError("full-corpus Tutor fixture contains duplicate case IDs")
    mode_counts = dict(Counter(case.mode for case in cases))
    if mode_counts != _EXPECTED_MODE_COUNTS:
        raise FullCorpusTutorFixtureError(
            f"invalid 42-case distribution: expected {_EXPECTED_MODE_COUNTS}, found {mode_counts}"
        )
    if sum(case.mode == "derive" and case.expected_refusal for case in cases) != 3:
        raise FullCorpusTutorFixtureError("expected exactly 3 Derive refusal cases")
    if sum(case.expected_refusal for case in cases) != 7:
        raise FullCorpusTutorFixtureError("expected exactly 7 refusal cases")
    if sum(case.unsupported for case in cases) != 4:
        raise FullCorpusTutorFixtureError("expected exactly 4 unsupported cases")
    if not any(case.node_id == "concept:attention" for case in cases):
        raise FullCorpusTutorFixtureError("expected at least one explicit concept:attention node_id case")
    return cases


def _validate_metadata_only_value(field_name: str, value: Any) -> None:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            return
        values.extend(value)
    for item in values:
        if _URL_VALUE.search(item):
            raise FullCorpusTutorFixtureError(f"metadata-only field {field_name} contains a URL string")
        if (
            _ABSOLUTE_POSIX_PATH.search(item)
            or _WINDOWS_PATH.search(item)
            or _UNC_PATH.search(item)
            or item.lstrip().startswith("\\\\")
            or _TRAVERSAL_PATH.search(item)
        ):
            raise FullCorpusTutorFixtureError(f"metadata-only field {field_name} contains a local path")


def _optional_identifier(data: dict[str, Any], field_name: str) -> str | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise FullCorpusTutorFixtureError(f"{field_name} must be a non-empty string when present")
    return value.strip()


def validate_tutor_evaluation_provider(
    provider: str | None,
    *,
    allow_real_provider: bool = False,
    ci: bool | None = None,
    api_key: str | None = None,
) -> str:
    normalized = (provider or "fake").strip().lower()
    if normalized == "fake":
        return normalized
    if normalized != "openai":
        raise RealProviderNotAllowed(f"unsupported Tutor evaluation provider: {normalized}")
    if not allow_real_provider:
        raise RealProviderNotAllowed("real provider requires explicit opt-in")
    is_ci = _is_ci() if ci is None else ci
    if is_ci:
        raise RealProviderNotAllowed("real provider is forbidden in CI")
    if not (api_key or os.getenv("OPENAI_API_KEY")):
        raise RealProviderNotAllowed("OPENAI_API_KEY is required for real provider evaluation")
    return normalized


class _TutorLike(Protocol):
    def answer(self, request: TutorRequest) -> TutorResponse: ...

    def quiz(self, *, article_id: str | None, node_id: str | None, topic: str | None, num_questions: int): ...


class FullCorpusTutorEvaluationRunner:
    """Evaluate bounded Tutor summaries without persisting corpus or model content."""

    def __init__(
        self,
        *,
        cases: list[FullCorpusTutorCase],
        article_store_path: Path | str,
        rag_index_dir: Path | str,
        graph_dir: Path | str,
        provider: str | None = None,
        allow_real_provider: bool = False,
        service_factory: Callable[[], _TutorLike] | None = None,
        max_failed_ids: int = 20,
    ) -> None:
        if not cases:
            raise ValueError("at least one Tutor evaluation case is required")
        if not 1 <= max_failed_ids <= _MAX_FAILED_IDS:
            raise ValueError(f"max_failed_ids must be between 1 and {_MAX_FAILED_IDS}")
        self.cases = list(cases)
        self.article_store_path = Path(article_store_path).expanduser().resolve()
        self.rag_index_dir = Path(rag_index_dir).expanduser().resolve()
        self.graph_dir = Path(graph_dir).expanduser().resolve()
        self.graph_file = self.graph_dir / "graph.json"
        self.provider = validate_tutor_evaluation_provider(provider, allow_real_provider=allow_real_provider)
        self.service_factory = service_factory
        self.max_failed_ids = max_failed_ids

    def run(self, *, output_path: Path | str | None = None) -> dict[str, Any]:
        self._validate_inputs()
        metrics = _MetricAccumulator(max_failed_ids=self.max_failed_ids)
        timings: dict[str, list[float]] = defaultdict(list)
        with _patched_env(self._runtime_env()):
            service = self._build_service()
            for case in self.cases:
                try:
                    response, quiz_questions, measured = self._run_case(service, case)
                except Exception:
                    metrics.record_execution_error(case.case_id)
                    continue
                metrics.add(case=case, response=response, quiz_questions=quiz_questions)
                for name in ("retrieval", "graph", "selection", "tutor"):
                    timings[name].append(measured[name])

        metric_values = metrics.to_dict()
        hard_metric_failures = _hard_metric_failures(metric_values)
        validity_failures = _evaluation_validity_failures(metric_values)
        if hard_metric_failures or validity_failures:
            status = "BLOCKED"
        elif self.provider != "fake" or not _is_complete_suite(self.cases):
            status = "CONDITIONAL"
        else:
            status = "PASS"
        result = {
            "status": status,
            "provider": self.provider,
            "case_count": len(self.cases),
            "input_kinds": {"article": 1, "rag": 1, "graph": 1},
            "mode_distribution": dict(sorted(Counter(case.mode for case in self.cases).items())),
            "metrics": metric_values,
            "hard_metric_thresholds": dict(HARD_METRIC_THRESHOLDS),
            "hard_metric_failures": hard_metric_failures,
            "evaluation_validity_failures": validity_failures,
            "timings_ms": {
                name: _latency_summary(timings[name])
                for name in ("retrieval", "graph", "selection", "tutor")
            },
            "failed_case_ids": metrics.failed_case_ids,
            "diagnostic_case_ids": metrics.diagnostic_case_ids,
        }
        if output_path is not None:
            _write_ignored_json_atomic(Path(output_path), result)
        return result

    def _validate_inputs(self) -> None:
        if not self.article_store_path.is_file():
            raise FileNotFoundError(f"Article store not found: {self.article_store_path}")
        if not self.rag_index_dir.is_dir():
            raise FileNotFoundError(f"RAG index directory not found: {self.rag_index_dir}")
        if not self.graph_dir.is_dir():
            raise FileNotFoundError(
                f"Graph input must be a directory containing graph.json: {self.graph_dir}"
            )
        if not self.graph_file.is_file():
            raise FileNotFoundError(f"Graph file not found: {self.graph_file}")
        if self.service_factory is not None:
            return

        try:
            articles = load_full_corpus_articles(self.article_store_path)
            corpus_article_ids = {article.id for article in articles}
            referenced_article_ids = {
                article_id
                for case in self.cases
                for article_id in (*case.expected_article_ids, case.article_id)
                if article_id is not None
            }
            missing_article_ids = sorted(referenced_article_ids - corpus_article_ids)
            if missing_article_ids:
                raise ValueError(
                    "Tutor evaluation case Article IDs absent from Article corpus: "
                    + ", ".join(missing_article_ids)
                )
            corpus_fingerprint = compute_corpus_fingerprint(articles)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"Article store input error: {error}") from error
        try:
            rag_artifact_dir = _resolve_rag_artifact_dir(self.rag_index_dir)
            loaded_index = load_full_corpus_index(
                rag_artifact_dir,
                article_store_path=self.article_store_path,
            )
        except (FullCorpusIndexError, OSError, ValueError, json.JSONDecodeError) as error:
            label = "fingerprint" if "fingerprint" in str(error).lower() else "input"
            raise ValueError(f"RAG index {label} error: {error}") from error
        if self.provider == "fake" and loaded_index.manifest.get("provider") != "fake":
            raise ValueError("fake Tutor evaluation requires a fake-provider RAG index")

        manifest_path = self.graph_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Graph manifest not found: {manifest_path}")
        try:
            graph_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Graph manifest input error: {manifest_path}") from error
        if not isinstance(graph_manifest, dict):
            raise ValueError(f"Graph manifest input error: {manifest_path}")
        if graph_manifest.get("corpus_fingerprint") != corpus_fingerprint:
            raise ValueError("Graph corpus fingerprint does not match Article store")
        try:
            graph = GraphStore(self.graph_file).load()
            graph_fingerprint = compute_graph_fingerprint(graph, corpus_fingerprint=corpus_fingerprint)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"Graph input error: {error}") from error
        if graph_manifest.get("graph_fingerprint") != graph_fingerprint:
            raise ValueError("Graph fingerprint does not match graph.json")

    def _runtime_env(self) -> dict[str, str]:
        return {
            "SCIENTIFIC_SPACES_ARTICLE_STORE": str(self.article_store_path),
            "SCIENTIFIC_SPACES_RAG_INDEX_DIR": str(self.rag_index_dir),
            "SCIENTIFIC_SPACES_GRAPH_FILE": str(self.graph_file),
            "SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake",
            "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": self.provider,
        }

    def _build_service(self) -> _TutorLike:
        if self.service_factory is not None:
            return self.service_factory()
        from app.tutor.service import TutorService

        if self.provider == "fake":
            return TutorService(llm_provider=FakeLLMProvider())
        return TutorService(llm_provider=OpenAICompatibleLLMProvider())

    def _run_case(
        self,
        service: _TutorLike,
        case: FullCorpusTutorCase,
    ) -> tuple[TutorResponse, list[Any], dict[str, float]]:
        timings: dict[str, float] = {"retrieval": 0.0, "graph": 0.0, "selection": 0.0, "tutor": 0.0}
        restores: list[tuple[object, str, object]] = []
        for attribute, method_name, timing_name in (
            ("retriever", "retrieve", "retrieval"),
            ("source_selector", "select", "selection"),
            (None, "_collect_graph_context", "graph"),
        ):
            component = service if attribute is None else getattr(service, attribute, None)
            method = getattr(component, method_name, None)
            if component is None or not callable(method):
                continue
            try:
                setattr(component, method_name, _timed(method, timings, timing_name))
                restores.append((component, method_name, method))
            except (AttributeError, TypeError):
                continue
        request_mode = "qa" if case.mode == "unsupported" else case.mode
        request = TutorRequest(
            question=case.question,
            mode=request_mode,  # type: ignore[arg-type]
            article_id=case.article_id,
            node_id=case.node_id,
            top_k=max(1, min(case.max_sources, 10)),
            include_graph_context=bool(case.node_id),
            include_zotero_context=False,
        )
        started = time.perf_counter()
        try:
            response = service.answer(request)
            quiz_questions = self._run_quiz(service, case) if case.mode == "quiz" else []
        finally:
            total_ms = (time.perf_counter() - started) * 1000
            for component, method_name, method in reversed(restores):
                setattr(component, method_name, method)
        component_ms = timings["retrieval"] + timings["graph"] + timings["selection"]
        timings["tutor"] = max(0.0, total_ms - component_ms)
        return response, quiz_questions, timings

    def _run_quiz(self, service: _TutorLike, case: FullCorpusTutorCase) -> list[Any]:
        if case.expected_question_count is None:
            raise ValueError(f"Quiz case is missing expected_question_count: {case.case_id}")
        return list(
            service.quiz(
                article_id=case.article_id,
                node_id=case.node_id,
                topic=case.question,
                num_questions=case.expected_question_count,
            )
        )


class _MetricAccumulator:
    def __init__(self, *, max_failed_ids: int) -> None:
        self.max_failed_ids = max_failed_ids
        self.case_count = 0
        self.article_source_count = 0
        self.selected_chunk_counts: list[int] = []
        self.selected_source_counts: list[int] = []
        self.schema_valid = 0
        self.title_present = 0
        self.url_present = 0
        self.section_present = 0
        self.duplicate_sources = 0
        self.total_sources = 0
        self.expected_hit_cases = 0
        self.expected_article_case_count = 0
        self.expected_expected_articles = 0
        self.expected_matched_articles = 0
        self.expected_selected_articles = 0
        self.irrelevant_article_count = 0
        self.expected_evidence_type_case_count = 0
        self.expected_evidence_type_passes = 0
        self.supported_case_count = 0
        self.supported_case_with_sources = 0
        self.citation_required_count = 0
        self.citation_passes = 0
        self.refusal_matches = 0
        self.refusal_expected_count = 0
        self.unsupported_case_count = 0
        self.no_source_refusal_passes = 0
        self.derive_refusal_case_count = 0
        self.derive_refusal_passes = 0
        self.supported_derive_case_count = 0
        self.supported_derive_formula_passes = 0
        self.unsupported_fabrication_count = 0
        self.answer_without_sources_count = 0
        self.quiz_case_count = 0
        self.quiz_total = 0
        self.quiz_with_sources = 0
        self.empty_quiz_suite_count = 0
        self.quiz_requested_count_passes = 0
        self.quiz_normalized_unique_questions = 0
        self.quiz_topic_relevant_questions = 0
        self.quiz_source_mapped_questions = 0
        self.research_count = 0
        self.research_local_only_passes = 0
        self.research_gaps = 0
        self.research_multi_article_passes = 0
        self.high_degree_concept_overexpansion_count = 0
        self.high_degree_concept_checked_count = 0
        self.mode_context: dict[str, list[tuple[int, int, bool]]] = defaultdict(list)
        self.source_budget_violation_count = 0
        self.graph_budget_violation_count = 0
        self.source_diversity_scores: list[float] = []
        self.execution_error_count = 0
        self.failed_case_ids: dict[str, list[str]] = {}
        self.diagnostic_case_ids: dict[str, list[str]] = {}

    def add(self, *, case: FullCorpusTutorCase, response: TutorResponse, quiz_questions: list[Any]) -> None:
        self.case_count += 1
        article_sources = [source for source in response.sources if source.source_type == "article_chunk"]
        source_ids = [source.source_id for source in article_sources]
        source_count = len(article_sources)
        self.total_sources += source_count
        self.article_source_count += source_count
        self.selected_source_counts.append(source_count)
        self.selected_chunk_counts.append(response.selection_summary.selected_chunk_count)
        self.duplicate_sources += source_count - len(set(source_ids))
        for source in article_sources:
            self.schema_valid += int(_valid_article_source(source))
            self.title_present += int(isinstance(source.title, str) and bool(source.title.strip()))
            self.url_present += int(isinstance(source.url, str) and bool(source.url.strip()))
            self.section_present += int(
                isinstance(source.section_title, str) and bool(source.section_title.strip())
            )

        source_article_ids = {
            article_id
            for source in article_sources
            if (article_id := _article_id(source.source_id))
        }
        self.source_diversity_scores.append(len(source_article_ids) / source_count if source_count else 0.0)
        expected_ids = set(case.expected_article_ids)
        matched_ids = source_article_ids & expected_ids
        if expected_ids and not case.expected_refusal:
            self.expected_article_case_count += 1
            self.expected_hit_cases += int(bool(matched_ids))
            self.expected_expected_articles += len(expected_ids)
            self.expected_matched_articles += len(matched_ids)
            self.expected_selected_articles += len(source_article_ids)
            self.irrelevant_article_count += sum(
                article_id not in expected_ids for article_id in source_article_ids
            )
            if expected_ids - matched_ids:
                self._diagnostic("expected_article_miss_ids", case.case_id)

        source_budget_violation = (
            source_count < case.min_sources
            or source_count > case.max_sources
            or source_count > 10
            or len(source_article_ids) > 6
            or (case.mode == "research" and not case.expected_refusal and len(source_article_ids) < 2)
            or response.selection_summary.selected_chunk_count > 10
            or response.selection_summary.selected_article_count > 6
        )
        if source_budget_violation:
            self.source_budget_violation_count += 1
            self._fail("budget_violation_ids", case.case_id)

        self._check_graph_budget(case, response)
        refused = response.refusal_reason is not None
        self.refusal_expected_count += int(case.expected_refusal)
        self.refusal_matches += int(refused == case.expected_refusal)
        if refused != case.expected_refusal:
            self._fail("refusal_mismatch_ids", case.case_id)

        self.expected_evidence_type_case_count += 1
        evidence_type_matches = _matches_expected_evidence_type(
            case=case,
            response=response,
            source_article_ids=source_article_ids,
        )
        self.expected_evidence_type_passes += int(evidence_type_matches)
        if not evidence_type_matches:
            self._fail("expected_evidence_type_failure_ids", case.case_id)

        if case.mode == "derive" and not case.expected_refusal:
            self.supported_derive_case_count += 1
            formula_evidence_present = response.evidence_summary.has_formula_evidence is True
            self.supported_derive_formula_passes += int(formula_evidence_present)
            if not formula_evidence_present:
                self._fail("supported_derive_formula_evidence_failure_ids", case.case_id)

        if not case.expected_refusal:
            self.supported_case_count += 1
            self.supported_case_with_sources += int(source_count > 0)
            self.citation_required_count += 1
            citation_ok = source_count > 0 and all(_valid_article_source(source) for source in article_sources)
            self.citation_passes += int(citation_ok)
            if source_count == 0:
                self._fail("supported_case_without_source_ids", case.case_id)
            if bool(response.answer.strip()) and source_count == 0:
                self.answer_without_sources_count += 1
                self._fail("answer_without_source_ids", case.case_id)
            if not citation_ok:
                self._fail("citation_failure_ids", case.case_id)

        if case.unsupported:
            self.unsupported_case_count += 1
            no_source_refusal = response.refusal_reason == "no_sources" and not response.sources
            self.no_source_refusal_passes += int(no_source_refusal)
            if not no_source_refusal:
                self._fail("no_source_refusal_failure_ids", case.case_id)
            if not refused or bool(response.sources):
                self.unsupported_fabrication_count += 1
                self._fail("fabrication_ids", case.case_id)

        if case.mode == "derive" and case.expected_refusal:
            self.derive_refusal_case_count += 1
            internal_reason = response.evidence_summary.refusal_reason
            derive_refusal = (
                response.refusal_reason == "insufficient_formula_sources"
                and internal_reason == "insufficient_formula_evidence"
            )
            self.derive_refusal_passes += int(derive_refusal)
            if not derive_refusal:
                self._fail("derive_refusal_failure_ids", case.case_id)

        if case.mode == "quiz":
            self.quiz_case_count += 1
            case_question_count = len(quiz_questions)
            case_questions_with_sources = 0
            case_questions_with_source_mapping = 0
            normalized_questions = [
                _normalize_quiz_text(getattr(question, "question", None))
                for question in quiz_questions
            ]
            unique_question_count = len(set(normalized_questions))
            topic_relevant_count = sum(
                _quiz_question_matches_topic(
                    topic=case.question,
                    question=getattr(question, "question", None),
                )
                for question in quiz_questions
            )
            expected_source_ids = (
                {case.article_id}
                if case.article_id is not None
                else set(case.expected_article_ids)
            )
            for question in quiz_questions:
                raw_sources = getattr(question, "sources", [])
                if not isinstance(raw_sources, list):
                    raw_sources = []
                question_sources = [
                    source
                    for source in raw_sources
                    if getattr(source, "source_type", None) == "article_chunk"
                ]
                valid_question_sources = bool(question_sources) and all(
                    _valid_article_source(source) for source in question_sources
                )
                if valid_question_sources:
                    case_questions_with_sources += 1
                source_mapping_valid = (
                    valid_question_sources
                    and len(question_sources) == len(raw_sources)
                    and bool(expected_source_ids)
                    and all(
                        _article_id(source.source_id) in expected_source_ids
                        for source in question_sources
                    )
                )
                if source_mapping_valid:
                    case_questions_with_source_mapping += 1
            self.quiz_total += len(quiz_questions)
            self.quiz_with_sources += case_questions_with_sources
            self.quiz_normalized_unique_questions += unique_question_count
            self.quiz_topic_relevant_questions += topic_relevant_count
            self.quiz_source_mapped_questions += case_questions_with_source_mapping
            expected_count = case.expected_question_count
            count_matches = expected_count is not None and case_question_count == expected_count
            self.quiz_requested_count_passes += int(count_matches)
            if not count_matches:
                self._fail("quiz_question_count_failure_ids", case.case_id)
            if unique_question_count != case_question_count:
                self._fail("quiz_duplicate_question_ids", case.case_id)
            if topic_relevant_count != case_question_count:
                self._fail("quiz_topic_relevance_failure_ids", case.case_id)
            if case_questions_with_source_mapping != case_question_count:
                self._fail("quiz_source_mapping_failure_ids", case.case_id)
            if not quiz_questions:
                self.empty_quiz_suite_count += 1
                self._fail("quiz_coverage_failure_ids", case.case_id)
            elif case_questions_with_sources != case_question_count:
                self._fail("quiz_coverage_failure_ids", case.case_id)
        if case.mode == "research":
            self.research_count += 1
            multi_article_evidence = len(source_article_ids) >= 2
            self.research_multi_article_passes += int(multi_article_evidence)
            if not multi_article_evidence:
                self._fail("research_multi_article_evidence_failure_ids", case.case_id)
            normalized_answer = response.answer.lower()
            local_only = "本地" in response.answer or "local" in normalized_answer
            has_gap = "资料缺口" in response.answer or "gap" in normalized_answer
            self.research_local_only_passes += int(local_only and has_gap)
            self.research_gaps += int(has_gap)
            if not local_only:
                self._fail("research_local_only_failure_ids", case.case_id)
            if not has_gap:
                self._fail("research_gap_failure_ids", case.case_id)

        self.mode_context[case.mode].append(
            (
                response.selection_summary.context_character_count,
                response.selection_summary.estimated_token_count,
                response.selection_summary.truncated,
            )
        )
        self._check_graph_overexpansion(case, response.graph_context)

    def _check_graph_budget(self, case: FullCorpusTutorCase, response: TutorResponse) -> None:
        context = response.graph_context if isinstance(response.graph_context, dict) else {}
        nodes = context.get("nodes") if isinstance(context.get("nodes"), list) else []
        edges = context.get("edges") if isinstance(context.get("edges"), list) else []
        unexpected_expansion = not case.node_id and bool(
            nodes
            or edges
            or response.selection_summary.graph_node_count
            or response.selection_summary.graph_edge_count
        )
        violation = (
            unexpected_expansion
            or len(nodes) > _MAX_GRAPH_NODES
            or len(edges) > _MAX_GRAPH_EDGES
            or response.selection_summary.graph_node_count > _MAX_GRAPH_NODES
            or response.selection_summary.graph_edge_count > _MAX_GRAPH_EDGES
        )
        if violation:
            self.graph_budget_violation_count += 1
            self._fail("graph_budget_violation_ids", case.case_id)

    def _check_graph_overexpansion(self, case: FullCorpusTutorCase, context: dict[str, Any]) -> None:
        if not case.node_id:
            return
        for node in context.get("nodes", []) if isinstance(context, dict) else []:
            if not isinstance(node, dict):
                continue
            if node.get("node_id") != case.node_id:
                continue
            metadata = node.get("metadata")
            if not isinstance(metadata, dict):
                continue
            source_count = metadata.get("source_count")
            if (
                not isinstance(source_count, int)
                or isinstance(source_count, bool)
                or source_count <= _HIGH_DEGREE_SOURCE_COUNT
            ):
                continue
            self.high_degree_concept_checked_count += 1
            provenance = metadata.get("sources")
            provenance_overflow = isinstance(provenance, (list, tuple)) and len(provenance) > 2
            if metadata.get("truncated") is not True or provenance_overflow:
                self.high_degree_concept_overexpansion_count += 1
                self._fail("high_degree_overexpansion_ids", case.case_id)

    def record_execution_error(self, case_id: str) -> None:
        self.execution_error_count += 1
        self._fail("execution_error_ids", case_id)

    def _fail(self, key: str, case_id: str) -> None:
        values = self.failed_case_ids.setdefault(key, [])
        if len(values) < self.max_failed_ids and case_id not in values:
            values.append(case_id)

    def _diagnostic(self, key: str, case_id: str) -> None:
        values = self.diagnostic_case_ids.setdefault(key, [])
        if len(values) < self.max_failed_ids and case_id not in values:
            values.append(case_id)

    def to_dict(self) -> dict[str, Any]:
        mode_context = {
            mode: {
                "context_characters": _distribution([item[0] for item in values]),
                "estimated_tokens": _distribution([item[1] for item in values]),
                "truncation_rate": _rate(item[2] for item in values),
            }
            for mode, values in sorted(self.mode_context.items())
        }
        return {
            "selected_source_count_distribution": _distribution(self.selected_source_counts),
            "selected_chunk_count_distribution": _distribution(self.selected_chunk_counts),
            "duplicate_source_rate": self.duplicate_sources / self.total_sources if self.total_sources else 0.0,
            "source_schema_valid_rate": _fraction(self.schema_valid, self.article_source_count),
            "source_title_present_rate": _fraction(self.title_present, self.article_source_count),
            "source_url_present_rate": _fraction(self.url_present, self.article_source_count),
            "source_section_present_rate": _fraction(self.section_present, self.article_source_count),
            "supported_case_non_empty_source_rate": _fraction(
                self.supported_case_with_sources,
                self.supported_case_count,
            ),
            "source_budget_violation_count": self.source_budget_violation_count,
            "graph_budget_violation_count": self.graph_budget_violation_count,
            "expected_article_hit_rate": _fraction(self.expected_hit_cases, self.expected_article_case_count),
            "expected_article_recall": _fraction(self.expected_matched_articles, self.expected_expected_articles),
            "source_diversity_rate": _mean_or_zero(self.source_diversity_scores),
            "irrelevant_article_rate": _fraction(
                self.irrelevant_article_count,
                self.expected_selected_articles,
            ),
            "expected_evidence_type_pass_rate": _fraction(
                self.expected_evidence_type_passes,
                self.expected_evidence_type_case_count,
            ),
            "supported_derive_formula_evidence_rate": _fraction(
                self.supported_derive_formula_passes,
                self.supported_derive_case_count,
            ),
            "high_degree_concept_checked_count": self.high_degree_concept_checked_count,
            "high_degree_concept_overexpansion_count": self.high_degree_concept_overexpansion_count,
            "citation_required_pass_rate": _fraction(
                self.citation_passes,
                self.citation_required_count,
            ),
            "refusal_match_rate": _fraction(self.refusal_matches, self.case_count),
            "expected_refusal_count": self.refusal_expected_count,
            "no_source_refusal_rate": _fraction(
                self.no_source_refusal_passes,
                self.unsupported_case_count,
            ),
            "derive_insufficient_evidence_refusal_rate": _fraction(
                self.derive_refusal_passes,
                self.derive_refusal_case_count,
            ),
            "unsupported_answer_fabrication_count": self.unsupported_fabrication_count,
            "answer_without_sources_count": self.answer_without_sources_count,
            "quiz_question_source_coverage": _fraction(
                self.quiz_with_sources,
                self.quiz_total + self.empty_quiz_suite_count,
            ),
            "quiz_question_count": self.quiz_total,
            "empty_quiz_suite_count": self.empty_quiz_suite_count,
            "quiz_requested_question_count_pass_rate": _fraction(
                self.quiz_requested_count_passes,
                self.quiz_case_count,
            ),
            "quiz_normalized_unique_question_rate": _fraction(
                self.quiz_normalized_unique_questions,
                self.quiz_total,
            ),
            "quiz_topic_relevance_rate": _fraction(
                self.quiz_topic_relevant_questions,
                self.quiz_total,
            ),
            "quiz_source_mapping_rate": _fraction(
                self.quiz_source_mapped_questions,
                self.quiz_total,
            ),
            "research_local_only_pass_rate": _fraction(
                self.research_local_only_passes,
                self.research_count,
            ),
            "research_gap_rate": _fraction(self.research_gaps, self.research_count),
            "research_multi_article_evidence_rate": _fraction(
                self.research_multi_article_passes,
                self.research_count,
            ),
            "execution_error_count": self.execution_error_count,
            "mode_context": mode_context,
        }


def _timed(method, timings: dict[str, float], name: str):
    def wrapped(*args, **kwargs):
        started = time.perf_counter()
        try:
            return method(*args, **kwargs)
        finally:
            timings[name] += (time.perf_counter() - started) * 1000

    return wrapped


def _valid_article_source(source: TutorSource) -> bool:
    return bool(
        source.source_type == "article_chunk"
        and isinstance(source.source_id, str)
        and source.source_id.strip()
        and isinstance(source.title, str)
        and source.title.strip()
        and isinstance(source.url, str)
        and source.url.strip()
        and isinstance(source.section_title, str)
        and source.section_title.strip()
        and isinstance(source.chunk_index, int)
        and not isinstance(source.chunk_index, bool)
        and source.chunk_index >= 0
    )


def _article_id(source_id: Any) -> str:
    return source_id.rsplit(":", 1)[0] if isinstance(source_id, str) else ""


def _normalize_quiz_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _quiz_question_matches_topic(*, topic: str, question: Any) -> bool:
    normalized_topic = _normalize_quiz_text(topic)
    normalized_question = _normalize_quiz_text(question)
    return bool(normalized_topic) and normalized_topic in normalized_question


def _matches_expected_evidence_type(
    *,
    case: FullCorpusTutorCase,
    response: TutorResponse,
    source_article_ids: set[str],
) -> bool:
    if case.expected_evidence_type == "formula":
        if case.expected_refusal:
            return response.evidence_summary.refusal_reason == "insufficient_formula_evidence"
        return response.evidence_summary.has_formula_evidence is True
    if case.expected_evidence_type == "article":
        return bool(source_article_ids)
    if case.expected_evidence_type == "multi_article":
        return len(source_article_ids) >= 2
    if case.expected_evidence_type == "unsupported":
        return response.refusal_reason == "no_sources" and not response.sources
    return False


def _hard_metric_failures(metrics: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    failures: dict[str, dict[str, float | int]] = {}
    for name, required in HARD_METRIC_THRESHOLDS.items():
        actual = metrics.get(name)
        if actual != required:
            failures[name] = {"actual": actual, "required": required}
    return failures


def _resolve_rag_artifact_dir(path: Path) -> Path:
    if (path / "manifest.json").is_file():
        return path
    if (path / "index" / "manifest.json").is_file():
        return path / "index"
    raise FullCorpusIndexError(f"Full-corpus index manifest not found under: {path}")


def _evaluation_validity_failures(metrics: dict[str, Any]) -> dict[str, dict[str, int]]:
    failures: dict[str, dict[str, int]] = {}
    execution_errors = int(metrics.get("execution_error_count") or 0)
    if execution_errors:
        failures["execution_error_count"] = {"actual": execution_errors, "required": 0}
    high_degree_checked = int(metrics.get("high_degree_concept_checked_count") or 0)
    if high_degree_checked < 1:
        failures["high_degree_concept_checked_count"] = {"actual": high_degree_checked, "required": 1}
    return failures


def _is_complete_suite(cases: list[FullCorpusTutorCase]) -> bool:
    return (
        len(cases) == 42
        and dict(Counter(case.mode for case in cases)) == _EXPECTED_MODE_COUNTS
        and sum(case.mode == "derive" and case.expected_refusal for case in cases) == 3
        and sum(case.unsupported for case in cases) == 4
    )


def _distribution(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0, "mean": 0.0, "median": 0.0, "p95": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "mean": float(mean(ordered)),
        "median": float(median(ordered)),
        "p95": ordered[_p95_index(len(ordered))],
        "max": ordered[-1],
    }


def _latency_summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "mean": float(mean(ordered)),
        "median": float(median(ordered)),
        "p95": ordered[_p95_index(len(ordered))],
        "max": ordered[-1],
    }


def _p95_index(length: int) -> int:
    return max(0, math.ceil(length * 0.95) - 1)


def _rate(values) -> float:
    materialized = list(values)
    return _fraction(sum(bool(value) for value in materialized), len(materialized))


def _fraction(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _mean_or_zero(values: list[float]) -> float:
    return float(mean(values)) if values else 0.0


def _is_ci() -> bool:
    return any(os.getenv(name, "").strip().lower() in {"1", "true", "yes"} for name in ("CI", "GITHUB_ACTIONS"))


@contextmanager
def _patched_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_ignored_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.expanduser().resolve()
    if ".local_data" not in resolved.parts:
        raise ValueError("Tutor evaluation output must be under an ignored .local_data directory")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(f".{resolved.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, resolved)
    finally:
        if temporary.exists():
            temporary.unlink()
