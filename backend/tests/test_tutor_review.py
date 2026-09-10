"""Tamper tests for static review preparation; no review decision is manufactured."""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from app.evaluation.tutor_review import (
    ARTICLE_VERSION,
    CANDIDATE_VERSION,
    DEFAULT_CANDIDATE_DIR,
    FILE_VERSIONS,
    MANIFEST_VERSION,
    ORIGINAL_ARTICLES,
    canonical_bytes,
    confirmation_binding_status,
    validate_review_candidate,
)


def independent_canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rebind(candidate):
    """Build a test manifest independently from the documented normalization rule."""
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = {}
    entries = {}
    for name, version in FILE_VERSIONS.items():
        raw = (candidate / name).read_bytes()
        normalized = raw if name.endswith(".md") else independent_canonical(json.loads(raw))
        hashes[name] = hashlib.sha256(normalized).hexdigest()
        entries[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "canonical_sha256": hashes[name], "version": version}
    manifest["files"] = entries
    manifest["candidate_digest"] = hashlib.sha256(independent_canonical({
        "candidate_version": CANDIDATE_VERSION, "content_sha256": hashes,
    })).hexdigest()
    write_json(manifest_path, manifest)
    return manifest["candidate_digest"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Static review validation must not access the network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    shutil.copyfile(ORIGINAL_ARTICLES, root / "articles.json")
    article = json.loads(ORIGINAL_ARTICLES.read_text(encoding="utf-8"))[0]
    quote = "For a=2, b=1 and y=7, x=3."
    start = article["content"].index(quote)
    evidence = {
        "article_id": article["id"], "source_id": article["id"] + ":0", "article_version": ARTICLE_VERSION,
        "start": start, "end": start + len(quote), "quote": quote,
    }
    write_json(root / "cases.json", {
        "schema_version": FILE_VERSIONS["cases.json"], "candidate_version": CANDIDATE_VERSION,
        "cases": [{
            "case_id": "static-check-arithmetic", "candidate_version": CANDIDATE_VERSION,
            "legacy_case_ids": ["arithmetic-supported"], "question": "已知 a=2、b=1、y=7，求 x。",
            "mode": "qa", "target_claim": "x=3", "allowed_evidence": [evidence],
            "original_expectation": {"claim": "x=3"}, "finding": "CORRECT",
            "proposed_relation": "SUPPORTED", "answer_behavior": "ANSWER", "adjudication": [],
            "assumptions": ["a=2"], "derivation": ["x=(7-1)/2=3"], "reference_answer": "x=3",
            "must_include": ["x=3"], "must_not_claim": ["x=99"], "equivalent_answers": ["x=6/2"],
            "human_decision": {"decision": None, "comment": None},
            "allowed_inference_rule_ids": ["real-arithmetic"],
            "supporting_locators": [{**evidence, "locator_id": "static-check-arithmetic:example"}],
        }],
        "legacy_contract_inventory": [{"case_id": "legacy-mode-contract", "status": "NOT_APPLICABLE"}],
    })
    write_json(root / "rubric.json", {
        "schema_version": FILE_VERSIONS["rubric.json"], "candidate_version": CANDIDATE_VERSION,
        "article_version": ARTICLE_VERSION,
        "relation_definitions": {"SUPPORTED": "蕴含主张", "CONTRADICTED": "蕴含否定", "INSUFFICIENT": "无法决定"},
        "behavior_definitions": {"ANSWER": "回答", "CORRECT_PREMISE": "纠正前提", "CONDITIONAL_ANSWER": "条件回答", "ABSTAIN": "不作决定"},
        "inference_rules": [{"id": "real-arithmetic", "text": "实数的四则运算"}],
        "criteria": [{"id": "evidence-support", "text": "检查证据是否推出主张"}],
        "human_review_requirement": "模型复核不能代替真人决定。",
    })
    (root / "review_package.md").write_text("# 合成审核包\n\n审核决定：\n\n意见：\n", encoding="utf-8")
    write_json(root / "manifest.json", {
        "schema_version": MANIFEST_VERSION, "candidate_version": CANDIDATE_VERSION,
        "status": "PREPARED_PENDING_HUMAN_REVIEW", "files": {}, "candidate_digest": "",
        "human_review": {"status": "PENDING", "reviewer": None, "approved_at": None},
        "model_review": {"status": "COMPLETED", "blind": False, "kind": "model_review", "independent_reviewer": "synthetic-model-reviewer"},
        "data_role": "development/regression", "unseen_holdout": False,
    })
    rebind(root)
    return root


def edit_json(candidate, filename, mutation, *, refresh=True):
    path = candidate / filename
    document = json.loads(path.read_text(encoding="utf-8"))
    mutation(document)
    write_json(path, document)
    if refresh and filename != "manifest.json":
        rebind(candidate)


def test_canonicalization_is_explicit_and_rejects_nonfinite_numbers():
    assert canonical_bytes({"z": 1, "a": "中文"}) == '{"a":"中文","z":1}'.encode("utf-8")
    with pytest.raises(ValueError):
        canonical_bytes({"value": float("nan")})


def test_prepared_fixture_is_valid_but_never_human_approved(candidate):
    before = {file.name: file.read_bytes() for file in candidate.iterdir()}
    result = validate_review_candidate(candidate)
    assert result["valid"] is True, result["errors"]
    assert result["status"] == "PREPARED_PENDING_HUMAN_REVIEW"
    assert result["human_review"] == {"status": "PENDING", "reviewer": None, "approved_at": None}
    assert (result["article_count"], result["case_count"]) == (2, 1)
    assert before == {file.name: file.read_bytes() for file in candidate.iterdir()}


def test_current_review_candidate_is_statically_valid():
    result = validate_review_candidate(DEFAULT_CANDIDATE_DIR)
    assert result["valid"] is True, result["errors"]
    assert result["article_count"] == 2
    assert result["case_count"] == 12


@pytest.mark.parametrize("filename", ("cases.json", "rubric.json", "review_package.md"))
def test_changed_content_invalidates_hashes_and_old_confirmation(candidate, filename):
    old_digest = validate_review_candidate(candidate)["candidate_digest"]
    old_confirmation = {"candidate_digest": old_digest, "reviewer": "a name is not authentication"}
    if filename.endswith(".json"):
        field = "reference_answer" if filename == "cases.json" else "human_review_requirement"
        def change(document):
            target = document["cases"][0] if filename == "cases.json" else document
            target[field] += " 新的待核对内容。"
        edit_json(candidate, filename, change, refresh=False)
    else:
        with (candidate / filename).open("a", encoding="utf-8") as stream:
            stream.write("\n新的审核说明。\n")
    result = validate_review_candidate(candidate)
    assert result["valid"] is False
    assert f"{filename}:canonical_hash_mismatch" in result["errors"]
    assert "manifest:candidate_digest_mismatch" in result["errors"]
    assert confirmation_binding_status(old_confirmation, result["candidate_digest"]) == "STALE"
    rebind(candidate)
    renewed = validate_review_candidate(candidate)
    assert renewed["valid"] is True
    assert renewed["human_review"]["status"] == "PENDING"
    assert confirmation_binding_status(old_confirmation, renewed["candidate_digest"]) == "STALE"


def test_byte_hash_detects_format_changes_even_when_canonical_content_is_equal(candidate):
    path = candidate / "cases.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    errors = validate_review_candidate(candidate)["errors"]
    assert "cases.json:byte_hash_mismatch" in errors
    assert "cases.json:canonical_hash_mismatch" not in errors


def test_original_articles_cannot_be_replaced_even_with_recomputed_manifest(candidate):
    edit_json(candidate, "articles.json", lambda data: data[0].update(content=data[0]["content"] + " changed"))
    errors = validate_review_candidate(candidate)["errors"]
    assert "articles:not_exact_original_bytes" in errors
    assert "manifest:candidate_digest_mismatch" not in errors


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("article_id", "unknown", "evidence:article_id_invalid"),
        ("source_id", "synthetic-affine-validation:0", "evidence:source_id_invalid"),
        ("article_version", "older/v0", "evidence:article_version_invalid"),
        ("url", "file:///synthetic-private", "evidence:url_invalid"),
        ("start", -1, "evidence:span_invalid"),
        ("start", True, "evidence:span_invalid"),
        ("end", 99_999, "evidence:span_invalid"),
        ("quote", "x=99", "evidence:quote_mismatch"),
    ],
)
def test_invalid_citations_fail_despite_recomputed_hashes(candidate, field, value, error):
    edit_json(candidate, "cases.json", lambda data: data["cases"][0]["allowed_evidence"][0].update({field: value}))
    assert error in validate_review_candidate(candidate)["errors"]


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda data: data["cases"].append(data["cases"][0]), "case:duplicate_id"),
        (lambda data: data["cases"][0].pop("target_claim"), "case:fields_missing"),
        (lambda data: data["cases"][0].update(finding="PASS"), "case:finding_invalid"),
        (lambda data: data["cases"][0].update(proposed_relation="NOT_MENTIONED"), "case:relation_invalid"),
        (lambda data: data["cases"][0].update(answer_behavior="APPROVE"), "case:behavior_invalid"),
        (lambda data: data["cases"][0].update(candidate_version="old/v0"), "case:candidate_version_invalid"),
        (lambda data: data["cases"][0].update(allowed_inference_rule_ids=["unknown-rule"]), "case:inference_rule_reference_invalid"),
        (lambda data: data["cases"][0].update(human_decision={"decision": "同意", "comment": "模型判断"}), "case:human_decision_must_be_blank"),
        (lambda data: data["legacy_contract_inventory"].append(data["legacy_contract_inventory"][0]), "inventory:duplicate_case_id"),
    ],
    ids=("duplicate", "missing", "finding", "relation", "behavior", "version", "inference-rule", "fake-human", "legacy-duplicate"),
)
def test_case_integrity_and_enums_fail_closed(candidate, mutation, error):
    edit_json(candidate, "cases.json", mutation)
    assert error in validate_review_candidate(candidate)["errors"]


