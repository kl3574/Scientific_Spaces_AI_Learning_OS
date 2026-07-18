from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from validate_suppressions import validate  # noqa: E402


class SuppressionValidationTests(unittest.TestCase):
    def test_empty_policy_passes(self) -> None:
        result = validate(
            {
                "schema_version": 1,
                "dependency_suppressions": [],
                "secret_suppressions": [],
            },
            today=date(2026, 7, 18),
            dependency_findings=[],
            secret_findings=[],
        )
        self.assertEqual(result["status"], "PASS")

    def test_expired_or_unmatched_dependency_suppression_blocks(self) -> None:
        suppression = {
            "id": "DEP-1",
            "ecosystem": "PyPI",
            "package": "example",
            "advisory_id": "OSV-1",
            "scope": "runtime",
            "reason": "documented false positive",
            "owner": "security-owner",
            "tracking_url": "https://example.invalid/DEP-1",
            "created_at": "2026-01-01",
            "review_after": "2026-02-01",
            "expires_at": "2026-03-01",
        }
        result = validate(
            {
                "schema_version": 1,
                "dependency_suppressions": [suppression],
                "secret_suppressions": [],
            },
            today=date(2026, 7, 18),
            dependency_findings=[],
            secret_findings=[],
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("expired" in item for item in result["findings"]))
        self.assertTrue(any("unmatched" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
