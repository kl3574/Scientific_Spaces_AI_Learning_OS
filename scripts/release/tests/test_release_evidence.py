from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


RELEASE_DIR = Path(__file__).resolve().parents[1]
SECURITY_DIR = RELEASE_DIR.parent / "security"
sys.path.insert(0, str(RELEASE_DIR))
sys.path.insert(0, str(SECURITY_DIR))

from build_release_evidence import build_evidence  # noqa: E402
from build_sbom import build_all  # noqa: E402
from common import SecurityToolError, write_canonical_json  # noqa: E402
from verify_release_evidence import verify  # noqa: E402


class ReleaseEvidenceTests(unittest.TestCase):
    def test_local_main_dry_run_never_authorizes_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            build_all(directory)
            evidence = build_evidence(
                tag="v1.1.0", sbom_dir=directory, dry_run=True, no_publish=True
            )
            self.assertEqual(evidence["boundary_status"], "PASS")
            self.assertFalse(evidence["publish_authorized"])
            self.assertFalse(evidence["would_authorize_publish"])
            path = directory / "release-evidence.json"
            write_canonical_json(path, evidence)
            result = verify(path, no_network=True)
            self.assertEqual(result["status"], "PASS")

    def test_branch_evidence_cannot_claim_publish_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            build_all(directory)
            evidence = build_evidence(
                tag="v1.1.0", sbom_dir=directory, dry_run=True, no_publish=True
            )
            evidence["would_authorize_publish"] = True
            path = directory / "release-evidence.json"
            write_canonical_json(path, evidence)
            with self.assertRaises(SecurityToolError):
                verify(path, no_network=True)


if __name__ == "__main__":
    unittest.main()
