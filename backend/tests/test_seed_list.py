from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.corpus.seeds import load_seed_urls


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_seed_urls_supports_article_list_object_and_canonicalizes(tmp_path: Path) -> None:
    seed_file = tmp_path / "article_list.json"
    seed_file.write_text(
        json.dumps(
            {
                "source": "https://spaces.ac.cn (科学空间 - 苏剑林)",
                "generated_at": "2026-07-09 09:40:13",
                "total": 6,
                "year_stats": {"2026": 2},
                "articles": [
                    {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "recent"},
                    {"id": "11804", "url": "https://spaces.ac.cn/archives/11804?from=dup", "title": "dup"},
                    {"id": "6508", "url": "https://kexue.fm/archives/6508", "title": "alias"},
                    {"id": "bad", "url": "https://spaces.ac.cn/search?q=attention", "title": "search"},
                    {"id": "comment", "url": "https://spaces.ac.cn/archives/6508#comments", "title": "comment"},
                    {"id": "no-url", "title": "missing url"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert load_seed_urls(seed_file) == [
        "https://spaces.ac.cn/archives/11804",
        "https://spaces.ac.cn/archives/6508",
    ]


def test_load_seed_urls_keeps_full_seed_out_of_tests_by_accepting_small_list(tmp_path: Path) -> None:
    seed_file = tmp_path / "small_seed.txt"
    seed_file.write_text(
        "\n".join(
            [
                "https://spaces.ac.cn/archives/100",
                "https://www.spaces.ac.cn/archives/101/?utm=ignored",
                "https://spaces.ac.cn/category/math",
            ]
        ),
        encoding="utf-8",
    )

    assert load_seed_urls(seed_file) == [
        "https://spaces.ac.cn/archives/100",
        "https://spaces.ac.cn/archives/101",
    ]


def test_run_full_corpus_pilot_cli_prints_seed_file_dry_run_json(tmp_path: Path) -> None:
    seed_file = tmp_path / "seed.json"
    output_dir = tmp_path / ".local_data" / "pilot"
    seed_file.write_text(
        json.dumps({"articles": [{"url": "https://spaces.ac.cn/archives/119"}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "corpus" / "run_full_corpus_pilot.py"),
            "--limit",
            "1",
            "--dry-run",
            "--seed-file",
            str(seed_file),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["target_count"] == 1
    assert payload["canonical_url_count"] == 1


def test_run_full_corpus_pilot_cli_accepts_1000_default_max_limit(tmp_path: Path) -> None:
    seed_file = tmp_path / "seed.json"
    output_dir = tmp_path / ".local_data" / "pilot"
    seed_file.write_text(
        json.dumps({"articles": [{"url": "https://spaces.ac.cn/archives/119"}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "corpus" / "run_full_corpus_pilot.py"),
            "--limit",
            "1000",
            "--delay-seconds",
            "8",
            "--dry-run",
            "--seed-file",
            str(seed_file),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["target_count"] == 1000
    assert payload["canonical_url_count"] == 1
