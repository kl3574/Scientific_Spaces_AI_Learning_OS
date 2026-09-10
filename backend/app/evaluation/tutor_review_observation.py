"""Observe candidate-review request isolation without evaluating product answers."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from app.evaluation.tutor_generation import (
    RecordingLegacyProvider,
    code_identity,
    fingerprint,
    synthetic_runtime,
    write_evaluation,
)
from app.evaluation.tutor_review import DEFAULT_CANDIDATE_DIR
from app.llm.provider import ChatRequest, RequestLLMProvider
from app.tutor.generation import POLICY_VERSION
from app.tutor.models import TutorRequest
from app.tutor.retrieval import ConfiguredTutorRetriever, RetrievalResult
from app.tutor.service import TutorService
from app.tutor.source_selection import SourceSelectionPolicy

OBSERVATION_VERSION = "tutor-review-request-observation/v1"
ORACLE_FIELDS = ("proposed_relation", "reference_answer", "must_include", "must_not_claim")
SPY_RESPONSE = "Synthetic request capture only; product answer quality has not been evaluated."


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class RecordingRequestProvider(RequestLLMProvider):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def chat_request(self, request: ChatRequest) -> str:
        self.calls.append({"messages": request.messages()})
        return SPY_RESPONSE

    def chat(self, **kwargs: Any) -> str:
        raise AssertionError("Structured observation must use explicit chat_request dispatch")


class RecordingRetriever:
    """Observe the configured product retriever before unchanged source selection."""

    def __init__(self) -> None:
        self.delegate = ConfiguredTutorRetriever()
        self.source_ids: list[str] = []

    def retrieve(self, request: TutorRequest, candidate_limit: int) -> RetrievalResult:
        result = self.delegate.retrieve(request=request, candidate_limit=candidate_limit)
        self.source_ids = [f"{row.chunk.article_id}:{row.chunk.chunk_index}" for row in result.results]
        return result


def project_product_input(articles: list[dict[str, Any]], case: dict[str, Any]) -> dict[str, Any]:
    """Only user question/mode and allowed Article knowledge cross into the product."""
    allowed_ids = {row["article_id"] for row in case["allowed_evidence"]}
    knowledge = [copy.deepcopy(article) for article in articles if article["id"] in allowed_ids]
    if {article["id"] for article in knowledge} != allowed_ids:
        raise ValueError("Allowed review Article is absent from the candidate snapshot")
    return {"question": case["question"], "mode": case["mode"], "articles": knowledge}


def mutate_oracle(case: dict[str, Any], rubric: dict[str, Any], *, nonce: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """A differential canary changes every listed oracle channel, not product input."""
    mutated = copy.deepcopy(case)
    for field in ORACLE_FIELDS:
        mutated[field] = f"{nonce}:{field}"
    return mutated, {"scoring_rubric": f"{nonce}:rubric", "replaced_rubric_sha256": fingerprint(rubric)}


def _observe(articles: list[dict[str, Any]], case: dict[str, Any], rubric: dict[str, Any], *, path: str) -> dict[str, Any]:
    # Rubric is evaluator-only by construction. Retaining it in the signature
    # lets the metamorphic check exercise the complete observation entry point.
    del rubric
    product = project_product_input(articles, case)
    provider = RecordingLegacyProvider(answer=SPY_RESPONSE) if path == "legacy" else RecordingRequestProvider()
    retriever = RecordingRetriever()
    with synthetic_runtime(product["articles"]) as counters:
        service = TutorService(llm_provider=provider, retriever=retriever,
                               source_selection_policy=SourceSelectionPolicy())
        response = service.answer(TutorRequest(
            question=product["question"], mode=product["mode"], top_k=2,
            include_graph_context=False, include_zotero_context=False,
        ))
    calls = copy.deepcopy(provider.calls)
    return {
        "product_input_sha256": fingerprint(product),
        "calls": calls,
        "request_serialization": _serialize(calls),
        "retrieved_source_ids": retriever.source_ids,
        "selected_source_ids": [source.source_id for source in response.sources if source.source_type == "article_chunk"],
        "refusal_reason": response.refusal_reason,
        "provider_call_count": len(calls),
        "network_attempt_count": counters["network_attempt_count"],
        "external_request_count": counters["external_request_count"],
    }


def observe_review_cases(
    articles: list[dict[str, Any]], cases_payload: dict[str, Any], rubric: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run original/oracle-mutated requests through both real product provider seams."""
    if not cases_payload["cases"]:
        raise ValueError("Review observations require at least one candidate case")
    results: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    for case in cases_payload["cases"]:
        allowed = sorted({row["source_id"] for row in case["allowed_evidence"]})
        required = sorted(set(case.get("required_source_ids", allowed)))
        if not set(required).issubset(allowed):
            raise ValueError("Required review source IDs must belong to allowed evidence")
        nonce = "ORACLE_ONLY_CANARY_" + hashlib.sha256(case["case_id"].encode()).hexdigest()
        if nonce in _serialize({"articles": articles, "case": case, "rubric": rubric}):
            raise ValueError("Differential canary must be unique to the oracle mutation")
        mutated, mutated_rubric = mutate_oracle(case, rubric, nonce=nonce)
        for path in ("legacy", "structured"):
            original = _observe(articles, case, rubric, path=path)
            changed = _observe(articles, mutated, mutated_rubric, path=path)
            same_input = original["product_input_sha256"] == changed["product_input_sha256"]
            same_request = original["request_serialization"] == changed["request_serialization"]
            canary_absent = nonce not in changed["request_serialization"]
            invoked = original["provider_call_count"] == changed["provider_call_count"] == 1
            missing_retrieval = sorted(set(required) - set(original["retrieved_source_ids"]))
            missing_selection = sorted(set(required) - set(original["selected_source_ids"]))
            unauthorized = sorted(set(original["selected_source_ids"]) - set(allowed))
            oracle_isolation = same_input and same_request and canary_absent
            isolation_status = "PASS" if invoked and oracle_isolation else "FAIL" if not oracle_isolation else "NOT_RUN"
            result = {
                "case_id": case["case_id"], "mode": case["mode"], "provider_path": path,
                "oracle_relation_preserved": case["proposed_relation"],
                "oracle_answer_behavior_preserved": case["answer_behavior"],
                "allowed_source_ids": allowed, "required_source_ids": required,
                "required_source_rule": "explicit" if "required_source_ids" in case else "all allowed evidence",
                "required_source_denominator": len(required),
                "retrieved_required_source_count": len(set(required) & set(original["retrieved_source_ids"])),
                "selected_required_source_count": len(set(required) & set(original["selected_source_ids"])),
                "retrieved_source_ids": original["retrieved_source_ids"],
                "selected_source_ids": original["selected_source_ids"],
                "missing_retrieved_source_ids": missing_retrieval,
                "missing_selected_source_ids": missing_selection,
                "unauthorized_selected_source_ids": unauthorized,
                "retrieval_status": "FAIL" if missing_retrieval or missing_selection or unauthorized else "PASS",
                "provider_call_count": original["provider_call_count"],
                "mutated_provider_call_count": changed["provider_call_count"],
                "refusal_reason": original["refusal_reason"],
                "oracle_isolation_status": isolation_status,
                "oracle_isolation_reason": "No generation request reached the spy" if not invoked else None,
                "same_product_input": same_input, "same_actual_request_bytes": same_request,
                "dedicated_canary_absent": canary_absent,
                "request_sha256": hashlib.sha256(original["request_serialization"].encode()).hexdigest(),
                "network_attempt_count": original["network_attempt_count"] + changed["network_attempt_count"],
                "external_request_count": original["external_request_count"] + changed["external_request_count"],
                "product_answer_quality": {"status": "NOT_RUN", "reason": "Request-capture spy only", "score": None},
            }
            results.append(result)
            for variant, observed in (("original", original), ("oracle-mutated", changed)):
                raw_rows.append({"case_id": case["case_id"], "provider_path": path, "variant": variant, **observed})
    failures = [f"{row['case_id']}:{row['provider_path']}" for row in results
                if row["retrieval_status"] == "FAIL" or row["oracle_isolation_status"] != "PASS"
                or row["network_attempt_count"] != 0]
    summary = {
        "schema_version": OBSERVATION_VERSION,
        "status": "FAIL" if failures else "PASS",
        "metadata": {
            "candidate_version": cases_payload["candidate_version"],
            "generation_policy_version": POLICY_VERSION,
            "candidate_inputs_sha256": fingerprint({"articles": articles, "cases": cases_payload, "rubric": rubric}),
            "configuration": {"top_k": 2, "max_context_chars": 24_000, "embedding": "fake",
                              "provider": "request-capture-spy", "graph_context": False, "zotero_context": False},
            "scope": "development/regression request isolation and fixture retrieval; no answer quality evaluation",
            "request_comparison_encoding": "Captured provider arguments/messages as compact sorted-key UTF-8 JSON; not HTTP wire bytes",
        },
        "case_count": len(cases_payload["cases"]), "case_path_denominator": len(results),
        "actual_product_invocations": len(raw_rows),
        "retrieval_passed": sum(row["retrieval_status"] == "PASS" for row in results),
        "oracle_isolation_passed": sum(row["oracle_isolation_status"] == "PASS" for row in results),
        "failed": failures,
        "not_run": [f"{row['case_id']}:{row['provider_path']}:oracle-isolation" for row in results if row["oracle_isolation_status"] == "NOT_RUN"],
        "not_applicable": [], "not_implemented": [], "skipped": [],
        "network_attempt_count": sum(row["network_attempt_count"] for row in results),
        "external_request_count": sum(row["external_request_count"] for row in results),
        "human_review": {"status": "PENDING", "reviewer": None, "approved_at": None},
        "product_answer_quality": {"status": "NOT_RUN", "reason": "Spies return a fixed observation marker", "score": None},
        "results": results,
    }
    return summary, raw_rows


