"""
app/api/chat_router.py
────────────────────────────────────────────────────────────────────────
상담 챗봇 엔드포인트. Hybrid RAG 오케스트레이터를 그대로 노출합니다.

  POST /api/chat/recommend  : 발화 → 감정+궁합 → 제자 추천 순위(카드용)
  POST /api/chat/answer     : 선택된 제자가 성경 근거로 응답

인증은 데모 단순화를 위해 헤더의 MBTI를 신뢰(선택). 실서비스에서는
verify_token으로 사용자 MBTI를 서버에서 확정하는 것이 안전합니다.
"""

from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import (
    RecommendRequest, RecommendResponse, DiscipleCard,
    ChatRequest, ChatResponse, Verse,
)
from app.services import hybrid_rag, auth
from app.services import mock_data

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _resolve_mbti(authorization: str, fallback: str = "INFJ") -> str:
    """토큰이 있으면 사용자 MBTI를, 없으면 fallback을 사용."""
    token = authorization.replace("Bearer ", "").strip()
    if token:
        try:
            return auth.verify_token(token)["mbti"]
        except Exception:
            pass
    return fallback


def _resolve_name(authorization: str, fallback: str = "") -> str:
    """토큰이 있으면 사용자 이름을, 없으면 fallback을 사용."""
    token = authorization.replace("Bearer ", "").strip()
    if token:
        try:
            return auth.verify_token(token)["name"]
        except Exception:
            pass
    return fallback


@router.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest, authorization: str = Header(default=""),
              x_user_mbti: str = Header(default="INFJ")):
    user_mbti = _resolve_mbti(authorization, x_user_mbti)
    result = hybrid_rag.recommend(user_mbti, req.message, req.emo_weight)

    cards = []
    for r in result["ranked"]:
        cards.append(DiscipleCard(
            id=r["id"], name=r["name"], mbti=r["mbti"], role=r.get("role"),
            traits=r.get("traits"), quote=r.get("quote"), quote_ref=r.get("quote_ref"),
            books=r.get("book_full_names") or r.get("books", []),
            best_mbti=mock_data.best_matching_mbti(r["mbti"]),
            compat=r.get("compat", 0), score=r.get("score", 0),
        ))
    return RecommendResponse(
        emotion=result["emotion"], emotion_label=result["emotion_label"], ranked=cards
    )


@router.post("/answer", response_model=ChatResponse)
def answer(req: ChatRequest, authorization: str = Header(default=""),
           x_user_mbti: str = Header(default="INFJ"), x_user_name: str = Header(default="")):
    user_mbti = _resolve_mbti(authorization, x_user_mbti)
    user_name = _resolve_name(authorization, x_user_name)
    out = hybrid_rag.answer(req.person_id, user_mbti, req.message, req.history, user_name)
    return ChatResponse(
        person_id=out["person"].get("id", req.person_id),
        person_name=out["person"].get("name", req.person_id),
        answer=out["answer"],
        verses=[Verse(**v) for v in out["verses"]],
    )
