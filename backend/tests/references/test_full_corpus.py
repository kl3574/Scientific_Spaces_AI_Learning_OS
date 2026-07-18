from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles
from app.references.full_corpus import (
    ControlledInterruption,
    FullCorpusReferenceConfig,
    FullCorpusReferenceError,
    preflight_article_store,
    run_full_corpus_reference_build,
)


def test_exact_preflight_streams_and_validates_identity(tmp_path: Path) -> None:
    config = _config(tmp_path, count=6)

    result = preflight_article_store(config)

    assert result.article_count == 6
    assert result.unique_id_count == 6
    assert result.unique_url_count == 6
    assert result.duplicate_id_count == 0
    assert result.duplicate_url_count == 0
    assert result.identity_stable is True


@pytest.mark.parametrize("field", ["count", "sha", "fingerprint"])
def test_preflight_rejects_wrong_approved_identity(tmp_path: Path, field: str) -> None:
    config = _config(tmp_path, count=4)
    values = dict(config.__dict__)
    if field == "count":
        values["expected_article_count"] = 5
    elif field == "sha":
        values["expected_article_store_sha256"] = "0" * 64
    else:
        values["expected_corpus_fingerprint"] = "0" * 64

    with pytest.raises(FullCorpusReferenceError):
        preflight_article_store(FullCorpusReferenceConfig(**values))


def test_preflight_rejects_symlink_source_and_output(tmp_path: Path) -> None:
    config = _config(tmp_path, count=3)
    linked_store = config.article_store.with_name("linked.json")
    linked_store.symlink_to(config.article_store.name)
    source_values = dict(config.__dict__)
    source_values["article_store"] = linked_store
    with pytest.raises(FullCorpusReferenceError, match="nonsymlink"):
        preflight_article_store(FullCorpusReferenceConfig(**source_values))

    unsafe_output = tmp_path / ".local_data" / "linked-output"
    actual_output = tmp_path / ".local_data" / "actual-output"
    actual_output.mkdir(parents=True)
    unsafe_output.symlink_to(actual_output, target_is_directory=True)
    output_values = dict(config.__dict__)
    output_values["output_dir"] = unsafe_output
    with pytest.raises(FullCorpusReferenceError, match="symlink"):
        run_full_corpus_reference_build(FullCorpusReferenceConfig(**output_values))


def test_controlled_interruption_resume_no_op_and_clean_determinism(tmp_path: Path) -> None:
    interrupted = _config(
        tmp_path,
        count=12,
        checkpoint_every=2,
        rebuild=True,
        simulate_interruption_after=5,
    )
    source_before = _sha256(interrupted.article_store)

    with pytest.raises(ControlledInterruption) as captured:
        run_full_corpus_reference_build(interrupted)

    assert captured.value.evidence["exit_code"] == 75
    assert captured.value.evidence["processed_article_count"] == 5
    assert captured.value.evidence["checkpoint_valid"] is True
    assert captured.value.evidence["current_store_unchanged"] is True
    assert not (interrupted.output_dir / "current").exists()
    checkpoint_path = interrupted.output_dir / "checkpoints" / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["next_position"] == 5
    assert checkpoint["completed_article_ids"] == sorted(checkpoint["completed_article_ids"])
    assert "content" not in checkpoint

    resumed = _copy_config(
        interrupted,
        rebuild=False,
        resume=True,
        simulate_interruption_after=None,
    )
    result = run_full_corpus_reference_build(resumed)

    assert result.status == "CONDITIONAL"
    assert result.action == "resume"
    assert result.processed_article_count == 12
    assert result.input_accounting_rate == 1.0
    assert result.classification_reconciliation_rate == 1.0
    assert result.silent_drop_count == 0
    assert result.provenance_complete_rate == 1.0
    assert result.deterministic_id_rate == 1.0
    assert result.duplicate_group_consistency_rate == 1.0
    assert result.external_network_request_count == 0
    assert result.unexpected_network_attempt_count == 0
    assert result.source_mutation_count == 0
    assert result.review_case_count >= 5
    assert result.resource_budgets_passed is True
    assert _sha256(interrupted.article_store) == source_before

    no_op = run_full_corpus_reference_build(
        _copy_config(resumed, resume=False)
    )
    assert no_op.action == "no_op"
    assert no_op.store_no_op is True
    assert no_op.content_file_hashes == result.content_file_hashes
    assert no_op.manifest_content_fingerprint == result.manifest_content_fingerprint

    deterministic_dir = (
        tmp_path / ".local_data" / "scientific_spaces" / "references" / "determinism"
    )
    clean = run_full_corpus_reference_build(
        _copy_config(
            resumed,
            output_dir=deterministic_dir,
            resume=False,
            rebuild=True,
        )
    )
    assert clean.content_file_hashes == result.content_file_hashes
    assert clean.manifest_content_fingerprint == result.manifest_content_fingerprint
    assert clean.build_fingerprint == result.build_fingerprint


