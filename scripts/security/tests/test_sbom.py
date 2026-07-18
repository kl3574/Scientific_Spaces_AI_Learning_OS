from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from build_sbom import build_all  # noqa: E402
from common import SecurityToolError  # noqa: E402
from validate_sbom import validate_all  # noqa: E402


class SbomTests(unittest.TestCase):
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
