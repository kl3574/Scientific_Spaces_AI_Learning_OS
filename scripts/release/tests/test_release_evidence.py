from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_manual_branch_dry_run_records_non_authorization_reasons(self) -> None:
        environment = {
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/validation/p3-005-provenance",
            "GITHUB_WORKFLOW_REF": "local/ci.yml@refs/heads/validation/p3-005-provenance",
        }
        with patch.dict(os.environ, environment, clear=False):
            with tempfile.TemporaryDirectory() as directory_name:
                directory = Path(directory_name)
                build_all(directory)
                evidence = build_evidence(
                    tag="v1.1.0", sbom_dir=directory, dry_run=True, no_publish=True
                )
                self.assertEqual(evidence["boundary_status"], "PASS")
                self.assertFalse(evidence["conditions"]["exact_tag_ref"])
                self.assertFalse(
                    evidence["conditions"]["sbom_commit_matches_tag_target"]
                )
                self.assertFalse(evidence["would_authorize_publish"])
                self.assertFalse(evidence["publish_authorized"])
                self.assertTrue(
                    {
                        "exact_tag_ref",
                        "sbom_commit_matches_tag_target",
                        "p3-005-no-publish-policy",
                    }.issubset(evidence["non_authorization_reasons"])
                )
                path = directory / "release-evidence.json"
                write_canonical_json(path, evidence)
                self.assertEqual(verify(path, no_network=True)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
