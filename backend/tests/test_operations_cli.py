from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.operations_helpers import make_local_data_root

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / script), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_audit_cli_writes_unified_manifest(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    result = _run("scripts/ops/audit_local_data.py", "--data-root", str(root), "--workers", "4")
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "PASS"
    assert payload["manifest"]["deterministic_fingerprint"]
    assert (root / "operations/local_data_manifest.json").is_file()


def test_complete_backup_cli_requires_explicit_pdf_policy(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    result = _run(
        "scripts/ops/backup_local_data.py",
        "--data-root",
        str(root),
        "--output-dir",
        str(tmp_path / "backups"),
        "--profile",
        "complete",
    )

    assert result.returncode != 0
    assert "--include-pdf or --exclude-pdf" in result.stderr


def test_backup_verify_restore_clis_round_trip_fixture(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    backup = _run(
        "scripts/ops/backup_local_data.py",
        "--data-root",
        str(root),
        "--output-dir",
        str(tmp_path / "backups"),
        "--profile",
        "essential",
        "--verify",
        "--workers",
        "4",
    )
    backup_payload = json.loads(backup.stdout)
    archive = backup_payload["archive_path"]
    verification = _run("scripts/ops/verify_local_backup.py", "--backup", archive, "--workers", "4")
    restore = _run(
        "scripts/ops/restore_local_backup.py",
        "--backup",
        archive,
        "--target-dir",
        str(tmp_path / "restore"),
        "--protected-data-root",
        str(root),
        "--verify",
        "--workers",
        "4",
    )

    assert backup.returncode == 0, backup.stderr
    assert verification.returncode == 0, verification.stderr
    assert json.loads(verification.stdout)["status"] == "PASS"
    assert restore.returncode == 0, restore.stderr
    assert json.loads(restore.stdout)["status"] == "PASS"


def test_cleanup_cli_defaults_to_dry_run(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    cache_file = root / "cache/transient.cache"

    result = _run(
        "scripts/ops/cleanup_local_data.py",
        "--data-root",
        str(root),
        "--category",
        "browser-cache",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stderr
    assert payload["dry_run"] is True
    assert cache_file.exists()


def test_health_cli_reports_pass_for_consistent_fixture(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    audit = _run("scripts/ops/audit_local_data.py", "--data-root", str(root))
    assert audit.returncode == 0, audit.stderr
    env = os.environ.copy()
    env.update(
        {
            "SCIENTIFIC_SPACES_ARTICLE_STORE": str(root / "corpus/pilot/article_store/articles.json"),
            "SCIENTIFIC_SPACES_RAG_INDEX_DIR": str(root / "rag/full_corpus"),
            "SCIENTIFIC_SPACES_GRAPH_FILE": str(root / "graph/full_corpus/graph.json"),
        }
    )

    result = _run("scripts/ops/check_local_system.py", "--data-root", str(root), "--workers", "4", env=env)
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "PASS"
