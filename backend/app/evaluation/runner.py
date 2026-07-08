from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.evaluation.metrics import MetricInputs, calculate_suite_metrics, result_case_metrics
from app.evaluation.models import EvalCase, EvalDataset, EvalResult, EvalSuiteResult
from app.graph.service import GraphService
from app.rag.service import NO_SOURCE_ANSWER, RagService
from app.tutor.models import TutorRequest
from app.tutor.service import TutorService


DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "evaluation"


def load_eval_dataset(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> EvalDataset:
    root = Path(fixture_dir)
    articles = json.loads((root / "articles.json").read_text(encoding="utf-8"))
    cases = [EvalCase.from_dict(item) for item in json.loads((root / "expected_cases.json").read_text(encoding="utf-8"))]
    zotero_links = _read_optional_json(root / "zotero_links.json", default={})
    graph_expected = _read_optional_json(root / "graph_expected.json", default={})
    return EvalDataset(articles=articles, cases=cases, zotero_links=zotero_links, graph_expected=graph_expected)


class EvaluationRunner:
    def __init__(self, fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> None:
        self.fixture_dir = Path(fixture_dir)
        self.dataset = load_eval_dataset(self.fixture_dir)
        self.valid_article_ids = {str(article["id"]) for article in self.dataset.articles}

    def run(self) -> EvalSuiteResult:
        results = [self.run_case(case.case_id) for case in self.dataset.cases]
        metrics = calculate_suite_metrics(
            MetricInputs(cases=self.dataset.cases, results=results, valid_article_ids=self.valid_article_ids)
        )
        passed = (
            metrics.citation_required_pass_rate == 1.0
            and metrics.no_source_refusal_rate == 1.0
            and metrics.source_schema_valid_rate == 1.0
            and metrics.no_fake_source_rate == 1.0
            and metrics.quiz_question_sources_rate == 1.0
            and metrics.research_local_only_rate == 1.0
            and metrics.no_source_answer_fabrication_count == 0
            and metrics.answer_without_sources_count == 0
            and metrics.quiz_without_sources_count == 0
        )
        return EvalSuiteResult(results=results, metrics=metrics, passed=passed)

    def run_case(self, case_id: str) -> EvalResult:
        case = self._case_by_id(case_id)
        with tempfile.TemporaryDirectory(prefix="scientific-spaces-eval-") as runtime_dir:
            runtime_root = Path(runtime_dir)
            article_file = runtime_root / "articles.json"
            zotero_file = runtime_root / "zotero_links.json"
            graph_file = runtime_root / "knowledge_graph.json"
            learning_file = runtime_root / "learning.json"
            tutor_file = runtime_root / "tutor_sessions.json"

            articles = [] if case.task_type == "no_source" else self.dataset.articles
            _write_json(article_file, articles)
            _write_json(zotero_file, self.dataset.zotero_links)

            env = {
                "SCIENTIFIC_SPACES_ARTICLES_FILE": str(article_file),
                "SCIENTIFIC_SPACES_ZOTERO_FILE": str(zotero_file),
                "SCIENTIFIC_SPACES_GRAPH_FILE": str(graph_file),
                "SCIENTIFIC_SPACES_LEARNING_FILE": str(learning_file),
                "SCIENTIFIC_SPACES_TUTOR_FILE": str(tutor_file),
                "SCIENTIFIC_SPACES_ZOTERO_PROVIDER": "fake",
                "SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER": "fake",
                "SCIENTIFIC_SPACES_LEARNING_BACKEND": "json",
            }
            with _patched_env(env):
                if case.node_id:
                    GraphService().build_graph()
                result = self._run_case_with_env(case)

        metrics = result_case_metrics(case, result, self.valid_article_ids)
        return EvalResult(
            case_id=result.case_id,
            task_type=result.task_type,
            answer=result.answer,
            sources=result.sources,
            refusal_reason=result.refusal_reason,
            mode=result.mode,
            follow_up_questions=result.follow_up_questions,
            quiz_questions=result.quiz_questions,
            graph_context=result.graph_context,
            zotero_context=result.zotero_context,
            metrics=metrics,
        )

    def _run_case_with_env(self, case: EvalCase) -> EvalResult:
        if case.task_type in {"rag_query", "no_source"}:
            return self._run_rag_case(case)
        if case.task_type == "tutor_quiz":
            return self._run_quiz_case(case)
        if case.task_type.startswith("tutor_"):
            return self._run_tutor_answer_case(case)
        raise ValueError(f"Unsupported evaluation task type: {case.task_type}")

    def _run_rag_case(self, case: EvalCase) -> EvalResult:
        service = RagService()
        service.build_index()
        payload = service.answer(question=case.question, top_k=max(1, case.top_k))
        return EvalResult(
            case_id=case.case_id,
            task_type=case.task_type,
            answer=str(payload.get("answer") or NO_SOURCE_ANSWER),
            sources=[dict(source) for source in payload.get("sources", [])],
        )

    def _run_tutor_answer_case(self, case: EvalCase) -> EvalResult:
        mode = case.task_type.removeprefix("tutor_")
        service = TutorService()
        response = service.answer(
            TutorRequest(
                question=case.question,
                mode=mode,  # type: ignore[arg-type]
                article_id=case.article_id,
                node_id=case.node_id,
                top_k=max(1, case.top_k),
                include_graph_context=True,
                include_zotero_context=True,
            )
        )
        return EvalResult(
            case_id=case.case_id,
            task_type=case.task_type,
            answer=response.answer,
            sources=[source.to_dict() for source in response.sources],
            refusal_reason=response.refusal_reason,
            mode=response.mode,
            follow_up_questions=response.follow_up_questions,
            graph_context=response.graph_context,
            zotero_context=response.zotero_context,
        )

    def _run_quiz_case(self, case: EvalCase) -> EvalResult:
        service = TutorService()
        questions = service.quiz(article_id=case.article_id, node_id=case.node_id, num_questions=max(1, case.top_k))
        quiz_questions = [question.to_dict() for question in questions]
        sources = [source for question in quiz_questions for source in question.get("sources", [])]
        answer = f"Generated {len(quiz_questions)} grounded quiz question(s)." if quiz_questions else NO_SOURCE_ANSWER
        refusal = None if quiz_questions else "no_sources"
        return EvalResult(
            case_id=case.case_id,
            task_type=case.task_type,
            answer=answer,
            sources=sources,
            refusal_reason=refusal,
            mode="quiz",
            quiz_questions=quiz_questions,
        )

    def _case_by_id(self, case_id: str) -> EvalCase:
        for case in self.dataset.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(f"Evaluation case not found: {case_id}")


def _read_optional_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def _patched_env(values: dict[str, str]) -> Iterator[None]:
    previous: dict[str, str | None] = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
