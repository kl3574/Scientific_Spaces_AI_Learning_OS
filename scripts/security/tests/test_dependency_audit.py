from __future__ import annotations

import sys
import unittest
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from run_dependency_audit import evaluate_findings, merge_findings  # noqa: E402


class DependencyAuditTests(unittest.TestCase):
    def test_merges_aliases_across_scanners(self) -> None:
        base = {
            "ecosystem": "PyPI",
            "package": "example",
            "version": "1.0.0",
            "dependency_scope": "runtime",
            "suppression_id": None,
            "status": "unreviewed",
        }
        merged = merge_findings(
            [
                {
                    **base,
                    "advisory_id": "PYSEC-1",
                    "aliases": ["GHSA-aaaa-bbbb-cccc"],
                    "severity": "UNKNOWN",
                    "sources": ["pip-audit"],
                },
                {
                    **base,
                    "advisory_id": "GHSA-aaaa-bbbb-cccc",
                    "aliases": ["PYSEC-1"],
                    "severity": "HIGH",
                    "sources": ["osv"],
                },
            ]
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["severity"], "HIGH")
        self.assertEqual(merged[0]["sources"], ["osv", "pip-audit"])

    def test_medium_blocks_without_exact_suppression(self) -> None:
        finding = {
            "ecosystem": "npm",
            "package": "example",
            "version": "1.0.0",
            "advisory_id": "GHSA-aaaa-bbbb-cccc",
            "aliases": [],
            "severity": "MEDIUM",
            "dependency_scope": "dev",
            "suppression_id": None,
            "status": "unreviewed",
            "sources": ["osv"],
        }
        policy = {"blocking": {"runtime": ["MEDIUM"], "dev": ["MEDIUM"]}}
        result = evaluate_findings(
            [finding], policy, {"dependency_suppressions": []}
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["findings"][0]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
