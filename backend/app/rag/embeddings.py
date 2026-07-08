from __future__ import annotations

import hashlib
import math
import os
import re
import urllib.request
import json
from typing import Protocol


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text."""


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_normalize(_embed_text(text, self.dimension)) for text in texts]


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int = 1536,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI-compatible embeddings")
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        vectors = [item["embedding"] for item in sorted(payload["data"], key=lambda item: item["index"])]
        if vectors:
            self.dimension = len(vectors[0])
        return vectors


_ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _embed_text(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    for token in _tokens(text):
        index = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dimension
        vector[index] += 1.0
    return vector


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    tokens = _ASCII_TOKEN_RE.findall(lowered)
    cjk_chars = _CJK_RE.findall(lowered)
    tokens.extend(cjk_chars)
    tokens.extend("".join(pair) for pair in zip(cjk_chars, cjk_chars[1:]))
    return tokens


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
