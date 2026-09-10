from __future__ import annotations

import json
import os
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Protocol


class LLMProvider(Protocol):
    def chat(self, *, question: str, contexts: list[Mapping[str, str]]) -> str:
        """Return an answer grounded in the provided contexts."""


@dataclass(frozen=True)
class ChatRequest:
    """Internal request: trusted task and untrusted data have separate fields."""

    instruction: str
    question: str
    contexts: tuple[Mapping[str, str], ...]

    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.instruction},
            {"role": "user", "content": _json({
                "user_question": self.question,
                "untrusted_evidence": [dict(context) for context in self.contexts],
            })},
        ]

    def legacy_arguments(self) -> dict:
        """Explicit text adaptation for chat-only providers; no role guarantee.

        JSON escaping keeps source delimiters inside data strings. The old
        keyword signature and nonempty evidence list remain usable. A custom
        provider still owns how these strings are ultimately sent to its model.
        """
        return {
            "question": _json({"trusted_task": self.instruction, "user_question": self.question}),
            "contexts": [
                {
                    "source_id": context["source_id"],
                    "article_title": _json(context["article_title"]),
                    "section_title": _json(context["section_title"]),
                    "content": _json({
                        "source_id": context["source_id"],
                        "untrusted_content": context["content"],
                    }),
                }
                for context in self.contexts
            ],
        }

    def input_character_count(self) -> int:
        # Count serialization/escaping as well as instructions, question,
        # evidence, IDs and titles. This is a character bound, not a tokenizer.
        return max(len(_json(self.messages())), len(_json(self.legacy_arguments())))


class RequestLLMProvider(ABC):
    """Explicit opt-in; existing custom LLMProvider implementations need no change."""

    @abstractmethod
    def chat_request(self, request: ChatRequest) -> str:
        raise NotImplementedError


def invoke_chat_request(provider: LLMProvider, request: ChatRequest) -> str:
    from app.llm.fake import FakeLLMProvider

    # Exact built-in types opt in here. Inheriting an old built-in must not
    # silently bypass a custom chat override (which may itself prevent network
    # access). Custom structured providers explicitly inherit RequestLLMProvider.
    if type(provider) in (FakeLLMProvider, OpenAICompatibleLLMProvider) or isinstance(provider, RequestLLMProvider):
        return provider.chat_request(request)
    return provider.chat(**request.legacy_arguments())


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


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
        return self._complete([
            {
                "role": "system",
                "content": "Answer only from the supplied contexts. If the contexts are insufficient, say so.",
            },
            {"role": "user", "content": f"Question: {question}\n\nContexts:\n{context_text}"},
        ])

    def chat_request(self, request: ChatRequest) -> str:
        return self._complete(request.messages())

    def _complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI-compatible chat")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=_json(
                {
                    "model": self.model,
                    "messages": messages,
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