def observe_candidate(candidate_dir: Path = DEFAULT_CANDIDATE_DIR) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from app.evaluation.tutor_review import canonical_bytes, validate_review_candidate

    validation = validate_review_candidate(candidate_dir)
    if not validation["valid"]:
        raise ValueError("Review candidate validation failed: " + ",".join(validation["errors"]))
    articles = json.loads((candidate_dir / "articles.json").read_text(encoding="utf-8"))
    cases = json.loads((candidate_dir / "cases.json").read_text(encoding="utf-8"))
    rubric = json.loads((candidate_dir / "rubric.json").read_text(encoding="utf-8"))
    for name, payload in (("articles.json", articles), ("cases.json", cases), ("rubric.json", rubric)):
        if hashlib.sha256(canonical_bytes(payload)).hexdigest() != validation["content_sha256"][name]:
            raise ValueError("Loaded review content differs from the validated snapshot")
    summary, rows = observe_review_cases(articles, cases, rubric)
    after = validate_review_candidate(candidate_dir)
    if not after["valid"] or after["candidate_digest"] != validation["candidate_digest"]:
        raise ValueError("Review candidate snapshot changed during product observations")
    summary["metadata"].update(code_identity())
    summary["metadata"]["validated_candidate_digest"] = validation["candidate_digest"]
    return summary, rows


def write_review_observation(summary: dict[str, Any], rows: list[dict[str, Any]], *, output_dir: Path) -> dict[str, Any]:
    if not output_dir.name.startswith("review-observation-"):
        raise ValueError("A new review-observation- run directory is required")
    return write_evaluation(summary, rows, output_dir=output_dir)
