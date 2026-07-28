from pathlib import Path

import pytest

from app.export import printed_pdf
from app.export.printed_pdf import article_samples, normalize_text
from app.storage.article_store import StoredArticle


def test_article_samples_use_body_anchors_not_site_boilerplate() -> None:
    content = """
这两个程序都是为了天体力学服务的...

[![开普勒方程求根器-界面](https://example.test/image.png)](/attachment/842/)

采用牛顿法，精度是 $E-e\\cdot\\sin E-M < 10^{-10}$。
再次在众多高手前班门弄斧，羞愧...

当作是做一下记录吧。

如果您觉得本文还不错，欢迎分享/打赏本文。

如果您需要引用本文，请参考：

苏剑林. (Aug. 09, 2010). 《示例文章》[Blog post].
"""
    printed_text = normalize_text(
        """
这两个程序都是为了天体力学服务的
采用牛顿法，精度是
E - e sin E - M < 10 -10
再次在众多高手前班门弄斧，羞愧
当作是做一下记录吧
"""
    )

    samples = article_samples(content)

    assert samples
    assert all(sample in printed_text for sample in samples)
    assert all("打赏" not in sample for sample in samples)
    assert all("苏剑林" not in sample for sample in samples)


def test_article_samples_support_genuine_image_centric_short_post() -> None:
    content = """
迟来的合照...

[![夏令营合照](https://example.test/photo.jpg)](/attachment/1451/)

Lamost下的天文夏令营

如果您觉得本文还不错，欢迎分享/打赏本文。

苏剑林. (Jul. 27, 2011). 《Lamost下的天文夏令营》[Blog post].
"""

    assert article_samples(content) == [
        "迟来的合照",
        "lamost下的天文夏令营",
    ]


def test_pdf_validation_accepts_distributed_majority_when_caption_reorders(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    article = StoredArticle(
        id="article-layout",
        title="生成模型示例",
        url="https://spaces.ac.cn/archives/6612",
        content="""
这是第一段可靠的正文内容并用于打印验证。

这是可能被浮动布局重排的图片标题内容。

这是最后一段可靠的正文内容并用于打印验证。
""",
        metadata={
            "date": "2019-05-10",
            "category": "数学",
            "references": [],
            "images": [],
        },
    )
    samples = article_samples(article.content)
    assert len(samples) == 3
    pdf_text = f"{article.title}\n{samples[0]}\n{samples[2]}\n中文"
    pdf_info = "Pages:           1\nPage size:       595 x 842 pts (A4)\n"
    pdf_path = tmp_path / "article.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n" + b"x" * 2_048 + b"\n%%EOF\n")

    def fake_pdf_command(command: list[str]) -> str:
        return pdf_info if command[0] == "pdfinfo" else pdf_text

    monkeypatch.setattr(printed_pdf, "_run_pdf_command", fake_pdf_command)

    inspection = printed_pdf.inspect_printed_article_pdf(
        article,
        pdf_path,
        mathjax_rendered=False,
    )

    assert inspection.sample_count == 3
    assert inspection.matched_sample_count == 2
