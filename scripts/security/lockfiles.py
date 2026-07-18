from __future__ import annotations

import base64
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from common import SecurityToolError


@dataclass(frozen=True)
class LockedPackage:
    ecosystem: str
    name: str
    version: str
    scope: str
    dependencies: tuple[str, ...]
    digest_algorithm: str | None = None
    digest: str | None = None

    @property
    def purl(self) -> str:
        if self.ecosystem == "PyPI":
            normalized = self.name.lower().replace("_", "-")
            return f"pkg:pypi/{quote(normalized, safe='')}@{quote(self.version, safe='')}"
        if self.ecosystem == "npm":
            return f"pkg:npm/{quote(self.name, safe='/')}@{quote(self.version, safe='')}"
        raise SecurityToolError(f"unsupported ecosystem: {self.ecosystem}")

    @property
    def bom_ref(self) -> str:
        return self.purl


_UV_NAME = re.compile(r'^name = "([^"]+)"$', re.MULTILINE)
_UV_VERSION = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
_UV_HASH = re.compile(r'hash = "sha256:([0-9a-fA-F]{64})"')
_UV_DEP = re.compile(
    r'\{\s*name = "([^"]+)"(?:,\s*version = "([^"]+)")?[^}]*\}'
)


def _first_uv_dependency_list(block: str) -> list[tuple[str, str | None]]:
    lines = block.splitlines()
    collecting = False
    payload: list[str] = []
    for line in lines:
        if not collecting and line == "dependencies = [":
            collecting = True
            continue
        if collecting and line == "]":
            break
        if collecting:
            payload.append(line)
    return [(match.group(1), match.group(2)) for match in _UV_DEP.finditer("\n".join(payload))]


