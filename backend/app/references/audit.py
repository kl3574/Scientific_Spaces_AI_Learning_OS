from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles
from app.references.store import ReferenceStoreError, audit_reference_store


_FORBIDDEN_TRACKED = re.compile(
    r"(?:^|/)(?:\.env(?:\..*)?|node_modules|\.next|\.local_data)(?:/|$)|"
    r"\.(?:sqlite|sqlite3|db|pdf|zip|tar|gz|trace|prof)$|"
    r"(?:faiss|knowledge_graph\.json|graph\.json|chunks\.jsonl|article_list\.json)$",
    re.IGNORECASE,
)
_SECRET_PATTERNS = (
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_ABSOLUTE_PATH = re.compile(
    r"(?:/home/[A-Za-z0-9._-]+(?:/[^\s\"']*)?|[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+(?:\\\\[^\s\"']*)?)"
)


@dataclass(frozen=True)
class ReferenceStoreAuditResult:
    status: str
    corpus_fingerprint: str
    build_fingerprint: str
    record_count: int
    evidence_count: int
    zotero_candidate_count: int
    network_request_count: int
    article_store_sha256: str
    article_count: int
    manifest_article_count: int
    input_accounting_rate: float
    classification_reconciliation_rate: float
    checkpoint_status: str
    checkpoint_next_position: int | None
    resource_budgets_passed: bool | None
    absolute_path_violation_count: int
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceArtifactAuditResult:
    status: str
    tracked_runtime_private_artifact_count: int
    secret_pattern_count: int
    local_absolute_path_count: int
    baseline_local_absolute_path_count: int
    findings: list[dict[str, str]]
    baseline_findings: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_pilot_store(
    article_store: Path | str,
    reference_store: Path | str,
    *,
    expected_article_count: int | None = None,
) -> ReferenceStoreAuditResult:
    article_path = Path(article_store)
    store_path = Path(reference_store)
    article_sha_before = _file_sha256(article_path)
    articles = load_full_corpus_articles(article_path)
    corpus_fingerprint = compute_corpus_fingerprint(articles)
    issues: list[str] = []
    try:
        manifest = audit_reference_store(store_path, expected_corpus_fingerprint=corpus_fingerprint)
    except ReferenceStoreError as exc:
        raise ReferenceStoreError(f"Pilot Reference Store audit failed: {exc}") from exc
    serialized = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(store_path.rglob("*"))
        if path.is_file() and path.suffix in {".json", ".jsonl"}
    )
    absolute_path_count = _runtime_absolute_path_count(
        serialized,
        roots=(Path.home(), article_path.resolve().parent, store_path.resolve()),
    )
    if absolute_path_count:
        issues.append("Reference Store contains local absolute paths")
    article_count = len(articles)
    manifest_article_count = int(manifest.counts.get("articles", 0))
    processed = int(manifest.counts.get("processed_articles", manifest_article_count))
    terminal_failures = int(manifest.counts.get("explicit_terminal_failures", 0))
    input_count = int(manifest.counts.get("input_articles", manifest_article_count))
    detected = int(manifest.counts.get("detected_candidates", 0))
    classified = int(manifest.counts.get("classified_candidates", detected))
    input_accounting_rate = (processed + terminal_failures) / input_count if input_count else 0.0
    classification_rate = classified / detected if detected else 1.0
    if expected_article_count is not None:
        if article_count != expected_article_count:
            issues.append("Article Store count does not match the expected full-corpus count")
        if manifest_article_count != expected_article_count or input_count != expected_article_count:
            issues.append("Reference Store Article accounting does not match the expected full corpus")
        if input_accounting_rate != 1.0:
            issues.append("Reference Store input accounting does not reconcile")
        if classification_rate != 1.0 or int(manifest.counts.get("silent_drops", 0)) != 0:
            issues.append("Reference Store candidate classification does not reconcile")
        if int(manifest.counts.get("unknown_article_statuses", 0)) != 0:
            issues.append("Reference Store contains unknown Article statuses")
        if int(manifest.counts.get("duplicate_processed_articles", 0)) != 0:
            issues.append("Reference Store contains duplicate processed Articles")
        if float(manifest.counts.get("deterministic_id_rate", 0.0)) != 1.0:
            issues.append("Reference Store deterministic ID rate is incomplete")
        if float(manifest.counts.get("duplicate_group_consistency_rate", 0.0)) != 1.0:
            issues.append("Reference Store duplicate consistency rate is incomplete")
        if int(manifest.counts.get("orphan_evidence_count", -1)) != 0:
            issues.append("Reference Store contains orphan evidence")
        if not isinstance(manifest.counts.get("rule_versions"), dict):
            issues.append("Reference Store rule-version binding is missing")
        if not manifest.counts.get("code_commit") or not manifest.counts.get("implementation_fingerprint"):
            issues.append("Reference Store code identity binding is missing")

    checkpoint_status = "NOT_CHECKED"
    checkpoint_next_position: int | None = None
    resource_budgets_passed: bool | None = None
    if expected_article_count is not None:
        checkpoint_path = store_path.parent / "checkpoints" / "checkpoint.json"
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint_status = str(checkpoint.get("status", "UNKNOWN"))
            checkpoint_next_position = int(checkpoint.get("next_position", -1))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            checkpoint_status = "CORRUPT"
            issues.append("Full-corpus checkpoint is missing or corrupt")
        else:
            if (
                checkpoint_status != "complete"
                or checkpoint_next_position != expected_article_count
                or checkpoint.get("corpus_fingerprint") != corpus_fingerprint
                or checkpoint.get("config_fingerprint") != manifest.configuration_fingerprint
                or checkpoint.get("store_build_fingerprint") != manifest.build_fingerprint
            ):
                issues.append("Full-corpus checkpoint does not match the installed store")
        run_report_path = store_path.parent / "reports" / "last_run.json"
        try:
            run_report = json.loads(run_report_path.read_text(encoding="utf-8"))
            resource_budgets_passed = bool(run_report.get("resource_budgets_passed"))
        except (OSError, json.JSONDecodeError, TypeError):
            issues.append("Full-corpus resource evidence is missing or corrupt")
        else:
            if not resource_budgets_passed or run_report.get("build_fingerprint") != manifest.build_fingerprint:
                issues.append("Full-corpus resource evidence does not match the installed store")
    article_sha_after = _file_sha256(article_path)
    if article_sha_before != article_sha_after:
        issues.append("Article Store changed during the audit")
    return ReferenceStoreAuditResult(
        status="PASS" if not issues else "BLOCKED",
        corpus_fingerprint=corpus_fingerprint,
        build_fingerprint=manifest.build_fingerprint,
        record_count=int(manifest.counts.get("records", 0)),
        evidence_count=int(manifest.counts.get("evidence", 0)),
        zotero_candidate_count=int(manifest.counts.get("zotero_candidates", 0)),
        network_request_count=manifest.network_request_count,
        article_store_sha256=article_sha_after,
        article_count=article_count,
        manifest_article_count=manifest_article_count,
        input_accounting_rate=input_accounting_rate,
        classification_reconciliation_rate=classification_rate,
        checkpoint_status=checkpoint_status,
        checkpoint_next_position=checkpoint_next_position,
        resource_budgets_passed=resource_budgets_passed,
        absolute_path_violation_count=absolute_path_count,
        issues=issues,
    )


