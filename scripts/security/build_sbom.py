from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any, Iterable

from common import (
    REPO_ROOT,
    SecurityToolError,
    canonical_json_bytes,
    git_commit,
    git_commit_timestamp,
    sha256_bytes,
    sha256_file,
    write_canonical_json,
)
from lockfiles import LockedPackage, parse_package_lock, parse_uv_lock


GENERATOR_NAME = "scientific-spaces-p3-005-sbom-builder"
GENERATOR_VERSION = "1.0.0"
NAMESPACE = uuid.UUID("f142ec15-e6ce-43aa-b047-39c39bb47b2a")


def _component(package: LockedPackage) -> dict[str, Any]:
    component: dict[str, Any] = {
        "type": "library",
        "bom-ref": package.bom_ref,
        "name": package.name,
        "version": package.version,
        "scope": "required" if package.scope == "runtime" else "optional",
        "purl": package.purl,
        "properties": [
            {"name": "scientific-spaces:dependency-scope", "value": package.scope},
            {"name": "scientific-spaces:ecosystem", "value": package.ecosystem},
        ],
    }
    if package.digest_algorithm and package.digest:
        component["hashes"] = [
            {"alg": package.digest_algorithm, "content": package.digest}
        ]
    return component


def _application_component(metadata: dict[str, Any], source_lock: str) -> dict[str, Any]:
    return {
        "type": "application",
        "bom-ref": metadata["bom_ref"],
        "name": metadata["name"],
        "version": metadata["version"],
        "properties": [
            {"name": "scientific-spaces:source-lock", "value": source_lock}
        ],
    }


def _components(packages: Iterable[LockedPackage]) -> list[dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}
    identities: dict[str, tuple[str, str, str]] = {}
    hashes: dict[str, dict[str, str]] = {}
    for package in packages:
        ref = package.bom_ref
        identity = (package.ecosystem, package.name, package.version)
        if ref in identities and identities[ref] != identity:
            raise SecurityToolError(f"conflicting package identity for SBOM bom-ref: {ref}")
        identities[ref] = identity
        component = components.setdefault(ref, _component(package))
        if package.scope == "runtime":
            component["scope"] = "required"
            component["properties"][0]["value"] = "runtime"
        available_hashes = hashes.setdefault(ref, {})
        if package.digest_algorithm and package.digest:
            algorithm = package.digest_algorithm
            if algorithm in available_hashes and available_hashes[algorithm] != package.digest:
                raise SecurityToolError(f"conflicting {algorithm} hash for SBOM bom-ref: {ref}")
            available_hashes[algorithm] = package.digest
    for ref, component in components.items():
        if hashes[ref]:
            component["hashes"] = [
                {"alg": algorithm, "content": digest}
                for algorithm, digest in sorted(hashes[ref].items())
            ]
    return [components[ref] for ref in sorted(components)]


def _dependencies(
    packages: Iterable[LockedPackage], root_ref: str, direct: list[str]
) -> list[dict[str, Any]]:
    entries: dict[str, set[str]] = {root_ref: set(direct)}
    for package in packages:
        entries.setdefault(package.bom_ref, set()).update(package.dependencies)
    return [
        {"ref": ref, "dependsOn": sorted(dependencies)}
        for ref, dependencies in sorted(entries.items())
    ]


def _serial(identity: str) -> str:
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, identity)}"


def build_ecosystem_bom(
    *,
    packages: list[LockedPackage],
    metadata: dict[str, Any],
    source_lock: str,
    source_hash: str,
    commit: str,
    timestamp: str,
) -> dict[str, Any]:
    components = _components(packages)
    identity = sha256_bytes(
        canonical_json_bytes(
            {
                "commit": commit,
                "root": metadata["bom_ref"],
                "source_hash": source_hash,
                "components": [item["bom-ref"] for item in components],
            }
        )
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": _serial(identity),
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": _application_component(metadata, source_lock),
            "properties": [
                {"name": "scientific-spaces:generator", "value": GENERATOR_NAME},
                {"name": "scientific-spaces:generator-version", "value": GENERATOR_VERSION},
                {"name": "scientific-spaces:git-commit", "value": commit},
                {"name": "scientific-spaces:source-lock-sha256", "value": source_hash},
            ],
        },
        "components": components,
        "dependencies": _dependencies(
            packages, metadata["bom_ref"], metadata["direct_dependencies"]
        ),
    }


