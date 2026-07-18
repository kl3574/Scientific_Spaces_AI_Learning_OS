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
    def _write(
        self, workflow: str
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        workflows = root / "workflows"
        workflows.mkdir()
        (workflows / "ci.yml").write_text(workflow, encoding="utf-8")
        pins = root / "pins.json"
        pins.write_text(
            json.dumps({"actions/checkout": {"sha": SHA}}), encoding="utf-8"
        )
        tools = root / "tools.json"
        tools.write_text(json.dumps({"uv": "0.11.21"}), encoding="utf-8")
        return temporary, workflows, pins, tools

    def test_accepts_full_pin_and_explicit_permissions(self) -> None:
        temporary, workflows, pins, tools = self._write(
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
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["third_party_action_full_sha_pin_rate"], 1.0)
        self.assertEqual(result["workflow_permissions_explicit_rate"], 1.0)

    def test_rejects_mutable_pin_and_implicit_job_permissions(self) -> None:
        temporary, workflows, pins, tools = self._write(
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
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("mutable action ref" in item for item in result["findings"]))
        self.assertTrue(any("implicit permissions" in item for item in result["findings"]))

    def _release_workflow(self, condition: str, uv_install: str = "uv==0.11.21") -> str:
        return f"""name: CI
on: [push, workflow_dispatch]
permissions:
  contents: read
jobs:
  release_evidence:
    if: >-
      {condition}
    permissions:
      contents: read
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v4.3.1
      - run: python -m pip install {uv_install}
"""

    def test_accepts_manual_or_tag_push_release_condition(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "github.event_name == 'workflow_dispatch' || "
                "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v'))"
            )
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "PASS")

    def test_rejects_tag_gated_manual_dispatch(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "startsWith(github.ref, 'refs/tags/v') && "
                "(github.event_name == 'push' || github.event_name == 'workflow_dispatch')"
            )
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("manual dispatch OR tag push" in item for item in result["findings"]))

    def test_rejects_release_condition_without_tag_push_boundary(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow("github.event_name == 'workflow_dispatch'")
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")

    def test_rejects_manual_and_tag_push_condition(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "github.event_name == 'workflow_dispatch' && "
                "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v'))"
            )
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")

    def test_accepts_configured_uv_pin(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "github.event_name == 'workflow_dispatch' || "
                "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v'))"
            )
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(inspect_all(workflows, pins, tools)["status"], "PASS")

    def test_rejects_bare_uv_install(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "github.event_name == 'workflow_dispatch' || "
                "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v'))",
                uv_install="uv",
            )
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("uv install must be exactly pinned" in item for item in result["findings"]))

    def test_rejects_wrong_uv_pin(self) -> None:
        temporary, workflows, pins, tools = self._write(
            self._release_workflow(
                "github.event_name == 'workflow_dispatch' || "
                "(github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v'))",
                uv_install="uv==0.10.0",
            )
        )
        self.addCleanup(temporary.cleanup)
        result = inspect_all(workflows, pins, tools)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("uv install must be exactly pinned" in item for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
