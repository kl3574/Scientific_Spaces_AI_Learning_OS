import json
import os
from pathlib import Path

import pytest

from app.export.pdf import ArticlePdfExporter, PdfExportError, PdfExportResult, validate_pdf_file


PDF_BYTES = b"%PDF-1.4\n% test pdf\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_pdf_exporter_retries_validates_pdf_and_records_success(tmp_path: Path) -> None:
    attempts = {"count": 0}

    def renderer(url: str, output_path: Path) -> PdfExportResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("mathjax did not settle")
        output_path.write_bytes(PDF_BYTES)
        return PdfExportResult(
            url=url,
            output_path=output_path,
            status="success",
            title="Article",
            http_status=200,
            file_size_bytes=0,
            duration_seconds=0.1,
            mathjax_available=True,
            error=None,
        )

    exporter = ArticlePdfExporter(renderer=renderer, retries=2, backoff_seconds=0)
    output_path = tmp_path / "article.pdf"

    result = exporter.export("https://spaces.ac.cn/archives/6508", output_path)

    assert attempts["count"] == 2
    assert result.status == "success"
    assert result.file_size_bytes == len(PDF_BYTES)
    assert result.mathjax_available is True
    assert output_path.exists()
    assert validate_pdf_file(output_path) == len(PDF_BYTES)
    assert exporter.failures == []


def test_pdf_exporter_records_failure_after_bounded_retries(tmp_path: Path) -> None:
    def renderer(url: str, output_path: Path) -> PdfExportResult:
        raise RuntimeError(f"blocked: {url}")

    exporter = ArticlePdfExporter(renderer=renderer, retries=2, backoff_seconds=0)

    with pytest.raises(PdfExportError) as exc_info:
        exporter.export("https://spaces.ac.cn/archives/11787", tmp_path / "failed.pdf")

    assert exc_info.value.url == "https://spaces.ac.cn/archives/11787"
    assert "blocked" in exc_info.value.reason
    assert exporter.failures == [
        {
            "url": "https://spaces.ac.cn/archives/11787",
            "reason": "RuntimeError: blocked: https://spaces.ac.cn/archives/11787",
        }
    ]
    assert not (tmp_path / "failed.pdf").exists()


def test_validate_pdf_file_rejects_non_pdf(tmp_path: Path) -> None:
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_bytes(b"not a pdf")

    with pytest.raises(PdfExportError) as exc_info:
        validate_pdf_file(invalid_pdf, url="fixture://invalid")

    assert exc_info.value.url == "fixture://invalid"
    assert "invalid PDF header" in exc_info.value.reason


@pytest.mark.pdf_live
@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="PDF live check is opt-in")
def test_live_pdf_export_generates_valid_pdf_and_cleans_artifacts(tmp_path: Path) -> None:
    urls = [
        "https://spaces.ac.cn/archives/6508",
        "https://spaces.ac.cn/archives/11777",
        "https://spaces.ac.cn/archives/11782",
        "https://spaces.ac.cn/archives/11784",
        "https://spaces.ac.cn/archives/11804",
    ]
    exporter = ArticlePdfExporter(retries=2, backoff_seconds=1)
    results = []
    rows = []

    try:
        for index, url in enumerate(urls, start=1):
            output_path = tmp_path / f"article-{index}.pdf"
            try:
                result = exporter.export(url, output_path)
            except PdfExportError as exc:
                rows.append(
                    {
                        "url": url,
                        "pdf_status": "FAIL",
                        "duration_seconds": None,
                        "file_size_bytes": 0,
                        "mathjax_available": False,
                        "failure_reason": exc.reason,
                    }
                )
                continue
            assert output_path.exists()
            assert validate_pdf_file(output_path) > 0
            results.append(result)
            rows.append(
                {
                    "url": url,
                    "pdf_status": "PASS",
                    "duration_seconds": round(result.duration_seconds, 3),
                    "file_size_bytes": result.file_size_bytes,
                    "mathjax_available": result.mathjax_available,
                    "failure_reason": None,
                }
            )

        assert len(results) >= 5, exporter.failures
        assert all(result.mathjax_available for result in results)
    finally:
        for pdf_path in tmp_path.glob("*.pdf"):
            pdf_path.unlink()
        print("PDF_EXPORT_LIVE_RESULTS=" + json.dumps(rows, ensure_ascii=False, sort_keys=True))
        print("PDF_EXPORT_LIVE_FAILURES=" + json.dumps(exporter.failures, ensure_ascii=False, sort_keys=True))
        assert list(tmp_path.glob("*.pdf")) == []
