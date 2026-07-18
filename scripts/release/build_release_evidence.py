from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
sys.path.insert(0, str(SECURITY_DIR))

from build_sbom import build_all  # noqa: E402
from common import (  # noqa: E402
    REPO_ROOT,
    SecurityToolError,
    git_commit,
    load_json,
    run,
    sha256_file,
    write_canonical_json,
)
from validate_sbom import validate_all  # noqa: E402


SBOM_NAMES = ("backend.cdx.json", "frontend.cdx.json", "combined.cdx.json")


def _metadata_property(document: dict[str, Any], name: str) -> str | None:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return None
    properties = metadata.get("properties", [])
    if not isinstance(properties, list):
        return None
    for item in properties:
        if isinstance(item, dict) and item.get("name") == name and isinstance(item.get("value"), str):
            return item["value"]
    return None


def build_evidence(
    *, tag: str, sbom_dir: Path, dry_run: bool, no_publish: bool
) -> dict[str, Any]:
    if not dry_run or not no_publish:
        raise SecurityToolError("P3-005 requires both --dry-run and --no-publish")
    if not tag.startswith("v"):
        raise SecurityToolError("release evidence tag must start with v")
    tag_ref = f"refs/tags/{tag}"
    tag_type = run(["git", "cat-file", "-t", tag_ref]).stdout.strip()
    if tag_type not in {"tag", "commit"}:
        raise SecurityToolError(f"unsupported tag object type: {tag_type}")
    tag_target = run(["git", "rev-parse", f"{tag_ref}^{{commit}}"]).stdout.strip()
    current_commit = git_commit()

    validation = validate_all(sbom_dir, structural_only=True)
    artifacts = []
    sbom_commits = set()
    for name in SBOM_NAMES:
        path = sbom_dir / name
        document = load_json(path)
        if not isinstance(document, dict):
            raise SecurityToolError(f"invalid SBOM: {name}")
        commit = _metadata_property(document, "scientific-spaces:git-commit")
        if not commit:
            raise SecurityToolError(f"SBOM missing git commit: {name}")
        sbom_commits.add(commit)
        artifacts.append({"name": name, "sha256": sha256_file(path)})

    workflow_ref = os.environ.get("GITHUB_REF", "refs/heads/main")
    workflow_identity = os.environ.get(
        "GITHUB_WORKFLOW_REF", "local/p3-005-release-evidence-dry-run"
    )
    event_name = os.environ.get("GITHUB_EVENT_NAME", "local")
    exact_tag_ref = workflow_ref == tag_ref
    trusted_event = event_name in {"push", "workflow_dispatch"}
    exact_subject = sbom_commits == {tag_target}
    conditions = {
        "exact_tag_ref": exact_tag_ref,
        "trusted_event": trusted_event,
        "annotated_or_explicit_tag_type": tag_type in {"tag", "commit"},
        "sbom_commit_matches_tag_target": exact_subject,
        "sbom_validation": validation["status"] == "PASS",
        "no_publish_requested": no_publish,
    }
    would_authorize_publish = all(
        conditions[key]
        for key in (
            "exact_tag_ref",
            "trusted_event",
            "annotated_or_explicit_tag_type",
            "sbom_commit_matches_tag_target",
            "sbom_validation",
        )
    )
    reasons = [key for key, value in conditions.items() if not value]
    evidence = {
        "schema_version": 1,
        "generation_mode": "dry-run-no-publish",
        "boundary_status": "PASS",
        "commit_sha": current_commit,
        "tag": tag,
        "tag_object_type": tag_type,
        "tag_target_sha": tag_target,
        "workflow_identity": workflow_identity,
        "workflow_ref": workflow_ref,
        "event_name": event_name,
        "backend_sbom_sha256": artifacts[0]["sha256"],
        "frontend_sbom_sha256": artifacts[1]["sha256"],
        "combined_sbom_sha256": artifacts[2]["sha256"],
        "eligible_artifacts": artifacts,
        "conditions": conditions,
        "would_authorize_publish": would_authorize_publish,
        "publish_authorized": False,
        "non_authorization_reasons": sorted(reasons + ["p3-005-no-publish-policy"]),
    }
    return evidence


def _execute(tag: str, sbom_dir: Path, output: Path) -> dict[str, Any]:
    evidence = build_evidence(tag=tag, sbom_dir=sbom_dir, dry_run=True, no_publish=True)
    write_canonical_json(output, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Build bounded no-publish release evidence.")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sbom-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-publish", action="store_true")
    args = parser.parse_args()
    try:
        if not args.dry_run or not args.no_publish:
            raise SecurityToolError("both --dry-run and --no-publish are mandatory")
        if args.sbom_dir:
            output = args.output or args.sbom_dir / "release-evidence.json"
            evidence = _execute(args.tag, args.sbom_dir, output)
            output_name = output.name
        else:
            with tempfile.TemporaryDirectory(prefix="p3-005-release-evidence-") as temporary_name:
                directory = Path(temporary_name)
                build_all(directory)
                output = directory / "release-evidence.json"
                evidence = _execute(args.tag, directory, output)
                output_name = "temporary/release-evidence.json"
    except (SecurityToolError, OSError, ValueError) as exc:
        print(f"release_evidence=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print(
        f"release_evidence=PASS mode={evidence['generation_mode']} tag={evidence['tag']} "
        f"tag_target={evidence['tag_target_sha']} publish_authorized=false "
        f"would_authorize_publish={str(evidence['would_authorize_publish']).lower()} "
        f"output={output_name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
