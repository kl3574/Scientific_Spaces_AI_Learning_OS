from pathlib import Path

from app.converter.markdown import html_to_markdown
from app.parser.article import parse_article_html


FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_article.html"
LIVE_STRUCTURE_FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_live_post_article.html"
ARTICLE_11787_FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_11787_article.html"


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


def test_parse_scientific_spaces_11787_edge_structure_preserves_article_body() -> None:
    html = ARTICLE_11787_FIXTURE.read_text(encoding="utf-8")

    article = parse_article_html(html, url="https://spaces.ac.cn/archives/11787")

    assert article.title == "矩阵函数近似中的暴力美学"
    assert article.category == "数学研究"
    assert "此前，我们在《矩阵平方根和逆平方根的高效计算》" in article.content
    assert "本文继续讨论矩阵函数近似的构造方式" in article.content
    assert "sidebar comment should never become article content" not in article.content
    assert "comment area should not be parsed" not in article.content
    assert "navigation should not become content" not in article.content
    assert "shareTo" not in article.content
    assert "$\\\\newcommand{\\\\msign}{\\\\mathop{\\\\text{msign}}}\\\\msign$" in article.content
    assert "$$X_{k+1}=\\\\frac{1}{2}X_k(3I-X_k^2)$$" in article.content
    assert article.images == ["https://spaces.ac.cn/usr/uploads/matrix-function.png"]
    assert article.references == [
        {
            "title": "Matrix function approximation",
            "url": "https://arxiv.org/abs/2506.10935",
        }
    ]


def test_parse_legacy_postcontent_uses_body_and_drops_print_chrome() -> None:
    html = """
    <html>
      <head><title>欢迎来到科学空间 - 科学空间|Scientific Spaces</title></head>
      <body>
        <div id="Header">site header</div>
        <div id="Sidebar">recent comment with $broken</div>
        <div id="content">
          <div class="Post">
            <h1>欢迎来到科学空间</h1>
            <p>发布日期：2009-01-01 分类：站点日志 <a href="/category/site">站点日志</a></p>
            <div id="share">分享到</div>
            <div id="PostContent">
              <p>这里是早期页面的正文内容，用于介绍科学空间的主要主题。</p>
              <p>正文虽然不长，但包含完整句子和数学公式 $E=mc^2$。</p>
              <img src="/usr/uploads/legacy.png" />
              <h2>参考资料</h2>
              <ul><li><a href="https://spaces.ac.cn/archives/100">历史文章</a></li></ul>
            </div>
            <div id="PostComment">comment area must not be parsed</div>
            <div class="navigation">navigation should not become content</div>
          </div>
        </div>
        <div id="Footer">footer</div>
      </body>
    </html>
    """

    article = parse_article_html(html, url="https://spaces.ac.cn/archives/12")

    assert article.title == "欢迎来到科学空间"
    assert article.date == "2009-01-01"
    assert article.category == "站点日志"
    assert "这里是早期页面的正文内容" in article.content
    assert "$E=mc^2$" in article.content
    assert "site header" not in article.content
    assert "recent comment" not in article.content
    assert "分享到" not in article.content
    assert "comment area must not be parsed" not in article.content
    assert "navigation should not become content" not in article.content
    assert "footer" not in article.content
    assert article.images == ["https://spaces.ac.cn/usr/uploads/legacy.png"]
    assert article.references == [
        {
            "title": "历史文章",
            "url": "https://spaces.ac.cn/archives/100",
        }
    ]
