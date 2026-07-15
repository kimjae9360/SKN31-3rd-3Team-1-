"""
app/core/config.py
────────────────────────────────────────────────────────────────────────
Eden 포털 백엔드 전역 설정.

★ 모델·DB 교체는 전부 이 파일 한 곳에서 이루어집니다. ★
  - 임베딩 모델을 바꾸려면        → EMBEDDING_MODEL / EMBEDDING_PROVIDER
  - LLM을 바꾸려면               → LLM_MODEL / LLM_PROVIDER
  - Vector DB를 바꾸려면          → VECTOR_BACKEND (chroma | faiss | qdrant ...)
  - Graph DB 접속 정보           → NEO4J_*
실제 서비스 로직(services/*)은 이 값들만 참조하므로,
여기만 고치면 다른 코드는 건드릴 필요가 없도록 설계했습니다.

값은 환경변수(.env)로 오버라이드할 수 있습니다. (pydantic-settings 사용)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str=""
    HUGGINGFACE_API_KEY: str=""

    # ── .env 파일 자동 로드 ────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ══════════════════════════════════════════════════════════════════
    # 1. 임베딩 모델  ─ 추후 변경 지점
    #    provider: "huggingface" | "openai" | "ollama"
    #    바꿀 때는 provider와 model 이름만 교체하면 services/embeddings.py가
    #    알아서 해당 백엔드를 로드합니다.
    # ══════════════════════════════════════════════════════════════════
    EMBEDDING_PROVIDER: str = "huggingface"
    EMBEDDING_MODEL: str = "jhgan/ko-sroberta-multitask"
    EMBEDDING_DEVICE: str = "cpu"           # "cuda" 로 바꾸면 GPU 사용
    EMBEDDING_NORMALIZE: bool = True

    # ══════════════════════════════════════════════════════════════════
    # 2. LLM  ─ 추후 변경 지점
    #    provider: "ollama" | "openai" | "anthropic"
    # ══════════════════════════════════════════════════════════════════
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    # LLM_BASE_URL: str = "http://localhost:11434"   # ollama 기본 주소
    LLM_BASE_URL: str = "https://api.openai.com/v1"   # openai 기본 주소

    # ══════════════════════════════════════════════════════════════════
    # 3. Vector DB
    # ══════════════════════════════════════════════════════════════════
    VECTOR_BACKEND: str = "chroma"          # "chroma" | "faiss" | "qdrant"
    CHROMA_DB_DIR: str = "./data/chroma_db"
    BIBLE_FILE: str = "./data/bible_structured.json"
    RETRIEVAL_K: int = 4                     # 최종 LLM에 넣을 구절 수
    RETRIEVAL_FETCH_K: int = 20              # rerank 전 1차로 넉넉히 가져올 수

    # ══════════════════════════════════════════════════════════════════
    # 4. Graph DB (Neo4j)
    # ══════════════════════════════════════════════════════════════════
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"

    # ══════════════════════════════════════════════════════════════════
    # 5. 하이브리드 RAG 동작 파라미터
    #    - USE_HYDE:        검색 전 가상 답변 생성(HyDE)으로 recall 향상
    #    - USE_RERANK:      1차 검색 결과를 재정렬해 정밀도 향상
    #    - GRAPH_FILTER:    그래프가 고른 성경서로 벡터 검색 범위 제한
    #    데모/실서비스에서 토글만으로 파이프라인을 조절할 수 있습니다.
    # ══════════════════════════════════════════════════════════════════
    USE_HYDE: bool = False
    USE_RERANK: bool = False
    GRAPH_GUIDED_FILTER: bool = True
    RERANK_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # ══════════════════════════════════════════════════════════════════
    # 6. 인증 (데모용 간이 JWT)
    # ══════════════════════════════════════════════════════════════════
    JWT_SECRET: str = "eden-demo-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7    # 7일

    # ══════════════════════════════════════════════════════════════════
    # 7. 앱 메타
    # ══════════════════════════════════════════════════════════════════
    APP_NAME: str = "Eden Portal API"
    CORS_ORIGINS: list[str] = ["*"]          # 배포 시 프론트 도메인으로 제한


@lru_cache
def get_settings() -> Settings:
    """싱글턴 설정 객체. 어디서든 get_settings()로 동일 인스턴스를 얻습니다."""
    return Settings()


settings = get_settings()