@pytest.mark.parametrize("human", (
    {"status": "APPROVED", "reviewer": None, "approved_at": None},
    {"status": "PENDING", "reviewer": "model-agent", "approved_at": None},
    {"status": "PENDING", "reviewer": None, "approved_at": "2026-01-01"},
))
def test_purported_human_approval_is_rejected(candidate, human):
    edit_json(candidate, "manifest.json", lambda data: data.update(human_review=human))
    result = validate_review_candidate(candidate)
    assert result["valid"] is False
    assert "manifest:human_review_must_be_unsigned_pending" in result["errors"]
    assert result["human_review"]["status"] == "PENDING"


def test_confirmation_helper_only_reports_content_binding(candidate):
    digest = validate_review_candidate(candidate)["candidate_digest"]
    assert confirmation_binding_status(None, digest) == "MISSING"
    assert confirmation_binding_status({"candidate_digest": "0" * 64}, digest) == "STALE"
    assert confirmation_binding_status({"candidate_digest": digest, "status": "APPROVED", "reviewer": "model"}, digest) == "UNVERIFIED"
    assert confirmation_binding_status("human-approved", digest) == "STALE"


@pytest.mark.parametrize("filename", ("articles.json", "cases.json", "manifest.json", "review_package.md"))
def test_symlink_files_are_rejected(candidate, tmp_path, filename):
    original = candidate / filename
    target = tmp_path / "outside"
    original.rename(target)
    original.symlink_to(target)
    assert validate_review_candidate(candidate)["valid"] is False


