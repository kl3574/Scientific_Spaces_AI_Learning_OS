from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from common import REPO_ROOT, SecurityToolError, load_json


USES_PATTERN = re.compile(
    r"^(?P<indent>\s*)(?:-\s*)?uses:\s*(?P<target>[^\s#]+)(?:\s+#\s*(?P<comment>.+))?$"
)
EXTERNAL_ACTION_PATTERN = re.compile(
    r"^(?P<repository>[^/@\s]+/[^/@\s]+)(?:/[^@\s]+)?@(?P<ref>[^\s]+)$"
)
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT_PATTERN = re.compile(r"\bv\d+(?:\.\d+){1,2}\b")
UV_INSTALL_PATTERN = re.compile(
    r"\bpython\s+-m\s+pip\s+install\s+(?P<package>uv(?:==[^\s;&|]+)?)(?=$|[\s;&|])"
)
SAFE_RELEASE_CONDITION = re.compile(
    r"^github\.event_name==(?P<quote1>['\"])workflow_dispatch(?P=quote1)\|\|"
    r"\(github\.event_name==(?P<quote2>['\"])push(?P=quote2)&&"
    r"startsWith\(github\.ref,(?P<quote3>['\"])refs/tags/v(?P=quote3)\)\)$"
)
WRITE_PERMISSIONS = {
    "actions",
    "attestations",
    "checks",
    "contents",
    "deployments",
    "id-token",
    "packages",
    "pull-requests",
    "releases",
    "security-events",
}


@dataclass(frozen=True)
class JobBlock:
    name: str
    lines: tuple[str, ...]


def workflow_files(root: Path) -> list[Path]:
    files = list(root.glob("*.yml")) + list(root.glob("*.yaml"))
    return sorted(files)


def _permissions(lines: Iterable[str], base_indent: int) -> dict[str, str] | None:
    lines_list = list(lines)
    marker = " " * base_indent + "permissions:"
    for index, line in enumerate(lines_list):
        if line.rstrip() != marker:
            continue
        result: dict[str, str] = {}
        child_indent = base_indent + 2
        for candidate in lines_list[index + 1 :]:
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= base_indent:
                break
            if indent == child_indent and ":" in candidate:
                key, value = candidate.strip().split(":", 1)
                result[key.strip()] = value.strip()
        return result
    return None


def _jobs(lines: list[str]) -> list[JobBlock]:
    try:
        jobs_index = next(index for index, line in enumerate(lines) if line.rstrip() == "jobs:")
    except StopIteration as exc:
        raise SecurityToolError("workflow is missing jobs") from exc
    blocks: list[JobBlock] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines[jobs_index + 1 :]:
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            if current_name is not None:
                blocks.append(JobBlock(current_name, tuple(current_lines)))
            current_name = match.group(1)
            current_lines = [line]
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        blocks.append(JobBlock(current_name, tuple(current_lines)))
    return blocks


def _job_condition(job: JobBlock) -> str | None:
    lines = list(job.lines)
    for index, line in enumerate(lines):
        if not re.match(r"^    if:\s*", line):
            continue
        value = line.split(":", 1)[1].strip()
        if value not in {">", ">-", "|", "|-"}:
            return value
        parts: list[str] = []
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= 4:
                break
            parts.append(candidate.strip())
        return " ".join(parts)
    return None


def _normalized_expression(value: str) -> str:
    return re.sub(r"\s+", "", value)