def audit_repository_artifacts(repo_root: Path | str, reference_store: Path | str) -> ReferenceArtifactAuditResult:
    root = Path(repo_root).resolve()
    store = Path(reference_store).resolve()
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    untracked = _git_paths(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    candidate_paths = sorted(set(value for value in tracked if value) | set(untracked))
    findings: list[dict[str, str]] = []
    baseline_findings: list[dict[str, str]] = []
    for relative in candidate_paths:
        if _is_forbidden_tracked(relative):
            findings.append({"kind": "tracked_runtime_private_artifact", "path": relative})
    for relative in candidate_paths:
        path = root / relative
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
            findings.append({"kind": "secret_pattern", "path": relative})
        current_paths = Counter(_ABSOLUTE_PATH.findall(text))
        if current_paths:
            baseline_text = _git_head_text(root, relative)
            baseline_paths = Counter(_ABSOLUTE_PATH.findall(baseline_text or ""))
            target = findings if current_paths - baseline_paths else baseline_findings
            target.append({"kind": "local_absolute_path", "path": relative})
    try:
        store.relative_to(root)
    except ValueError:
        pass
    else:
        tracked_store = [path for path in tracked if path and (root / path).resolve().is_relative_to(store)]
        findings.extend({"kind": "tracked_reference_store", "path": path} for path in tracked_store)
    counts = {
        kind: sum(item["kind"] == kind for item in findings)
        for kind in (
            "tracked_runtime_private_artifact",
            "tracked_reference_store",
            "secret_pattern",
            "local_absolute_path",
        )
    }
    tracked_count = counts["tracked_runtime_private_artifact"] + counts["tracked_reference_store"]
    return ReferenceArtifactAuditResult(
        status="PASS" if not findings else "BLOCKED",
        tracked_runtime_private_artifact_count=tracked_count,
        secret_pattern_count=counts["secret_pattern"],
        local_absolute_path_count=counts["local_absolute_path"],
        baseline_local_absolute_path_count=len(baseline_findings),
        findings=findings,
        baseline_findings=baseline_findings,
    )


def _git_paths(root: Path, arguments: list[str]) -> list[str]:
    return [
        value
        for value in subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .split("\0")
        if value
    ]


def _git_head_text(root: Path, relative: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _is_forbidden_tracked(relative: str) -> bool:
    if relative.lower() in {".env.example", ".env.sample"}:
        return False
    return _FORBIDDEN_TRACKED.search(relative) is not None


def _runtime_absolute_path_count(text: str, *, roots: tuple[Path, ...]) -> int:
    prefixes = sorted(
        {
            str(root.resolve())
            for root in roots
            if str(root.resolve()) not in {"/", "."}
        },
        key=len,
        reverse=True,
    )
    return sum(text.count(prefix) for prefix in prefixes)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