def _uv_optional_dev_dependencies(block: str) -> list[tuple[str, str | None]]:
    marker = "[package.optional-dependencies]\n"
    if marker not in block:
        return []
    tail = block.split(marker, 1)[1]
    match = re.search(r"^dev = \[\n(?P<body>.*?)^\]$", tail, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    return [
        (item.group(1), item.group(2)) for item in _UV_DEP.finditer(match.group("body"))
    ]


def parse_uv_lock(path: Path) -> tuple[list[LockedPackage], dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SecurityToolError(f"cannot read uv lock: {path}") from exc

    raw_blocks = text.split("[[package]]")[1:]
    records: list[dict[str, Any]] = []
    for block in raw_blocks:
        name_match = _UV_NAME.search(block)
        version_match = _UV_VERSION.search(block)
        if not name_match or not version_match:
            raise SecurityToolError("uv.lock package is missing name or version")
        name = name_match.group(1)
        version = version_match.group(1)
        dependencies = _first_uv_dependency_list(block)
        records.append(
            {
                "name": name,
                "version": version,
                "dependencies": dependencies,
                "dev_dependencies": _uv_optional_dev_dependencies(block),
                "digest": (_UV_HASH.search(block).group(1) if _UV_HASH.search(block) else None),
                "editable": 'source = { editable = "." }' in block,
            }
        )

    roots = [record for record in records if record["editable"]]
    if len(roots) != 1:
        raise SecurityToolError(f"expected one editable uv root, found {len(roots)}")
    root = roots[0]

    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not record["editable"]:
            by_name[record["name"]].append(record)

    def resolve(name: str, version: str | None) -> dict[str, Any]:
        candidates = by_name.get(name, [])
        if version:
            candidates = [record for record in candidates if record["version"] == version]
        if len(candidates) != 1:
            raise SecurityToolError(
                f"cannot uniquely resolve uv dependency {name}"
                + (f"=={version}" if version else "")
            )
        return candidates[0]

    runtime_keys: set[tuple[str, str]] = set()
    dev_keys: set[tuple[str, str]] = set()

    def traverse(
        seeds: list[tuple[str, str | None]], target: set[tuple[str, str]]
    ) -> None:
        queue = deque(seeds)
        while queue:
            name, version = queue.popleft()
            record = resolve(name, version)
            key = (record["name"], record["version"])
            if key in target:
                continue
            target.add(key)
            queue.extend(record["dependencies"])

    traverse(root["dependencies"], runtime_keys)
    traverse(root["dev_dependencies"], dev_keys)

    packages: list[LockedPackage] = []
    for record in records:
        if record["editable"]:
            continue
        key = (record["name"], record["version"])
        scope = "runtime" if key in runtime_keys else "dev"
        dependency_refs = []
        for name, version in record["dependencies"]:
            resolved = resolve(name, version)
            dependency_refs.append(
                LockedPackage(
                    "PyPI", resolved["name"], resolved["version"], scope, ()
                ).bom_ref
            )
        packages.append(
            LockedPackage(
                ecosystem="PyPI",
                name=record["name"],
                version=record["version"],
                scope=scope,
                dependencies=tuple(sorted(set(dependency_refs))),
                digest_algorithm="SHA-256" if record["digest"] else None,
                digest=record["digest"],
            )
        )

    direct = []
    for name, version in root["dependencies"]:
        resolved = resolve(name, version)
        direct.append(LockedPackage("PyPI", resolved["name"], resolved["version"], "runtime", ()).bom_ref)
    for name, version in root["dev_dependencies"]:
        resolved = resolve(name, version)
        direct.append(LockedPackage("PyPI", resolved["name"], resolved["version"], "dev", ()).bom_ref)

    metadata = {
        "name": root["name"],
        "version": root["version"],
        "bom_ref": "application:backend",
        "direct_dependencies": sorted(set(direct)),
    }
    return sorted(packages, key=lambda item: (item.name, item.version)), metadata


def _npm_name_from_path(path: str) -> str:
    marker = "node_modules/"
    if marker not in path:
        raise SecurityToolError(f"invalid npm package path: {path}")
    return path.rsplit(marker, 1)[1]


def _npm_digest(integrity: str | None) -> tuple[str | None, str | None]:
    if not integrity or "-" not in integrity:
        return None, None
    algorithm, encoded = integrity.split("-", 1)
    algorithm_map = {"sha256": "SHA-256", "sha384": "SHA-384", "sha512": "SHA-512"}
    if algorithm not in algorithm_map:
        return None, None
    try:
        return algorithm_map[algorithm], base64.b64decode(encoded).hex()
    except ValueError:
        return None, None


def parse_package_lock(path: Path) -> tuple[list[LockedPackage], dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SecurityToolError(f"invalid npm lock: {path}") from exc
    if data.get("lockfileVersion") != 3 or not isinstance(data.get("packages"), dict):
        raise SecurityToolError("frontend package-lock.json must use lockfileVersion 3")

    raw_packages: dict[str, dict[str, Any]] = {
        key: value
        for key, value in data["packages"].items()
        if key and key.startswith("node_modules/") and isinstance(value, dict)
    }
    name_to_paths: dict[str, list[str]] = defaultdict(list)
    for package_path in raw_packages:
        name_to_paths[_npm_name_from_path(package_path)].append(package_path)

    def resolve_dependency(parent_path: str, dependency_name: str) -> str:
        candidate = f"{parent_path}/node_modules/{dependency_name}"
        if candidate in raw_packages:
            return candidate
        candidates = name_to_paths.get(dependency_name, [])
        if not candidates:
            raise SecurityToolError(f"unresolved npm dependency: {dependency_name}")
        return sorted(candidates, key=lambda item: (item.count("node_modules/"), len(item)))[0]

    path_to_ref: dict[str, str] = {}
    for package_path, package in raw_packages.items():
        name = package.get("name") or _npm_name_from_path(package_path)
        version = package.get("version")
        if not isinstance(version, str) or not version:
            raise SecurityToolError(f"npm package is missing version: {package_path}")
        path_to_ref[package_path] = LockedPackage("npm", name, version, "dev", ()).bom_ref

    packages: list[LockedPackage] = []
    for package_path, package in raw_packages.items():
        name = package.get("name") or _npm_name_from_path(package_path)
        version = package["version"]
        dependency_names = set((package.get("dependencies") or {}).keys())
        optional_names = set((package.get("optionalDependencies") or {}).keys())
        dependency_refs = []
        for dependency_name in sorted(dependency_names):
            if package.get("optional") is True and dependency_name not in name_to_paths:
                continue
            dependency_refs.append(
                path_to_ref[resolve_dependency(package_path, dependency_name)]
            )
        for dependency_name in sorted(optional_names):
            if dependency_name not in name_to_paths:
                continue
            dependency_refs.append(
                path_to_ref[resolve_dependency(package_path, dependency_name)]
            )
        algorithm, digest = _npm_digest(package.get("integrity"))
        packages.append(
            LockedPackage(
                ecosystem="npm",
                name=name,
                version=version,
                scope="dev" if package.get("dev") is True else "runtime",
                dependencies=tuple(sorted(set(dependency_refs))),
                digest_algorithm=algorithm,
                digest=digest,
            )
        )

    root = data["packages"].get("")
    if not isinstance(root, dict):
        raise SecurityToolError("npm lock is missing root package")
    direct_names = set((root.get("dependencies") or {}).keys())
    direct_names.update((root.get("devDependencies") or {}).keys())
    direct_refs = [
        path_to_ref[resolve_dependency("", name)] for name in sorted(direct_names)
    ]
    metadata = {
        "name": root.get("name") or data.get("name") or "frontend",
        "version": root.get("version") or data.get("version") or "0",
        "bom_ref": "application:frontend",
        "direct_dependencies": sorted(set(direct_refs)),
    }
    return sorted(packages, key=lambda item: (item.name, item.version)), metadata
