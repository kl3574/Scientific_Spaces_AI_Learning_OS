"""Read-only validation of one synthetic review candidate, never human approval."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "p3-044-affine-review/v3"
MANIFEST_VERSION = "p3-044-affine-review-manifest/v1"
ARTICLE_VERSION = "p3-044-affine-articles/v1"
FILE_VERSIONS = {
    "articles.json": ARTICLE_VERSION,
    "cases.json": "p3-044-affine-review-cases/v1",
    "rubric.json": "p3-044-affine-review-rubric/v1",
    "review_package.md": "p3-044-affine-review-package/v1",
}
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "tests/fixtures/evaluation/tutor_generation"
DEFAULT_CANDIDATE_DIR = FIXTURE_ROOT / "review_candidate_v3"
ORIGINAL_ARTICLES = FIXTURE_ROOT / "acceptance_articles.json"
ORIGINAL_ARTICLES_SHA256 = "e30232053dd49fd5ef9bdb268dfe8ca863d28d4d0a44a062a57d4dac1de48238"
ARTICLE_IDS = {"synthetic-affine-inverse", "synthetic-affine-validation"}
RELATIONS = {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT"}
BEHAVIORS = {"ANSWER", "CORRECT_PREMISE", "CONDITIONAL_ANSWER", "ABSTAIN"}
FINDINGS = {"CORRECT", "INCORRECT", "AMBIGUOUS", "MISSING_CONDITIONS"}
PENDING = "PREPARED_PENDING_HUMAN_REVIEW"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_MAX_FILE_BYTES = 2_000_000


def canonical_bytes(value: Any) -> bytes:
    """UTF-8 JSON with sorted keys, compact separators, and no NaN/Infinity."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def confirmation_binding_status(record: Any, candidate_digest: str) -> str:
    """Check only content binding; even a matching purported signature is unverified."""
    if record is None:
        return "MISSING"
    if (
        not isinstance(record, dict)
        or not isinstance(candidate_digest, str)
        or _HASH.fullmatch(candidate_digest) is None
        or record.get("candidate_digest") != candidate_digest
    ):
        return "STALE"
    return "UNVERIFIED"


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonfinite JSON number")


def _read_bytes(path: Path) -> bytes:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_FILE_BYTES:
        raise ValueError("file shape or size")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_FILE_BYTES:
            raise ValueError("file shape or size")
        raw = stream.read(_MAX_FILE_BYTES + 1)
    if len(raw) > _MAX_FILE_BYTES:
        raise ValueError("file size")
    return raw


def _read_json(path: Path) -> tuple[bytes, Any]:
    raw = _read_bytes(path)
    parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    canonical_bytes(parsed)
    return raw, parsed


