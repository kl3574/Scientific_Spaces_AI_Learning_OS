from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from app.crawler.browser import BrowserArticleFetcher, BrowserFetchResult
from app.crawler.canonical import RejectedUrl, canonicalize_article_urls
from app.crawler.rss import DEFAULT_FEED_URL, default_fetch_xml
from app.parser.article import ParsedArticle, parse_article_html
from app.storage.article_store import ArticleStore, StoredArticle
from app.validation.quality import ArticleQualityValidator

DEFAULT_OUTPUT_DIR = Path(".local_data/scientific_spaces/corpus/pilot")
USER_AGENT = "ScientificSpacesAILearningOS/1.1 Pilot"
REQUIRED_METADATA_KEYS = {"date", "category", "references", "images"}


class ArticleFetcher(Protocol):
    failures: list[dict[str, str]]

    def fetch(self, url: str) -> BrowserFetchResult: ...


@dataclass(frozen=True)
class PilotConfig:
    limit: int = 10
    max_limit: int = 50
    concurrency: int = 1
    delay_seconds: float = 3.0
    output_dir: Path = DEFAULT_OUTPUT_DIR
    dry_run: bool = False
    feed_url: str = DEFAULT_FEED_URL
    seed_urls: tuple[str, ...] = ()
    manual_urls: tuple[str, ...] = ()
    max_consecutive_failures: int = 5

    def __post_init__(self) -> None:
        output_dir = Path(self.output_dir)
        object.__setattr__(self, "output_dir", output_dir)
        if self.limit < 1 or self.limit > self.max_limit or self.limit > 50:
            raise ValueError("limit must be between 1 and 50")
        if self.max_limit > 50:
            raise ValueError("max_limit must be <= 50")
        if self.concurrency != 1:
            raise ValueError("pilot concurrency must be 1")
        if self.delay_seconds < 3:
            raise ValueError("delay_seconds must be >= 3")
        if self.limit > 30 and self.delay_seconds < 5:
            raise ValueError("delay_seconds must be >= 5 for medium batch limits above 30")
        if self.max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be >= 1")
        if ".local_data" not in output_dir.parts:
            raise ValueError("output_dir must be under an ignored .local_data runtime directory")


@dataclass(frozen=True)
class PilotFailure:
    url: str
    reason: str
    category: str


