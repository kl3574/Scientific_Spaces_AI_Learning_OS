from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.corpus.pilot import FullCorpusPilot, PilotConfig, classify_failure_reason, default_robots_allowed
from app.crawler.browser import BrowserFetchResult


RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <item><link>https://spaces.ac.cn/archives/6508</link></item>
    <item><link>https://kexue.fm/archives/6508?alias=1</link></item>
    <item><link>https://spaces.ac.cn/search?q=attention</link></item>
    <item><link>https://spaces.ac.cn/archives/11787</link></item>
  </channel>
</rss>
"""


def _rss_fixture_for_urls(urls: list[str]) -> str:
    items = "\n".join(f"    <item><link>{url}</link></item>" for url in urls)
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
{items}
  </channel>
</rss>
"""


def _output_dir(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "pilot"


def _article_html(title: str = "Attention 测试文章") -> str:
    return f"""
    <html>
      <head><title>{title} - 科学空间|Scientific Spaces</title></head>
      <body>
        <div id="content">
          <div class="Post">
            <h1>{title}</h1>
            <p>发布日期：2026-07-01 分类：数学研究 <a href="/category/math">数学研究</a></p>
            <div class="entry-content">
              <p>这是一篇用于 pilot 的正文，包含足够长度来验证内容抽取质量。</p>
              <p>Attention 机制通过 $q k^T$ 计算相关性，并保留数学公式。</p>
              <p>为了超过最小长度，这里继续描述正文内容，确保不是标题、导航、评论或者分享脚本。</p>
              <p>正文需要保持中文、Markdown、图片和参考文献元数据。这里继续补充有效正文内容。</p>
              <p>更多正文内容用于稳定通过 content completeness 检查，避免短内容误判。</p>
              <img src="/assets/example.png" />
              <h2>参考文献</h2>
              <ol><li><a href="https://spaces.ac.cn/archives/1">参考链接</a></li></ol>
            </div>
          </div>
        </div>
      </body>
    </html>
    """


class RecordingFetcher:
    def __init__(self, failures: dict[str, str] | None = None) -> None:
        self.calls: list[str] = []
        self.failures: list[dict[str, str]] = []
        self._failures = failures or {}

    def fetch(self, url: str) -> BrowserFetchResult:
        self.calls.append(url)
        if url in self._failures:
            reason = self._failures[url]
            self.failures.append({"url": url, "reason": reason})
            raise RuntimeError(reason)
        return BrowserFetchResult(
            url=url,
            html=_article_html(),
            title="Attention 测试文章",
            status=200,
            mathjax_available=True,
        )


def test_limit_greater_than_30_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="limit must be between 1 and 30"):
        PilotConfig(limit=31, output_dir=_output_dir(tmp_path))


def test_dry_run_does_not_fetch(tmp_path: Path) -> None:
    fetcher = RecordingFetcher()
    pilot = FullCorpusPilot(
        PilotConfig(limit=2, dry_run=True, output_dir=_output_dir(tmp_path)),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.discovered_url_count == 4
    assert summary.canonical_url_count == 2
    assert summary.duplicate_count == 1
    assert summary.selected_count == 2
    assert summary.attempted_count == 0
    assert fetcher.calls == []


def test_output_path_is_under_ignored_runtime_directory(tmp_path: Path) -> None:
    config = PilotConfig(output_dir=_output_dir(tmp_path))

    assert ".local_data" in config.output_dir.parts
    assert config.output_dir.parts[-2:] == ("corpus", "pilot")


def test_validation_summary_computes_metrics_and_writes_runtime_files(tmp_path: Path) -> None:
    output_dir = _output_dir(tmp_path)
    fetcher = RecordingFetcher()
    pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir, delay_seconds=3),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.status == "CONDITIONAL"
    assert summary.attempted_count == 1
    assert summary.imported_count == 1
    assert summary.invalid_content_count == 0
    assert summary.content_completeness_rate == 1.0
    assert summary.formula_valid_rate == 1.0
    assert summary.metadata_completeness_rate == 1.0
    assert summary.request_delay_seconds == 3
    assert summary.concurrency == 1
    assert (output_dir / "validation_summary.json").exists()
    assert (output_dir / "progress.json").exists()
    assert json.loads((output_dir / "validation_summary.json").read_text(encoding="utf-8"))["imported_count"] == 1


