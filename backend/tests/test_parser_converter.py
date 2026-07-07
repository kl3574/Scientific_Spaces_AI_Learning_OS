from pathlib import Path

from app.converter.markdown import html_to_markdown
from app.parser.article import parse_article_html


FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_article.html"


def test_parse_article_html_extracts_required_article_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")

    article = parse_article_html(html, url="https://spaces.ac.cn/archives/1234")

    assert article.title == "Attention机制的一个直观解释"
    assert article.url == "https://spaces.ac.cn/archives/1234"
    assert article.date == "2024-01-02"
    assert article.category == "信息时代"
    assert article.images == ["https://spaces.ac.cn/usr/uploads/attention.png"]
    assert article.references == [
        {
            "title": "Attention Is All You Need",
            "url": "https://arxiv.org/abs/1706.03762",
        }
    ]
    assert "$QK^T / \\sqrt{d}$" in article.content


def test_html_to_markdown_preserves_structure_math_images_and_code() -> None:
    html = FIXTURE.read_text(encoding="utf-8")

    markdown = html_to_markdown(html, base_url="https://spaces.ac.cn/")

    assert "# Attention机制的一个直观解释" in markdown
    assert "## 动机" in markdown
    assert "$QK^T / \\sqrt{d}$" in markdown
    assert "![attention diagram](https://spaces.ac.cn/usr/uploads/attention.png)" in markdown
    assert "```" in markdown
    assert "score = q @ k.T" in markdown
