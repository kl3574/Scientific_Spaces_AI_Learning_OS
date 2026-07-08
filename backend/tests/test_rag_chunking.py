from app.rag.chunking import chunk_article


def test_chunk_article_uses_markdown_sections_and_preserves_source_metadata() -> None:
    chunks = chunk_article(
        article_id="article-1",
        article_title="Attention机制",
        article_url="https://spaces.ac.cn/archives/6508",
        content="""# Attention机制

开头内容。

## Query Key Value

第一段解释。

$$
QK^T
$$

第二段解释。

## Code Example

```python
def score(q, k):
    return q @ k.T
```
""",
    )

    assert [chunk.section_title for chunk in chunks] == ["Attention机制", "Query Key Value", "Code Example"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert all(chunk.article_id == "article-1" for chunk in chunks)
    assert all(chunk.article_title == "Attention机制" for chunk in chunks)
    assert all(chunk.article_url == "https://spaces.ac.cn/archives/6508" for chunk in chunks)
    assert "$$\nQK^T\n$$" in chunks[1].content
    assert "```python\ndef score(q, k):\n    return q @ k.T\n```" in chunks[2].content


def test_chunk_article_does_not_split_equation_or_code_blocks() -> None:
    chunks = chunk_article(
        article_id="article-2",
        article_title="公式和代码",
        article_url="https://spaces.ac.cn/archives/1",
        content="""## Math

文本。

$$
a = b + c
d = e + f
$$

```text
line 1
line 2
```
""",
    )

    assert len(chunks) == 1
    assert chunks[0].content.count("$$") == 2
    assert chunks[0].content.count("```") == 2
    assert "a = b + c\nd = e + f" in chunks[0].content
    assert "line 1\nline 2" in chunks[0].content