def test_directory_symlink_traversal_and_manifest_file_injection_are_rejected(candidate, tmp_path):
    linked = tmp_path / "linked"
    linked.symlink_to(candidate, target_is_directory=True)
    assert validate_review_candidate(linked)["errors"] == ["candidate_directory_invalid"]
    assert validate_review_candidate(candidate / ".." / "candidate")["errors"] == ["candidate_directory_invalid"]
    edit_json(candidate, "manifest.json", lambda data: data["files"].update({"../outside.json": {}}))
    assert "manifest:file_names_invalid" in validate_review_candidate(candidate)["errors"]


def test_nonregular_candidate_file_is_rejected_without_opening_a_pipe(candidate):
    path = candidate / "review_package.md"
    path.unlink()
    os.mkfifo(path)
    assert validate_review_candidate(candidate)["valid"] is False


@pytest.mark.parametrize("raw", ('{"cases":[],"cases":[]}', '{"value":NaN}'))
def test_ambiguous_or_nonfinite_json_is_rejected(candidate, raw):
    (candidate / "cases.json").write_text(raw, encoding="utf-8")
    assert "cases.json:unreadable_or_invalid_json" in validate_review_candidate(candidate)["errors"]


def test_cli_is_read_only_and_omits_paths_and_candidate_prose(candidate):
    edit_json(candidate, "cases.json", lambda data: data["cases"][0].update(question="SYNTHETIC_PRIVATE_PROMPT_SENTINEL"))
    before = {path.name: path.read_bytes() for path in candidate.iterdir()}
    script = Path(__file__).resolve().parents[2] / "scripts/eval/validate_tutor_review.py"
    result = subprocess.run([sys.executable, str(script), "--candidate-dir", str(candidate)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["valid"] is True
    assert result.stderr == ""
    assert str(candidate) not in result.stdout
    assert "SYNTHETIC_PRIVATE_PROMPT_SENTINEL" not in result.stdout
    assert before == {path.name: path.read_bytes() for path in candidate.iterdir()}
    failed = subprocess.run([sys.executable, str(script), "--candidate-dir", str(candidate / "missing")], capture_output=True, text=True)
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["valid"] is False
    assert str(candidate) not in failed.stdout + failed.stderr
