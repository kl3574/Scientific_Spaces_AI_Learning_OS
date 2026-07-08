from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np

from app.rag.chunking import ArticleChunk
from app.rag.embeddings import EmbeddingProvider


@dataclass(frozen=True)
class SearchResult:
    chunk: ArticleChunk
    score: float


class FaissVectorStore:
    def __init__(self, *, index: faiss.IndexFlatL2, chunks: list[ArticleChunk]) -> None:
        self.index = index
        self.chunks = chunks

    @classmethod
    def empty(cls, dimension: int) -> "FaissVectorStore":
        return cls(index=faiss.IndexFlatL2(dimension), chunks=[])

    @classmethod
    def from_chunks(cls, chunks: list[ArticleChunk], embedding_provider: EmbeddingProvider) -> "FaissVectorStore":
        if not chunks:
            return cls.empty(embedding_provider.dimension)
        vectors = np.asarray(embedding_provider.embed([chunk.content for chunk in chunks]), dtype="float32")
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)
        return cls(index=index, chunks=chunks)

    def search(self, query: str, *, top_k: int, embedding_provider: EmbeddingProvider) -> list[SearchResult]:
        if top_k <= 0 or not self.chunks or self.index.ntotal == 0:
            return []
        query_vector = np.asarray(embedding_provider.embed([query]), dtype="float32")
        distances, indices = self.index.search(query_vector, min(top_k, len(self.chunks)))
        results: list[SearchResult] = []
        for distance, index in zip(distances[0], indices[0]):
            if index < 0:
                continue
            results.append(SearchResult(chunk=self.chunks[int(index)], score=float(distance)))
        return results