def _safe_directory(value: Path | str) -> Path:
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("path traversal")
    path = path.absolute()
    if any(item.is_symlink() for item in (path, *path.parents)) or not path.is_dir():
        raise ValueError("directory shape")
    return path


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_review_candidate(candidate_dir: Path | str = DEFAULT_CANDIDATE_DIR) -> dict[str, Any]:
    """Validate the frozen originals, citation coordinates, schemas and hash binding.

    Output deliberately excludes candidate prose, prompts and filesystem paths.
    Validity certifies static consistency only, not mathematics or a human decision.
    """
    errors: list[str] = []
    summary = {
        "schema_version": "p3-044-affine-review-validation/v1",
        "valid": False, "status": "INVALID", "candidate_version": CANDIDATE_VERSION,
        "candidate_digest": None, "content_sha256": {}, "article_count": 0, "case_count": 0, "errors": errors,
        "human_review": {"status": "PENDING", "reviewer": None, "approved_at": None},
    }

    def check(condition, code):
        if not condition:
            errors.append(code)
        return bool(condition)

    try:
        root = _safe_directory(candidate_dir)
    except (OSError, ValueError, TypeError):
        errors.append("candidate_directory_invalid")
        return summary
    documents = {}
    raw_files = {}
    for name in ("manifest.json", *FILE_VERSIONS):
        try:
            if name == "review_package.md":
                raw_files[name] = _read_bytes(root / name)
                documents[name] = raw_files[name].decode("utf-8")
                if b"\r" in raw_files[name] or not documents[name].strip():
                    raise ValueError("review package requires nonempty UTF-8 LF text")
            else:
                raw_files[name], documents[name] = _read_json(root / name)
        except (OSError, ValueError, UnicodeError, RecursionError):
            errors.append(f"{name}:unreadable_or_invalid_json")
    if errors:
        return summary

    manifest, articles, cases_document, rubric = (
        documents[name] for name in ("manifest.json", "articles.json", "cases.json", "rubric.json")
    )
    canonical_hashes = {
        name: hashlib.sha256(raw_files[name] if name == "review_package.md" else canonical_bytes(documents[name])).hexdigest()
        for name in FILE_VERSIONS
    }
    summary["content_sha256"] = canonical_hashes
    digest = hashlib.sha256(canonical_bytes({
        "candidate_version": CANDIDATE_VERSION, "content_sha256": canonical_hashes,
    })).hexdigest()
    summary["candidate_digest"] = digest
    if not check(isinstance(manifest, dict), "manifest:object_required"):
        return summary
    check(set(manifest) == {
        "schema_version", "candidate_version", "status", "files", "candidate_digest",
        "human_review", "model_review", "data_role", "unseen_holdout",
    }, "manifest:fields_invalid")
    check(manifest.get("schema_version") == MANIFEST_VERSION, "manifest:schema_version_invalid")
    check(manifest.get("candidate_version") == CANDIDATE_VERSION, "manifest:candidate_version_invalid")
    check(manifest.get("status") == PENDING, "manifest:review_status_must_be_pending")
    check(manifest.get("candidate_digest") == digest, "manifest:candidate_digest_mismatch")
    check(manifest.get("human_review") == {
        "status": "PENDING", "reviewer": None, "approved_at": None,
    }, "manifest:human_review_must_be_unsigned_pending")
    check(manifest.get("data_role") == "development/regression", "manifest:data_role_invalid")
    check(manifest.get("unseen_holdout") is False, "manifest:unseen_holdout_invalid")
    model_review = manifest.get("model_review")
    if check(isinstance(model_review, dict), "manifest:model_review_required"):
        check(set(model_review) == {"status", "blind", "kind", "independent_reviewer"}
              and model_review.get("status") == "COMPLETED"
              and model_review.get("blind") is False
              and model_review.get("kind") == "model_review"
              and _text(model_review.get("independent_reviewer")), "manifest:model_review_invalid")
    entries = manifest.get("files")
    if check(isinstance(entries, dict), "manifest:files_object_required"):
        check(set(entries) == set(FILE_VERSIONS), "manifest:file_names_invalid")
        for name, version in FILE_VERSIONS.items():
            entry = entries.get(name)
            if not check(isinstance(entry, dict), f"{name}:manifest_entry_required"):
                continue
            check(set(entry) == {"sha256", "canonical_sha256", "version"}, f"{name}:manifest_fields_invalid")
            check(entry.get("version") == version, f"{name}:version_invalid")
            check(entry.get("sha256") == hashlib.sha256(raw_files[name]).hexdigest(), f"{name}:byte_hash_mismatch")
            check(entry.get("canonical_sha256") == canonical_hashes[name], f"{name}:canonical_hash_mismatch")

    try:
        original_raw, _ = _read_json(ORIGINAL_ARTICLES)
        check(hashlib.sha256(original_raw).hexdigest() == ORIGINAL_ARTICLES_SHA256,
              "articles:original_baseline_changed")
        check(raw_files["articles.json"] == original_raw, "articles:not_exact_original_bytes")
    except (OSError, ValueError, UnicodeError, RecursionError):
        errors.append("articles:original_baseline_unavailable")
    by_id = {}
    if check(isinstance(articles, list) and len(articles) == 2, "articles:exact_two_required"):
        summary["article_count"] = len(articles)
        for article in articles:
            if not check(isinstance(article, dict), "articles:object_required"):
                continue
            identity = article.get("id")
            if not check(_identifier(identity), "articles:id_invalid"):
                continue
            check(identity not in by_id, "articles:duplicate_id")
            by_id[identity] = article
            check(article.get("url") == f"https://example.test/articles/{identity}", "articles:url_invalid")
            check(_text(article.get("title")) and _text(article.get("content")), "articles:text_required")
        check(set(by_id) == ARTICLE_IDS, "articles:original_ids_mismatch")

    rule_ids = set()
    if check(isinstance(rubric, dict), "rubric:object_required"):
        check(rubric.get("schema_version") == FILE_VERSIONS["rubric.json"], "rubric:schema_version_invalid")
        check(rubric.get("candidate_version") == CANDIDATE_VERSION, "rubric:candidate_version_invalid")
        check(rubric.get("article_version") == ARTICLE_VERSION, "rubric:article_version_invalid")
        for name, expected in (("relation_definitions", RELATIONS), ("behavior_definitions", BEHAVIORS)):
            definitions = rubric.get(name)
            check(isinstance(definitions, dict) and set(definitions) == expected
                  and all(_text(value) for value in definitions.values()), f"rubric:{name}_invalid")
        for name in ("inference_rules", "criteria"):
            rules = rubric.get(name)
            seen = set()
            if check(isinstance(rules, list) and bool(rules), f"rubric:{name}_required"):
                for rule in rules:
                    if not check(isinstance(rule, dict) and _identifier(rule.get("id"))
                                 and _text(rule.get("text")), f"rubric:{name}_entry_invalid"):
                        continue
                    check(rule["id"] not in seen, f"rubric:{name}_duplicate_id")
                    seen.add(rule["id"])
            if name == "inference_rules":
                rule_ids = seen
        check(bool(rubric.get("human_review_requirement")), "rubric:human_review_requirement_missing")

    locator_ids = set()

    def check_locator(locator, prefix, *, identified=False):
        required = {"article_id", "source_id", "article_version", "start", "end", "quote"}
        if identified:
            required.add("locator_id")
        if not check(isinstance(locator, dict) and required <= set(locator), f"{prefix}:fields_missing"):
            return
        if identified:
            identity = locator.get("locator_id")
            if check(_identifier(identity), f"{prefix}:id_invalid"):
                check(identity not in locator_ids, f"{prefix}:duplicate_id")
                locator_ids.add(identity)
        identity = locator.get("article_id")
        if not check(isinstance(identity, str) and identity in by_id, f"{prefix}:article_id_invalid"):
            return
        check(locator.get("article_version") == ARTICLE_VERSION, f"{prefix}:article_version_invalid")
        check(locator.get("source_id") == f"{identity}:0", f"{prefix}:source_id_invalid")
        start, end, quote = (locator.get(key) for key in ("start", "end", "quote"))
        content = by_id[identity].get("content")
        if check(type(start) is int and type(end) is int and isinstance(content, str)
                 and 0 <= start < end <= len(content) and _text(quote), f"{prefix}:span_invalid"):
            check(content[start:end] == quote, f"{prefix}:quote_mismatch")
        if "url" in locator:
            check(locator["url"] == by_id[identity].get("url"), f"{prefix}:url_invalid")

    if not check(isinstance(cases_document, dict), "cases:object_required"):
        return summary
    check(cases_document.get("schema_version") == FILE_VERSIONS["cases.json"], "cases:schema_version_invalid")
    check(cases_document.get("candidate_version") == CANDIDATE_VERSION, "cases:candidate_version_invalid")
    cases = cases_document.get("cases")
    if check(isinstance(cases, list) and bool(cases), "cases:nonempty_list_required"):
        summary["case_count"] = len(cases)
        case_ids = set()
        required = {
            "case_id", "candidate_version", "legacy_case_ids", "question", "mode", "target_claim",
            "allowed_evidence", "original_expectation", "finding", "proposed_relation", "answer_behavior",
            "adjudication", "assumptions", "derivation", "reference_answer", "must_include",
            "must_not_claim", "equivalent_answers", "human_decision",
        }
        for case in cases:
            if not check(isinstance(case, dict) and required <= set(case), "case:fields_missing"):
                continue
            identity = case.get("case_id")
            if check(_identifier(identity), "case:id_invalid"):
                check(identity not in case_ids, "case:duplicate_id")
                case_ids.add(identity)
            check(case.get("candidate_version") == CANDIDATE_VERSION, "case:candidate_version_invalid")
            for field in ("question", "target_claim", "reference_answer"):
                check(_text(case.get(field)), f"case:{field}_required")
            check(case.get("mode") in ("explain", "derive", "qa", "quiz", "research"), "case:mode_invalid")
            check(isinstance(case.get("finding"), str) and case["finding"] in FINDINGS, "case:finding_invalid")
            check(case.get("proposed_relation") is None or case["proposed_relation"] in tuple(RELATIONS), "case:relation_invalid")
            check(case.get("answer_behavior") is None or case["answer_behavior"] in tuple(BEHAVIORS), "case:behavior_invalid")
            check(case.get("human_decision") == {"decision": None, "comment": None}, "case:human_decision_must_be_blank")
            check(isinstance(case.get("original_expectation"), dict), "case:original_expectation_invalid")
            for field in ("legacy_case_ids", "adjudication", "assumptions", "derivation", "must_include",
                          "must_not_claim", "equivalent_answers"):
                check(isinstance(case.get(field), list), f"case:{field}_list_required")
            legacy_ids = case.get("legacy_case_ids")
            if isinstance(legacy_ids, list):
                check(all(_identifier(item) for item in legacy_ids), "case:legacy_id_invalid")
                check(len({str(item) for item in legacy_ids}) == len(legacy_ids), "case:duplicate_legacy_id")
            if case.get("proposed_relation") is None or case.get("answer_behavior") is None:
                check(bool(case.get("adjudication")), "case:unresolved_adjudication_required")
            evidence = case.get("allowed_evidence")
            if check(isinstance(evidence, list) and bool(evidence), "case:evidence_required"):
                evidence_ids = set()
                for locator in evidence:
                    check_locator(locator, "evidence")
                    if isinstance(locator, dict) and isinstance(locator.get("source_id"), str):
                        check(locator["source_id"] not in evidence_ids, "evidence:duplicate_source_id")
                        evidence_ids.add(locator["source_id"])
            if "supporting_locators" in case:
                if check(isinstance(case["supporting_locators"], list), "case:supporting_locators_invalid"):
                    for locator in case["supporting_locators"]:
                        check_locator(locator, "locator", identified=True)
            if "allowed_inference_rule_ids" in case:
                allowed = case["allowed_inference_rule_ids"]
                check(isinstance(allowed, list) and all(isinstance(item, str) and item in rule_ids for item in allowed),
                      "case:inference_rule_reference_invalid")
    inventory = cases_document.get("legacy_contract_inventory")
    if check(isinstance(inventory, list), "cases:legacy_inventory_required"):
        seen = set()
        for item in inventory:
            if not check(isinstance(item, dict) and _identifier(item.get("case_id")), "inventory:case_id_invalid"):
                continue
            check(item["case_id"] not in seen, "inventory:duplicate_case_id")
            seen.add(item["case_id"])
            if "variant" in item:
                variant = item["variant"]
                if not check(isinstance(variant, dict), "inventory:variant_invalid"):
                    continue
                check(variant.get("variant_id") == "legacy-affine-no-formula/v1", "inventory:variant_version_invalid")
                check(variant.get("article_id") == "synthetic-affine-inverse", "inventory:variant_article_invalid")
                content = variant.get("content")
                if check(_text(content), "inventory:variant_content_invalid"):
                    check(variant.get("content_sha256") == hashlib.sha256(content.encode("utf-8")).hexdigest(),
                          "inventory:variant_hash_mismatch")
    summary["errors"] = list(dict.fromkeys(errors))
    summary["valid"] = not errors
    summary["status"] = PENDING if not errors else "INVALID"
    return summary
