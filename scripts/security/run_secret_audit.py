from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from common import REPO_ROOT, SecurityToolError, load_json, write_canonical_json
from validate_suppressions import validate as validate_suppressions


SYNTHETIC_MARKERS = (
    "dummy",
    "example",
    "fake",
    "placeholder",
    "redacted",
    "synthetic",
    "test-only",
)


def irreversible_fingerprint(rule_id: str, value: str) -> str:
    payload = f"scientific-spaces-p3-005\0{rule_id}\0{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compile_rules(policy: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise SecurityToolError("secret rules must be a non-empty array")
    compiled = []
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise SecurityToolError("malformed secret rule")
        pattern = rule.get("pattern")
        if not isinstance(pattern, str):
            raise SecurityToolError(f"secret rule {rule['id']} is missing pattern")
        try:
            compiled.append((rule["id"], re.compile(pattern)))
        except re.error as exc:
            raise SecurityToolError(f"invalid secret rule {rule['id']}") from exc
    return compiled


def classify_match(path: str, line: str) -> str:
    lowered = line.lower()
    normalized_path = path.lower()
    if "/tests/" in f"/{normalized_path}" or "/fixtures/" in f"/{normalized_path}":
        return "synthetic_fixture"
    if any(marker in lowered for marker in SYNTHETIC_MARKERS):
        return "synthetic_example"
    return "credible"


def scan_text(
    path: str,
    text: str,
    rules: list[tuple[str, re.Pattern[str]]],
    *,
    line_offset: int = 0,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1 + line_offset):
        for rule_id, pattern in rules:
            for match in pattern.finditer(line):
                value = match.group(0)
                findings.append(
                    {
                        "rule_id": rule_id,
                        "path": path,
                        "line": line_number,
                        "irreversible_fingerprint": irreversible_fingerprint(rule_id, value),
                        "classification": classify_match(path, line),
                        "suppression_id": None,
                        "source": "tracked",
                    }
                )
    return findings


