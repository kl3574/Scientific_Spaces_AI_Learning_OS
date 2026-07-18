from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SECURITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SECURITY_DIR))

from check_workflow_policy import inspect_all  # noqa: E402


SHA = "1" * 40


class WorkflowPolicyTests(unittest.TestCase):
    def _write(self, workflow: str) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        workflows = root / "workflows"
        workflows.mkdir()
        (workflows / "ci.yml").write_text(workflow, encoding="utf-8")
        pins = root / "pins.json"
        pins.write_text(
            json.dumps({"actions/checkout": {"sha": SHA}}), encoding="utf-8"
        )
        return temporary, workflows, pins

    def test_accepts_full_pin_and_explicit_permissions(self) -> None:
        temporary, workflows, pins = self._write(
            f"""name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    permissions:
      contents: read
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v4.3.1
"""
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["third_party_action_full_sha_pin_rate"], 1.0)
        self.assertEqual(result["workflow_permissions_explicit_rate"], 1.0)

    def test_rejects_mutable_pin_and_implicit_job_permissions(self) -> None:
        temporary, workflows, pins = self._write(
            """name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("mutable action ref" in item for item in result["findings"]))
        self.assertTrue(any("implicit permissions" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
