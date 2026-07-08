from app.llm.fake import FakeLLMProvider


def test_fake_llm_provider_requires_sources_for_substantive_answer() -> None:
    provider = FakeLLMProvider()

    answer = provider.chat(
        question="什么是Attention？",
        contexts=[
            {
                "content": "Attention 用 query 和 key 计算相关性。",
                "article_title": "Attention机制",
                "section_title": "定义",
            }
        ],
    )

    assert "Attention" in answer
    assert "query" in answer


def test_fake_llm_provider_refuses_without_contexts() -> None:
    provider = FakeLLMProvider()

    answer = provider.chat(question="什么是Attention？", contexts=[])

    assert "无法基于当前资料回答" in answer
