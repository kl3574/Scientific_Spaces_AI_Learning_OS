from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from run_secret_audit import compile_rules, evaluate, scan_text  # noqa: E402


class SecretAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "sk-proj-" + "A" * 32
        self.rules = compile_rules(
            {
                "rules": [
                    {
                        "id": "openai-api-key",
                        "pattern": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
                    }
                ]
            }
        )

    def test_credible_match_blocks_without_logging_value(self) -> None:
        findings = scan_text("config.txt", f"token={self.secret}", self.rules)
        result = evaluate(findings, {"secret_suppressions": []})
        self.assertEqual(result["status"], "BLOCKED")
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn(self.secret, rendered)

    def test_test_fixture_is_reported_not_credible(self) -> None:
        findings = scan_text(
            "scripts/security/tests/fixture.txt", f"fake token={self.secret}", self.rules
        )
        result = evaluate(findings, {"secret_suppressions": []})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["findings"][0]["classification"], "synthetic_fixture")


if __name__ == "__main__":
    unittest.main()
