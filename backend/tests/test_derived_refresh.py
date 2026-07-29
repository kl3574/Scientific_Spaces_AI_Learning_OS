from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.graph.full_corpus import build_full_corpus_graph
from app.operations.derived_refresh import (
    DerivedPaths,
    DerivedRefreshConfig,
    DerivedRefreshError,
    RefreshBuilders,
    install_derived_bundle,
    production_paths,
    refresh_derived_assets,
)
from app.rag.full_corpus import (
    build_full_corpus_index,
    compute_corpus_fingerprint,
    load_full_corpus_articles,
)
from app.references.full_corpus import (
    FullCorpusReferenceConfig,
    run_full_corpus_reference_build,
)


TARGET_ARCHIVES = ("11814", "11818", "11823")
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_refresh_defaults_to_read_only_plan(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=False)
    data_root = config.data_root

    result = refresh_derived_assets(config)

    assert result["status"] == "PASS"
    assert result["mode"] == "dry_run"
    assert result["action"] == "refresh_required"
    assert result["install_performed"] is False
    assert _sha256(article_store) == config.expected_article_store_sha256
    assert not (data_root / "derived_refresh").exists()
    assert not (data_root / "rag").exists()
    assert not (data_root / "graph").exists()
    assert not (data_root / "references").exists()


def test_refresh_rejects_tracked_data_root(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=False)
    values = dict(config.__dict__)
    values["data_root"] = tmp_path / "tracked-runtime"

    with pytest.raises(DerivedRefreshError, match="ignored .local_data"):
        refresh_derived_assets(DerivedRefreshConfig(**values))

    assert article_store.is_file()
    assert not (tmp_path / "tracked-runtime").exists()


def test_refresh_cli_defaults_to_read_only_plan(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=False)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/ops/refresh_derived_assets.py"),
            "--article-store",
            str(article_store),
            "--data-root",
            str(config.data_root),
            "--expected-article-count",
            str(config.expected_article_count),
            "--expected-article-store-sha256",
            config.expected_article_store_sha256,
            "--expected-corpus-fingerprint",
            config.expected_corpus_fingerprint,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0, completed.stderr
    assert payload["mode"] == "dry_run"
    assert payload["action"] == "refresh_required"
    assert not (config.data_root / "derived_refresh").exists()


def test_refresh_builds_valid_bundle_backs_up_prior_state_and_then_noops(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=True)
    old_store = config.data_root / "corpus" / "old" / "articles.json"
    _write_articles(old_store, TARGET_ARCHIVES[:2])
    _build_direct_bundle(
        article_store=old_store,
        paths=production_paths(config.data_root),
        minimum_review_cases=1,
    )
    source_before = _sha256(article_store)

    first = refresh_derived_assets(config)
    backup_path = Path(first["backup_path"])
    installed_records = {
        name: _tree_digest(path)
        for name, path in production_paths(config.data_root).items()
    }
    backup_count = len(list((config.data_root / "derived_refresh" / "backups").iterdir()))

    second = refresh_derived_assets(config)

    assert first["status"] == "PASS"
    assert first["action"] == "refreshed"
    assert first["install_performed"] is True
    assert first["external_network_request_count"] == 0
    assert first["unexpected_network_attempt_count"] == 0
    assert first["staged_validation"]["article_count"] == 3
    assert set(first["staged_validation"]["rag"]["targets"]) == set(TARGET_ARCHIVES)
    assert set(first["staged_validation"]["graph"]["targets"]) == set(TARGET_ARCHIVES)
    assert set(first["staged_validation"]["references"]["targets"]) == set(TARGET_ARCHIVES)
    assert backup_path.is_dir()
    assert (backup_path / "backup_manifest.json").is_file()
    assert all((backup_path / name).is_dir() for name in ("rag", "graph", "references"))
    assert json.loads(
        (backup_path / "rag" / "index" / "manifest.json").read_text(encoding="utf-8")
    )["article_count"] == 2
    assert _sha256(article_store) == source_before
    assert second["action"] == "no_op"
    assert second["install_performed"] is False
    assert len(list((config.data_root / "derived_refresh" / "backups").iterdir())) == backup_count
    assert {
        name: _tree_digest(path)
        for name, path in production_paths(config.data_root).items()
    } == installed_records


