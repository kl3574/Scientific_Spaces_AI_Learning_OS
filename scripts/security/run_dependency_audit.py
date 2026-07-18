from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from common import REPO_ROOT, SecurityToolError, load_json, write_canonical_json
from lockfiles import LockedPackage, parse_package_lock, parse_uv_lock
from validate_suppressions import validate as validate_suppressions


OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "UNKNOWN": 5}
MERGE_SEVERITY_ORDER = {"UNKNOWN": -1, "NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def normalize_severity(value: object) -> str:
    if isinstance(value, str):
        normalized = value.upper()
        if normalized in SEVERITY_ORDER:
            return normalized
    return "UNKNOWN"


def osv_severity(vulnerability: dict[str, Any]) -> str:
    database_specific = vulnerability.get("database_specific")
    if isinstance(database_specific, dict):
        value = normalize_severity(database_specific.get("severity"))
        if value != "UNKNOWN":
            return value
    ecosystem_specific = vulnerability.get("ecosystem_specific")
    if isinstance(ecosystem_specific, dict):
        value = normalize_severity(ecosystem_specific.get("severity"))
        if value != "UNKNOWN":
            return value
    return "UNKNOWN"


def _base_finding(package: LockedPackage, advisory_id: str, source: str) -> dict[str, Any]:
    return {
        "ecosystem": package.ecosystem,
        "package": package.name,
        "version": package.version,
        "advisory_id": advisory_id,
        "aliases": [],
        "severity": "UNKNOWN",
        "dependency_scope": package.scope,
        "suppression_id": None,
        "status": "unreviewed",
        "sources": [source],
    }


def query_osv(packages: list[LockedPackage], *, timeout: int = 30) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for offset in range(0, len(packages), 100):
        batch = packages[offset : offset + 100]
        payload = {
            "queries": [
                {
                    "package": {"ecosystem": package.ecosystem, "name": package.name},
                    "version": package.version,
                }
                for package in batch
            ]
        }
        request = urllib.request.Request(
            OSV_BATCH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Scientific-Spaces-CI-Security/1.0",
            },
            method="POST",
        )
        last_error: Exception | None = None
        response_data: dict[str, Any] | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response_data = json.load(response)
                break
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        if response_data is None:
            raise SecurityToolError(f"OSV scanner unavailable: {type(last_error).__name__}")
        results = response_data.get("results")
        if not isinstance(results, list) or len(results) != len(batch):
            raise SecurityToolError("malformed OSV querybatch response")
        for package, result in zip(batch, results):
            if not isinstance(result, dict):
                raise SecurityToolError("malformed OSV result")
            vulnerabilities = result.get("vulns", [])
            if not isinstance(vulnerabilities, list):
                raise SecurityToolError("malformed OSV vulnerability list")
            for vulnerability in vulnerabilities:
                if not isinstance(vulnerability, dict) or not isinstance(vulnerability.get("id"), str):
                    raise SecurityToolError("malformed OSV vulnerability")
                finding = _base_finding(package, vulnerability["id"], "osv")
                aliases = vulnerability.get("aliases", [])
                finding["aliases"] = sorted(
                    value for value in aliases if isinstance(value, str)
                )
                finding["severity"] = osv_severity(vulnerability)
                findings.append(finding)
    return findings


def _requirements_file(packages: list[LockedPackage], path: Path) -> None:
    lines = [
        f"{package.name}=={package.version}"
        for package in packages
        if package.ecosystem == "PyPI"
    ]
    path.write_text("\n".join(sorted(set(lines))) + "\n", encoding="utf-8")


