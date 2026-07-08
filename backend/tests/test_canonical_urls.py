from __future__ import annotations

from app.crawler.canonical import canonicalize_article_url, canonicalize_article_urls, extract_archive_id


def test_canonicalize_spaces_article_url() -> None:
    assert canonicalize_article_url("http://www.spaces.ac.cn/archives/6508/?utm=ignored#comments") == (
        "https://spaces.ac.cn/archives/6508"
    )
    assert extract_archive_id("https://spaces.ac.cn/archives/6508") == "6508"


def test_canonicalize_kexue_alias() -> None:
    assert canonicalize_article_url("https://kexue.fm/archives/11787") == (
        "https://spaces.ac.cn/archives/11787"
    )


def test_reject_non_article_url() -> None:
    assert canonicalize_article_url("https://spaces.ac.cn/search?q=attention") is None
    assert canonicalize_article_url("https://spaces.ac.cn/content.html") is None
    assert canonicalize_article_url("https://example.com/archives/6508") is None
    assert canonicalize_article_url("https://spaces.ac.cn/archives/not-an-id") is None


def test_dedupe_urls_after_canonicalization() -> None:
    summary = canonicalize_article_urls(
        [
            "http://spaces.ac.cn/archives/6508",
            "https://www.spaces.ac.cn/archives/6508/",
            "https://kexue.fm/archives/6508?from=alias",
            "https://spaces.ac.cn/archives/11787",
            "https://spaces.ac.cn/search?q=attention",
        ]
    )

    assert summary.canonical_urls == [
        "https://spaces.ac.cn/archives/6508",
        "https://spaces.ac.cn/archives/11787",
    ]
    assert summary.duplicate_count == 2
    assert summary.rejected_count == 1
