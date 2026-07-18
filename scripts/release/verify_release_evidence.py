from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


SECURITY_DIR = Path(__file__).resolve().parents[1] / "security"
sys.path.insert(0, str(SECURITY_DIR))

from common import SecurityToolError, load_json, run, sha256_file  # noqa: E402


EXPECTED_ARTIFACTS = {
    "backend.cdx.json",
    "frontend.cdx.json",
    "combined.cdx.json",
}
ABSOLUTE_PATH = re.compile(r"^(?:/(?:home|Users|root|tmp)/|[A-Za-z]:\\\\Users\\\\)")


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def verify(path: Path, *, no_network: bool) -> dict[str, Any]:
    if not no_network:
        raise SecurityToolError("P3-005 verification requires --no-network")
    evidence = load_json(path)
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1:
        raise SecurityToolError("invalid release evidence schema")
    if evidence.get("generation_mode") != "dry-run-no-publish":
        raise SecurityToolError("release evidence is not a no-publish dry run")
    if evidence.get("boundary_status") != "PASS":
        raise SecurityToolError("release boundary did not pass")
    if evidence.get("publish_authorized") is not False:
        raise SecurityToolError("P3-005 evidence must not authorize publication")
    workflow_ref = evidence.get("workflow_ref")
    if isinstance(workflow_ref, str) and workflow_ref.startswith("refs/heads/"):
        if evidence.get("would_authorize_publish") is not False:
            raise SecurityToolError("ordinary branch evidence can authorize publication")

    tag = evidence.get("tag")
    if not isinstance(tag, str):
        raise SecurityToolError("release evidence is missing tag")
    tag_ref = f"refs/tags/{tag}"
    actual_type = run(["git", "cat-file", "-t", tag_ref]).stdout.strip()
    actual_target = run(["git", "rev-parse", f"{tag_ref}^{{commit}}"]).stdout.strip()
    if evidence.get("tag_object_type") != actual_type:
        raise SecurityToolError("release evidence tag object type mismatch")
    if evidence.get("tag_target_sha") != actual_target:
        raise SecurityToolError("release evidence tag target mismatch")

    artifacts = evidence.get("eligible_artifacts")
    if not isinstance(artifacts, list):
        raise SecurityToolError("release evidence artifacts must be an array")
    names = {item.get("name") for item in artifacts if isinstance(item, dict)}
    if names != EXPECTED_ARTIFACTS:
        raise SecurityToolError("release evidence contains unknown or missing artifacts")
    digest_fields = {
        "backend.cdx.json": "backend_sbom_sha256",
        "frontend.cdx.json": "frontend_sbom_sha256",
        "combined.cdx.json": "combined_sbom_sha256",
    }
    for item in artifacts:
        if not isinstance(item, dict):
            raise SecurityToolError("malformed release evidence artifact")
        name = item["name"]
        artifact_path = path.parent / name
        if not artifact_path.is_file():
            raise SecurityToolError(f"release evidence artifact is missing: {name}")
        digest = sha256_file(artifact_path)
        if item.get("sha256") != digest or evidence.get(digest_fields[name]) != digest:
            raise SecurityToolError(f"release evidence digest mismatch: {name}")
    if any(ABSOLUTE_PATH.search(value) for value in _strings(evidence)):
        raise SecurityToolError("release evidence contains a local absolute path")
    return {
        "status": "PASS",
        "tag": tag,
        "tag_target_sha": actual_target,
        "publish_authorized": False,
        "artifact_count": len(artifacts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release evidence without network access.")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--no-network", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.evidence, no_network=args.no_network)
    except (SecurityToolError, OSError, ValueError) as exc:
        print(f"release_evidence_verification=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print(
        "release_evidence_verification=PASS tag={tag} tag_target={tag_target_sha} "
        "artifacts={artifact_count} publish_authorized=false".format(**result)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
