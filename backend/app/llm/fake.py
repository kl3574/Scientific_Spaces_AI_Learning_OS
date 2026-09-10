from __future__ import annotations

from typing import Mapping

from app.llm.provider import ChatRequest


class FakeLLMProvider:
    def chat_request(self, request: ChatRequest) -> str:
        # Deterministic plumbing fixture, not a simulation of teaching quality.
        return self.chat(question=request.question, contexts=list(request.contexts))

    def chat(self, *, question: str, contexts: list[Mapping[str, str]]) -> str:
        if not contexts:
            return "无法基于当前资料回答。"
        first = contexts[0]
        excerpt = " ".join(first["content"].split())[:280]
        return (
            f"基于《{first['article_title']}》的“{first['section_title']}”章节，"
            f"针对“{question}”，可依据原文概括为：{excerpt}"
        )