@dataclass(frozen=True)
class PilotSummary:
    status: str
    target_count: int
    discovered_url_count: int
    canonical_url_count: int
    duplicate_count: int
    selected_count: int
    attempted_count: int
    imported_count: int
    failed_count: int
    skipped_count: int
    content_completeness_rate: float
    formula_valid_rate: float
    metadata_completeness_rate: float
    short_content_count: int
    invalid_content_count: int
    invalid_candidate_count: int
    invalid_imported_content_count: int
    skipped_non_article_or_legacy_page: int
    parser_quality_issues: list[str]
    browser_transient_failures: int
    permanent_failures: int
    failed_url_categories: dict[str, int]
    sample_article_ids: list[str]
    elapsed_seconds: float
    request_delay_seconds: float
    concurrency: int
    rejected_urls: list[dict[str, str]] = field(default_factory=list)
    runtime_output_path: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FullCorpusPilot:
    def __init__(
        self,
        config: PilotConfig | None = None,
        *,
        fetch_xml: Callable[[str], str] = default_fetch_xml,
        browser_fetcher: ArticleFetcher | None = None,
        robots_allowed: Callable[[Sequence[str]], bool] = lambda urls: default_robots_allowed(urls),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config or PilotConfig()
        self.fetch_xml = fetch_xml
        self.browser_fetcher = browser_fetcher or BrowserArticleFetcher(retries=2, backoff_seconds=3)
        self.robots_allowed = robots_allowed
        self.sleep = sleep
        self.store = ArticleStore(self.config.output_dir / "article_store" / "articles.json")

    def run(self) -> PilotSummary:
        started_at = time.monotonic()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        failures: list[PilotFailure] = []
        parser_quality_issues: list[str] = []

        existing_articles = self.store.list_articles()
        if not self.config.dry_run and len(existing_articles) >= self.config.limit:
            selected_urls = [article.url for article in existing_articles[: self.config.limit]]
            summary = self._build_summary(
                status=_status_for_pilot(
                    target_count=self.config.limit,
                    selected_count=len(selected_urls),
                    duplicate_count=0,
                    imported_count=len(selected_urls),
                    failures=[],
                    stored_articles=existing_articles[: self.config.limit],
                ),
                discovered_count=len(selected_urls),
                canonical_url_count=len(selected_urls),
                duplicate_count=0,
                selected_urls=selected_urls,
                attempted_count=0,
                imported_articles=existing_articles[: self.config.limit],
                failures=[],
                parser_quality_issues=[],
                skipped_count=len(selected_urls),
                rejected_urls=[],
                elapsed_seconds=time.monotonic() - started_at,
            )
            self._write_runtime_files(summary, completed_urls=selected_urls)
            return summary

        try:
            discovered_urls = self._load_candidates()
        except Exception as exc:  # noqa: BLE001 - discovery/network failures must be summarized.
            reason = _failure_reason(exc)
            failures.append(PilotFailure(url=self.config.feed_url, reason=reason, category=classify_failure_reason(reason)))
            discovered_urls = [article.url for article in existing_articles]
            discovered_urls.extend(self.config.seed_urls)
            discovered_urls.extend(self.config.manual_urls)
            if not discovered_urls:
                summary = self._build_summary(
                    status="BLOCKED",
                    discovered_count=0,
                    canonical_url_count=0,
                    duplicate_count=0,
                    selected_urls=[],
                    attempted_count=0,
                    imported_articles=[],
                    failures=failures,
                    parser_quality_issues=parser_quality_issues,
                    skipped_count=0,
                    rejected_urls=[],
                    elapsed_seconds=time.monotonic() - started_at,
                )
                self._write_runtime_files(summary, completed_urls=[])
                return summary

        canonical = canonicalize_article_urls(discovered_urls)
        selected_urls = canonical.canonical_urls[: self.config.limit]
        skipped_count = 0

        if self.config.dry_run:
            skipped_count = max(canonical.canonical_url_count - len(selected_urls), 0)
            summary = self._build_summary(
                status="CONDITIONAL",
                discovered_count=canonical.discovered_count,
                canonical_url_count=canonical.canonical_url_count,
                duplicate_count=canonical.duplicate_count,
                selected_urls=selected_urls,
                attempted_count=0,
                imported_articles=[],
                failures=failures,
                parser_quality_issues=parser_quality_issues,
                skipped_count=skipped_count,
                rejected_urls=canonical.rejected_urls,
                elapsed_seconds=time.monotonic() - started_at,
            )
            self._write_runtime_files(summary, completed_urls=[])
            return summary

        if not self.robots_allowed(canonical.canonical_urls):
            failures.append(PilotFailure(url=self.config.feed_url, reason="robots/source policy not confirmed", category="permanent_failure"))
            selected_existing_urls = [article.url for article in existing_articles[: self.config.limit]]
            summary = self._build_summary(
                status="CONDITIONAL" if selected_existing_urls else "BLOCKED",
                discovered_count=canonical.discovered_count,
                canonical_url_count=canonical.canonical_url_count,
                duplicate_count=canonical.duplicate_count,
                selected_urls=selected_existing_urls,
                attempted_count=0,
                imported_articles=existing_articles[: self.config.limit],
                failures=failures,
                parser_quality_issues=parser_quality_issues,
                skipped_count=len(selected_existing_urls),
                rejected_urls=canonical.rejected_urls,
                elapsed_seconds=time.monotonic() - started_at,
            )
            self._write_runtime_files(summary, completed_urls=selected_existing_urls)
            return summary

        completed_urls = self._read_completed_urls()
        imported_articles: list[ParsedArticle] = []
        attempted_count = 0
        selected_urls = [article.url for article in existing_articles[: self.config.limit]]
        skipped_count += len(selected_urls)
        consecutive_failures = 0

        for url in canonical.canonical_urls:
            if len(selected_urls) >= self.config.limit:
                break
            if url in completed_urls:
                if url not in selected_urls:
                    selected_urls.append(url)
                    skipped_count += 1
                continue
            if attempted_count > 0:
                self.sleep(self.config.delay_seconds)
            attempted_count += 1

            try:
                result = self.browser_fetcher.fetch(url)
                article = parse_article_html(result.html, url=url)
                quality_issues = _article_quality_issues(article)
                if quality_issues:
                    parser_quality_issues.extend(f"{url}: {issue}" for issue in quality_issues)
                    failures.append(PilotFailure(url=url, reason="; ".join(quality_issues), category="skipped_non_article_or_legacy_page"))
                    consecutive_failures += 1
                    if consecutive_failures >= self.config.max_consecutive_failures:
                        break
                    continue
                stored = self.store.upsert(article)
                imported_articles.append(article)
                completed_urls.append(stored.url)
                selected_urls.append(stored.url)
                consecutive_failures = 0
            except Exception as exc:  # noqa: BLE001 - keep external fetch/parser detail.
                reason = _failure_reason(exc)
                failures.append(PilotFailure(url=url, reason=reason, category=classify_failure_reason(reason)))
                consecutive_failures += 1
                if consecutive_failures >= self.config.max_consecutive_failures:
                    break

        for failure in getattr(self.browser_fetcher, "failures", []):
            url = failure.get("url", "")
            reason = failure.get("reason", "unknown failure")
            if not any(existing.url == url for existing in failures):
                failures.append(PilotFailure(url=url, reason=reason, category=classify_failure_reason(reason)))

        stored_articles = self.store.list_articles()
        status = _status_for_pilot(
            target_count=self.config.limit,
            selected_count=len(selected_urls),
            duplicate_count=canonical.duplicate_count,
            imported_count=len(stored_articles),
            failures=failures,
            stored_articles=stored_articles,
        )
        summary = self._build_summary(
            status=status,
            discovered_count=canonical.discovered_count,
            canonical_url_count=canonical.canonical_url_count,
            duplicate_count=canonical.duplicate_count,
            selected_urls=selected_urls,
            attempted_count=attempted_count,
            imported_articles=stored_articles,
            failures=failures,
            parser_quality_issues=parser_quality_issues,
            skipped_count=skipped_count,
            rejected_urls=canonical.rejected_urls,
            elapsed_seconds=time.monotonic() - started_at,
        )
        self._write_runtime_files(summary, completed_urls=completed_urls)
        return summary

    def _load_candidates(self) -> list[str]:
        if self.config.seed_urls:
            return list(self.config.seed_urls) + list(self.config.manual_urls)
        candidates = list(self.config.manual_urls)
        rss_urls = _discover_rss_candidate_urls(self.config.feed_url, fetch_xml=self.fetch_xml, max_items=self.config.max_limit)
        return rss_urls + candidates

    def _build_summary(
        self,
        *,
        status: str,
        discovered_count: int,
        canonical_url_count: int,
        duplicate_count: int,
        selected_urls: list[str],
        attempted_count: int,
        imported_articles: list[ParsedArticle | StoredArticle],
        failures: list[PilotFailure],
        parser_quality_issues: list[str],
        skipped_count: int,
        rejected_urls: list[RejectedUrl],
        elapsed_seconds: float,
    ) -> PilotSummary:
        validation = ArticleQualityValidator(sample_size=max(len(imported_articles), 1)).validate(imported_articles)
        failed_url_categories = _failure_counts(failures)
        metadata_completeness_rate = _metadata_completeness_rate(imported_articles)
        invalid_candidate_count = _invalid_candidate_count(failed_url_categories)
        invalid_imported_content_count = _invalid_imported_content_count(imported_articles)
        invalid_content_count = invalid_candidate_count + invalid_imported_content_count
        return PilotSummary(
            status=status,
            target_count=self.config.limit,
            discovered_url_count=discovered_count,
            canonical_url_count=canonical_url_count,
            duplicate_count=duplicate_count,
            selected_count=len(selected_urls),
            attempted_count=attempted_count,
            imported_count=len(imported_articles),
            failed_count=len(failures),
            skipped_count=skipped_count,
            content_completeness_rate=validation.content_completeness_rate,
            formula_valid_rate=1.0 if validation.formulas_valid else 0.0,
            metadata_completeness_rate=metadata_completeness_rate,
            short_content_count=_short_content_count(imported_articles),
            invalid_content_count=invalid_content_count,
            invalid_candidate_count=invalid_candidate_count,
            invalid_imported_content_count=invalid_imported_content_count,
            skipped_non_article_or_legacy_page=failed_url_categories.get("skipped_non_article_or_legacy_page", 0),
            parser_quality_issues=parser_quality_issues,
            browser_transient_failures=failed_url_categories.get("browser_transient", 0),
            permanent_failures=failed_url_categories.get("permanent_failure", 0),
            failed_url_categories=failed_url_categories,
            sample_article_ids=[urlsplit(article.url).path.rsplit("/", 1)[-1] for article in imported_articles],
            elapsed_seconds=round(elapsed_seconds, 3),
            request_delay_seconds=self.config.delay_seconds,
            concurrency=self.config.concurrency,
            rejected_urls=[asdict(item) for item in rejected_urls],
            runtime_output_path=str(self.config.output_dir),
        )

    def _write_runtime_files(self, summary: PilotSummary, *, completed_urls: list[str]) -> None:
        if not completed_urls:
            completed_urls = self._read_completed_urls()
        if not completed_urls:
            completed_urls = [article.url for article in self.store.list_articles()]
        (self.config.output_dir / "validation_summary.json").write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.config.output_dir / "progress.json").write_text(
            json.dumps({"completed_urls": sorted(set(completed_urls))}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        failures = []
        for category, count in summary.failed_url_categories.items():
            failures.append({"category": category, "count": count})
        failed_path = self.config.output_dir / "failed_urls.jsonl"
        failed_path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in failures),
            encoding="utf-8",
        )

    def _read_completed_urls(self) -> list[str]:
        progress_path = self.config.output_dir / "progress.json"
        if not progress_path.exists():
            return [article.url for article in self.store.list_articles()]
        try:
            data = json.loads(progress_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [article.url for article in self.store.list_articles()]
        urls = data.get("completed_urls", [])
        completed_urls = [str(url) for url in urls if isinstance(url, str)]
        if completed_urls:
            return completed_urls
        return [article.url for article in self.store.list_articles()]


def classify_failure_reason(reason: str) -> str:
    normalized = reason.lower()
    if "content extraction" in normalized or "article body" in normalized or "empty html" in normalized:
        return "invalid_content"
    if "timeout" in normalized or "tls" in normalized or "handshake" in normalized:
        return "browser_transient"
    if "http status 403" in normalized or "http status 429" in normalized:
        return "browser_transient"
    if "robots" in normalized or "source policy" in normalized:
        return "permanent_failure"
    return "permanent_failure"


def default_robots_allowed(
    urls: Sequence[str],
    *,
    fetch_robots: Callable[[str, float], str] | None = None,
    timeout_seconds: float = 10,
) -> bool:
    if not urls:
        return True
    robots_url = "https://spaces.ac.cn/robots.txt"
    fetcher = fetch_robots or _fetch_robots_txt
    try:
        robots_text = fetcher(robots_url, timeout_seconds)
    except (OSError, URLError, TimeoutError):
        return False
    parser = RobotFileParser(robots_url)
    parser.parse(robots_text.splitlines())
    return all(parser.can_fetch(USER_AGENT, url) for url in urls)


def _fetch_robots_txt(url: str, timeout_seconds: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _article_quality_issues(article: ParsedArticle | StoredArticle) -> list[str]:
    report = ArticleQualityValidator(sample_size=1).validate([article])
    issues = [issue.split(": ", 1)[1] if ": " in issue else issue for issue in report.issues]
    if _metadata_keys_missing(article):
        issues.append("metadata missing required keys")
    if _contains_page_chrome(article.content):
        issues.append("sidebar/comment/share script/navigation contamination detected")
    return issues


def _invalid_candidate_count(failed_url_categories: dict[str, int]) -> int:
    return failed_url_categories.get("invalid_content", 0) + failed_url_categories.get("skipped_non_article_or_legacy_page", 0)


def _invalid_imported_content_count(articles: list[ParsedArticle | StoredArticle]) -> int:
    return sum(1 for article in articles if _article_quality_issues(article))


def _discover_rss_candidate_urls(
    feed_url: str,
    *,
    fetch_xml: Callable[[str], str],
    max_items: int,
) -> list[str]:
    root = ElementTree.fromstring(fetch_xml(feed_url))
    urls: list[str] = []
    items_seen = 0
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] != "item":
            continue
        if items_seen >= max_items:
            break
        items_seen += 1
        link = None
        guid = None
        for child in item:
            local_name = child.tag.rsplit("}", 1)[-1]
            if local_name == "link" and child.text:
                link = child.text.strip()
            if local_name == "guid" and child.text:
                guid = child.text.strip()
        if link or guid:
            urls.append(link or guid or "")
    return urls


def _metadata_keys_missing(article: ParsedArticle | StoredArticle) -> bool:
    if isinstance(article, StoredArticle):
        metadata = article.metadata
    else:
        metadata = {"date": article.date, "category": article.category, "references": article.references, "images": article.images}
    return not REQUIRED_METADATA_KEYS.issubset(metadata.keys())


def _contains_page_chrome(content: str) -> bool:
    lowered = content.lower()
    markers = ("发表评论", "登录后评论", "分享到", "shareto", "sidebar", "navigation")
    return any(marker in lowered for marker in markers)


def _failure_reason(exc: Exception) -> str:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, str):
        return reason
    return f"{type(exc).__name__}: {exc}"