def test_invalid_content_is_classified_as_blocker(tmp_path: Path) -> None:
    class InvalidContentFetcher(RecordingFetcher):
        def fetch(self, url: str) -> BrowserFetchResult:
            self.calls.append(url)
            return BrowserFetchResult(url=url, html="<html><title>Only title</title></html>", title="Only title", status=200, mathjax_available=False)

    pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=_output_dir(tmp_path)),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=InvalidContentFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.status == "BLOCKED"
    assert summary.imported_count == 0
    assert summary.invalid_content_count == 1
    assert summary.parser_quality_issues


def test_transient_failures_are_classified_separately(tmp_path: Path) -> None:
    assert classify_failure_reason("TimeoutError: navigation timed out") == "browser_transient"
    assert classify_failure_reason("HTTP status 403") == "browser_transient"
    assert classify_failure_reason("HTTP status 429") == "browser_transient"
    assert classify_failure_reason("content extraction failed: article body not detected") == "invalid_content"

    failing_url = "https://spaces.ac.cn/archives/6508"
    pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=_output_dir(tmp_path)),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=RecordingFetcher({failing_url: "TimeoutError: navigation timed out"}),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.status == "CONDITIONAL"
    assert summary.browser_transient_failures == 1
    assert summary.failed_url_categories == {"browser_transient": 1}


def test_discovery_failure_is_recorded_as_blocker(tmp_path: Path) -> None:
    pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=_output_dir(tmp_path)),
        fetch_xml=lambda _url: (_ for _ in ()).throw(TimeoutError("TLS handshake timed out")),
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.status == "BLOCKED"
    assert summary.discovered_url_count == 0
    assert summary.failed_url_categories == {"browser_transient": 1}


def test_discovery_failure_preserves_existing_progress(tmp_path: Path) -> None:
    output_dir = _output_dir(tmp_path)
    output_dir.mkdir(parents=True)
    progress_path = output_dir / "progress.json"
    progress_path.write_text(
        json.dumps({"completed_urls": ["https://spaces.ac.cn/archives/6508"]}),
        encoding="utf-8",
    )

    pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir),
        fetch_xml=lambda _url: (_ for _ in ()).throw(TimeoutError("TLS handshake timed out")),
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = pilot.run()

    assert summary.status == "BLOCKED"
    assert json.loads(progress_path.read_text(encoding="utf-8")) == {
        "completed_urls": ["https://spaces.ac.cn/archives/6508"]
    }


def test_resume_uses_article_store_when_progress_is_missing(tmp_path: Path) -> None:
    output_dir = _output_dir(tmp_path)
    first_fetcher = RecordingFetcher()
    first_pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=first_fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )
    first_summary = first_pilot.run()
    assert first_summary.imported_count == 1
    (output_dir / "progress.json").unlink()

    second_fetcher = RecordingFetcher()
    second_pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=second_fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    second_summary = second_pilot.run()

    assert second_summary.attempted_count == 0
    assert second_summary.imported_count == 1
    assert second_fetcher.calls == []


