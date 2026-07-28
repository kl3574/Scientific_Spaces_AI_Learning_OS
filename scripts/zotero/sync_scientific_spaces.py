#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from websockets.sync.client import connect  # noqa: E402

from app.export.pdf import ArticlePdfExporter, PdfExportError  # noqa: E402
from app.storage.article_store import ArticleStore, StoredArticle  # noqa: E402
from app.zotero.sync import (  # noqa: E402
    DEFAULT_COLLECTION_NAME,
    LocalZoteroSyncTransport,
    ZoteroArticleSync,
    ZoteroPdfMigrationCoordinator,
    ZoteroPdfMigrationTarget,
    ZoteroSyncError,
    ZoteroSyncResult,
    inspect_pdf_bytes,
)

DEFAULT_ARTICLE_STORE = (
    REPO_ROOT
    / ".local_data"
    / "scientific_spaces"
    / "corpus"
    / "pilot"
    / "article_store"
    / "articles.json"
)
MAX_BATCH_SIZE = 3


@dataclass(frozen=True)
class PdfRuntimeInspection:
    file_size_bytes: int
    page_count: int
    a4_page: bool
    extracted_text_chars: int
    sample_count: int
    matched_sample_count: int
    chinese_present: bool
    title_present: bool
    mathjax_rendered: bool

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "a4_page": self.a4_page,
            "extracted_text_chars": self.extracted_text_chars,
            "sample_count": self.sample_count,
            "matched_sample_count": self.matched_sample_count,
            "chinese_present": self.chinese_present,
            "title_present": self.title_present,
            "mathjax_rendered": self.mathjax_rendered,
        }


class ZoteroDevToolsEvaluator:
    def __init__(
        self,
        websocket_url: str,
        *,
        timeout_seconds: float = 20,
    ) -> None:
        if not websocket_url.startswith("ws://127.0.0.1:"):
            raise ZoteroSyncError(
                "Zotero debugger URL must use a localhost WebSocket"
            )
        self.websocket_url = websocket_url
        self.timeout_seconds = timeout_seconds

    def evaluate_json(self, expression: str) -> dict[str, Any]:
        try:
            with connect(
                self.websocket_url,
                open_timeout=self.timeout_seconds,
                close_timeout=2,
            ) as websocket:
                self._receive_json(websocket)
                process = self._request(
                    websocket,
                    {"to": "root", "type": "getProcess", "id": 0},
                    lambda payload: "processDescriptor" in payload,
                )
                descriptor = process["processDescriptor"]["actor"]
                target = self._request(
                    websocket,
                    {"to": descriptor, "type": "getTarget"},
                    lambda payload: "process" in payload,
                )["process"]
                console_actor = target["consoleActor"]
                acknowledgement = self._request(
                    websocket,
                    {
                        "to": console_actor,
                        "type": "evaluateJSAsync",
                        "text": expression,
                        "mapped": {"await": True},
                    },
                    lambda payload: "resultID" in payload
                    and payload.get("type") != "evaluationResult",
                )
                result_id = acknowledgement["resultID"]
                evaluation = self._receive_until(
                    websocket,
                    lambda payload: payload.get("type") == "evaluationResult"
                    and payload.get("resultID") == result_id,
                )
        except ZoteroSyncError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize privileged bridge failures.
            raise ZoteroSyncError("Zotero Desktop bridge request failed") from exc

        if evaluation.get("hasException"):
            raise ZoteroSyncError("Zotero Desktop rejected the bounded PDF operation")
        raw_result = evaluation.get("result")
        if not isinstance(raw_result, str):
            raise ZoteroSyncError("Zotero Desktop returned an invalid bridge result")
        try:
            payload = json.loads(raw_result)
        except json.JSONDecodeError as exc:
            raise ZoteroSyncError(
                "Zotero Desktop returned a non-JSON bridge result"
            ) from exc
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise ZoteroSyncError("Zotero Desktop PDF operation did not complete")
        return payload

    def _request(
        self,
        websocket: Any,
        payload: dict[str, Any],
        predicate: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any]:
        websocket.send(json.dumps(payload))
        return self._receive_until(websocket, predicate)

    def _receive_until(
        self,
        websocket: Any,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any]:
        for _ in range(100):
            payload = self._receive_json(websocket)
            if payload.get("error"):
                raise ZoteroSyncError("Zotero Desktop debugger returned an error")
            if predicate(payload):
                return payload
        raise ZoteroSyncError("Zotero Desktop debugger response was not received")

    def _receive_json(self, websocket: Any) -> dict[str, Any]:
        raw = websocket.recv(timeout=self.timeout_seconds)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ZoteroSyncError("Zotero Desktop debugger response is invalid")
        return payload


