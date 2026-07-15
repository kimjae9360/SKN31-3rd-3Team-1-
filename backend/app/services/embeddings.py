"""
app/services/embeddings.py
────────────────────────────────────────────────────────────────────────
임베딩 모델 추상화 레이어.

config.EMBEDDING_PROVIDER 값에 따라 알맞은 LangChain Embeddings 객체를
만들어 돌려줍니다. 새 프로바이더를 추가하려면 _BUILDERS 에 한 줄만 추가하면 됩니다.

이렇게 분리해 두면 vector_store.py 등 상위 코드는 "임베딩 객체"만 받으면 되고,
어떤 모델인지는 신경 쓰지 않아도 됩니다. (의존성 역전)
"""

from functools import lru_cache
from app.core.config import settings


def _build_huggingface():
    # 현재 팀 기본값: 한국어 문장 임베딩(ko-sroberta)
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": settings.EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": settings.EMBEDDING_NORMALIZE},
    )


def _build_openai():
    # 예: text-embedding-3-small 등으로 교체할 때
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)


def _build_ollama():
    # 예: ollama 임베딩 모델(nomic-embed-text 등)
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL, base_url=settings.LLM_BASE_URL
    )


# provider 이름 → 빌더 함수 매핑. 새 백엔드는 여기에 등록.
_BUILDERS = {
    "huggingface": _build_huggingface,
    "openai": _build_openai,
    "ollama": _build_ollama,
}


@lru_cache
def get_embeddings():
    """설정에 지정된 임베딩 객체를 (싱글턴으로) 반환."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider not in _BUILDERS:
        raise ValueError(
            f"지원하지 않는 EMBEDDING_PROVIDER='{provider}'. "
            f"선택지: {list(_BUILDERS)}"
        )
    return _BUILDERS[provider]()
