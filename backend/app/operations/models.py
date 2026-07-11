from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetRecord:
    asset_type: str
    relative_path: str
    tier: str
    size_bytes: int
    record_count: int | None
    fingerprint: str | None
    source_fingerprint: str | None
    schema_version: str
    rebuild_command: str | None
    required_for_restore: bool
    contains_user_data: bool
    backup_priority: int
    exists: bool
    file_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AssetRecord:
        return cls(**{name: payload.get(name) for name in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LocalDataManifest:
    schema_version: int
    generated_at: str
    deterministic_fingerprint: str
    assets: tuple[AssetRecord, ...]
    manifest_path: str = field(default="", repr=False, compare=False)

    def fingerprint_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assets": [asset.to_dict() for asset in self.assets],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.fingerprint_payload(),
            "generated_at": self.generated_at,
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }


@dataclass(frozen=True)
class OperationIssue:
    issue_code: str
    message: str
    severity: str = "BLOCKED"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class BackupVerificationResult:
    status: str
    archive_path: Path
    profile: str | None
    pdf_included: bool | None
    file_count: int
    issues: tuple[OperationIssue, ...]
    asset_fingerprints: dict[str, str]
    asset_record_counts: dict[str, int | None]

    @property
    def issue_codes(self) -> tuple[str, ...]:
        return tuple(issue.issue_code for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "archive_path": str(self.archive_path),
            "profile": self.profile,
            "pdf_included": self.pdf_included,
            "file_count": self.file_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "asset_fingerprints": dict(sorted(self.asset_fingerprints.items())),
            "asset_record_counts": dict(sorted(self.asset_record_counts.items())),
        }


@dataclass(frozen=True)
class BackupResult:
    status: str
    archive_path: Path
    profile: str
    pdf_included: bool
    file_count: int
    source_manifest_fingerprint: str
    asset_fingerprints: dict[str, str]
    verification: BackupVerificationResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "archive_path": str(self.archive_path),
            "profile": self.profile,
            "pdf_included": self.pdf_included,
            "file_count": self.file_count,
            "source_manifest_fingerprint": self.source_manifest_fingerprint,
            "asset_fingerprints": dict(sorted(self.asset_fingerprints.items())),
            "verification": self.verification.to_dict() if self.verification else None,
        }


@dataclass(frozen=True)
class RestoreResult:
    status: str
    target_dir: Path
    file_count: int
    restored_asset_counts: dict[str, int | None]
    restored_fingerprints: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "target_dir": str(self.target_dir),
            "file_count": self.file_count,
            "restored_asset_counts": dict(sorted(self.restored_asset_counts.items())),
            "restored_fingerprints": dict(sorted(self.restored_fingerprints.items())),
        }


@dataclass(frozen=True)
class CleanupResult:
    status: str
    dry_run: bool
    categories: tuple[str, ...]
    candidate_paths: tuple[Path, ...]
    deleted_paths: tuple[Path, ...]
    reclaimed_bytes: int

    def to_dict(self, *, data_root: Path | None = None) -> dict[str, Any]:
        def display(path: Path) -> str:
            if data_root is None:
                return str(path)
            try:
                return path.relative_to(data_root).as_posix()
            except ValueError:
                return str(path)

        return {
            "status": self.status,
            "dry_run": self.dry_run,
            "categories": list(self.categories),
            "candidate_paths": [display(path) for path in self.candidate_paths],
            "deleted_paths": [display(path) for path in self.deleted_paths],
            "reclaimed_bytes": self.reclaimed_bytes,
        }


@dataclass(frozen=True)
class CapacityReport:
    status: str
    article_store_size_bytes: int
    markdown_size_bytes: int
    pdf_size_bytes: int
    rag_size_bytes: int
    graph_size_bytes: int
    logs_temp_size_bytes: int
    total_size_bytes: int
    essential_backup_estimated_bytes: int
    complete_backup_estimated_bytes: int
    free_bytes: int
    issue_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HealthIssue:
    issue_code: str
    affected_asset: str
    remediation_command: str
    rebuildable: bool
    backup_required_first: bool
    severity: str = "WARN"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HealthReport:
    status: str
    article_count: int
    corpus_fingerprint: str | None
    issues: tuple[HealthIssue, ...]
    capacity: CapacityReport
    checks: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "article_count": self.article_count,
            "corpus_fingerprint": self.corpus_fingerprint,
            "issues": [issue.to_dict() for issue in self.issues],
            "capacity": self.capacity.to_dict(),
            "checks": dict(sorted(self.checks.items())),
        }
