from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export" / "export_local_corpus_pdfs.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_local_corpus_pdfs", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Summary:
    status = "PASS"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "PASS",
            "input_article_count": 1311,
            "selected_article_count": 20,
            "exported_count": 20,
        }


def test_cli_builds_offline_config_with_bounded_workers(monkeypatch, capsys, tmp_path: Path) -> None:
    module = _load_script()
    captured: dict[str, object] = {}

    def fake_export(*, config, progress_callback):
        captured["config"] = config
        progress_callback(
            {
                "completed": 20,
                "selected": 20,
                "article_id": "a1",
                "status": "PASS",
                "exported": 20,
                "regenerated": 0,
                "unchanged": 0,
                "failed": 0,
            }
        )
        return _Summary()

    monkeypatch.setattr(module, "export_local_pdf_library", fake_export)
    code = module.main(
        [
            "--article-store",
            str(tmp_path / "articles.json"),
            "--output-dir",
            str(tmp_path / "pdf-library"),
            "--mode",
            "offline",
            "--limit",
            "20",
            "--workers",
            "4",
            "--resume",
        ]
    )

    config = captured["config"]
    assert config.mode == "offline"
    assert config.limit == 20
    assert config.workers == 4
    assert config.resume is True
    assert config.rebuild is False
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PASS"
    assert output["exported_count"] == 20


def test_cli_returns_nonzero_for_blocked_summary(monkeypatch, tmp_path: Path) -> None:
    module = _load_script()

    class BlockedSummary(_Summary):
        status = "BLOCKED"

        def to_dict(self) -> dict[str, object]:
            return {"status": "BLOCKED"}

    monkeypatch.setattr(
        module,
        "export_local_pdf_library",
        lambda **_: BlockedSummary(),
    )
    code = module.main(
        [
            "--article-store",
            str(tmp_path / "articles.json"),
            "--output-dir",
            str(tmp_path / "pdf-library"),
        ]
    )
    assert code == 1


def test_cli_parser_exposes_required_resume_and_selection_options() -> None:
    module = _load_script()
    help_text = module.build_parser().format_help()
    for option in (
        "--article-store",
        "--markdown-dir",
        "--output-dir",
        "--mode",
        "--article-id",
        "--limit",
        "--resume",
        "--no-resume",
        "--rebuild",
        "--workers",
        "--allow-source-access",
        "--delay-seconds",
    ):
        assert option in help_text