def run_pip_audit(
    packages: list[LockedPackage], tool_version: str, temporary: Path
) -> list[dict[str, Any]]:
    requirements = temporary / "python-requirements.txt"
    output = temporary / "pip-audit.json"
    _requirements_file(packages, requirements)
    command = [
        "uvx",
        "--from",
        f"pip-audit=={tool_version}",
        "pip-audit",
        "--requirement",
        str(requirements),
        "--format",
        "json",
        "--vulnerability-service",
        "osv",
        "--desc",
        "off",
        "--aliases",
        "on",
        "--progress-spinner",
        "off",
        "--no-deps",
        "--disable-pip",
        "--output",
        str(output),
    ]
    command.extend(["--timeout", "30"])
    result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(3):
        output.unlink(missing_ok=True)
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        if result.returncode in (0, 1) and output.is_file():
            break
        if attempt < 2:
            time.sleep(2**attempt)
    assert result is not None
    if result.returncode not in (0, 1) or not output.is_file():
        raise SecurityToolError(f"pip-audit unavailable or malformed (exit={result.returncode})")
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SecurityToolError("malformed pip-audit JSON") from exc
    dependencies = data.get("dependencies") if isinstance(data, dict) else None
    if not isinstance(dependencies, list):
        raise SecurityToolError("pip-audit JSON is missing dependencies")
    package_map = {(package.name.lower(), package.version): package for package in packages}
    findings: list[dict[str, Any]] = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise SecurityToolError("malformed pip-audit dependency")
        name = dependency.get("name")
        version = dependency.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise SecurityToolError("pip-audit dependency missing identity")
        package = package_map.get((name.lower().replace("_", "-"), version))
        if package is None:
            package = package_map.get((name.lower(), version))
        if package is None:
            raise SecurityToolError(f"pip-audit returned unexpected package: {name}=={version}")
        vulnerabilities = dependency.get("vulns", [])
        if not isinstance(vulnerabilities, list):
            raise SecurityToolError("malformed pip-audit vulnerabilities")
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict) or not isinstance(vulnerability.get("id"), str):
                raise SecurityToolError("malformed pip-audit vulnerability")
            finding = _base_finding(package, vulnerability["id"], "pip-audit")
            aliases = vulnerability.get("aliases", [])
            finding["aliases"] = sorted(value for value in aliases if isinstance(value, str))
            findings.append(finding)
    return findings


def run_npm_audit(
    packages: list[LockedPackage], temporary: Path
) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["npm", "audit", "--package-lock-only", "--json", "--audit-level=low"],
        cwd=REPO_ROOT / "frontend",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        env={**os.environ, "npm_config_update_notifier": "false", "npm_config_fund": "false"},
    )
    if result.returncode not in (0, 1):
        raise SecurityToolError(f"npm audit unavailable (exit={result.returncode})")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SecurityToolError("malformed npm audit JSON") from exc
    vulnerabilities = data.get("vulnerabilities")
    if not isinstance(vulnerabilities, dict):
        raise SecurityToolError("npm audit JSON is missing vulnerabilities")
    package_map: dict[str, list[LockedPackage]] = {}
    for package in packages:
        package_map.setdefault(package.name, []).append(package)
    findings: list[dict[str, Any]] = []
    for name, vulnerability in vulnerabilities.items():
        if not isinstance(vulnerability, dict):
            raise SecurityToolError("malformed npm audit vulnerability")
        matched_packages = package_map.get(name, [])
        if not matched_packages:
            raise SecurityToolError(f"npm audit returned unexpected package: {name}")
        via_entries = vulnerability.get("via", [])
        advisory_entries = [entry for entry in via_entries if isinstance(entry, dict)]
        if not advisory_entries:
            advisory_entries = [vulnerability]
        for package in matched_packages:
            for entry in advisory_entries:
                source = entry.get("source")
                url = str(entry.get("url") or "")
                advisory_id = next(
                    (token for token in url.replace("/", " ").split() if token.startswith("GHSA-")),
                    f"NPM-{source}" if source is not None else f"NPM-{name}",
                )
                finding = _base_finding(package, advisory_id, "npm-audit")
                finding["severity"] = normalize_severity(
                    entry.get("severity") or vulnerability.get("severity")
                )
                findings.append(finding)
    return findings


def _identifiers(finding: dict[str, Any]) -> set[str]:
    values = {str(finding.get("advisory_id", ""))}
    values.update(str(value) for value in finding.get("aliases", []))
    return {value for value in values if value}


