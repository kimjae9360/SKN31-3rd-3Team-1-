"""
app/main.py
────────────────────────────────────────────────────────────────────────
FastAPI 진입점. 라우터 등록 + CORS + 헬스체크.

실행:
  cd backend
  uvicorn app.main:app --reload --port 8000

문서: http://localhost:8000/docs (Swagger UI 자동 생성)
"""

from dotenv import load_dotenv
import os
load_dotenv()  # .env 파일이 있으면 환경변수로 로드 

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth_router, chat_router, explore_router

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(explore_router.router)


@app.get("/health")
def health():
    """서비스 연결 상태 요약 (배포 모니터링용)."""
    return {
        "status": "ok",
        "llm": {"provider": settings.LLM_PROVIDER, "model": settings.LLM_MODEL},
        "embedding": {"provider": settings.EMBEDDING_PROVIDER, "model": settings.EMBEDDING_MODEL},
        "vector_backend": settings.VECTOR_BACKEND,
        "hybrid": {
            "graph_guided_filter": settings.GRAPH_GUIDED_FILTER,
            "hyde": settings.USE_HYDE,
            "rerank": settings.USE_RERANK,
        },
    }
