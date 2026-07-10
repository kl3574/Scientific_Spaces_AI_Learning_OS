from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

from app.evaluation.full_corpus import (
    FullCorpusEvaluationRunner,
    FullCorpusRetrievalCase,
    default_full_corpus_cases,
)
from app.rag.full_corpus import FullCorpusRagService, build_full_corpus_index
from app.rag.service import NO_SOURCE_ANSWER


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_store(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "id": "attention-1",
                    "title": "Attention",
                    "url": "https://spaces.ac.cn/archives/1",
                    "content": "# Attention\n\nquery key value transformer attention",
                    "metadata": {"date": "2018-01-01", "category": "NLP", "references": [], "images": []},
                },
                {
                    "id": "matrix-2",
                    "title": "Matrix",
                    "url": "https://spaces.ac.cn/archives/2",
                    "content": "# Matrix\n\nSVD singular value matrix decomposition",
                    "metadata": {"date": "2012-01-01", "category": "math", "references": [], "images": []},
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _cases() -> list[FullCorpusRetrievalCase]:
    return [
        FullCorpusRetrievalCase(
            case_id="attention",
            category="attention_transformer",
            question="attention query key transformer",
            expected_article_ids=("attention-1",),
            top_k=2,
        ),
        FullCorpusRetrievalCase(
            case_id="matrix",
            category="matrix_analysis",
            question="SVD singular value matrix",
            expected_article_ids=("matrix-2",),
            top_k=2,
        ),
        FullCorpusRetrievalCase(
            case_id="unsupported",
            category="unsupported",
            question="zxqv_unsupported_7f3c9a",
            expected_refusal=True,
            top_k=2,
        ),
    ]


def test_full_corpus_evaluation_uses_local_index_and_preserves_contracts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store)
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def reject_network(*_args, **_kwargs):
        raise AssertionError("full-corpus evaluation must not access the network")

    monkeypatch.setattr(urllib.request, "urlopen", reject_network)
    service_questions: list[str] = []
    original_answer = FullCorpusRagService.answer

    def record_service_answer(self, *, question: str, top_k: int = 5):
        service_questions.append(question)
        return original_answer(self, question=question, top_k=top_k)

    monkeypatch.setattr(FullCorpusRagService, "answer", record_service_answer)

    result = FullCorpusEvaluationRunner(
        article_store_path=store,
        index_dir=output,
        cases=_cases(),
    ).run()

    metrics = result["metrics"]
    assert result["status"] == "PASS"
    assert {case.question for case in _cases()} <= set(service_questions)
    assert metrics["indexed_article_coverage_rate"] == 1.0
    assert metrics["retrieval_query_count"] == 3
    assert metrics["supported_query_source_rate"] == 1.0
    assert metrics["expected_article_hit_at_k"] == 1.0
    assert metrics["source_schema_valid_rate"] == 1.0
    assert metrics["source_title_present_rate"] == 1.0
    assert metrics["source_url_present_rate"] == 1.0
    assert metrics["source_section_present_rate"] == 1.0
    assert metrics["no_source_refusal_rate"] == 1.0
    assert metrics["unsupported_answer_fabrication_count"] == 0
    assert metrics["duplicate_source_count"] == 0
    assert metrics["retrieval_error_count"] == 0
    assert result["cases"][0]["sources"][0].keys() >= {
        "article_id",
        "title",
        "url",
        "section",
        "chunk_id",
        "score",
    }
    assert result["rag_service_smoke"]["supported"]["sources"]
    assert result["rag_service_smoke"]["supported"]["sources"][0].keys() >= {
        "article_id",
        "article_title",
        "article_url",
        "section_title",
        "chunk_index",
    }
    assert result["rag_service_smoke"]["no_source"] == {
        "answer": NO_SOURCE_ANSWER,
        "sources": [],
    }
    assert (output / "reports" / "retrieval_smoke.json").is_file()
    assert (output / "reports" / "benchmark.json").is_file()


def test_full_corpus_rag_service_applies_no_source_gate_to_loaded_index(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store)
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    service = FullCorpusRagService.load(
        article_store_path=store,
        index_dir=output,
    )

    supported = service.answer(question="attention query key", top_k=2)
    unsupported = service.answer(question="zxqv_unsupported_7f3c9a", top_k=2)

    assert supported["sources"]
    assert unsupported == {"answer": NO_SOURCE_ANSWER, "sources": []}


def test_full_corpus_eval_blocks_rag_service_source_schema_regression(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store)
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    original_answer = FullCorpusRagService.answer

    def remove_source_url(self, *, question: str, top_k: int = 5):
        payload = original_answer(self, question=question, top_k=top_k)
        if payload["sources"]:
            payload = {**payload, "sources": [dict(source) for source in payload["sources"]]}
            payload["sources"][0].pop("article_url", None)
        return payload

    monkeypatch.setattr(FullCorpusRagService, "answer", remove_source_url)

    result = FullCorpusEvaluationRunner(
        article_store_path=store,
        index_dir=output,
        cases=_cases(),
    ).run()

    assert result["status"] == "BLOCKED"
    assert result["metrics"]["service_source_schema_valid_rate"] < 1.0


def test_default_full_corpus_cases_cover_required_categories() -> None:
    cases = default_full_corpus_cases()

    assert len(cases) == 12
    assert {case.category for case in cases} == {
        "attention_transformer",
        "probability_statistics",
        "optimizer",
        "diffusion_model",
        "matrix_analysis",
        "variational_differential_equation",
        "early_mathematics",
        "astronomy_physics",
        "nlp_bert",
        "gan_vae",
        "website_tools",
        "unsupported",
    }
    assert sum(case.expected_refusal for case in cases) == 1


def test_full_corpus_eval_cli_is_explicit_and_does_not_require_api_key(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    cases_file = tmp_path / "cases.json"
    _write_store(store)
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    cases_file.write_text(
        json.dumps([case.to_dict() for case in _cases()], ensure_ascii=False),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/eval/run_full_corpus_rag_eval.py",
            "--article-store",
            str(store),
            "--index-dir",
            str(output),
            "--expected-article-count",
            "2",
            "--cases-file",
            str(cases_file),
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "PASS"
    assert payload["metrics"]["retrieval_query_count"] == 3