def inspect_workflow(
    path: Path,
    pin_map: dict[str, object],
    tool_versions: dict[str, object],
) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    findings: list[str] = []
    actions: list[dict[str, str]] = []

    uv_version = tool_versions.get("uv")
    if not isinstance(uv_version, str) or not uv_version:
        raise SecurityToolError("tool-versions.json must define uv")

    for line_number, line in enumerate(lines, start=1):
        for uv_match in UV_INSTALL_PATTERN.finditer(line):
            expected = f"uv=={uv_version}"
            if uv_match.group("package") != expected:
                findings.append(
                    f"{path}:{line_number}: uv install must be exactly pinned to {expected}"
                )
        match = USES_PATTERN.match(line)
        if not match:
            continue
        target = match.group("target")
        if target.startswith("./"):
            actions.append({"target": target, "kind": "local", "line": str(line_number)})
            continue
        external = EXTERNAL_ACTION_PATTERN.match(target)
        if not external:
            findings.append(f"{path}:{line_number}: malformed external action: {target}")
            continue
        repository = external.group("repository")
        ref = external.group("ref")
        comment = (match.group("comment") or "").strip()
        actions.append(
            {
                "repository": repository,
                "ref": ref,
                "comment": comment,
                "line": str(line_number),
            }
        )
        if not FULL_SHA_PATTERN.fullmatch(ref):
            findings.append(f"{path}:{line_number}: mutable action ref: {target}")
            continue
        if not VERSION_COMMENT_PATTERN.search(comment):
            findings.append(f"{path}:{line_number}: missing version comment: {repository}")
        pin = pin_map.get(repository)
        if not isinstance(pin, dict) or pin.get("sha") != ref:
            findings.append(f"{path}:{line_number}: SHA is absent from action-pins.json: {target}")

    workflow_permissions = _permissions(lines, 0)
    if workflow_permissions != {"contents": "read"}:
        findings.append(f"{path}: workflow permissions must be exactly contents: read")

    jobs = _jobs(lines)
    for job in jobs:
        permissions = _permissions(job.lines, 4)
        if permissions is None:
            findings.append(f"{path}: job {job.name} has implicit permissions")
            continue
        if permissions.get("contents") != "read":
            findings.append(f"{path}: job {job.name} must declare contents: read")
        for permission, value in permissions.items():
            if permission in WRITE_PERMISSIONS and value == "write":
                findings.append(f"{path}: job {job.name} has prohibited {permission}: write")

    release_jobs = [job for job in jobs if job.name == "release_evidence"]
    if release_jobs:
        condition = _job_condition(release_jobs[0])
        if condition is None or not SAFE_RELEASE_CONDITION.fullmatch(
            _normalized_expression(condition)
        ):
            findings.append(
                f"{path}: release_evidence condition must allow manual dispatch OR tag push only"
            )

    external_count = sum(1 for action in actions if action.get("kind") != "local")
    immutable_count = sum(
        1
        for action in actions
        if action.get("kind") != "local" and FULL_SHA_PATTERN.fullmatch(action.get("ref", ""))
    )
    pin_rate = 1.0 if external_count == 0 else immutable_count / external_count
    explicit_jobs = sum(1 for job in jobs if _permissions(job.lines, 4) is not None)
    permission_rate = 1.0 if not jobs else explicit_jobs / len(jobs)
    try:
        display_path = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        display_path = path.as_posix()
    return {
        "path": display_path,
        "actions": actions,
        "job_count": len(jobs),
        "third_party_action_full_sha_pin_rate": pin_rate,
        "workflow_permissions_explicit": workflow_permissions is not None,
        "job_permissions_explicit_rate": permission_rate,
        "findings": findings,
    }


def inspect_all(
    workflows: Path,
    pins: Path,
    tool_versions_path: Path,
) -> dict[str, object]:
    pin_map = load_json(pins)
    if not isinstance(pin_map, dict):
        raise SecurityToolError("action-pins.json must contain an object")
    tool_versions = load_json(tool_versions_path)
    if not isinstance(tool_versions, dict):
        raise SecurityToolError("tool-versions.json must contain an object")
    files = workflow_files(workflows)
    if not files:
        raise SecurityToolError("no workflow files found")
    results = [inspect_workflow(path, pin_map, tool_versions) for path in files]
    findings = [finding for result in results for finding in result["findings"]]
    external_actions = sum(
        sum(1 for action in result["actions"] if action.get("kind") != "local")
        for result in results
    )
    immutable_actions = sum(
        sum(
            1
            for action in result["actions"]
            if action.get("kind") != "local"
            and FULL_SHA_PATTERN.fullmatch(action.get("ref", ""))
        )
        for result in results
    )
    jobs = sum(result["job_count"] for result in results)
    explicit_jobs = sum(
        round(result["job_permissions_explicit_rate"] * result["job_count"])
        for result in results
    )
    return {
        "status": "PASS" if not findings else "BLOCKED",
        "workflow_count": len(results),
        "third_party_action_count": external_actions,
        "third_party_action_full_sha_pin_rate": (
            1.0 if external_actions == 0 else immutable_actions / external_actions
        ),
        "workflow_permissions_explicit_rate": (
            1.0
            if jobs == 0
            else explicit_jobs / jobs
        ),
        "workflows": results,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow pins and permissions.")
    parser.add_argument(
        "--workflows", type=Path, default=REPO_ROOT / ".github" / "workflows"
    )
    parser.add_argument(
        "--pins",
        type=Path,
        default=REPO_ROOT / ".github" / "security" / "action-pins.json",
    )
    parser.add_argument(
        "--tool-versions",
        type=Path,
        default=REPO_ROOT / ".github" / "security" / "tool-versions.json",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        result = inspect_all(args.workflows, args.pins, args.tool_versions)
    except SecurityToolError as exc:
        print(f"workflow_policy=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "workflow_policy={status} workflows={workflow_count} actions={third_party_action_count} "
            "pin_rate={third_party_action_full_sha_pin_rate:.3f} "
            "permission_rate={workflow_permissions_explicit_rate:.3f}".format(**result)
        )
        for finding in result["findings"]:
            print(f"finding={finding}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
