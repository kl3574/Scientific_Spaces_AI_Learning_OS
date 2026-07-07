from pathlib import Path

from app.converter.markdown import html_to_markdown
from app.parser.article import parse_article_html


FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_article.html"
LIVE_STRUCTURE_FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_live_post_article.html"


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


def test_parse_scientific_spaces_live_post_structure_uses_article_body_not_sidebar() -> None:
    html = LIVE_STRUCTURE_FIXTURE.read_text(encoding="utf-8")

    article = parse_article_html(html, url="https://spaces.ac.cn/archives/11777")

    assert article.title == "流形上的最速下降：6. Muon + 双旋转"
    assert article.category == "数学研究"
    assert "我们知道，用Adam、Muon等优化器更新矩阵参数时" in article.content
    assert "这段正文模拟科学空间真实文章主体" in article.content
    assert "recent comment with stray dollar" not in article.content
    assert "comment area must not be parsed" not in article.content
    assert "一键分享" not in article.content
    assert "shareTo" not in article.content
    assert "$X=U\\\\Sigma V^T$" in article.content
    assert "$$G=UV^T$$" in article.content
    assert article.images == ["https://spaces.ac.cn/usr/uploads/muon.png"]
    assert article.references == [
        {
            "title": "Muon optimizer paper",
            "url": "https://arxiv.org/abs/2502.16982",
        }
    ]