class ZoteroRemoteDesktopBridge:
    def __init__(self, evaluator: ZoteroDevToolsEvaluator) -> None:
        self.evaluator = evaluator

    def attach_pdf(
        self,
        target: ZoteroPdfMigrationTarget,
        pdf_path: Path,
        title: str,
    ) -> None:
        payload = {
            "parentKey": target.parent_key,
            "articleID": target.article_id,
            "url": target.article_url,
            "pdfPath": str(pdf_path),
            "title": title,
        }
        result = self.evaluator.evaluate_json(
            _attach_pdf_expression(payload)
        )
        if result.get("attachment") not in {"created", "existing"}:
            raise ZoteroSyncError("Zotero Desktop did not attach the PDF")

    def trash_html(self, target: ZoteroPdfMigrationTarget) -> None:
        payload = {
            "parentKey": target.parent_key,
            "articleID": target.article_id,
            "url": target.article_url,
        }
        result = self.evaluator.evaluate_json(
            _trash_html_expression(payload)
        )
        if result.get("html") not in {"trashed", "absent"}:
            raise ZoteroSyncError("Zotero Desktop did not remove the HTML attachment")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Idempotently sync bounded Scientific Spaces Articles and optional "
            "browser-printed PDFs into a private Zotero collection."
        )
    )
    parser.add_argument("--article-store", type=Path, default=DEFAULT_ARTICLE_STORE)
    parser.add_argument("--article-id", action="append", required=True)
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument(
        "--with-pdf",
        action="store_true",
        help="Require one browser-printed PDF child per Article.",
    )
    parser.add_argument(
        "--replace-html",
        action="store_true",
        help=(
            "Move the attributable HTML child to Zotero Trash only after all "
            "requested PDFs pass readback."
        ),
    )
    parser.add_argument(
        "--debugger-url",
        help=(
            "Temporary localhost Zotero DevTools WebSocket used only to attach "
            "PDFs to existing parents and trash replaced HTML children."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Perform Zotero writes. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()

    if args.replace_html and not args.with_pdf:
        return _print_error("--replace-html requires --with-pdf")
    if args.replace_html and not args.write:
        return _print_error("--replace-html requires --write")

    requested_ids = list(dict.fromkeys(args.article_id))
    if len(requested_ids) != len(args.article_id):
        return _print_error("Duplicate --article-id values are not allowed")
    if len(requested_ids) > MAX_BATCH_SIZE:
        return _print_error(
            f"At most {MAX_BATCH_SIZE} Articles may be synced in one bounded run"
        )

    stored_by_id = {
        article.id: article
        for article in ArticleStore(args.article_store).list_articles()
    }
    missing_ids = [
        article_id for article_id in requested_ids if article_id not in stored_by_id
    ]
    if missing_ids:
        return _print_error(
            "Expected exactly one stored Article for every requested id; "
            f"missing count: {len(missing_ids)}"
        )
    articles = [stored_by_id[article_id] for article_id in requested_ids]

    transport = LocalZoteroSyncTransport()
    sync = ZoteroArticleSync(
        transport,
        collection_name=args.collection_name,
    )
    try:
        preflight = [
            sync.sync(article, require_pdf=args.with_pdf)
            for article in articles
        ]
    except ZoteroSyncError as exc:
        return _print_error(str(exc))

    if not args.write:
        _print_result(
            status="dry_run",
            results=preflight,
            inspections={},
            network_fetch_count=0,
            html_trashed_count=0,
        )
        return 0

    if not args.with_pdf:
        try:
            results = [sync.sync(article, write=True) for article in articles]
        except ZoteroSyncError as exc:
            return _print_error(str(exc))
        _print_result(
            status="ok",
            results=results,
            inspections={},
            network_fetch_count=0,
            html_trashed_count=0,
        )
        return 0

    requires_bridge = any(
        result.status == "migration_required"
        or (args.replace_html and result.html_attachment_count > 0)
        for result in preflight
    )
    if requires_bridge and not args.debugger_url:
        return _print_error(
            "Existing-parent PDF migration requires a temporary localhost "
            "Zotero debugger URL"
        )

    try:
        results, inspections, network_fetch_count, html_trashed_count = (
            _write_pdf_batch(
                sync,
                articles,
                preflight,
                replace_html=args.replace_html,
                debugger_url=args.debugger_url,
            )
        )
    except (PdfExportError, ZoteroSyncError) as exc:
        return _print_error(str(exc))

    _print_result(
        status="ok",
        results=results,
        inspections=inspections,
        network_fetch_count=network_fetch_count,
        html_trashed_count=html_trashed_count,
    )
    return 0


def _write_pdf_batch(
    sync: ZoteroArticleSync,
    articles: list[StoredArticle],
    preflight: list[ZoteroSyncResult],
    *,
    replace_html: bool,
    debugger_url: str | None,
) -> tuple[
    list[ZoteroSyncResult],
    dict[str, PdfRuntimeInspection],
    int,
    int,
]:
    pending = [
        article
        for article, result in zip(articles, preflight, strict=True)
        if result.pdf_status != "existing"
    ]
    inspections: dict[str, PdfRuntimeInspection] = {}

    with tempfile.TemporaryDirectory(
        prefix="scientific-spaces-zotero-pdf-"
    ) as raw_directory:
        directory = Path(raw_directory)
        pdf_paths: dict[str, Path] = {}
        exporter = ArticlePdfExporter(settle_ms=10_000)
        for article in pending:
            path = directory / f"{article.id}.pdf"
            export_result = exporter.export(article.url, path)
            inspection = _inspect_runtime_pdf(
                article,
                path,
                mathjax_rendered=export_result.mathjax_available,
            )
            pdf_paths[article.id] = path
            inspections[article.id] = inspection

        # Every pending PDF has passed local validation before the first write.
        for article, result in zip(articles, preflight, strict=True):
            if result.status != "dry_run":
                continue
            sync.sync(
                article,
                write=True,
                require_pdf=True,
                pdf_bytes=pdf_paths[article.id].read_bytes(),
            )

        bridge: ZoteroRemoteDesktopBridge | None = None
        coordinator: ZoteroPdfMigrationCoordinator | None = None
        migration_assignments = [
            (article, pdf_paths[article.id])
            for article, result in zip(articles, preflight, strict=True)
            if result.status == "migration_required"
        ]
        if migration_assignments:
            if not debugger_url:
                raise ZoteroSyncError(
                    "Zotero debugger URL is required for existing parents"
                )
            bridge = ZoteroRemoteDesktopBridge(
                ZoteroDevToolsEvaluator(debugger_url)
            )
            coordinator = ZoteroPdfMigrationCoordinator(sync, bridge)
            coordinator.attach_existing_pdfs(migration_assignments)

        verified = [sync.wait_for_existing_pdf(article) for article in articles]
        html_to_trash = sum(
            result.html_attachment_count for result in verified
        )
        if replace_html and html_to_trash:
            if not debugger_url:
                raise ZoteroSyncError(
                    "Zotero debugger URL is required to replace HTML attachments"
                )
            if coordinator is None:
                bridge = ZoteroRemoteDesktopBridge(
                    ZoteroDevToolsEvaluator(debugger_url)
                )
                coordinator = ZoteroPdfMigrationCoordinator(sync, bridge)
            verified = coordinator.replace_html_after_verified_pdfs(articles)

    return verified, inspections, len(pending), html_to_trash if replace_html else 0


def _inspect_runtime_pdf(
    article: StoredArticle,
    path: Path,
    *,
    mathjax_rendered: bool,
) -> PdfRuntimeInspection:
    inspection = inspect_pdf_bytes(path.read_bytes())
    pdf_info = _run_pdf_command(["pdfinfo", str(path)])
    extracted_text = _run_pdf_command(["pdftotext", str(path), "-"])

    page_match = re.search(r"^Pages:\s+(\d+)\s*$", pdf_info, flags=re.MULTILINE)
    if page_match is None or int(page_match.group(1)) < 1:
        raise ZoteroSyncError("Printed PDF has no readable pages")
    page_count = int(page_match.group(1))
    a4_page = bool(
        re.search(
            r"^Page size:.*(?:A4|595\.?\d* x 842\.?\d*)",
            pdf_info,
            re.MULTILINE,
        )
    )
    if not a4_page:
        raise ZoteroSyncError("Printed PDF is not A4")

    normalized_text = _normalize_text(extracted_text)
    title_present = _normalize_text(article.title) in normalized_text
    if not title_present:
        raise ZoteroSyncError("Printed PDF does not contain the Article title")
    chinese_present = bool(re.search(r"[\u3400-\u9fff]", extracted_text))
    if not chinese_present:
        raise ZoteroSyncError("Printed PDF does not contain Chinese text")

    samples = _article_samples(article.content)
    matched_samples = sum(sample in normalized_text for sample in samples)
    required_matches = max(1, math.ceil(len(samples) * 0.6))
    boundary_samples_present = (
        samples[0] in normalized_text
        and samples[-1] in normalized_text
    )
    if matched_samples < required_matches or not boundary_samples_present:
        raise ZoteroSyncError(
            "Printed PDF does not preserve enough authoritative Article content"
        )
    if _formula_expected(article.content) and not mathjax_rendered:
        raise ZoteroSyncError("Printed PDF was created without MathJax evidence")

    return PdfRuntimeInspection(
        file_size_bytes=inspection.file_size_bytes,
        page_count=page_count,
        a4_page=a4_page,
        extracted_text_chars=len(extracted_text),
        sample_count=len(samples),
        matched_sample_count=matched_samples,
        chinese_present=chinese_present,
        title_present=title_present,
        mathjax_rendered=mathjax_rendered,
    )


def _run_pdf_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ZoteroSyncError("Local PDF validation command failed") from exc
    return result.stdout


def _article_samples(content: str) -> list[str]:
    samples: list[str] = []
    for raw_paragraph in re.split(r"\n\s*\n", content):
        paragraph = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", raw_paragraph)
        paragraph = re.sub(r"https?://\S+", " ", paragraph)
        normalized = _normalize_text(paragraph)
        if len(normalized) < 32:
            continue
        if len(re.findall(r"[\u3400-\u9fff]", normalized)) < 8:
            continue
        sample = normalized[:80]
        if sample not in samples:
            samples.append(sample)
    if not samples:
        normalized = _normalize_text(content)
        if len(normalized) < 32:
            raise ZoteroSyncError("Article content is too short for PDF validation")
        samples = [normalized[:80]]
    if len(samples) <= 3:
        return samples
    indexes = {
        round(index * (len(samples) - 1) / 2)
        for index in range(3)
    }
    return [samples[index] for index in sorted(indexes)]


def _normalize_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _formula_expected(content: str) -> bool:
    return bool(
        re.search(
            r"\$\$|(?<!\\)\$[^$\n]+(?<!\\)\$|\\begin\{|\\\[|\\\(",
            content,
        )
    )


def _attach_pdf_expression(payload: dict[str, str]) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return f"""
(async () => {{
  const payload = {data};
  const parent = Zotero.Items.getByLibraryAndKey(
    Zotero.Libraries.userLibraryID,
    payload.parentKey
  );
  if (!parent || parent.deleted || !parent.isTopLevelItem()) {{
    throw new Error("approved parent unavailable");
  }}
  const provenance = String(parent.getField("extra") || "")
    .split(/\\r?\\n/)
    .includes("Scientific Spaces Article ID: " + payload.articleID);
  if (String(parent.getField("url") || "") !== payload.url || !provenance) {{
    throw new Error("approved parent provenance mismatch");
  }}
  const children = Zotero.Items.get(parent.getAttachments())
    .filter((item) => item && !item.deleted);
  const pdfs = children.filter(
    (item) => item.attachmentContentType === "application/pdf"
  );
  if (pdfs.length > 1) {{
    throw new Error("duplicate PDF attachments");
  }}
  if (pdfs.length === 1) {{
    return JSON.stringify({{status: "ok", attachment: "existing"}});
  }}
  const attachment = await Zotero.Attachments.importFromFile({{
    file: payload.pdfPath,
    parentItemID: parent.id,
    title: payload.title,
    contentType: "application/pdf"
  }});
  attachment.setField("url", payload.url);
  await attachment.saveTx();
  return JSON.stringify({{status: "ok", attachment: "created"}});
}})()
""".strip()


def _trash_html_expression(payload: dict[str, str]) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return f"""
(async () => {{
  const payload = {data};
  const parent = Zotero.Items.getByLibraryAndKey(
    Zotero.Libraries.userLibraryID,
    payload.parentKey
  );
  if (!parent || parent.deleted || !parent.isTopLevelItem()) {{
    throw new Error("approved parent unavailable");
  }}
  const provenance = String(parent.getField("extra") || "")
    .split(/\\r?\\n/)
    .includes("Scientific Spaces Article ID: " + payload.articleID);
  if (String(parent.getField("url") || "") !== payload.url || !provenance) {{
    throw new Error("approved parent provenance mismatch");
  }}
  const children = Zotero.Items.get(parent.getAttachments())
    .filter((item) => item && !item.deleted);
  const pdfs = children.filter(
    (item) => item.attachmentContentType === "application/pdf"
  );
  const html = children.filter(
    (item) => item.attachmentContentType === "text/html"
  );
  if (pdfs.length !== 1 || html.length > 1) {{
    throw new Error("unsafe replacement cardinality");
  }}
  if (html.length === 0) {{
    return JSON.stringify({{status: "ok", html: "absent"}});
  }}
  await Zotero.Items.trashTx([html[0].id]);
  return JSON.stringify({{status: "ok", html: "trashed"}});
}})()
""".strip()


def _print_result(
    *,
    status: str,
    results: list[ZoteroSyncResult],
    inspections: dict[str, PdfRuntimeInspection],
    network_fetch_count: int,
    html_trashed_count: int,
) -> None:
    output_results = []
    for result in results:
        payload = result.to_dict()
        runtime = inspections.get(result.article_id)
        payload["print_validation"] = runtime.to_dict() if runtime else None
        output_results.append(payload)
    print(
        json.dumps(
            {
                "status": status,
                "requested_count": len(results),
                "network_fetch_count": network_fetch_count,
                "html_trashed_count": html_trashed_count,
                "temporary_pdf_artifacts": 0,
                "results": output_results,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


def _print_error(message: str) -> int:
    print(
        json.dumps(
            {"status": "error", "error": message},
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
