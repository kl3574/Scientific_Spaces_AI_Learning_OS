from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from common import REPO_ROOT, SecurityToolError, load_json, sha256_file
from lockfiles import parse_package_lock, parse_uv_lock


SECRET_PATTERNS = [
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
ABSOLUTE_PATH = re.compile(r"^(?:/(?:home|Users|root|tmp)/|[A-Za-z]:\\\\Users\\\\)")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _component_refs(document: dict[str, Any]) -> set[str]:
    components = document.get("components")
    if not isinstance(components, list):
        raise SecurityToolError("SBOM components must be an array")
    refs: set[str] = set()
    purls: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            raise SecurityToolError("SBOM component must be an object")
        ref = component.get("bom-ref")
        if not isinstance(ref, str) or not ref:
            raise SecurityToolError("SBOM component missing bom-ref")
        if ref in refs:
            raise SecurityToolError(f"duplicate SBOM bom-ref: {ref}")
        refs.add(ref)
        purl = component.get("purl")
        if purl is not None:
            if not isinstance(purl, str) or purl in purls:
                raise SecurityToolError(f"duplicate or invalid SBOM purl: {purl}")
            purls.add(purl)
    return refs


def validate_document(document: dict[str, Any], path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") != "1.6":
        raise SecurityToolError(f"{path.name}: expected CycloneDX 1.6")
    metadata = document.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("component"), dict):
        raise SecurityToolError(f"{path.name}: missing metadata component")
    root_ref = metadata["component"].get("bom-ref")
    if not isinstance(root_ref, str):
        raise SecurityToolError(f"{path.name}: metadata component missing bom-ref")
    component_refs = _component_refs(document)
    all_refs = component_refs | {root_ref}
    dependencies = document.get("dependencies")
    if not isinstance(dependencies, list):
        raise SecurityToolError(f"{path.name}: dependencies must be an array")
    dependency_refs: set[str] = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict) or not isinstance(dependency.get("ref"), str):
            raise SecurityToolError(f"{path.name}: malformed dependency entry")
        ref = dependency["ref"]
        if ref not in all_refs:
            raise SecurityToolError(f"{path.name}: dependency ref is unknown: {ref}")
        dependency_refs.add(ref)
        depends_on = dependency.get("dependsOn", [])
        if not isinstance(depends_on, list) or any(item not in all_refs for item in depends_on):
            raise SecurityToolError(f"{path.name}: dependency target is unknown")
    if dependency_refs != all_refs:
        missing = sorted(all_refs - dependency_refs)
        raise SecurityToolError(f"{path.name}: dependency entries missing: {','.join(missing[:5])}")

    forbidden_count = 0
    for value in _strings(document):
        if ABSOLUTE_PATH.search(value):
            forbidden_count += 1
        lowered = value.lower()
        if any(fragment.lower() in lowered for fragment in policy["forbidden_path_fragments"]):
            forbidden_count += 1
        if ("/" in value or "\\" in value) and any(
            lowered.endswith(suffix) for suffix in policy["forbidden_file_suffixes"]
        ):
            forbidden_count += 1
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            forbidden_count += 1
    if forbidden_count:
        raise SecurityToolError(f"{path.name}: forbidden or secret values found: {forbidden_count}")
    return {
        "component_count": len(component_refs),
        "dependency_count": len(dependencies),
        "forbidden_artifact_count": forbidden_count,
        "fingerprint": sha256_file(path),
    }


def _validate_coverage(documents: dict[str, dict[str, Any]]) -> None:
    python_packages, _ = parse_uv_lock(REPO_ROOT / "backend" / "uv.lock")
    npm_packages, _ = parse_package_lock(REPO_ROOT / "frontend" / "package-lock.json")
    backend_refs = {component["bom-ref"] for component in documents["backend"]["components"]}
    frontend_refs = {component["bom-ref"] for component in documents["frontend"]["components"]}
    expected_backend = {package.bom_ref for package in python_packages}
    expected_frontend = {package.bom_ref for package in npm_packages}
    if backend_refs != expected_backend:
        raise SecurityToolError("backend SBOM does not exactly cover backend/uv.lock")
    if frontend_refs != expected_frontend:
        raise SecurityToolError("frontend SBOM does not exactly cover frontend/package-lock.json")
    combined_refs = {component["bom-ref"] for component in documents["combined"]["components"]}
    expected_combined = expected_backend | expected_frontend | {
        "application:backend",
        "application:frontend",
    }
    if combined_refs != expected_combined:
        raise SecurityToolError("combined SBOM does not cover both ecosystem SBOMs")


def _schema_validate(paths: list[Path], policy: dict[str, Any]) -> None:
    validator = str(policy["schema_validator"])
    if "==" not in validator:
        raise SecurityToolError("schema validator must be exactly pinned")
    request = urllib.request.Request(
        str(policy["schema_api_url"]),
        headers={
            "Accept": "application/vnd.github.raw+json",
            "User-Agent": "Scientific-Spaces-CI-Security/1.0",
        },
    )
    schema_content: bytes | None = None
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                schema_content = response.read()
            break
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    if schema_content is None:
        raise SecurityToolError(
            f"CycloneDX schema unavailable: {type(last_error).__name__}"
        )
    if hashlib.sha256(schema_content).hexdigest() != policy["schema_sha256"]:
        raise SecurityToolError("CycloneDX schema digest mismatch")
    with tempfile.TemporaryDirectory(prefix="p3-005-schema-") as temporary_name:
        schema_path = Path(temporary_name) / "bom-1.6.schema.json"
        schema_path.write_bytes(schema_content)
        command = [
            "uvx",
            "--from",
            validator,
            "check-jsonschema",
            "--schemafile",
            str(schema_path),
        ] + [str(path) for path in paths]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise SecurityToolError(f"CycloneDX schema validation failed: {detail[:1000]}")


def validate_all(output_dir: Path, *, structural_only: bool = False) -> dict[str, Any]:
    policy = load_json(REPO_ROOT / ".github" / "security" / "sbom-policy.json")
    paths = {
        "backend": output_dir / "backend.cdx.json",
        "frontend": output_dir / "frontend.cdx.json",
        "combined": output_dir / "combined.cdx.json",
    }
    documents: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        document = load_json(path)
        if not isinstance(document, dict):
            raise SecurityToolError(f"{path.name}: SBOM must be an object")
        documents[name] = document
        results[name] = validate_document(document, path, policy)
    _validate_coverage(documents)
    combined_size = paths["combined"].stat().st_size
    if combined_size > int(policy["max_combined_bytes"]):
        raise SecurityToolError("combined SBOM exceeds 5 MiB budget")
    if not structural_only:
        _schema_validate(list(paths.values()), policy)
    return {
        "status": "PASS",
        "schema_validation": "NOT_RUN" if structural_only else "PASS",
        "backend_lock_coverage": "PASS",
        "frontend_lock_coverage": "PASS",
        "combined_size": combined_size,
        "forbidden_artifact_count": 0,
        "documents": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CycloneDX 1.6 SBOMs.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--structural-only", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_all(args.output_dir, structural_only=args.structural_only)
    except (SecurityToolError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"sbom_validation=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print(
        "sbom_validation=PASS schema={schema_validation} backend_coverage={backend_lock_coverage} "
        "frontend_coverage={frontend_lock_coverage} combined_bytes={combined_size} "
        "forbidden={forbidden_artifact_count}".format(**result)
    )
    for name, document in sorted(result["documents"].items()):
        print(
            f"sbom name={name} components={document['component_count']} "
            f"dependencies={document['dependency_count']} sha256={document['fingerprint']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
