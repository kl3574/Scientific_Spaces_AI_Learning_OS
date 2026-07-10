from __future__ import annotations

import json
import math
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

from app.rag.full_corpus import (
    FullCorpusRagService,
    FullCorpusChunk,
    FullCorpusIndexError,
    embedding_provider_for_manifest,
    load_full_corpus_articles,
    load_full_corpus_index,
)
from app.rag.service import NO_SOURCE_ANSWER


@dataclass(frozen=True)
class FullCorpusRetrievalCase:
    case_id: str
    category: str
    question: str
    expected_article_ids: tuple[str, ...] = ()
    expected_refusal: bool = False
    top_k: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "question": self.question,
            "expected_article_ids": list(self.expected_article_ids),
            "expected_refusal": self.expected_refusal,
            "top_k": self.top_k,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FullCorpusRetrievalCase":
        return cls(
            case_id=str(data["case_id"]),
            category=str(data["category"]),
            question=str(data["question"]),
            expected_article_ids=tuple(str(item) for item in data.get("expected_article_ids", [])),
            expected_refusal=bool(data.get("expected_refusal", False)),
            top_k=int(data.get("top_k", 10)),
        )


def default_full_corpus_cases() -> list[FullCorpusRetrievalCase]:
    return [
        FullCorpusRetrievalCase(
            case_id="attention_transformer",
            category="attention_transformer",
            question="Attention is All You Need query key value",
            expected_article_ids=("69e708f3cca249cf",),
        ),
        FullCorpusRetrievalCase(
            case_id="probability_statistics",
            category="probability_statistics",
            question="傅里叶级数拟合一维概率密度函数",
            expected_article_ids=("521a5341f8f043db",),
        ),
        FullCorpusRetrievalCase(
            case_id="optimizer",
            category="optimizer",
            question="Muon优化器 从向量到矩阵",
            expected_article_ids=("a125a50e90a05ab1",),
        ),
        FullCorpusRetrievalCase(
            case_id="diffusion_model",
            category="diffusion_model",
            question="DDPM 拆楼 建楼 生成扩散模型",
            expected_article_ids=("b82bf69b78f43224",),
        ),
        FullCorpusRetrievalCase(
            case_id="matrix_analysis",
            category="matrix_analysis",
            question="矩阵函数近似中的暴力美学",
            expected_article_ids=("fa0f240c54f24dd6",),
        ),
        FullCorpusRetrievalCase(
            case_id="variational_differential_equation",
            category="variational_differential_equation",
            question="变分与理论力学",
            expected_article_ids=("236014ed5caff857",),
        ),
        FullCorpusRetrievalCase(
            case_id="early_mathematics",
            category="early_mathematics",
            question="正十七边形的尺规作图",
            expected_article_ids=("768eace5587506b5",),
        ),
        FullCorpusRetrievalCase(
            case_id="astronomy_physics",
            category="astronomy_physics",
            question="NASA每日一图 经典的猎户座星云",
            expected_article_ids=("8f42ff9cb70827e1",),
        ),
        FullCorpusRetrievalCase(
            case_id="nlp_bert",
            category="nlp_bert",
            question="当Bert遇上Keras",
            expected_article_ids=("711dc29f2a841a4e",),
        ),
        FullCorpusRetrievalCase(
            case_id="gan_vae",
            category="gan_vae",
            question="用变分推断统一理解 VAE GAN AAE ALI",
            expected_article_ids=("ccad0ab5f530e981",),
        ),
        FullCorpusRetrievalCase(
            case_id="website_tools",
            category="website_tools",
            question="MathJax兼容谷歌翻译和延时加载",
            expected_article_ids=("dd6de529aa0fe808",),
        ),
        FullCorpusRetrievalCase(
            case_id="unsupported",
            category="unsupported",
            question="zxqv_unsupported_7f3c9a",
            expected_refusal=True,
        ),
    ]


