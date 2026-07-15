"""
app/services/llm.py
────────────────────────────────────────────────────────────────────────
LLM 추상화 레이어. 임베딩과 같은 패턴으로, provider만 바꾸면 교체됩니다.

get_llm()      : 채팅/생성용 LLM 객체
새 프로바이더는 _BUILDERS 에 등록만 하면 됩니다.
"""

from functools import lru_cache
from app.core.config import settings


def _build_ollama(temperature: float):
    # 현재 팀 기본값: 로컬 Ollama (korean-yanolja-eeve)
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.LLM_MODEL,
        temperature=temperature,
        base_url=settings.LLM_BASE_URL,
    )


def _build_openai(temperature: float):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY or None,  # 없으면 OPENAI_API_KEY 환경변수 자동 사용
    )


def _build_anthropic(temperature: float):
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=settings.LLM_MODEL, temperature=temperature)


_BUILDERS = {
    "ollama": _build_ollama,
    "openai": _build_openai,
    "anthropic": _build_anthropic,
}


@lru_cache
def get_llm(temperature: float | None = None):
    """
    설정된 LLM 객체 반환.
    temperature를 인자로 주면 상황별로 다른 온도를 쓸 수 있습니다.
    (예: 라우팅은 0.0, 상담 생성은 0.3)
    """
    provider = settings.LLM_PROVIDER.lower()
    if provider not in _BUILDERS:
        raise ValueError(
            f"지원하지 않는 LLM_PROVIDER='{provider}'. 선택지: {list(_BUILDERS)}"
        )
    temp = settings.LLM_TEMPERATURE if temperature is None else temperature
    return _BUILDERS[provider](temp)