def merge_findings(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for finding in findings:
        match = None
        for candidate in merged:
            same_package = all(
                candidate.get(field) == finding.get(field)
                for field in ("ecosystem", "package", "version")
            )
            if same_package and _identifiers(candidate) & _identifiers(finding):
                match = candidate
                break
        if match is None:
            merged.append(dict(finding))
            continue
        identifiers = _identifiers(match) | _identifiers(finding)
        match["advisory_id"] = sorted(identifiers)[0]
        match["aliases"] = sorted(identifiers - {match["advisory_id"]})
        match["sources"] = sorted(set(match.get("sources", [])) | set(finding.get("sources", [])))
        if MERGE_SEVERITY_ORDER[normalize_severity(finding.get("severity"))] > MERGE_SEVERITY_ORDER[
            normalize_severity(match.get("severity"))
        ]:
            match["severity"] = normalize_severity(finding.get("severity"))
    return sorted(
        merged,
        key=lambda item: (
            item["ecosystem"],
            item["package"],
            item["version"],
            item["advisory_id"],
        ),
    )


def evaluate_findings(
    findings: list[dict[str, Any]], policy: dict[str, Any], suppressions: dict[str, Any]
) -> dict[str, Any]:
    suppression_entries = suppressions.get("dependency_suppressions", [])
    if not isinstance(suppression_entries, list):
        raise SecurityToolError("dependency suppressions must be an array")
    suppression_map = {
        (
            item.get("ecosystem"),
            item.get("package"),
            item.get("advisory_id"),
            item.get("scope"),
        ): item
        for item in suppression_entries
        if isinstance(item, dict)
    }
    evaluated: list[dict[str, Any]] = []
    for original in findings:
        finding = dict(original)
        severity = normalize_severity(finding.get("severity"))
        scope = str(finding.get("dependency_scope"))
        key = (
            finding.get("ecosystem"),
            finding.get("package"),
            finding.get("advisory_id"),
            scope,
        )
        suppression = suppression_map.get(key)
        blocking_severities = set(policy.get("blocking", {}).get(scope, []))
        if suppression is not None:
            finding["suppression_id"] = suppression.get("id")
            finding["status"] = "suppressed"
        elif severity in blocking_severities:
            finding["status"] = "blocked"
        else:
            finding["status"] = "reported"
        evaluated.append(finding)
    blocked = [finding for finding in evaluated if finding["status"] == "blocked"]
    return {
        "status": "PASS" if not blocked else "BLOCKED",
        "findings": evaluated,
        "blocked_count": len(blocked),
        "reported_count": sum(item["status"] == "reported" for item in evaluated),
        "suppressed_count": sum(item["status"] == "suppressed" for item in evaluated),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit locked Python and npm dependencies.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        python_packages, _ = parse_uv_lock(REPO_ROOT / "backend" / "uv.lock")
        npm_packages, _ = parse_package_lock(REPO_ROOT / "frontend" / "package-lock.json")
        policy = load_json(REPO_ROOT / ".github" / "security" / "dependency-policy.json")
        suppressions = load_json(REPO_ROOT / ".github" / "security" / "suppressions.json")
        tool_versions = load_json(REPO_ROOT / ".github" / "security" / "tool-versions.json")
        with tempfile.TemporaryDirectory(prefix="p3-005-dependency-") as temporary_name:
            temporary = Path(temporary_name)
            pip_findings = run_pip_audit(
                python_packages, str(tool_versions["pip_audit"]), temporary
            )
            npm_findings = run_npm_audit(npm_packages, temporary)
            osv_findings = query_osv(python_packages + npm_packages)
        merged = merge_findings(pip_findings + npm_findings + osv_findings)
        suppression_result = validate_suppressions(
            suppressions, dependency_findings=merged, secret_findings=None
        )
        if suppression_result["status"] != "PASS":
            raise SecurityToolError("suppression validation failed")
        evaluation = evaluate_findings(merged, policy, suppressions)
        result = {
            "schema_version": 1,
            "status": evaluation["status"],
            "package_counts": {"PyPI": len(python_packages), "npm": len(npm_packages)},
            "scanner_results": {
                "pip_audit": "PASS",
                "npm_audit": "PASS",
                "osv_multi_ecosystem": "PASS",
            },
            "finding_count": len(evaluation["findings"]),
            "blocked_count": evaluation["blocked_count"],
            "reported_count": evaluation["reported_count"],
            "suppressed_count": evaluation["suppressed_count"],
            "findings": evaluation["findings"],
        }
        if args.output:
            write_canonical_json(args.output, result)
    except (SecurityToolError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"dependency_audit=BLOCKED reason={exc}", file=sys.stderr)
        return 2

    print(
        "dependency_audit={status} pypi={PyPI} npm={npm} findings={finding_count} "
        "blocked={blocked_count} suppressed={suppressed_count}".format(
            **result, **result["package_counts"]
        )
    )
    for finding in result["findings"]:
        sources = ",".join(finding["sources"])
        print(
            f"finding ecosystem={finding['ecosystem']} package={finding['package']} "
            f"version={finding['version']} advisory={finding['advisory_id']} "
            f"severity={finding['severity']} scope={finding['dependency_scope']} "
            f"status={finding['status']} sources={sources}"
        )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