def test_resume_rejects_corrupt_payload_and_checkpoint_identity(tmp_path: Path) -> None:
    interrupted = _config(
        tmp_path,
        count=7,
        checkpoint_every=2,
        rebuild=True,
        simulate_interruption_after=3,
    )
    with pytest.raises(ControlledInterruption):
        run_full_corpus_reference_build(interrupted)

    checkpoint_path = interrupted.output_dir / "checkpoints" / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    first_id = checkpoint["completed_article_ids"][0]
    extraction_path = (
        interrupted.output_dir
        / "checkpoints"
        / "extractions"
        / f"{hashlib.sha256(first_id.encode('utf-8')).hexdigest()}.json"
    )
    extraction_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(FullCorpusReferenceError, match="checksum"):
        run_full_corpus_reference_build(
            _copy_config(
                interrupted,
                rebuild=False,
                resume=True,
                simulate_interruption_after=None,
            )
        )

    clean = _config(
        tmp_path / "identity",
        count=7,
        checkpoint_every=2,
        rebuild=True,
        simulate_interruption_after=3,
    )
    with pytest.raises(ControlledInterruption):
        run_full_corpus_reference_build(clean)
    identity_checkpoint = clean.output_dir / "checkpoints" / "checkpoint.json"
    payload = json.loads(identity_checkpoint.read_text(encoding="utf-8"))
    payload["corpus_fingerprint"] = "0" * 64
    identity_checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FullCorpusReferenceError, match="identity mismatch"):
        run_full_corpus_reference_build(
            _copy_config(
                clean,
                rebuild=False,
                resume=True,
                simulate_interruption_after=None,
            )
        )


def test_full_build_covers_fake_and_unavailable_matching_without_writes(tmp_path: Path) -> None:
    result = run_full_corpus_reference_build(_config(tmp_path, count=10, rebuild=True))

    assert result.fake_matching["automatic_write_count"] == 0
    assert result.fake_matching["private_library_read_count"] == 0
    assert result.fake_matching["false_exact_match_count"] == 0
    assert result.fake_matching["title_only_exact_match_count"] == 0
    assert result.fake_matching["ambiguous_auto_confirmation_count"] == 0
    assert result.fake_matching["decision_counts"]["exact"] >= 1
    assert result.fake_matching["decision_counts"]["probable"] >= 1
    assert result.fake_matching["decision_counts"]["ambiguous"] >= 1
    assert result.unavailable_matching["decision_counts"] == {"unmatched": result.record_count}


def test_resource_budget_overrun_blocks_result(tmp_path: Path) -> None:
    config = _config(tmp_path, count=5, rebuild=True)
    result = run_full_corpus_reference_build(_copy_config(config, max_store_bytes=1))

    assert result.status == "BLOCKED"
    assert result.resource_budgets_passed is False


def _config(
    tmp_path: Path,
    *,
    count: int,
    checkpoint_every: int = 3,
    rebuild: bool = False,
    resume: bool = False,
    simulate_interruption_after: int | None = None,
) -> FullCorpusReferenceConfig:
    article_store = (
        tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "article_store" / "articles.json"
    )
    _write_articles(article_store, count=count)
    sha256 = _sha256(article_store)
    fingerprint = compute_corpus_fingerprint(load_full_corpus_articles(article_store))
    output_dir = tmp_path / ".local_data" / "scientific_spaces" / "references" / "full-corpus"
    return FullCorpusReferenceConfig(
        article_store=article_store,
        output_dir=output_dir,
        expected_article_count=count,
        expected_article_store_sha256=sha256,
        expected_corpus_fingerprint=fingerprint,
        checkpoint_every=checkpoint_every,
        rebuild=rebuild,
        resume=resume,
        simulate_interruption_after=simulate_interruption_after,
        no_network=True,
        minimum_review_cases=5,
        min_available_disk_bytes=0,
        code_commit="0" * 40,
    )


def _copy_config(config: FullCorpusReferenceConfig, **updates: object) -> FullCorpusReferenceConfig:
    values = dict(config.__dict__)
    values.update(updates)
    return FullCorpusReferenceConfig(**values)


def _write_articles(path: Path, *, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(count):
        records.append(
            {
                "id": f"article-{index:04d}",
                "title": f"Fixture Article {index}",
                "url": f"https://spaces.ac.cn/archives/{5000 + index}",
                "content": (
                    f"# Fixture Article {index}\n\n"
                    f"DOI:10.1000/full-corpus-{index}.\n\n"
                    f"See [external](https://example.org/papers/{index}) and "
                    f"[internal](/archives/{4000 + index}).\n\n"
                    "## References\n"
                    f"[{index + 1}] Example Author, Deterministic Work {index}, 2020.\n"
                ),
                "metadata": {
                    "date": "2020-01-01",
                    "category": "fixture",
                    "references": [],
                    "images": [],
                },
            }
        )
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
