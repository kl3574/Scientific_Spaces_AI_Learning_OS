from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.graph.full_corpus import audit_graph, build_full_corpus_graph
from app.graph.models import GraphDocument
from app.graph.service import GraphService
from app.graph.store import GraphStore
from app.rag.full_corpus import (
    FullCorpusRagService,
    build_full_corpus_index,
    compute_corpus_fingerprint,
    load_full_corpus_articles,
    load_full_corpus_index,
)
from app.references.full_corpus import (
    FullCorpusReferenceConfig,
    run_full_corpus_reference_build,
)
from app.references.network import ZeroNetworkGuard
from app.references.store import audit_reference_store

DEFAULT_TARGET_ARCHIVE_IDS = ("11814", "11818", "11823")


class DerivedRefreshError(RuntimeError):
    def __init__(self, message: str, *, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence or {}


class RefreshAlreadyRunningError(DerivedRefreshError):
    pass


@dataclass(frozen=True)
class DerivedRefreshConfig:
    article_store: Path
    data_root: Path
    expected_article_count: int
    expected_article_store_sha256: str
    expected_corpus_fingerprint: str
    target_archive_ids: tuple[str, ...] = DEFAULT_TARGET_ARCHIVE_IDS
    execute: bool = False
    checkpoint_every: int = 50
    minimum_review_cases: int = 60
    min_available_disk_bytes: int = 0
    code_commit: str = "unknown"

    def __post_init__(self) -> None:
        object.__setattr__(self, "article_store", Path(self.article_store).expanduser().resolve())
        object.__setattr__(self, "data_root", Path(self.data_root).expanduser().resolve())
        object.__setattr__(
            self,
            "target_archive_ids",
            tuple(str(value).strip() for value in self.target_archive_ids),
        )
        if self.expected_article_count < 1:
            raise ValueError("expected_article_count must be positive")
        if len(self.expected_article_store_sha256) != 64:
            raise ValueError("expected_article_store_sha256 must be a SHA-256 digest")
        if len(self.expected_corpus_fingerprint) != 64:
            raise ValueError("expected_corpus_fingerprint must be a SHA-256 digest")
        if not self.target_archive_ids or any(not value.isdigit() for value in self.target_archive_ids):
            raise ValueError("target_archive_ids must contain numeric archive IDs")
        if len(set(self.target_archive_ids)) != len(self.target_archive_ids):
            raise ValueError("target_archive_ids must be unique")
        if self.checkpoint_every < 1:
            raise ValueError("checkpoint_every must be positive")
        if self.minimum_review_cases < 1:
            raise ValueError("minimum_review_cases must be positive")


@dataclass(frozen=True)
class SourceIdentity:
    article_count: int
    article_store_sha256: str
    corpus_fingerprint: str
    article_ids_by_archive: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DerivedPaths:
    rag: Path
    graph: Path
    references: Path

    def items(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("rag", self.rag),
            ("graph", self.graph),
            ("references", self.references),
        )

    def to_dict(self) -> dict[str, str]:
        return {name: str(path) for name, path in self.items()}


@dataclass(frozen=True)
class RefreshBuilders:
    rag: Callable[..., dict[str, Any]] = build_full_corpus_index
    graph: Callable[..., dict[str, Any]] = build_full_corpus_graph
    references: Callable[[FullCorpusReferenceConfig], Any] = run_full_corpus_reference_build


InstallStepHook = Callable[[str, int], None]
PostInstallValidator = Callable[[], dict[str, Any]]


class ExclusiveRefreshLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: Any = None

    def __enter__(self) -> ExclusiveRefreshLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.close()
            self._handle = None
            raise RefreshAlreadyRunningError("Another derived refresh is already running") from exc
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(f"{os.getpid()}\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
        return False


def refresh_derived_assets(
    config: DerivedRefreshConfig,
    *,
    builders: RefreshBuilders | None = None,
    install_step_hook: InstallStepHook | None = None,
    post_install_validator: PostInstallValidator | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    _validate_data_root(config.data_root)
    source = validate_source_identity(config)
    production = production_paths(config.data_root)
    current = inspect_current_bundle(config, source=source, paths=production)
    base_result = {
        "status": "PASS",
        "mode": "execute" if config.execute else "dry_run",
        "source": source.to_dict(),
        "paths": production.to_dict(),
        "current": current,
        "target_archive_ids": list(config.target_archive_ids),
        "external_network_request_count": 0,
        "unexpected_network_attempt_count": 0,
    }
    if current["valid"]:
        return {
            **base_result,
            "action": "no_op",
            "install_performed": False,
            "backup_path": None,
            "elapsed_seconds": time.perf_counter() - started,
        }
    if not config.execute:
        return {
            **base_result,
            "action": "refresh_required",
            "install_performed": False,
            "backup_path": None,
            "elapsed_seconds": time.perf_counter() - started,
        }

    runtime_root = config.data_root / "derived_refresh"
    _reject_symlink_components(runtime_root)
    lock_path = runtime_root / "refresh.lock"
    with ExclusiveRefreshLock(lock_path):
        source = validate_source_identity(config)
        current = inspect_current_bundle(config, source=source, paths=production)
        if current["valid"]:
            return {
                **base_result,
                "current": current,
                "action": "no_op",
                "install_performed": False,
                "backup_path": None,
                "elapsed_seconds": time.perf_counter() - started,
            }
        result = _execute_refresh(
            config,
            source=source,
            production=production,
            runtime_root=runtime_root,
            builders=builders or RefreshBuilders(),
            install_step_hook=install_step_hook,
            post_install_validator=post_install_validator,
            started=started,
        )
        _write_json_atomic(runtime_root / "last_run.json", result)
        return result


def validate_source_identity(config: DerivedRefreshConfig) -> SourceIdentity:
    source_path = config.article_store.expanduser().resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise DerivedRefreshError("Article Store must be a regular nonsymlink file")
    if ".local_data" not in source_path.parts:
        raise DerivedRefreshError("Article Store must be inside an ignored .local_data directory")
    _reject_symlink_components(source_path)
    sha256 = _file_sha256(source_path)
    articles = load_full_corpus_articles(source_path)
    fingerprint = compute_corpus_fingerprint(articles)
    if len(articles) != config.expected_article_count:
        raise DerivedRefreshError(
            f"Article Store count mismatch: expected {config.expected_article_count}, got {len(articles)}"
        )
    if sha256 != config.expected_article_store_sha256:
        raise DerivedRefreshError("Article Store SHA-256 does not match the approved input")
    if fingerprint != config.expected_corpus_fingerprint:
        raise DerivedRefreshError("Article Store corpus fingerprint does not match the approved input")
    article_ids_by_archive: dict[str, str] = {}
    for article in articles:
        archive_id = article.url.rstrip("/").rsplit("/", 1)[-1]
        if archive_id in config.target_archive_ids:
            article_ids_by_archive[archive_id] = article.id
    missing = sorted(set(config.target_archive_ids) - set(article_ids_by_archive))
    if missing:
        raise DerivedRefreshError(
            "Target Articles are missing from the approved Article Store: " + ", ".join(missing)
        )
    return SourceIdentity(
        article_count=len(articles),
        article_store_sha256=sha256,
        corpus_fingerprint=fingerprint,
        article_ids_by_archive=dict(sorted(article_ids_by_archive.items())),
    )


def production_paths(data_root: Path | str) -> DerivedPaths:
    root = Path(data_root).expanduser().resolve()
    return DerivedPaths(
        rag=root / "rag" / "full_corpus",
        graph=root / "graph" / "full_corpus",
        references=root / "references" / "full-corpus",
    )


def _validate_data_root(path: Path) -> None:
    resolved = path.expanduser().resolve()
    if ".local_data" not in resolved.parts or resolved.parts[-1] == ".local_data":
        raise DerivedRefreshError("Derived data root must be below an ignored .local_data directory")
    _reject_symlink_components(resolved)


def inspect_current_bundle(
    config: DerivedRefreshConfig,
    *,
    source: SourceIdentity,
    paths: DerivedPaths,
) -> dict[str, Any]:
    manifests = {
        "rag": _read_json(paths.rag / "index" / "manifest.json"),
        "graph": _read_json(paths.graph / "manifest.json"),
        "references": _read_json(paths.references / "current" / "manifest.json"),
    }
    summary = {
        name: {
            "exists": path.is_dir(),
            "article_count": manifests[name].get("article_count")
            if name != "references"
            else (manifests[name].get("counts") or {}).get("articles"),
            "corpus_fingerprint": manifests[name].get("corpus_fingerprint"),
        }
        for name, path in paths.items()
    }
    try:
        validation = validate_derived_bundle(
            article_store=config.article_store,
            source=source,
            paths=paths,
        )
    except Exception as exc:
        return {
            "valid": False,
            "components": summary,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "valid": True,
        "components": summary,
        "validation": validation,
    }


def validate_derived_bundle(
    *,
    article_store: Path,
    source: SourceIdentity,
    paths: DerivedPaths,
) -> dict[str, Any]:
    articles = load_full_corpus_articles(article_store)
    if len(articles) != source.article_count:
        raise DerivedRefreshError("Article count changed while validating derived assets")
    if compute_corpus_fingerprint(articles) != source.corpus_fingerprint:
        raise DerivedRefreshError("Article corpus changed while validating derived assets")
    by_id = {article.id: article for article in articles}

    loaded_rag = load_full_corpus_index(paths.rag / "index", article_store_path=article_store)
    rag_service = FullCorpusRagService.load(
        article_store_path=article_store,
        index_dir=paths.rag,
        allow_real_provider=False,
    )
    rag_targets: dict[str, Any] = {}
    for archive_id, article_id in source.article_ids_by_archive.items():
        article = by_id[article_id]
        query = " ".join((article.title, article.content[:500]))
        results = rag_service.search(question=query, top_k=20)
        retrieved_ids = [result.chunk.article_id for result in results]
        if article_id not in retrieved_ids:
            raise DerivedRefreshError(f"RAG did not retrieve target Article /archives/{archive_id}")
        rag_targets[archive_id] = {
            "article_id": article_id,
            "chunk_count": sum(
                1 for chunk in loaded_rag.chunks if chunk.article_id == article_id
            ),
            "retrieved": True,
            "retrieval_rank": retrieved_ids.index(article_id) + 1,
        }

    graph_manifest = _required_json(paths.graph / "manifest.json")
    graph_payload = _required_json(paths.graph / "graph.json")
    graph = GraphDocument.from_dict(graph_payload)
    graph_audit = audit_graph(articles, graph)
    if graph_audit["status"] != "PASS":
        raise DerivedRefreshError("Graph integrity audit did not pass")
    if graph_manifest.get("corpus_fingerprint") != source.corpus_fingerprint:
        raise DerivedRefreshError("Graph corpus fingerprint is stale")
    if graph_manifest.get("article_count") != source.article_count:
        raise DerivedRefreshError("Graph Article count is stale")
    graph_service = GraphService(store=GraphStore(paths.graph / "graph.json"))
    graph_targets: dict[str, Any] = {}
    for archive_id, article_id in source.article_ids_by_archive.items():
        page = graph_service.list_nodes(article_id=article_id, page=1, page_size=100)
        if not page["items"]:
            raise DerivedRefreshError(f"Graph does not represent target Article /archives/{archive_id}")
        graph_targets[archive_id] = {
            "article_id": article_id,
            "node_count": page["total"],
        }

    reference_manifest = audit_reference_store(
        paths.references / "current",
        expected_corpus_fingerprint=source.corpus_fingerprint,
    )
    if reference_manifest.counts.get("articles") != source.article_count:
        raise DerivedRefreshError("Reference Store Article count is stale")
    article_index = _required_json(paths.references / "current" / "article_index.json")
    reference_targets: dict[str, Any] = {}
    for archive_id, article_id in source.article_ids_by_archive.items():
        bucket = article_index.get(article_id)
        if not isinstance(bucket, dict):
            raise DerivedRefreshError(
                f"Reference Store does not account for target Article /archives/{archive_id}"
            )
        reference_targets[archive_id] = {
            "article_id": article_id,
            "reference_count": len(bucket.get("reference_ids") or []),
            "evidence_count": len(bucket.get("evidence_ids") or []),
        }

    return {
        "status": "PASS",
        "article_count": source.article_count,
        "corpus_fingerprint": source.corpus_fingerprint,
        "rag": {
            "article_count": loaded_rag.manifest["article_count"],
            "chunk_count": loaded_rag.manifest["chunk_count"],
            "provider": loaded_rag.manifest["provider"],
            "targets": rag_targets,
        },
        "graph": {
            "article_count": graph_manifest["article_count"],
            "node_count": graph_manifest["node_count"],
            "edge_count": graph_manifest["edge_count"],
            "graph_fingerprint": graph_manifest["graph_fingerprint"],
            "targets": graph_targets,
        },
        "references": {
            "article_count": reference_manifest.counts["articles"],
            "record_count": reference_manifest.counts["records"],
            "evidence_count": reference_manifest.counts["evidence"],
            "build_fingerprint": reference_manifest.build_fingerprint,
            "network_request_count": reference_manifest.network_request_count,
            "targets": reference_targets,
        },
    }


def install_derived_bundle(
    *,
    staged: DerivedPaths,
    production: DerivedPaths,
    post_install_validator: PostInstallValidator,
    install_step_hook: InstallStepHook | None = None,
) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    original = {
        name: _tree_record(path) if path.exists() else None
        for name, path in production.items()
    }
    rollback_paths: dict[str, Path] = {}
    installed: list[str] = []
    try:
        for index, ((name, target), (staged_name, staged_path)) in enumerate(
            zip(production.items(), staged.items(), strict=True),
            start=1,
        ):
            if name != staged_name:
                raise DerivedRefreshError("Derived component order mismatch")
            if not staged_path.is_dir() or staged_path.is_symlink():
                raise DerivedRefreshError(f"Staged {name} component is unavailable")
            target.parent.mkdir(parents=True, exist_ok=True)
            rollback = target.with_name(f".{target.name}.p3-010-rollback-{run_id}")
            if rollback.exists():
                raise DerivedRefreshError(f"Rollback path already exists for {name}")
            if target.exists():
                os.replace(target, rollback)
                rollback_paths[name] = rollback
            os.replace(staged_path, target)
            _fsync_directory(target.parent)
            installed.append(name)
            if install_step_hook is not None:
                install_step_hook(name, index)
        validation = post_install_validator()
    except Exception as exc:
        rollback_errors = _rollback_install(
            production=production,
            rollback_paths=rollback_paths,
            installed=installed,
        )
        restored = {
            name: (
                _tree_record(path) == original[name]
                if original[name] is not None and path.exists()
                else original[name] is None and not path.exists()
            )
            for name, path in production.items()
        }
        if rollback_errors or not all(restored.values()):
            raise DerivedRefreshError(
                "Derived bundle installation failed and rollback was incomplete",
                evidence={
                    "cause": f"{type(exc).__name__}: {exc}",
                    "rollback_errors": rollback_errors,
                    "components_restored": restored,
                },
            ) from exc
        raise DerivedRefreshError(
            "Derived bundle installation failed; complete prior bundle restored",
            evidence={
                "cause": f"{type(exc).__name__}: {exc}",
                "rollback_errors": [],
                "components_restored": restored,
            },
        ) from exc

    cleanup_warnings: list[str] = []
    for name, rollback in rollback_paths.items():
        try:
            _remove_path(rollback)
        except OSError as exc:
            cleanup_warnings.append(f"{name}: {type(exc).__name__}: {exc}")
    return {
        "status": "PASS",
        "installed_components": installed,
        "post_install_validation": validation,
        "rollback_cleanup_warnings": cleanup_warnings,
    }


def create_recovery_backup(
    *,
    production: DerivedPaths,
    backup_root: Path,
    source: SourceIdentity,
) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    staging = backup_root / f".backup-staging-{run_id}"
    final = backup_root / (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{source.corpus_fingerprint[:12]}-{run_id[:8]}"
    )
    if staging.exists() or final.exists():
        raise DerivedRefreshError("Backup path collision")
    staging.mkdir()
    components: dict[str, Any] = {}
    try:
        for name, source_path in production.items():
            if not source_path.is_dir() or source_path.is_symlink():
                raise DerivedRefreshError(f"Existing {name} snapshot is unavailable for backup")
            _reject_tree_symlinks(source_path)
            target = staging / name
            shutil.copytree(source_path, target, copy_function=shutil.copy2)
            source_record = _tree_record(source_path)
            backup_record = _tree_record(target)
            if source_record != backup_record:
                raise DerivedRefreshError(f"Backup verification failed for {name}")
            components[name] = source_record
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "purpose": "P3-010 pre-refresh recovery snapshot",
            "approved_source": source.to_dict(),
            "components": components,
        }
        _write_json_atomic(staging / "backup_manifest.json", manifest)
        os.replace(staging, final)
        _fsync_directory(final.parent)
        return final
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _execute_refresh(
    config: DerivedRefreshConfig,
    *,
    source: SourceIdentity,
    production: DerivedPaths,
    runtime_root: Path,
    builders: RefreshBuilders,
    install_step_hook: InstallStepHook | None,
    post_install_validator: PostInstallValidator | None,
    started: float,
) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    staging_root = runtime_root / "staging" / run_id
    staged = DerivedPaths(
        rag=staging_root / "rag" / "full_corpus",
        graph=staging_root / "graph" / "full_corpus",
        references=staging_root / "references" / "full-corpus",
    )
    backup_path: Path | None = None
    network_evidence = {
        "external_network_request_count": 0,
        "unexpected_network_attempt_count": 0,
    }
    try:
        staging_root.mkdir(parents=True)
        with ZeroNetworkGuard() as network:
            rag_result = builders.rag(
                article_store_path=config.article_store,
                output_dir=staged.rag,
                provider_name="fake",
                rebuild=True,
                expected_article_count=config.expected_article_count,
                allow_real_provider=False,
            )
            graph_result = builders.graph(
                article_store_path=config.article_store,
                output_dir=staged.graph,
                rebuild=True,
                expected_article_count=config.expected_article_count,
            )
            reference_result = builders.references(
                FullCorpusReferenceConfig(
                    article_store=config.article_store,
                    output_dir=staged.references,
                    expected_article_count=config.expected_article_count,
                    expected_article_store_sha256=config.expected_article_store_sha256,
                    expected_corpus_fingerprint=config.expected_corpus_fingerprint,
                    checkpoint_every=config.checkpoint_every,
                    rebuild=True,
                    no_network=True,
                    minimum_review_cases=config.minimum_review_cases,
                    min_available_disk_bytes=config.min_available_disk_bytes,
                    code_commit=config.code_commit,
                )
            )
            network_evidence = {
                "external_network_request_count": network.external_network_request_count,
                "unexpected_network_attempt_count": network.unexpected_network_attempt_count,
            }
        if network_evidence != {
            "external_network_request_count": 0,
            "unexpected_network_attempt_count": 0,
        }:
            raise DerivedRefreshError("Offline derived build attempted network access")
        if rag_result.get("status") != "PASS" or graph_result.get("status") != "PASS":
            raise DerivedRefreshError("A staged derived builder did not pass")
        reference_payload = (
            reference_result.to_dict()
            if hasattr(reference_result, "to_dict")
            else dict(reference_result)
        )
        if reference_payload.get("status") not in {"PASS", "CONDITIONAL"}:
            raise DerivedRefreshError("The staged Reference build did not pass machine gates")
        if (
            reference_payload.get("external_network_request_count") != 0
            or reference_payload.get("unexpected_network_attempt_count") != 0
            or reference_payload.get("source_mutation_count") != 0
            or reference_payload.get("input_accounting_rate") != 1.0
            or reference_payload.get("classification_reconciliation_rate") != 1.0
            or reference_payload.get("silent_drop_count") != 0
        ):
            raise DerivedRefreshError("The staged Reference build failed an offline integrity gate")

        existing_reviews = production.references / "reviews"
        if existing_reviews.is_dir():
            _reject_symlink_components(existing_reviews)
            _reject_tree_symlinks(existing_reviews)
            shutil.copytree(existing_reviews, staged.references / "reviews")
        staged_validation = validate_derived_bundle(
            article_store=config.article_store,
            source=source,
            paths=staged,
        )
        if validate_source_identity(config) != source:
            raise DerivedRefreshError("Article Store changed during staged build")

        backup_path = create_recovery_backup(
            production=production,
            backup_root=runtime_root / "backups",
            source=source,
        )
        validator = post_install_validator or (
            lambda: validate_derived_bundle(
                article_store=config.article_store,
                source=source,
                paths=production,
            )
        )
        install = install_derived_bundle(
            staged=staged,
            production=production,
            post_install_validator=validator,
            install_step_hook=install_step_hook,
        )
        source_after = validate_source_identity(config)
        if source_after != source:
            raise DerivedRefreshError("Article Store changed during derived bundle installation")
        return {
            "status": "PASS",
            "mode": "execute",
            "action": "refreshed",
            "source": source.to_dict(),
            "source_after": source_after.to_dict(),
            "paths": production.to_dict(),
            "target_archive_ids": list(config.target_archive_ids),
            "build": {
                "rag": rag_result,
                "graph": graph_result,
                "references": reference_payload,
            },
            "staged_validation": staged_validation,
            "install": install,
            "install_performed": True,
            "backup_path": str(backup_path),
            **network_evidence,
            "elapsed_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        failure = {
            "status": "BLOCKED",
            "mode": "execute",
            "action": "failed",
            "source": source.to_dict(),
            "paths": production.to_dict(),
            "backup_path": str(backup_path) if backup_path else None,
            **network_evidence,
            "error": f"{type(exc).__name__}: {exc}",
            "error_evidence": exc.evidence if isinstance(exc, DerivedRefreshError) else {},
            "elapsed_seconds": time.perf_counter() - started,
        }
        runtime_root.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(runtime_root / "last_run.json", failure)
        if isinstance(exc, DerivedRefreshError):
            raise
        raise DerivedRefreshError("Derived refresh failed", evidence=failure) from exc
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        staging_parent = staging_root.parent
        if staging_parent.is_dir() and not any(staging_parent.iterdir()):
            staging_parent.rmdir()


def _rollback_install(
    *,
    production: DerivedPaths,
    rollback_paths: dict[str, Path],
    installed: Iterable[str],
) -> list[str]:
    errors: list[str] = []
    targets = dict(production.items())
    for name in reversed(list(installed)):
        target = targets[name]
        rollback = rollback_paths.get(name)
        try:
            _remove_path(target)
            if rollback is not None:
                os.replace(rollback, target)
            _fsync_directory(target.parent)
        except OSError as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    for name, rollback in rollback_paths.items():
        if name in installed or not rollback.exists():
            continue
        target = targets[name]
        try:
            os.replace(rollback, target)
            _fsync_directory(target.parent)
        except OSError as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    return errors


def _tree_record(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    file_count = 0
    size_bytes = 0
    for item in sorted(path.rglob("*"), key=lambda value: value.relative_to(path).as_posix()):
        relative = item.relative_to(path).as_posix()
        if item.is_symlink():
            raise DerivedRefreshError(f"Symlink is not allowed in a derived snapshot: {relative}")
        if not item.is_file():
            continue
        file_digest = _file_sha256(item)
        size = item.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        file_count += 1
        size_bytes += size
    return {
        "tree_sha256": digest.hexdigest(),
        "file_count": file_count,
        "size_bytes": size_bytes,
    }


def _reject_tree_symlinks(path: Path) -> None:
    if path.is_symlink():
        raise DerivedRefreshError(f"Derived snapshot cannot be a symlink: {path}")
    for item in path.rglob("*"):
        if item.is_symlink():
            raise DerivedRefreshError(f"Derived snapshot cannot contain symlinks: {item}")


def _reject_symlink_components(path: Path) -> None:
    cursor = path
    while cursor != cursor.parent:
        if cursor.exists() and cursor.is_symlink():
            raise DerivedRefreshError(f"Path cannot contain symlinks: {cursor}")
        cursor = cursor.parent


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _required_json(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    if not value:
        raise DerivedRefreshError(f"Required JSON artifact is missing or invalid: {path.name}")
    return value


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
