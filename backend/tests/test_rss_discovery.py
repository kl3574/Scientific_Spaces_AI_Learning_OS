from app.crawler.rss import discover_rss_article_urls, parse_rss_article_urls


RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>科学空间|Scientific Spaces</title>
    <item>
      <title>first</title>
      <link>https://spaces.ac.cn/archives/11804</link>
    </item>
    <item>
      <title>duplicate with query</title>
      <link>https://spaces.ac.cn/archives/11804?utm_source=rss</link>
    </item>
    <item>
      <title>second with trailing slash</title>
      <link>https://spaces.ac.cn/archives/11784/</link>
    </item>
    <item>
      <title>not an article</title>
      <link>https://spaces.ac.cn/category/AI/</link>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_article_urls_filters_canonicalizes_and_deduplicates() -> None:
    urls = parse_rss_article_urls(RSS_FIXTURE, max_items=10)

    assert urls == [
        "https://spaces.ac.cn/archives/11804",
        "https://spaces.ac.cn/archives/11784",
    ]


def test_discover_rss_article_urls_uses_fetcher_and_max_items() -> None:
    calls: list[str] = []

    def fetch_xml(url: str) -> str:
        calls.append(url)
        return RSS_FIXTURE

    urls = discover_rss_article_urls(
        "https://spaces.ac.cn/feed",
        fetch_xml=fetch_xml,
        max_items=1,
    )

    assert calls == ["https://spaces.ac.cn/feed"]
    assert urls == ["https://spaces.ac.cn/archives/11804"]