def test_independent_offline_builds_have_matching_semantic_fingerprints(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=False)
    first = DerivedPaths(
        rag=config.data_root / "determinism-a" / "rag",
        graph=config.data_root / "determinism-a" / "graph",
        references=config.data_root / "determinism-a" / "references",
    )
    second = DerivedPaths(
        rag=config.data_root / "determinism-b" / "rag",
        graph=config.data_root / "determinism-b" / "graph",
        references=config.data_root / "determinism-b" / "references",
    )

    _build_direct_bundle(article_store=article_store, paths=first, minimum_review_cases=1)
    _build_direct_bundle(article_store=article_store, paths=second, minimum_review_cases=1)

    first_rag = _read_json(first.rag / "index" / "manifest.json")
    second_rag = _read_json(second.rag / "index" / "manifest.json")
    first_graph = _read_json(first.graph / "manifest.json")
    second_graph = _read_json(second.graph / "manifest.json")
    first_references = _read_json(first.references / "current" / "manifest.json")
    second_references = _read_json(second.references / "current" / "manifest.json")
    assert first_rag["corpus_fingerprint"] == second_rag["corpus_fingerprint"]
    assert first_rag["index_file_sha256"] == second_rag["index_file_sha256"]
    assert first_rag["chunk_metadata_sha256"] == second_rag["chunk_metadata_sha256"]
    assert first_graph["corpus_fingerprint"] == second_graph["corpus_fingerprint"]
    assert first_graph["graph_fingerprint"] == second_graph["graph_fingerprint"]
    assert first_references["corpus_fingerprint"] == second_references["corpus_fingerprint"]
    assert first_references["build_fingerprint"] == second_references["build_fingerprint"]
    assert first_references["files"] == second_references["files"]


