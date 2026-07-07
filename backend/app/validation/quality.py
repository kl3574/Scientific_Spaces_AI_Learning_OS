from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from app.parser.article import ParsedArticle
from app.storage.article_store import StoredArticle


@dataclass(frozen=True)
class ValidationReport:
    total_available: int
    total_checked: int
    title_presence_rate: float
    content_completeness_rate: float
    images_valid: bool
    formulas_valid: bool
    issues: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def write_json(self, path: Path | str) -> None:
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


class ArticleQualityValidator:
    def __init__(
        self,
        *,
        sample_size: int = 10,
        min_content_chars: int = 300,
        random_seed: int = 0,
    ) -> None:
        self.sample_size = sample_size
        self.min_content_chars = min_content_chars
        self.random_seed = random_seed

    def _sample(self, articles: list[StoredArticle]) -> list[StoredArticle]:
        if len(articles) <= self.sample_size:
            return articles
        rng = random.Random(self.random_seed)
        return rng.sample(articles, self.sample_size)

    def validate(self, articles: Iterable[StoredArticle | ParsedArticle]) -> ValidationReport:
        all_articles = list(articles)
        sampled = self._sample(all_articles)
        issues: list[str] = []

        title_ok = 0
        content_ok = 0
        images_ok = True
        formulas_ok = True

        for article in sampled:
            if article.title.strip():
                title_ok += 1
            else:
                issues.append(f"{article.url}: missing title")

            if len(article.content.strip()) >= self.min_content_chars:
                content_ok += 1
            else:
                issues.append(f"{article.url}: content shorter than {self.min_content_chars} characters")

            for image in _article_images(article):
                parsed = urlparse(str(image))
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    images_ok = False
                    issues.append(f"{article.url}: invalid image path {image}")

            if not _formula_delimiters_are_balanced(article.content):
                formulas_ok = False
                issues.append(f"{article.url}: formula delimiters look unbalanced")

        total = len(sampled)
        return ValidationReport(
            total_available=len(all_articles),
            total_checked=total,
            title_presence_rate=(title_ok / total) if total else 1.0,
            content_completeness_rate=(content_ok / total) if total else 1.0,
            images_valid=images_ok,
            formulas_valid=formulas_ok,
            issues=issues,
        )


def _formula_delimiters_are_balanced(content: str) -> bool:
    display_count = content.count("$$")
    inline_count = len(re.findall(r"(?<!\\)\$(?!\$)", content))
    return display_count % 2 == 0 and inline_count % 2 == 0


def _article_images(article: StoredArticle | ParsedArticle) -> list[str]:
    if isinstance(article, ParsedArticle):
        return article.images
    return list(article.metadata.get("images", []))