def build_combined_bom(
    backend: dict[str, Any], frontend: dict[str, Any], *, commit: str, timestamp: str
) -> dict[str, Any]:
    backend_root = backend["metadata"]["component"]
    frontend_root = frontend["metadata"]["component"]
    components_by_ref = {
        component["bom-ref"]: component
        for component in [backend_root, frontend_root]
        + backend["components"]
        + frontend["components"]
    }
    dependencies_by_ref: dict[str, set[str]] = {}
    for dependency in backend["dependencies"] + frontend["dependencies"]:
        dependencies_by_ref.setdefault(dependency["ref"], set()).update(
            dependency.get("dependsOn", [])
        )
    dependencies_by_ref["application:combined"] = {
        backend_root["bom-ref"],
        frontend_root["bom-ref"],
    }
    dependency_entries = [
        {"ref": ref, "dependsOn": sorted(values)}
        for ref, values in sorted(dependencies_by_ref.items())
    ]
    identity = sha256_bytes(
        canonical_json_bytes(
            {
                "backend_serial": backend["serialNumber"],
                "frontend_serial": frontend["serialNumber"],
                "commit": commit,
            }
        )
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": _serial(identity),
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": {
                "type": "application",
                "bom-ref": "application:combined",
                "name": "scientific-spaces-ai-learning-os",
                "version": "v1.1.0",
            },
            "properties": [
                {"name": "scientific-spaces:generator", "value": GENERATOR_NAME},
                {"name": "scientific-spaces:generator-version", "value": GENERATOR_VERSION},
                {"name": "scientific-spaces:git-commit", "value": commit},
                {"name": "scientific-spaces:backend-serial", "value": backend["serialNumber"]},
                {"name": "scientific-spaces:frontend-serial", "value": frontend["serialNumber"]},
            ],
        },
        "components": [components_by_ref[ref] for ref in sorted(components_by_ref)],
        "dependencies": dependency_entries,
    }


def build_all(output_dir: Path) -> dict[str, Any]:
    backend_lock = REPO_ROOT / "backend" / "uv.lock"
    frontend_lock = REPO_ROOT / "frontend" / "package-lock.json"
    python_packages, backend_metadata = parse_uv_lock(backend_lock)
    npm_packages, frontend_metadata = parse_package_lock(frontend_lock)
    commit = git_commit()
    timestamp = git_commit_timestamp()
    backend = build_ecosystem_bom(
        packages=python_packages,
        metadata=backend_metadata,
        source_lock="backend/uv.lock",
        source_hash=sha256_file(backend_lock),
        commit=commit,
        timestamp=timestamp,
    )
    frontend = build_ecosystem_bom(
        packages=npm_packages,
        metadata=frontend_metadata,
        source_lock="frontend/package-lock.json",
        source_hash=sha256_file(frontend_lock),
        commit=commit,
        timestamp=timestamp,
    )
    combined = build_combined_bom(backend, frontend, commit=commit, timestamp=timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "backend": output_dir / "backend.cdx.json",
        "frontend": output_dir / "frontend.cdx.json",
        "combined": output_dir / "combined.cdx.json",
    }
    for name, value in (("backend", backend), ("frontend", frontend), ("combined", combined)):
        write_canonical_json(paths[name], value)
    return {
        "commit": commit,
        "backend_components": len(backend["components"]),
        "frontend_components": len(frontend["components"]),
        "combined_components": len(combined["components"]),
        "fingerprints": {name: sha256_file(path) for name, path in paths.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic CycloneDX 1.6 SBOMs.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_all(args.output_dir)
    except (SecurityToolError, OSError, ValueError) as exc:
        print(f"sbom_build=BLOCKED reason={exc}")
        return 2
    print(
        "sbom_build=PASS backend={backend_components} frontend={frontend_components} "
        "combined={combined_components} commit={commit}".format(**result)
    )
    for name, fingerprint in sorted(result["fingerprints"].items()):
        print(f"sbom_fingerprint name={name} sha256={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
