from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from build_sbom import build_all, build_combined_bom, build_ecosystem_bom  # noqa: E402
from common import SecurityToolError, canonical_json_bytes, sha256_bytes  # noqa: E402
from lockfiles import LockedPackage, parse_package_lock, parse_uv_lock  # noqa: E402
from validate_sbom import validate_all  # noqa: E402


class SbomTests(unittest.TestCase):
    def parse_npm_fixture(self, records: dict, root: dict | None = None):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "package-lock.json"
            path.write_text(json.dumps({"lockfileVersion": 3, "packages": {
                "": {"name": "fixture", "version": "1", **(root or {})}, **records,
            }}), encoding="utf-8")
            return parse_package_lock(path)

    def test_current_lock_bundled_and_root_consumers_keep_distinct_ancestors(self) -> None:
        packages, _ = parse_package_lock(SECURITY_DIR.parents[1] / "frontend/package-lock.json")
        self.assertEqual(len(packages), 245)
        inventory = [(p.bom_ref, p.ecosystem, p.name, p.version, p.scope, p.digest_algorithm, p.digest)
                     for p in packages]
        self.assertEqual(sha256_bytes(canonical_json_bytes(inventory)),
                         "c60f9a470c9f2782f2843d1078a3f764ed781bf7ace717ab79adf388bfbd907d")
        for name, version, expected, rejected in (
            ("@napi-rs/wasm-runtime", "1.0.7", "1.6.0", "1.11.3"),
            ("@img/sharp-wasm32", "0.35.4", "1.11.3", "1.6.0"),
        ):
            with self.subTest(importer=name):
                package = next(p for p in packages if p.name == name and p.version == version)
                self.assertIn("pkg:npm/%40emnapi/runtime@" + expected, package.dependencies)
                self.assertNotIn("pkg:npm/%40emnapi/runtime@" + rejected, package.dependencies)

    def test_scoped_dependency_uses_each_nearest_legal_node_ancestor(self) -> None:
        importer = "node_modules/@outer/host/node_modules/@inner/consumer"
        # Node's installed _nodeModulePaths order, bounded at the lock root.
        candidates = [
            importer + "/node_modules/@dep/target",
            "node_modules/@outer/host/node_modules/@inner/node_modules/@dep/target",
            "node_modules/@outer/host/node_modules/@dep/target",
            "node_modules/@outer/node_modules/@dep/target",
            "node_modules/@dep/target",
        ]
        for nearest in range(len(candidates)):
            with self.subTest(nearest=nearest):
                records = {importer: {"version": "1", "dependencies": {"@dep/target": "*"}},
                           "node_modules/unrelated/node_modules/@dep/target": {"version": "99"},
                           "node_modules/@outer/host/node_modules/node_modules/@dep/target": {"version": "98"}}
                records.update({path: {"version": str(index + 1)}
                                for index, path in enumerate(candidates) if index >= nearest})
                packages, _ = self.parse_npm_fixture(records)
                consumer = next(p for p in packages if p.name == "@inner/consumer")
                self.assertEqual(consumer.dependencies, (f"pkg:npm/%40dep/target@{nearest + 1}",))
                self.assertEqual(len(packages), len(records))

    def test_root_direct_dependencies_do_not_resolve_into_another_branch(self) -> None:
        packages, metadata = self.parse_npm_fixture({
            "node_modules/@dep/target": {"version": "1"},
            "node_modules/other/node_modules/@dep/target": {"version": "9"},
        }, {"dependencies": {"@dep/target": "*"}})
        self.assertEqual(metadata["direct_dependencies"], ["pkg:npm/%40dep/target@1"])
        self.assertEqual(len(packages), 2)

    def test_missing_required_dependencies_reject_unrelated_same_name(self) -> None:
        for owner in ("package", "root_dependencies", "root_devDependencies"):
            for unrelated in (False, True):
                with self.subTest(owner=owner, unrelated=unrelated):
                    records = {"node_modules/importer": {"version": "1"}}
                    root = {}
                    if owner == "package":
                        records["node_modules/importer"]["dependencies"] = {"target": "*"}
                    else:
                        root[owner.removeprefix("root_")] = {"target": "*"}
                    if unrelated:
                        records["node_modules/unrelated/node_modules/target"] = {"version": "9"}
                    with self.assertRaisesRegex(SecurityToolError, "unresolved npm dependency: target"):
                        self.parse_npm_fixture(records, root)

    def test_optional_omissions_use_legal_reachability_and_preserve_inventory(self) -> None:
        importer = "node_modules/branch/node_modules/@scope/importer"
        for field in ("dependencies", "optionalDependencies"):
            for unrelated in (False, True):
                for reachable in (False, True):
                    with self.subTest(field=field, unrelated=unrelated, reachable=reachable):
                        owner = {"version": "1", field: {"target": "*", "kept": "*"}}
                        if field == "dependencies":
                            owner["optional"] = True
                        records = {importer: owner, "node_modules/kept": {"version": "1"}}
                        if unrelated:
                            records["node_modules/unrelated/node_modules/target"] = {"version": "9", "dev": True}
                        if reachable:
                            records["node_modules/branch/node_modules/target"] = {"version": "2"}
                        packages, _ = self.parse_npm_fixture(records)
                        consumer = next(p for p in packages if p.name == "@scope/importer")
                        expected = ("pkg:npm/kept@1", "pkg:npm/target@2") if reachable else ("pkg:npm/kept@1",)
                        self.assertEqual(consumer.dependencies, expected)
                        self.assertEqual(len(packages), len(records))
                        if unrelated:
                            other = next(p for p in packages if p.name == "target" and p.version == "9")
                            self.assertEqual(other.scope, "dev")

    def test_current_frontend_and_combined_edges_change_without_component_drift(self) -> None:
        root = SECURITY_DIR.parents[1]
        npm_packages, npm_metadata = parse_package_lock(root / "frontend/package-lock.json")
        python_packages, python_metadata = parse_uv_lock(root / "backend/uv.lock")
        documents = {}
        for name, packages, metadata, source_lock in (
            ("frontend", npm_packages, npm_metadata, "frontend/package-lock.json"),
            ("backend", python_packages, python_metadata, "backend/uv.lock"),
        ):
            documents[name] = build_ecosystem_bom(
                packages=packages, metadata=metadata, source_lock=source_lock,
                source_hash="b" * 64, commit="c" * 40, timestamp="2026-09-09T00:00:00Z",
            )
        documents["combined"] = build_combined_bom(
            documents["backend"], documents["frontend"], commit="c" * 40, timestamp="2026-09-09T00:00:00Z",
        )
        expected = {
            "frontend": (244, 245, "914b8c1b8e7b920fb44aed6809d68664f7ec0c6a2a6a3fc6655f73d8a858ac12"),
            "combined": (286, 287, "49cbd10a5bae0d89109c6a8d1d6229d97729facd8c8d84a4eb0a960d1e62ccb9"),
        }
        for name, (component_count, dependency_count, component_hash) in expected.items():
            with self.subTest(document=name):
                document = documents[name]
                self.assertEqual(len(document["components"]), component_count)
                self.assertEqual(len(document["dependencies"]), dependency_count)
                self.assertEqual(sha256_bytes(canonical_json_bytes(document["components"])), component_hash)
                edges = {entry["ref"]: entry["dependsOn"] for entry in document["dependencies"]}
                self.assertIn("pkg:npm/%40emnapi/runtime@1.6.0", edges["pkg:npm/%40napi-rs/wasm-runtime@1.0.7"])
                self.assertNotIn("pkg:npm/%40emnapi/runtime@1.11.3", edges["pkg:npm/%40napi-rs/wasm-runtime@1.0.7"])
                self.assertIn("pkg:npm/%40emnapi/runtime@1.11.3", edges["pkg:npm/%40img/sharp-wasm32@0.35.4"])

    def ecosystem_bom(self, packages: list[LockedPackage]) -> dict:
        return build_ecosystem_bom(
            packages=packages,
            metadata={
                "name": "fixture", "version": "1", "bom_ref": "application:fixture",
                "direct_dependencies": [packages[0].bom_ref],
            },
            source_lock="fixture.lock", source_hash="b" * 64,
            commit="c" * 40, timestamp="2026-09-09T00:00:00Z",
        )

    def test_duplicate_free_output_is_unchanged(self) -> None:
        package = LockedPackage("npm", "example", "1.0.0", "dev", (), "SHA-256", "a" * 64)
        document = self.ecosystem_bom([package])
        self.assertEqual(
            sha256_bytes(canonical_json_bytes(document)),
            "9ea30ccb9e04599d75efc8f4647d972459cefdb0475ea519fd1a1772f4b71145",
        )

    def test_duplicate_occurrences_retain_hash_edges_and_runtime_scope(self) -> None:
        root = LockedPackage(
            "npm", "example", "1.0.0", "runtime", ("pkg:npm/left@1",),
            "SHA-256", "a" * 64,
        )
        bundled = replace(
            root, scope="dev", dependencies=("pkg:npm/right@1",),
            digest_algorithm=None, digest=None,
        )
        document = self.ecosystem_bom([root, bundled])
        self.assertEqual(len(document["components"]), 1)
        component = document["components"][0]
        self.assertEqual(component["hashes"], [{"alg": "SHA-256", "content": "a" * 64}])
        self.assertEqual(component["scope"], "required")
        self.assertIn(
            {"name": "scientific-spaces:dependency-scope", "value": "runtime"},
            component["properties"],
        )
        entries = [entry for entry in document["dependencies"] if entry["ref"] == root.bom_ref]
        self.assertEqual(entries, [{"ref": root.bom_ref, "dependsOn": ["pkg:npm/left@1", "pkg:npm/right@1"]}])
        self.assertEqual(document, self.ecosystem_bom([bundled, root]))

    def test_hashes_are_merged_without_losing_available_algorithms(self) -> None:
        package = LockedPackage("npm", "example", "1.0.0", "dev", (), "SHA-256", "a" * 64)
        other_hash = replace(package, digest_algorithm="SHA-512", digest="d" * 128)
        expected = [
            {"alg": "SHA-256", "content": "a" * 64},
            {"alg": "SHA-512", "content": "d" * 128},
        ]
        document = self.ecosystem_bom([package, package, other_hash])
        self.assertEqual(document["components"][0]["hashes"], expected)
        self.assertEqual(len(document["components"]), 1)
        self.assertEqual(document, self.ecosystem_bom([other_hash, package, package]))

    def test_conflicting_hashes_are_rejected_in_both_orders(self) -> None:
        package = LockedPackage("npm", "example", "1.0.0", "dev", (), "SHA-256", "a" * 64)
        conflict = replace(package, digest="d" * 64)
        for packages in ([package, conflict], [conflict, package]):
            with self.subTest(first_digest=packages[0].digest):
                with self.assertRaisesRegex(SecurityToolError, "conflicting SHA-256 hash"):
                    self.ecosystem_bom(packages)

    def test_conflicting_identity_is_rejected_in_both_orders(self) -> None:
        package = LockedPackage("PyPI", "example_name", "1.0.0", "dev", ())
        conflict = replace(package, name="example-name")
        self.assertEqual(package.bom_ref, conflict.bom_ref)
        for packages in ([package, conflict], [conflict, package]):
            with self.subTest(first_name=packages[0].name):
                with self.assertRaisesRegex(SecurityToolError, "conflicting package identity"):
                    self.ecosystem_bom(packages)

    def test_distinct_versions_and_ecosystems_remain_separate(self) -> None:
        package = LockedPackage("npm", "example", "1.0.0", "dev", ())
        packages = [package, replace(package, version="2.0.0"), replace(package, ecosystem="PyPI")]
        document = self.ecosystem_bom(packages)
        self.assertEqual(
            [component["bom-ref"] for component in document["components"]],
            ["pkg:npm/example@1.0.0", "pkg:npm/example@2.0.0", "pkg:pypi/example@1.0.0"],
        )
        self.assertEqual(len(document["dependencies"]), 4)

    def test_current_lock_occurrences_keep_hashes_in_ecosystem_and_combined(self) -> None:
        packages, _ = parse_package_lock(SECURITY_DIR.parents[1] / "frontend/package-lock.json")
        occurrences = [package for package in packages if package.bom_ref == "pkg:npm/tslib@2.8.1"]
        self.assertGreater(len(occurrences), 1)
        hashed = next(package for package in occurrences if package.digest)
        self.assertTrue(any(package.digest is None for package in occurrences))
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            build_all(directory)
            self.assertEqual(validate_all(directory, structural_only=True)["status"], "PASS")
            for name in ("frontend", "combined"):
                with self.subTest(bom=name):
                    document = json.loads((directory / f"{name}.cdx.json").read_text())
                    components = [item for item in document["components"] if item["bom-ref"] == hashed.bom_ref]
                    self.assertEqual(len(components), 1)
                    self.assertIn(
                        {"alg": hashed.digest_algorithm, "content": hashed.digest},
                        components[0]["hashes"],
                    )
                    refs = [entry["ref"] for entry in document["dependencies"]]
                    self.assertEqual(len(refs), len(set(refs)))

    def test_build_is_deterministic_and_structurally_valid(self) -> None:
        with tempfile.TemporaryDirectory() as first_name, tempfile.TemporaryDirectory() as second_name:
            first = Path(first_name)
            second = Path(second_name)
            first_result = build_all(first)
            second_result = build_all(second)
            self.assertEqual(first_result["fingerprints"], second_result["fingerprints"])
            validation = validate_all(first, structural_only=True)
            self.assertEqual(validation["status"], "PASS")
            self.assertEqual(validation["forbidden_artifact_count"], 0)

    def test_absolute_private_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            build_all(directory)
            path = directory / "backend.cdx.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["metadata"]["properties"].append(
                {"name": "bad", "value": "/home/example/private.db"}
            )
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(SecurityToolError):
                validate_all(directory, structural_only=True)


if __name__ == "__main__":
    unittest.main()