def test_resume_uses_article_store_before_source_discovery_when_limit_is_satisfied(tmp_path: Path) -> None:
    output_dir = _output_dir(tmp_path)
    first_pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir),
        fetch_xml=lambda _url: RSS_FIXTURE,
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )
    assert first_pilot.run().imported_count == 1

    second_fetcher = RecordingFetcher()
    second_pilot = FullCorpusPilot(
        PilotConfig(limit=1, output_dir=output_dir),
        fetch_xml=lambda _url: (_ for _ in ()).throw(TimeoutError("source unavailable")),
        browser_fetcher=second_fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = second_pilot.run()

    assert summary.status == "CONDITIONAL"
    assert summary.discovered_url_count == 1
    assert summary.selected_count == 1
    assert summary.attempted_count == 0
    assert summary.imported_count == 1
    assert summary.browser_transient_failures == 0
    assert second_fetcher.calls == []


def test_cumulative_resume_to_20_counts_existing_and_new_articles(tmp_path: Path) -> None:
    urls = [f"https://spaces.ac.cn/archives/{1000 + index}" for index in range(20)]
    rss_fixture = _rss_fixture_for_urls(urls)
    output_dir = _output_dir(tmp_path)

    first_pilot = FullCorpusPilot(
        PilotConfig(limit=10, output_dir=output_dir),
        fetch_xml=lambda _url: rss_fixture,
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )
    assert first_pilot.run().status == "PASS"

    second_fetcher = RecordingFetcher()
    second_pilot = FullCorpusPilot(
        PilotConfig(limit=20, output_dir=output_dir, delay_seconds=5),
        fetch_xml=lambda _url: rss_fixture,
        browser_fetcher=second_fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = second_pilot.run()

    assert summary.status == "PASS"
    assert summary.selected_count == 20
    assert summary.imported_count == 20
    assert summary.attempted_count == 10
    assert summary.skipped_count == 10
    assert second_fetcher.calls == urls[10:20]
    assert summary.request_delay_seconds == 5
    assert summary.concurrency == 1


def test_transient_discovery_failure_preserves_existing_success_summary(tmp_path: Path) -> None:
    urls = [f"https://spaces.ac.cn/archives/{2000 + index}" for index in range(10)]
    rss_fixture = _rss_fixture_for_urls(urls)
    output_dir = _output_dir(tmp_path)

    first_pilot = FullCorpusPilot(
        PilotConfig(limit=10, output_dir=output_dir),
        fetch_xml=lambda _url: rss_fixture,
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )
    assert first_pilot.run().status == "PASS"

    second_pilot = FullCorpusPilot(
        PilotConfig(limit=20, output_dir=output_dir, delay_seconds=5),
        fetch_xml=lambda _url: (_ for _ in ()).throw(TimeoutError("TLS handshake timed out")),
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = second_pilot.run()
    written_summary = json.loads((output_dir / "validation_summary.json").read_text(encoding="utf-8"))

    assert summary.status == "CONDITIONAL"
    assert summary.imported_count == 10
    assert summary.attempted_count == 0
    assert summary.failed_url_categories == {"browser_transient": 1}
    assert written_summary["imported_count"] == 10
    assert written_summary["status"] == "CONDITIONAL"


def test_manual_urls_can_complete_cumulative_target_when_rss_is_transient(tmp_path: Path) -> None:
    existing_urls = [f"https://spaces.ac.cn/archives/{3000 + index}" for index in range(10)]
    manual_urls = [f"https://spaces.ac.cn/archives/{4000 + index}" for index in range(10)]
    output_dir = _output_dir(tmp_path)

    first_pilot = FullCorpusPilot(
        PilotConfig(limit=10, output_dir=output_dir),
        fetch_xml=lambda _url: _rss_fixture_for_urls(existing_urls),
        browser_fetcher=RecordingFetcher(),
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )
    assert first_pilot.run().status == "PASS"

    second_fetcher = RecordingFetcher()
    second_pilot = FullCorpusPilot(
        PilotConfig(limit=20, output_dir=output_dir, delay_seconds=5, manual_urls=tuple(manual_urls)),
        fetch_xml=lambda _url: (_ for _ in ()).throw(TimeoutError("TLS handshake timed out")),
        browser_fetcher=second_fetcher,
        robots_allowed=lambda _urls: True,
        sleep=lambda _seconds: None,
    )

    summary = second_pilot.run()

    assert summary.status == "PASS"
    assert summary.selected_count == 20
    assert summary.imported_count == 20
    assert summary.attempted_count == 10
    assert summary.skipped_count == 10
    assert summary.failed_url_categories == {"browser_transient": 1}
    assert second_fetcher.calls == manual_urls


def test_default_robots_allowed_fails_closed_on_timeout() -> None:
    def timeout_fetcher(_url: str, _timeout: float) -> str:
        raise TimeoutError("robots timed out")

    assert default_robots_allowed(["https://spaces.ac.cn/archives/6508"], fetch_robots=timeout_fetcher) is False
