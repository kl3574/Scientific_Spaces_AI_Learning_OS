from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.fake import FakeLLMProvider
from app.llm.provider import LLMProvider
from app.rag.chunking import ArticleChunk, chunk_article
from app.rag.embeddings import EmbeddingProvider, FakeEmbeddingProvider
from app.rag.vector_store import FaissVectorStore
from app.services.article_reader import article_store_path
from app.storage.article_store import ArticleStore


NO_SOURCE_ANSWER = "无法基于当前资料回答。"


@dataclass
class RagIndex:
    article_count: int
    chunks: list[ArticleChunk]
    vector_store: FaissVectorStore


class RagService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.index: RagIndex | None = None

    def build_index(self) -> dict[str, int]:
        articles = ArticleStore(article_store_path()).list_articles()
        chunks: list[ArticleChunk] = []
        for article in articles:
            chunks.extend(
                chunk_article(
                    article_id=article.id,
                    article_title=article.title,
                    article_url=article.url,
                    content=article.content,
                )
            )
        vector_store = FaissVectorStore.from_chunks(chunks, self.embedding_provider)
        self.index = RagIndex(article_count=len(articles), chunks=chunks, vector_store=vector_store)
        return {"article_count": len(articles), "chunk_count": len(chunks)}

    def answer(self, *, question: str, top_k: int = 5) -> dict[str, Any]:
        if self.index is None:
            self.build_index()
        if self.index is None or not self.index.chunks:
            return {"answer": NO_SOURCE_ANSWER, "sources": []}

        results = self.index.vector_store.search(question, top_k=top_k, embedding_provider=self.embedding_provider)
        if not results:
            return {"answer": NO_SOURCE_ANSWER, "sources": []}

        contexts = [
            {
                "content": result.chunk.content,
                "article_title": result.chunk.article_title,
                "section_title": result.chunk.section_title,
            }
            for result in results
        ]
        answer = self.llm_provider.chat(question=question, contexts=contexts)
        sources = [result.chunk.source() for result in results]
        if not sources:
            return {"answer": NO_SOURCE_ANSWER, "sources": []}
        return {"answer": answer, "sources": sources}


_SERVICE = RagService()


def get_rag_service() -> RagService:
    return _SERVICE


def reset_rag_service() -> None:
    global _SERVICE
    _SERVICE = RagService()
