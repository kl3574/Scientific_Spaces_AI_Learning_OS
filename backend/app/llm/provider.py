from __future__ import annotations

import json
import os
import urllib.request
from typing import Mapping, Protocol


class LLMProvider(Protocol):
    def chat(self, *, question: str, contexts: list[Mapping[str, str]]) -> str:
        """Return an answer grounded in the provided contexts."""


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("OPENAI_CHAT_MODEL") or "gpt-4o-mini"

    def chat(self, *, question: str, contexts: list[Mapping[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI-compatible chat")
        context_text = "\n\n".join(
            f"[{index + 1}] {context['article_title']} / {context['section_title']}\n{context['content']}"
            for index, context in enumerate(contexts)
        )
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer only from the supplied contexts. If the contexts are insufficient, say so.",
                        },
                        {"role": "user", "content": f"Question: {question}\n\nContexts:\n{context_text}"},
                    ],
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload["choices"][0]["message"]["content"])