class FullCorpusEvaluationRunner:
    def __init__(
        self,
        *,
        article_store_path: Path | str,
        index_dir: Path | str,
        cases: list[FullCorpusRetrievalCase] | None = None,
        expected_article_count: int | None = None,
    ) -> None:
        self.article_store_path = Path(article_store_path).expanduser().resolve()
        self.index_dir, self.output_root = _resolve_index_paths(Path(index_dir).expanduser().resolve())
        self.cases = cases or default_full_corpus_cases()
        self.expected_article_count = expected_article_count

    def run(self) -> dict[str, Any]:
        articles = load_full_corpus_articles(self.article_store_path)
        if self.expected_article_count is not None and len(articles) != self.expected_article_count:
            raise FullCorpusIndexError(
                f"Expected {self.expected_article_count} Articles but found {len(articles)}"
            )
        loaded = load_full_corpus_index(self.index_dir, article_store_path=self.article_store_path)
        provider = embedding_provider_for_manifest(loaded.manifest)
        service = FullCorpusRagService(loaded_index=loaded, embedding_provider=provider)
        chunks_by_key = {(chunk.article_id, chunk.chunk_index): chunk for chunk in loaded.chunks}

        rows: list[dict[str, Any]] = []
        latencies_ms: list[float] = []
        retrieval_errors = 0
        for case in self.cases:
            started = time.perf_counter()
            try:
                row = self._run_case(
                    case,
                    loaded=loaded,
                    embedding_provider=provider,
                    service=service,
                    chunks_by_key=chunks_by_key,
                )
            except Exception as exc:
                retrieval_errors += 1
                row = {
                    "case_id": case.case_id,
                    "category": case.category,
                    "question": case.question,
                    "expected_article_ids": list(case.expected_article_ids),
                    "expected_refusal": case.expected_refusal,
                    "answer": NO_SOURCE_ANSWER,
                    "sources": [],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            latency_ms = (time.perf_counter() - started) * 1000
            row["latency_ms"] = latency_ms
            latencies_ms.append(latency_ms)
            rows.append(row)

        metrics = _calculate_metrics(
            cases=self.cases,
            rows=rows,
            article_count=len(articles),
            indexed_article_ids={chunk.article_id for chunk in loaded.chunks},
            retrieval_error_count=retrieval_errors,
        )
        rag_service_smoke = _rag_service_smoke(
            cases=self.cases,
            service=service,
        )
        performance = _latency_summary(latencies_ms)
        status = "PASS" if _passes(metrics, rag_service_smoke) else "BLOCKED"
        result = {
            "status": status,
            "provider": loaded.manifest["provider"],
            "corpus_fingerprint": loaded.manifest["corpus_fingerprint"],
            "metrics": metrics,
            "performance": performance,
            "cases": rows,
            "rag_service_smoke": rag_service_smoke,
            "limitations": [
                "Fake embeddings provide deterministic structural evidence, not production semantic quality.",
                "Unsupported-query refusal uses an exact local-token support gate before the frozen no-source contract.",
            ],
        }
        reports_dir = self.output_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(reports_dir / "retrieval_smoke.json", result)
        _write_json_atomic(
            reports_dir / "benchmark.json",
            {
                "provider": loaded.manifest["provider"],
                "article_count": loaded.manifest["article_count"],
                "chunk_count": loaded.manifest["chunk_count"],
                **performance,
            },
        )
        return result

    def _run_case(
        self,
        case: FullCorpusRetrievalCase,
        *,
        loaded,
        embedding_provider,
        service: FullCorpusRagService,
        chunks_by_key: dict[tuple[str, int], FullCorpusChunk],
    ) -> dict[str, Any]:
        locally_supported = service.has_local_support(case.question)
        service_payload = service.answer(
            question=case.question,
            top_k=max(1, min(case.top_k, 20)),
        )
        service_sources = [dict(source) for source in service_payload.get("sources", [])]
        sources: list[dict[str, Any]] = []
        if service_sources:
            results = loaded.vector_store.search(
                case.question,
                top_k=max(1, min(case.top_k, 20)),
                embedding_provider=embedding_provider,
            )
            for result in results:
                chunk = chunks_by_key[(result.chunk.article_id, result.chunk.chunk_index)]
                sources.append(chunk.to_source(score=result.score))
        return {
            "case_id": case.case_id,
            "category": case.category,
            "question": case.question,
            "expected_article_ids": list(case.expected_article_ids),
            "expected_refusal": case.expected_refusal,
            "local_token_support": locally_supported,
            "answer": str(service_payload.get("answer") or NO_SOURCE_ANSWER),
            "sources": sources,
            "service_sources": service_sources,
            "error": None,
        }


def _calculate_metrics(
    *,
    cases: list[FullCorpusRetrievalCase],
    rows: list[dict[str, Any]],
    article_count: int,
    indexed_article_ids: set[str],
    retrieval_error_count: int,
) -> dict[str, Any]:
    paired = list(zip(cases, rows))
    supported = [(case, row) for case, row in paired if not case.expected_refusal]
    unsupported = [(case, row) for case, row in paired if case.expected_refusal]
    all_sources = [source for _case, row in paired for source in row["sources"]]
    all_service_sources = [source for _case, row in paired for source in row.get("service_sources", [])]
    expected_rows = [(case, row) for case, row in supported if case.expected_article_ids]
    duplicate_source_count = sum(
        len(row["sources"]) - len({source["chunk_id"] for source in row["sources"]})
        for _case, row in paired
    )
    unsupported_fabrications = sum(
        1
        for _case, row in unsupported
        if row["answer"] != NO_SOURCE_ANSWER or bool(row.get("service_sources"))
    )
    return {
        "indexed_article_coverage_rate": len(indexed_article_ids) / article_count if article_count else 1.0,
        "retrieval_query_count": len(cases),
        "supported_query_source_rate": _rate(bool(row["sources"]) for _case, row in supported),
        "service_supported_query_source_rate": _rate(
            bool(row.get("service_sources")) and row["answer"] != NO_SOURCE_ANSWER for _case, row in supported
        ),
        "expected_article_hit_at_k": _rate(
            bool(set(case.expected_article_ids) & {source["article_id"] for source in row["sources"]})
            for case, row in expected_rows
        ),
        "source_schema_valid_rate": _rate(_valid_source(source) for source in all_sources),
        "source_title_present_rate": _rate(bool(source.get("title")) for source in all_sources),
        "source_url_present_rate": _rate(bool(source.get("url")) for source in all_sources),
        "source_section_present_rate": _rate(bool(source.get("section")) for source in all_sources),
        "service_source_schema_valid_rate": _rate(_valid_rag_source(source) for source in all_service_sources),
        "no_source_refusal_rate": _rate(
            row["answer"] == NO_SOURCE_ANSWER and not row.get("service_sources") for _case, row in unsupported
        ),
        "unsupported_answer_fabrication_count": unsupported_fabrications,
        "duplicate_source_count": duplicate_source_count,
        "retrieval_error_count": retrieval_error_count,
    }


def _rag_service_smoke(*, cases, service: FullCorpusRagService) -> dict[str, Any]:
    supported_case = next((case for case in cases if not case.expected_refusal), None)
    if supported_case is None:
        raise FullCorpusIndexError("At least one supported query is required for RAG service smoke")
    supported = service.answer(question=supported_case.question, top_k=min(supported_case.top_k, 20))
    unsupported_case = next((case for case in cases if case.expected_refusal), None)
    if unsupported_case is None:
        raise FullCorpusIndexError("At least one unsupported query is required for no-source smoke")
    no_source = service.answer(question=unsupported_case.question, top_k=min(unsupported_case.top_k, 20))
    return {"supported": supported, "no_source": no_source}


def _resolve_index_paths(path: Path) -> tuple[Path, Path]:
    if (path / "manifest.json").is_file():
        return path, path.parent
    if (path / "index" / "manifest.json").is_file():
        return path / "index", path
    raise FullCorpusIndexError(f"Full-corpus index manifest not found under: {path}")


def _valid_source(source: dict[str, Any]) -> bool:
    required = ("article_id", "title", "url", "section", "chunk_id", "score")
    return all(source.get(field) is not None for field in required) and isinstance(source.get("score"), float)


def _valid_rag_source(source: dict[str, Any]) -> bool:
    return (
        bool(source.get("article_id"))
        and bool(source.get("article_title"))
        and bool(source.get("article_url"))
        and bool(source.get("section_title"))
        and isinstance(source.get("chunk_index"), int)
    )


def _passes(metrics: dict[str, Any], rag_service_smoke: dict[str, Any]) -> bool:
    supported_source = rag_service_smoke["supported"].get("sources", [])
    no_source = rag_service_smoke["no_source"]
    return (
        metrics["indexed_article_coverage_rate"] == 1.0
        and metrics["supported_query_source_rate"] == 1.0
        and metrics["service_supported_query_source_rate"] == 1.0
        and metrics["expected_article_hit_at_k"] >= 0.7
        and metrics["source_schema_valid_rate"] == 1.0
        and metrics["source_title_present_rate"] == 1.0
        and metrics["source_url_present_rate"] == 1.0
        and metrics["source_section_present_rate"] == 1.0
        and metrics["service_source_schema_valid_rate"] == 1.0
        and metrics["no_source_refusal_rate"] == 1.0
        and metrics["unsupported_answer_fabrication_count"] == 0
        and metrics["duplicate_source_count"] == 0
        and metrics["retrieval_error_count"] == 0
        and bool(supported_source)
        and rag_service_smoke["supported"].get("answer") != NO_SOURCE_ANSWER
        and all(_valid_rag_source(source) for source in supported_source)
        and no_source == {"answer": NO_SOURCE_ANSWER, "sources": []}
    )


def _rate(values) -> float:
    items = list(values)
    return sum(1 for value in items if value) / len(items) if items else 1.0


def _latency_summary(latencies_ms: list[float]) -> dict[str, float | int]:
    ordered = sorted(latencies_ms)
    if not ordered:
        return {
            "query_count": 0,
            "query_latency_min_ms": 0.0,
            "query_latency_mean_ms": 0.0,
            "query_latency_median_ms": 0.0,
            "query_latency_p95_ms": 0.0,
            "query_latency_max_ms": 0.0,
        }
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "query_count": len(ordered),
        "query_latency_min_ms": ordered[0],
        "query_latency_mean_ms": float(mean(ordered)),
        "query_latency_median_ms": float(median(ordered)),
        "query_latency_p95_ms": ordered[p95_index],
        "query_latency_max_ms": ordered[-1],
    }


def _write_json_atomic(path: Path, data: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
