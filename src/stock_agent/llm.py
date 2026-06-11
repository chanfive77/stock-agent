"""OpenAI LLM 래퍼.

API 키가 없거나 llm.enabled=False 이면 None 을 반환하여
각 에이전트가 룰 기반 fallback 으로 동작하도록 한다.
"""

from __future__ import annotations

from functools import lru_cache

from .config import LLMConfig


@lru_cache(maxsize=1)
def _build(model: str, temperature: float, api_key: str):
    # 지연 import: LLM 미사용 환경에서 불필요한 의존성 로딩 방지
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)


def get_llm(cfg: LLMConfig):
    """설정에 따라 ChatOpenAI 인스턴스 또는 None 반환."""
    if not cfg.enabled or not cfg.api_key:
        return None
    return _build(cfg.model, cfg.temperature, cfg.api_key)


def complete(cfg: LLMConfig, system: str, user: str) -> str | None:
    """단발성 프롬프트 호출. 실패 시 None."""
    llm = get_llm(cfg)
    if llm is None:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return (resp.content or "").strip()
    except Exception:
        return None
