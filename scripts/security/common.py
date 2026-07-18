from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]


class SecurityToolError(RuntimeError):
    """A fail-closed security tool error."""


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd or REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        raise SecurityToolError(
            f"command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{stderr}" if stderr else "")
        )
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SecurityToolError(f"invalid JSON: {path}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(ref: str = "HEAD") -> str:
    return run(["git", "rev-parse", f"{ref}^{{commit}}"]).stdout.strip()


def git_commit_timestamp(ref: str = "HEAD") -> str:
    epoch = int(run(["git", "show", "-s", "--format=%ct", ref]).stdout.strip())
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_relative_repository_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise SecurityToolError(f"path escapes repository: {path}") from exc


def sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted(set(values))
