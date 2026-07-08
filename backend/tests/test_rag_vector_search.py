from app.rag.chunking import ArticleChunk
from app.rag.embeddings import FakeEmbeddingProvider
from app.rag.vector_store import FaissVectorStore


def make_chunk(index: int, content: str) -> ArticleChunk:
    return ArticleChunk(
        article_id=f"article-{index}",
        article_title=f"Article {index}",
        article_url=f"https://spaces.ac.cn/archives/{index}",
        section_title=f"Section {index}",
        chunk_index=index,
        content=content,
    )


def test_fake_embedding_provider_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimension=16)

    first = provider.embed(["attention query key"])[0]
    second = provider.embed(["attention query key"])[0]

    assert first == second
    assert len(first) == 16


def test_faiss_vector_store_returns_relevant_chunks() -> None:
    provider = FakeEmbeddingProvider(dimension=32)
    chunks = [
        make_chunk(0, "attention query key value transformer"),
        make_chunk(1, "matrix function Taylor approximation"),
    ]
    store = FaissVectorStore.from_chunks(chunks, provider)

    results = store.search("query key attention", top_k=1, embedding_provider=provider)

    assert len(results) == 1
    assert results[0].chunk.article_id == "article-0"
    assert results[0].chunk.section_title == "Section 0"


def test_faiss_vector_store_empty_index_returns_empty_results() -> None:
    provider = FakeEmbeddingProvider(dimension=32)
    store = FaissVectorStore.empty(dimension=32)

    assert store.search("attention", top_k=5, embedding_provider=provider) == []
