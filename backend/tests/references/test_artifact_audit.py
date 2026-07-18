from __future__ import annotations

import subprocess
from pathlib import Path

from app.references.audit import _runtime_absolute_path_count, audit_repository_artifacts


def test_store_path_audit_distinguishes_source_examples_from_runtime_paths(tmp_path: Path) -> None:
    generic_source_path = "/" + "home/you/python/lib/site-packages"
    public_url = "https://sites.example" + "/" + "home/blog/article"
    source_text = (
        f"{public_url} "
        f"{generic_source_path}"
    )

    assert _runtime_absolute_path_count(source_text, roots=(tmp_path,)) == 0
    assert _runtime_absolute_path_count(f"runtime={tmp_path}/private.json", roots=(tmp_path,)) == 1


def test_artifact_audit_separates_legacy_paths_from_current_changes(tmp_path: Path) -> None:
    _init_repository(tmp_path)
    legacy_path = "/" + "home/example/input.json"
    (tmp_path / ".env.example").write_text("EXAMPLE_TOKEN=replace-me\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"Legacy example: {legacy_path}\n", encoding="utf-8")
    _git(tmp_path, "add", ".env.example", "README.md")
    _git(tmp_path, "commit", "-m", "baseline")

    baseline = audit_repository_artifacts(tmp_path, tmp_path / ".local_data" / "references")

    assert baseline.status == "PASS"
    assert baseline.tracked_runtime_private_artifact_count == 0
    assert baseline.local_absolute_path_count == 0
    assert baseline.baseline_local_absolute_path_count == 1

    (tmp_path / "README.md").write_text(
        f"Legacy example: {legacy_path}\nUnrelated current edit.\n",
        encoding="utf-8",
    )
    modified_baseline = audit_repository_artifacts(tmp_path, tmp_path / ".local_data" / "references")
    assert modified_baseline.status == "PASS"
    assert modified_baseline.baseline_local_absolute_path_count == 1

    docs = tmp_path / "docs"
    docs.mkdir()
    current_path = "/" + "home/example/private.json"
    (docs / "new.md").write_text(f"Do not commit {current_path}\n", encoding="utf-8")

    changed = audit_repository_artifacts(tmp_path, tmp_path / ".local_data" / "references")

    assert changed.status == "BLOCKED"
    assert changed.local_absolute_path_count == 1
    assert changed.findings == [{"kind": "local_absolute_path", "path": "docs/new.md"}]


def test_artifact_audit_blocks_tracked_env_and_untracked_secret(tmp_path: Path) -> None:
    _init_repository(tmp_path)
    (tmp_path / "README.md").write_text("safe\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "baseline")
    (tmp_path / ".env").write_text("TOKEN=not-a-real-secret\n", encoding="utf-8")
    _git(tmp_path, "add", "-f", ".env")
    docs = tmp_path / "docs"
    docs.mkdir()
    synthetic_secret = "sk-proj-" + "abcdefghijklmnopqrstuvwxyz1234"
    (docs / "new.md").write_text(f"token {synthetic_secret}\n", encoding="utf-8")

    result = audit_repository_artifacts(tmp_path, tmp_path / ".local_data" / "references")

    assert result.status == "BLOCKED"
    assert result.tracked_runtime_private_artifact_count == 1
    assert result.secret_pattern_count == 1


def _init_repository(path: Path) -> None:
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "Reference Audit Test")
    _git(path, "config", "user.email", "reference-audit@example.invalid")


def _git(path: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=path, check=True, capture_output=True)