def scan_tracked_files(
    rules: list[tuple[str, re.Pattern[str]]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    file_limit = int(policy.get("tracked_file_byte_limit", 0))
    total_limit = int(policy.get("tracked_total_byte_limit", 0))
    if file_limit <= 0 or total_limit <= 0:
        raise SecurityToolError("tracked secret-scan budgets must be positive")
    total = 0
    findings: list[dict[str, Any]] = []
    for raw_path in dict.fromkeys(result.stdout.split(b"\0")):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", errors="strict")
        content = (REPO_ROOT / path).read_bytes()
        total += len(content)
        if total > total_limit:
            raise SecurityToolError("tracked secret-scan total byte budget exceeded")
        if len(content) > file_limit:
            raise SecurityToolError(f"tracked secret-scan file byte budget exceeded: {path}")
        if b"\0" in content:
            continue
        text = content.decode("utf-8", errors="replace")
        findings.extend(scan_text(path, text, rules))
    return findings


def scan_history(
    rules: list[tuple[str, re.Pattern[str]]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    commit_count_result = subprocess.run(
        ["git", "rev-list", "--all", "--count"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    commit_count = int(commit_count_result.stdout.strip())
    commit_limit = int(policy.get("history_commit_limit", 0))
    byte_limit = int(policy.get("history_output_byte_limit", 0))
    if commit_limit <= 0 or byte_limit <= 0:
        raise SecurityToolError("history secret-scan budgets must be positive")
    if commit_count > commit_limit:
        raise SecurityToolError(
            f"history commit budget exceeded: {commit_count}>{commit_limit}"
        )

    process = subprocess.Popen(
        [
            "git",
            "log",
            "--all",
            "--format=commit %H",
            "--patch",
            "--no-ext-diff",
            "--no-color",
            "--unified=0",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        errors="replace",
    )
    assert process.stdout is not None
    current_path = "<unknown>"
    current_line = 0
    total_bytes = 0
    findings: list[dict[str, Any]] = []
    for line in process.stdout:
        total_bytes += len(line.encode("utf-8", errors="replace"))
        if total_bytes > byte_limit:
            process.kill()
            raise SecurityToolError("history secret-scan byte budget exceeded")
        if line.startswith("+++ b/"):
            current_path = line[6:].rstrip("\n")
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            current_line = int(match.group(1)) if match else 0
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        payload = line[1:].rstrip("\n")
        line_findings = scan_text(
            current_path, payload, rules, line_offset=max(current_line - 1, 0)
        )
        for finding in line_findings:
            finding["source"] = "history"
        findings.extend(line_findings)
        current_line += 1
    stderr = process.stderr.read() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code != 0:
        raise SecurityToolError(f"history secret scan failed: {stderr.strip()}")
    return findings


def deduplicate(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    rank = {"synthetic_example": 0, "synthetic_fixture": 0, "credible": 1}
    for original in findings:
        key = (
            original["rule_id"],
            original["path"],
            original["irreversible_fingerprint"],
        )
        finding = merged.get(key)
        if finding is None:
            finding = dict(original)
            finding["sources"] = [original["source"]]
            finding.pop("source", None)
            merged[key] = finding
            continue
        finding["line"] = min(int(finding["line"]), int(original["line"]))
        finding["sources"] = sorted(set(finding["sources"]) | {original["source"]})
        if rank[original["classification"]] > rank[finding["classification"]]:
            finding["classification"] = original["classification"]
    return sorted(
        merged.values(),
        key=lambda item: (item["path"], item["line"], item["rule_id"]),
    )


def evaluate(
    findings: list[dict[str, Any]], suppressions: dict[str, Any]
) -> dict[str, Any]:
    suppression_entries = suppressions.get("secret_suppressions", [])
    if not isinstance(suppression_entries, list):
        raise SecurityToolError("secret suppressions must be an array")
    suppression_map = {
        (
            item.get("rule_id"),
            item.get("path"),
            item.get("irreversible_fingerprint"),
        ): item
        for item in suppression_entries
        if isinstance(item, dict)
    }
    evaluated: list[dict[str, Any]] = []
    for original in findings:
        finding = dict(original)
        key = (
            finding["rule_id"],
            finding["path"],
            finding["irreversible_fingerprint"],
        )
        suppression = suppression_map.get(key)
        if finding["classification"] == "credible":
            finding["status"] = "blocked"
        elif suppression is not None:
            finding["suppression_id"] = suppression.get("id")
            finding["status"] = "suppressed"
        else:
            finding["status"] = "reported"
        evaluated.append(finding)
    credible = [item for item in evaluated if item["classification"] == "credible"]
    return {
        "status": "PASS" if not credible else "BLOCKED",
        "credible_secret_findings": len(credible),
        "reported_false_positive_count": sum(
            item["status"] == "reported" for item in evaluated
        ),
        "suppressed_count": sum(item["status"] == "suppressed" for item in evaluated),
        "findings": evaluated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked files and bounded history for secrets.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        policy = load_json(REPO_ROOT / ".github" / "security" / "secret-rules.json")
        suppressions = load_json(REPO_ROOT / ".github" / "security" / "suppressions.json")
        rules = compile_rules(policy)
        findings = deduplicate(
            scan_tracked_files(rules, policy) + scan_history(rules, policy)
        )
        suppression_result = validate_suppressions(
            suppressions, dependency_findings=None, secret_findings=findings
        )
        if suppression_result["status"] != "PASS":
            raise SecurityToolError("suppression validation failed")
        evaluation = evaluate(findings, suppressions)
        result = {
            "schema_version": 1,
            "status": evaluation["status"],
            "history_commit_limit": policy["history_commit_limit"],
            "credible_secret_findings": evaluation["credible_secret_findings"],
            "reported_false_positive_count": evaluation["reported_false_positive_count"],
            "suppressed_count": evaluation["suppressed_count"],
            "findings": evaluation["findings"],
        }
        if args.output:
            write_canonical_json(args.output, result)
    except (SecurityToolError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"secret_audit=BLOCKED reason={exc}", file=sys.stderr)
        return 2

    print(
        "secret_audit={status} credible={credible_secret_findings} "
        "reported={reported_false_positive_count} suppressed={suppressed_count}".format(
            **result
        )
    )
    for finding in result["findings"]:
        print(
            f"finding rule_id={finding['rule_id']} path={finding['path']} "
            f"line={finding['line']} fingerprint={finding['irreversible_fingerprint']} "
            f"classification={finding['classification']} status={finding['status']}"
        )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
