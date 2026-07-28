from __future__ import annotations

import hashlib
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.storage.article_store import StoredArticle

MIN_PDF_BYTES = 1_024
MAX_PDF_BYTES = 64 * 1024 * 1024
BOILERPLATE_PREFIXES = tuple(
    "".join(character.lower() for character in value if character.isalnum())
    for value in (
        "转载到请包括本文地址",
        "更详细的转载事宜请参考",
        "如果您还有什么疑惑或建议",
        "如果您觉得本文还不错",
        "打赏",
        "微信打赏",
        "支付宝打赏",
        "因为网站后台对打赏并无记录",
        "如果您需要引用本文",
        "苏剑林.",
        "@online",
    )
)


class PrintedPdfValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrintedPdfInspection:
    file_size_bytes: int
    sha256: str
    page_count: int
    a4_page: bool
    extracted_text_chars: int
    sample_count: int
    matched_sample_count: int
    chinese_present: bool
    title_present: bool
    formula_expected: bool
    mathjax_rendered: bool

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "sha256": self.sha256,
            "page_count": self.page_count,
            "a4_page": self.a4_page,
            "extracted_text_chars": self.extracted_text_chars,
            "sample_count": self.sample_count,
            "matched_sample_count": self.matched_sample_count,
            "chinese_present": self.chinese_present,
            "title_present": self.title_present,
            "formula_expected": self.formula_expected,
            "mathjax_rendered": self.mathjax_rendered,
        }


def inspect_printed_article_pdf(
    article: StoredArticle,
    path: Path | str,
    *,
    mathjax_rendered: bool,
) -> PrintedPdfInspection:
    pdf_path = Path(path)
    payload = _read_pdf(pdf_path)
    pdf_info = _run_pdf_command(["pdfinfo", str(pdf_path)])
    extracted_text = _run_pdf_command(["pdftotext", str(pdf_path), "-"])

    page_match = re.search(r"^Pages:\s+(\d+)\s*$", pdf_info, flags=re.MULTILINE)
    if page_match is None or int(page_match.group(1)) < 1:
        raise PrintedPdfValidationError("Printed PDF has no readable pages")
    page_count = int(page_match.group(1))
    a4_page = bool(
        re.search(
            r"^Page size:.*(?:A4|595\.?\d* x 842\.?\d*)",
            pdf_info,
            flags=re.MULTILINE,
        )
    )
    if not a4_page:
        raise PrintedPdfValidationError("Printed PDF is not A4")

    normalized_text = normalize_text(extracted_text)
    title_present = normalize_text(article.title) in normalized_text
    if not title_present:
        raise PrintedPdfValidationError(
            "Printed PDF does not contain the Article title"
        )
    chinese_present = bool(re.search(r"[\u3400-\u9fff]", extracted_text))
    if not chinese_present:
        raise PrintedPdfValidationError(
            "Printed PDF does not contain Chinese text"
        )

    samples = article_samples(article.content)
    matched_samples = sum(sample in normalized_text for sample in samples)
    required_matches = max(1, math.ceil(len(samples) * 0.6))
    if matched_samples < required_matches:
        raise PrintedPdfValidationError(
            "Printed PDF does not preserve enough authoritative Article content"
        )

    expected_formula = formula_expected(article.content)
    if expected_formula and not mathjax_rendered:
        raise PrintedPdfValidationError(
            "Printed PDF was created without MathJax evidence"
        )

    return PrintedPdfInspection(
        file_size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        page_count=page_count,
        a4_page=a4_page,
        extracted_text_chars=len(extracted_text),
        sample_count=len(samples),
        matched_sample_count=matched_samples,
        chinese_present=chinese_present,
        title_present=title_present,
        formula_expected=expected_formula,
        mathjax_rendered=mathjax_rendered,
    )


def article_samples(content: str) -> list[str]:
    samples: list[str] = []
    short_samples: list[str] = []
    for raw_paragraph in re.split(r"\n\s*\n", content):
        if re.search(r"!\[[^\]]*\]\(", raw_paragraph):
            continue
        paragraph = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", raw_paragraph)
        paragraph = re.sub(r"https?://\S+", " ", paragraph)
        normalized = normalize_text(paragraph)
        if not normalized or any(
            normalized.startswith(prefix) for prefix in BOILERPLATE_PREFIXES
        ):
            continue
        if (
            len(re.findall(r"[\u3400-\u9fff]", normalized)) >= 4
            and normalized not in short_samples
        ):
            short_samples.append(normalized[:80])
        anchors = [
            normalize_text(match.group(0))
            for match in re.finditer(
                (
                    r"[\u3400-\u9fff]"
                    r"(?:[\u3400-\u9fff\s，。！？、：；（）()《》“”‘’·…—-]"
                    r"){6,}[\u3400-\u9fff]"
                ),
                paragraph,
            )
        ]
        stable_anchors = [
            anchor[:80]
            for anchor in anchors
            if len(re.findall(r"[\u3400-\u9fff]", anchor)) >= 8
        ]
        if not stable_anchors:
            if len(normalized) < 32:
                continue
            if len(re.findall(r"[\u3400-\u9fff]", normalized)) < 8:
                continue
            stable_anchors = [normalized[:80]]
        for sample in stable_anchors:
            if sample not in samples:
                samples.append(sample)
    if not samples:
        if short_samples:
            samples = short_samples
        else:
            normalized = normalize_text(content)
            if len(normalized) < 32:
                raise PrintedPdfValidationError(
                    "Article content is too short for PDF validation"
                )
            samples = [normalized[:80]]
    if len(samples) <= 3:
        return samples
    indexes = {
        round(index * (len(samples) - 1) / 2)
        for index in range(3)
    }
    return [samples[index] for index in sorted(indexes)]


def normalize_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def formula_expected(content: str) -> bool:
    return bool(
        re.search(
            r"\$\$|(?<!\\)\$[^$\n]+(?<!\\)\$|\\begin\{|\\\[|\\\(",
            content,
        )
    )


def _read_pdf(path: Path) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PrintedPdfValidationError("Printed PDF is unavailable") from exc
    if len(payload) < MIN_PDF_BYTES:
        raise PrintedPdfValidationError(
            "Printed PDF is too short to contain an Article"
        )
    if len(payload) > MAX_PDF_BYTES:
        raise PrintedPdfValidationError(
            "Printed PDF exceeds the bounded size limit"
        )
    if not payload.startswith(b"%PDF-"):
        raise PrintedPdfValidationError("Printed PDF header is invalid")
    if b"%%EOF" not in payload[-2_048:]:
        raise PrintedPdfValidationError("Printed PDF end marker is missing")
    return payload


def _run_pdf_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PrintedPdfValidationError(
            "Local PDF validation command failed"
        ) from exc
    return result.stdout
