"""Offline observations of the actual Tutor path; no semantic or real-model grading."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from unittest.mock import patch

from app.evaluation.provider_eval.operations import audit_evaluation_output
from app.evaluation.provider_eval.output import _ensure_safe_child, _write_json_atomic, _write_jsonl_atomic
from app.evaluation.runner import DEFAULT_FIXTURE_DIR, _patched_env, _write_json
from app.llm.fake import FakeLLMProvider
from app.tutor.models import TutorRequest
from app.tutor.service import TutorService
from app.tutor.source_selection import SourceSelectionPolicy

MODES = ("explain", "derive", "qa", "quiz", "research")
SCHEMA_VERSION = "tutor-generation-evaluation/v1"
EVALUATION_POLICY_VERSION = "synthetic-product-observation/v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = DEFAULT_FIXTURE_DIR / "tutor_generation"
RESPONSE_FIELDS = {
    "answer", "mode", "sources", "graph_context", "zotero_context",
    "follow_up_questions", "refusal_reason", "selection_summary", "evidence_summary",
}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class RecordingLegacyProvider:
    """The original chat-only custom-provider contract, with a real incoming-call spy."""

    def __init__(self, *, answer: str | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.answer = answer
        self.error = error

    def chat(self, *, question: str, contexts: list[Mapping[str, str]]) -> str:
        self.calls.append({"question": question, "contexts": [dict(item) for item in contexts]})
        if self.error is not None:
            raise self.error
        if self.answer is not None:
            return self.answer
        return FakeLLMProvider().chat(question="Synthetic offline observation", contexts=contexts)


@contextmanager
def synthetic_runtime(articles: list[dict[str, Any]]) -> Iterator[dict[str, int]]:
    """Reuse fixture stores, isolate all product configuration, and deny network I/O."""
    with tempfile.TemporaryDirectory(prefix="tutor-generation-eval-") as directory:
        root = Path(directory)
        article_file = root / "articles.json"
        _write_json(article_file, articles)
        _write_json(root / "zotero.json", {})
        env = {
            "SCIENTIFIC_SPACES_ARTICLES_FILE": str(article_file),
            "SCIENTIFIC_SPACES_ARTICLE_STORE": str(article_file),
            "SCIENTIFIC_SPACES_DATA_DIR": str(root),
            "SCIENTIFIC_SPACES_ZOTERO_FILE": str(root / "zotero.json"),
            "SCIENTIFIC_SPACES_GRAPH_FILE": str(root / "graph.json"),
            "SCIENTIFIC_SPACES_LEARNING_FILE": str(root / "learning.json"),
            "SCIENTIFIC_SPACES_TUTOR_FILE": str(root / "tutor.json"),
            "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": "fake",
            "SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake",
            "SCIENTIFIC_SPACES_LEARNING_BACKEND": "json",
        }
        counters = {"network_attempt_count": 0, "external_request_count": 0}

        def denied(*args: Any, **kwargs: Any) -> None:
            counters["network_attempt_count"] += 1
            raise RuntimeError("Network access is disabled for synthetic Tutor evaluation")

        clean_env = {key: value for key, value in os.environ.items() if not key.startswith("SCIENTIFIC_SPACES_")}
        with patch.dict(os.environ, clean_env, clear=True), _patched_env(env), \
                patch.object(socket.socket, "connect", denied), \
                patch.object(socket.socket, "connect_ex", denied), \
                patch.object(socket.socket, "sendto", denied), \
                patch.object(socket, "create_connection", denied), \
                patch.object(socket, "getaddrinfo", denied):
            yield counters


def load_fixture_groups() -> list[dict[str, Any]]:
    existing = json.loads((DEFAULT_FIXTURE_DIR / "articles.json").read_text(encoding="utf-8"))
    return [
        {
            "split": "development", "controlled_mode_comparison": False, "topic": "attention-and-estimation-bound",
            "data_role": "development/regression", "unseen_holdout": False,
            "question": "Attention CRB formula definition",
            "articles": [article for article in existing if article["id"] in {"attention-basics", "crb-formula"}],
        },
        {
            # Historical split identifier retained for existing baseline comparisons.
            # These Articles have already guided development and are no longer unseen.
            "split": "acceptance", "controlled_mode_comparison": True, "topic": "affine-calibration",
            "data_role": "development/regression", "unseen_holdout": False,
            "question": "Affine calibration inverse conditions and example",
            "articles": json.loads((FIXTURE_DIR / "acceptance_articles.json").read_text(encoding="utf-8")),
        },
    ]


def observe_modes(group: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    with synthetic_runtime(group["articles"]) as counters:
        for mode in MODES:
            spy = RecordingLegacyProvider()
            response = TutorService(llm_provider=spy, source_selection_policy=SourceSelectionPolicy()).answer(
                TutorRequest(question=group["question"], mode=mode, top_k=2,
                             include_graph_context=False, include_zotero_context=False)
            )
            rows.append({
                "case_id": f"{group['split']}-{mode}", "split": group["split"], "topic": group["topic"],
                "mode": mode, "calls": spy.calls, "response": response.to_dict(),
            })
    return rows, counters


def _check(case_id: str, passed: bool, *, split: str = "acceptance", detail: str = "") -> dict[str, Any]:
    return {"case_id": case_id, "split": split, "status": "PASS" if passed else "FAIL", "detail": detail}


def _instruction(call: dict[str, Any]) -> str:
    try:
        question = json.loads(call["question"])
    except (ValueError, TypeError):
        return ""
    return str(question.get("trusted_task", "")) if isinstance(question, dict) else ""


def _evidence(call: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for context in call["contexts"]:
        try:
            content = json.loads(context["content"])
        except (ValueError, TypeError):
            content = context["content"]
        rows.append({
            "source_id": context.get("source_id"),
            "content": content.get("untrusted_content") if isinstance(content, dict) else content,
        })
    return rows


def _summarize_contracts(checks: list[dict[str, Any]]) -> dict[str, Any]:
    executed = [check for check in checks if check["status"] in {"PASS", "FAIL"}]
    return {
        "status": "PASS" if executed and all(check["status"] == "PASS" for check in executed) else "FAIL",
        "sample_count": len(checks), "executed_denominator": len(executed),
        "passed": sum(check["status"] == "PASS" for check in checks),
        "failed": [check["case_id"] for check in checks if check["status"] == "FAIL"],
        "skipped": [check for check in checks if check["status"] not in {"PASS", "FAIL"}],
        "checks": checks,
    }


def _metric(numerator: int, denominator: int) -> dict[str, Any]:
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def fixture_arithmetic_observation(answer: str, truth: dict[str, Any]) -> dict[str, Any]:
    """An exact authored-example check, never a general mathematical judge."""
    matches = re.findall(r"\bx\s*=\s*([^\s,;。；]+)", answer)
    expected = (truth["y"] - truth["b"]) / truth["a"]
    token = matches[0].removesuffix(".") if len(matches) == 1 else ""
    observed = float(token) if re.fullmatch(r"-?\d+(?:\.\d+)?", token) else None
    relation = "unresolved" if observed is None else "supported" if observed == expected else "contradicted"
    return {"fixture_arithmetic_relation": relation, "observed_x": observed, "expected_x": expected}


def _boundary_checks(group: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    checks: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    network_attempts = 0
    truth = json.loads((FIXTURE_DIR / "arithmetic_truth.json").read_text(encoding="utf-8"))
    missing_formula = [{**group["articles"][0], "content": "# Affine calibration\n\nAffine calibration is a scale and shift mapping. The defining equation is unavailable."}]
    scenarios = [
        ("no-source", [], "Affine calibration", "qa", "no_sources"),
        ("low-relevance", group["articles"], "volcanic obsidian petrology", "qa", "no_sources"),
        ("derive-no-formula", missing_formula, "Affine calibration", "derive", "insufficient_formula_sources"),
    ]
    for case_id, articles, question, mode, expected in scenarios:
        with synthetic_runtime(articles) as counts:
            spy = RecordingLegacyProvider()
            response = TutorService(llm_provider=spy).answer(TutorRequest(
                question=question, mode=mode, include_graph_context=False, include_zotero_context=False,
            ))
        network_attempts += counts["network_attempt_count"]
        checks.append(_check(case_id, response.refusal_reason == expected and not spy.calls
                             and counts["network_attempt_count"] == 0,
                             detail=f"Expected {expected}; generator calls {len(spy.calls)}"))

    for error in (TimeoutError("synthetic timeout"), RuntimeError("synthetic provider failure")):
        with synthetic_runtime(group["articles"]) as counts:
            spy = RecordingLegacyProvider(error=error)
            observed = None
            try:
                TutorService(llm_provider=spy).answer(TutorRequest(
                    question=group["question"], mode="qa", include_graph_context=False,
                    include_zotero_context=False,
                ))
            except (TimeoutError, RuntimeError) as caught:
                observed = caught
        network_attempts += counts["network_attempt_count"]
        checks.append(_check(f"provider-{type(error).__name__}", observed is error and len(spy.calls) == 1,
                             detail="Service propagates the original exception after one invocation"))

    with synthetic_runtime(group["articles"]) as counts:
        service = TutorService()
        response = service.answer(TutorRequest(question=group["question"], mode="qa",
                                              include_graph_context=False, include_zotero_context=False))
        checks.append(_check("fake-default", isinstance(service.llm_provider, FakeLLMProvider)
                             and response.refusal_reason is None))

    network_attempts += counts["network_attempt_count"]

    for label, answer in (("supported-arithmetic", "For a=2, b=1, y=7 the inverse gives x=3."),
                          ("wrong-claim-valid-source", "For a=2, b=1, y=7 the inverse gives x=99.")):
        with synthetic_runtime(group["articles"]) as counts:
            spy = RecordingLegacyProvider(answer=answer)
            response = TutorService(llm_provider=spy).answer(TutorRequest(
                question=group["question"], mode="qa", top_k=2,
                include_graph_context=False, include_zotero_context=False,
            ))
        network_attempts += counts["network_attempt_count"]
        valid_ids = set(truth["source_ids"])
        arithmetic = fixture_arithmetic_observation(response.answer, truth)
        format_valid = bool(response.sources) and all(source.source_id in valid_ids for source in response.sources)
        contrasts.append({
            "case_id": label, "synthetic": True, "source_ids_valid": format_valid,
            "service_refusal_reason": response.refusal_reason,
            **arithmetic,
            "fixture_relation_basis": "Authored affine example: (7-1)/2 = 3",
            "semantic_correctness": None, "human_review_status": "PENDING",
            "response_sha256": fingerprint(response.to_dict()),
        })
    checks.append(_check("valid-id-does-not-prove-semantic-correctness",
                         all(row["source_ids_valid"] for row in contrasts)
                         and all(row["semantic_correctness"] is None for row in contrasts),
                         detail="Both contrast responses have valid IDs; no semantic score is awarded"))
    checks.append(_check("synthetic-arithmetic-contrast-detected",
                         [row["fixture_arithmetic_relation"] for row in contrasts] == ["supported", "contradicted"],
                         detail="Reads actual returned x and compares against (y-b)/a; exact synthetic example only"))
    checks.extend([
        {"case_id": "automatic-necessary-condition-validation", "split": "acceptance",
         "status": "NOT_IMPLEMENTED", "detail": "No semantic condition validator exists; instruction transfer is tested separately"},
        {"case_id": "public-character-span-scoring", "split": "acceptance", "status": "NOT_APPLICABLE",
         "detail": "TutorSource exposes section/chunk identifiers, not verified character spans; none are invented"},
    ])
    return checks, contrasts, network_attempts


def code_identity(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    def git(*args: str) -> bytes:
        return subprocess.run(["git", "-C", str(repo_root), *args], check=True, capture_output=True).stdout

    head = git("rev-parse", "HEAD").decode().strip()
    tracked_diff = git("diff", "--binary", "HEAD")
    names = git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    untracked = {name: hashlib.sha256((repo_root / name).read_bytes()).hexdigest()
                 for name in names if name and (repo_root / name).is_file() and not (repo_root / name).is_symlink()}
    return {"head": head, "worktree_change_sha256": fingerprint({
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(), "untracked_file_sha256": untracked,
    }), "dirty": bool(tracked_diff or untracked)}


def run_evaluation(*, baseline: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Imported here so the observation helper remains runnable against the unmodified baseline.
    from app.tutor.generation import MODE_TASKS, POLICY_VERSION
    from app.rag.chunking import chunk_article

    groups = load_fixture_groups()
    all_rows: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    split_metrics: dict[str, Any] = {}
    network_attempts = 0
    for group in groups:
        rows, counts = observe_modes(group)
        all_rows.extend(rows)
        network_attempts += counts["network_attempt_count"]
        source_sets = [tuple(source["source_id"] for source in row["response"]["sources"]) for row in rows]
        if group["controlled_mode_comparison"]:
            checks.append(_check(f"{group['split']}-same-ordered-evidence", len(set(source_sets)) == 1,
                                 split=group["split"]))
        calls = [row["calls"][0] for row in rows if len(row["calls"]) == 1]
        checks.append(_check(f"{group['split']}-five-distinct-requests",
                             len(calls) == 5 and len({fingerprint(call) for call in calls}) == 5,
                             split=group["split"]))
        for row in rows:
            transfer = (len(row["calls"]) == 1
                        and MODE_TASKS[row["mode"]] in _instruction(row["calls"][0]))
            checks.append(_check(f"{row['case_id']}-task-transferred", transfer, split=group["split"]))
            checks.append(_check(f"{row['case_id']}-public-response-fields",
                                 set(row["response"]) == RESPONSE_FIELDS and row["response"]["mode"] == row["mode"]
                                 and row["response"]["refusal_reason"] is None, split=group["split"]))
        chunks = {f"{chunk.article_id}:{chunk.chunk_index}": chunk for article in group["articles"]
                  for chunk in chunk_article(article_id=article["id"], article_title=article["title"],
                                             article_url=article["url"], content=article["content"])}
        evidence_rows = [item for call in calls for item in _evidence(call)]
        exact = sum(item["source_id"] in chunks and item["content"] == chunks[item["source_id"]].content
                    for item in evidence_rows)
        returned = [source_id for source_set in source_sets for source_id in source_set]
        split_metrics[group["split"]] = {
            "topic": group["topic"], "article_ids": sorted(article["id"] for article in group["articles"]),
            "data_role": group["data_role"], "unseen_holdout": group["unseen_holdout"],
            "mode_samples": len(rows), "article_count": len(group["articles"]),
            "controlled_mode_comparison": group["controlled_mode_comparison"],
            "observed_ordered_source_variants": len(set(source_sets)),
            "source_id_membership": _metric(sum(source_id in chunks for source_id in returned), len(returned)),
            "exact_synthetic_chunk_content": _metric(exact, len(evidence_rows)),
        }
    boundaries, contrasts, boundary_network_attempts = _boundary_checks(groups[1])
    network_attempts += boundary_network_attempts
    checks.extend(boundaries)
    checks.append(_check("network-denied-zero-attempts", network_attempts == 0))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "metadata": {**code_identity(), "evaluation_policy_version": EVALUATION_POLICY_VERSION,
                     "generation_policy_version": POLICY_VERSION,
                     "fixture_sha256": fingerprint({"groups": groups, "arithmetic_truth": json.loads((FIXTURE_DIR / "arithmetic_truth.json").read_text(encoding="utf-8"))}), "synthetic": True,
                     "configuration": {"embedding": "fake", "provider": "chat-only-spy-and-fake",
                                       "top_k": 2, "max_context_chars": 24_000,
                                       "graph_context": False, "zotero_context": False},
                     "network_attempt_count": network_attempts, "external_request_count": 0,
                     "comparison_conditions": "Historical acceptance split compares the same question and ordered evidence; both splits are development/regression, not unseen holdouts; development preserves existing mode-dependent source selection"},
        "contract_results": _summarize_contracts(checks),
        "fixture_results": {"status": "PASS" if all(
            split[metric]["value"] == 1.0 for split in split_metrics.values()
            for metric in ("source_id_membership", "exact_synthetic_chunk_content")
        ) else "FAIL", "synthetic": True, "splits": split_metrics, "contrast_cases": contrasts,
                            "scope": "Fixture membership and exact chunk text only; not semantic correctness or real retrieval quality"},
        "human_review": {"status": "PENDING", "completed": 0, "sample_denominator": len(all_rows) + len(contrasts),
                         "mathematical_correctness": None, "evidence_support": None, "teaching_clarity": None},
        "real_provider_results": {"status": "NOT_RUN", "reason": "Not authorized in this task",
                                  "sample_count": 0, "quality": None, "latency": None, "cost": None},
    }
    if baseline is not None:
        after = [row for row in all_rows if row["split"] == "acceptance"]
        same = len(baseline) == len(after) == 5 and all(
            old["mode"] == new["mode"] and old["sources"] == [source["source_id"] for source in new["response"]["sources"]]
            and len(old["calls"]) == len(new["calls"]) == 1
            and [entry["content"] for entry in _evidence(old["calls"][0])] == [entry["content"] for entry in _evidence(new["calls"][0])]
            and old["calls"][0]["question"] == json.loads(new["calls"][0]["question"])["user_question"]
            for old, new in zip(baseline, after)
        )
        summary["comparison"] = {
            "baseline_capture_sha256": fingerprint(baseline), "same_question_and_ordered_evidence": same,
            "before_request_variants": len({fingerprint(row["calls"]) for row in baseline}),
            "after_request_variants": len({fingerprint(row["calls"]) for row in after}),
            "scope": "Observed requests only; no answer quality improvement inference",
        }
        if not same:
            summary["contract_results"] = _summarize_contracts(checks + [_check("baseline-comparison-conditions", False)])
    return summary, all_rows


def write_evaluation(summary: dict[str, Any], rows: list[dict[str, Any]], *, output_dir: Path) -> dict[str, Any]:
    """Reuse atomic output/audit primitives; confine all observations to ignored output."""
    allowed_root = REPO_ROOT / "eval_outputs" / "tutor_generation"
    _ensure_safe_child(output_dir, REPO_ROOT)
    _ensure_safe_child(output_dir, allowed_root)
    if allowed_root.is_symlink() or output_dir.resolve() == allowed_root.resolve():
        raise ValueError("Use a new run directory beneath eval_outputs/tutor_generation")
    output_dir.mkdir(parents=True, exist_ok=False)
    completed_at = datetime.now(timezone.utc).isoformat()
    _write_json_atomic(output_dir / "run.json", {**summary["metadata"], "completed_at": completed_at})
    _write_json_atomic(output_dir / "aggregate.json", summary)
    _write_jsonl_atomic(output_dir / "cases.jsonl", rows)
    audit = audit_evaluation_output(output_dir)
    if not audit.passed:
        raise ValueError("Synthetic evaluation output failed the existing artifact audit")
    return audit.to_dict()