def _failure_counts(failures: list[PilotFailure]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for failure in failures:
        counts[failure.category] = counts.get(failure.category, 0) + 1
    return counts


def _metadata_completeness_rate(articles: list[ParsedArticle | StoredArticle]) -> float:
    if not articles:
        return 1.0
    complete = sum(1 for article in articles if not _metadata_keys_missing(article))
    return complete / len(articles)


def _short_content_count(articles: list[ParsedArticle | StoredArticle]) -> int:
    return sum(1 for article in articles if len(article.content.strip()) < 300)


def _status_for_pilot(
    *,
    target_count: int,
    selected_count: int,
    duplicate_count: int,
    imported_count: int,
    failures: list[PilotFailure],
    stored_articles: list[ParsedArticle | StoredArticle],
) -> str:
    categories = _failure_counts(failures)
    validation = ArticleQualityValidator(sample_size=max(len(stored_articles), 1)).validate(stored_articles)
    metadata_rate = _metadata_completeness_rate(stored_articles)
    if _invalid_imported_content_count(stored_articles) > 0:
        return "BLOCKED"
    if selected_count < target_count and _invalid_candidate_count(categories) > 0:
        return "BLOCKED"
    if selected_count < target_count and categories.get("permanent_failure", 0) > 0:
        return "BLOCKED"
    if duplicate_count == 0 and selected_count >= target_count and imported_count >= target_count:
        if validation.content_completeness_rate >= 0.95 and validation.formulas_valid and metadata_rate >= 0.95:
            return "PASS"
    return "CONDITIONAL"