def test_builder_failure_preserves_source_and_does_not_install(tmp_path: Path) -> None:
    article_store, config = _source_and_config(tmp_path, execute=True)
    source_before = _sha256(article_store)

    def fail_rag(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("injected build failure")

    with pytest.raises(DerivedRefreshError, match="Derived refresh failed"):
        refresh_derived_assets(
            config,
            builders=RefreshBuilders(rag=fail_rag),
        )

    assert _sha256(article_store) == source_before
    assert not production_paths(config.data_root).rag.exists()
    assert not production_paths(config.data_root).graph.exists()
    assert not production_paths(config.data_root).references.exists()


def test_install_step_failure_restores_complete_prior_bundle(tmp_path: Path) -> None:
    production, staged = _marker_bundles(tmp_path)
    before = {name: _tree_digest(path) for name, path in production.items()}

    def fail_after_graph(_name: str, index: int) -> None:
        if index == 2:
            raise RuntimeError("injected install failure")

    with pytest.raises(DerivedRefreshError, match="complete prior bundle restored") as captured:
        install_derived_bundle(
            staged=staged,
            production=production,
            post_install_validator=lambda: {"status": "PASS"},
            install_step_hook=fail_after_graph,
        )

    assert captured.value.evidence["components_restored"] == {
        "rag": True,
        "graph": True,
        "references": True,
    }
    assert {name: _tree_digest(path) for name, path in production.items()} == before


def test_post_install_failure_restores_complete_prior_bundle(tmp_path: Path) -> None:
    production, staged = _marker_bundles(tmp_path)
    before = {name: _tree_digest(path) for name, path in production.items()}

    def fail_validation() -> dict[str, object]:
        raise RuntimeError("injected post-install failure")

    with pytest.raises(DerivedRefreshError, match="complete prior bundle restored") as captured:
        install_derived_bundle(
            staged=staged,
            production=production,
            post_install_validator=fail_validation,
        )

    assert captured.value.evidence["components_restored"] == {
        "rag": True,
        "graph": True,
        "references": True,
    }
    assert {name: _tree_digest(path) for name, path in production.items()} == before


def _source_and_config(
    tmp_path: Path,
    *,
    execute: bool,
) -> tuple[Path, DerivedRefreshConfig]:
    data_root = tmp_path / ".local_data" / "scientific_spaces"
    article_store = data_root / "corpus" / "pilot" / "article_store" / "articles.json"
    _write_articles(article_store, TARGET_ARCHIVES)
    articles = load_full_corpus_articles(article_store)
    config = DerivedRefreshConfig(
        article_store=article_store,
        data_root=data_root,
        expected_article_count=len(articles),
        expected_article_store_sha256=_sha256(article_store),
        expected_corpus_fingerprint=compute_corpus_fingerprint(articles),
        target_archive_ids=TARGET_ARCHIVES,
        execute=execute,
        checkpoint_every=1,
        minimum_review_cases=1,
        min_available_disk_bytes=0,
        code_commit="0" * 40,
    )
    return article_store, config


def _write_articles(path: Path, archives: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for index, archive_id in enumerate(archives):
        token = ("Alpha", "Beta", "Gamma")[index]
        records.append(
            {
                "id": f"article-{archive_id}",
                "title": f"{token} exact retrieval topic {archive_id}",
                "url": f"https://spaces.ac.cn/archives/{archive_id}",
                "content": (
                    f"# {token} section\n\n"
                    f"{token}Exact{archive_id} matrix attention derivation and evidence.\n\n"
                    f"DOI: 10.1000/{archive_id}\n\n"
                    "$$\nA^T A = I\n$$\n"
                ),
                "metadata": {
                    "date": f"2026-07-{index + 1:02d}",
                    "category": "fixture",
                    "references": [f"10.1000/{archive_id}"],
                    "images": [],
                },
            }
        )
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def _build_direct_bundle(
    *,
    article_store: Path,
    paths: DerivedPaths,
    minimum_review_cases: int,
) -> None:
    articles = load_full_corpus_articles(article_store)
    count = len(articles)
    sha256 = _sha256(article_store)
    fingerprint = compute_corpus_fingerprint(articles)
    build_full_corpus_index(
        article_store_path=article_store,
        output_dir=paths.rag,
        provider_name="fake",
        rebuild=True,
        expected_article_count=count,
    )
    build_full_corpus_graph(
        article_store_path=article_store,
        output_dir=paths.graph,
        rebuild=True,
        expected_article_count=count,
    )
    result = run_full_corpus_reference_build(
        FullCorpusReferenceConfig(
            article_store=article_store,
            output_dir=paths.references,
            expected_article_count=count,
            expected_article_store_sha256=sha256,
            expected_corpus_fingerprint=fingerprint,
            checkpoint_every=1,
            rebuild=True,
            no_network=True,
            minimum_review_cases=minimum_review_cases,
            min_available_disk_bytes=0,
            code_commit="0" * 40,
        )
    )
    assert result.status in {"PASS", "CONDITIONAL"}


def _marker_bundles(tmp_path: Path) -> tuple[DerivedPaths, DerivedPaths]:
    production = DerivedPaths(
        rag=tmp_path / "production" / "rag",
        graph=tmp_path / "production" / "graph",
        references=tmp_path / "production" / "references",
    )
    staged = DerivedPaths(
        rag=tmp_path / "staged" / "rag",
        graph=tmp_path / "staged" / "graph",
        references=tmp_path / "staged" / "references",
    )
    for name, path in production.items():
        path.mkdir(parents=True)
        (path / "marker.txt").write_text(f"old-{name}", encoding="utf-8")
    for name, path in staged.items():
        path.mkdir(parents=True)
        (path / "marker.txt").write_text(f"new-{name}", encoding="utf-8")
    return production, staged


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(item.read_bytes())
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
