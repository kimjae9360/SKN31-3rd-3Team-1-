"""
app/models/schemas.py
────────────────────────────────────────────────────────────────────────
API 요청/응답 Pydantic 스키마. 프론트-백엔드 계약(contract)을 한곳에 모음.
"""

from pydantic import BaseModel, Field
from typing import Literal


# ── 인증 / 회원 ────────────────────────────────────────────────────────
# ★ 초반 온보딩 대신, 회원가입 시 정보(성별·MBTI)를 수집합니다.
class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    gender: Literal["adam", "eve"]          # 아담의 후손 / 하와의 후손
    mbti: str = Field(min_length=4, max_length=4)   # 가입 시 4문항→MBTI 또는 직접 선택


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    email: str
    name: str
    gender: str
    mbti: str


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


# ── 추천 / 채팅 ────────────────────────────────────────────────────────
class RecommendRequest(BaseModel):
    message: str
    emo_weight: float = 1.0                  # '다른 벗 추천' 반복 시 증가


class DiscipleCard(BaseModel):
    id: str
    name: str
    mbti: str
    role: str | None = None
    traits: str | None = None
    quote: str | None = None
    quote_ref: str | None = None
    books: list[str] = []
    best_mbti: list[str] = []
    compat: float = 0
    score: float = 0


class RecommendResponse(BaseModel):
    emotion: str
    emotion_label: str
    ranked: list[DiscipleCard]


class ChatRequest(BaseModel):
    person_id: str
    message: str
    history: str = ""                        # 이전 대화 요약/이어붙임


class Verse(BaseModel):
    book: str
    chapter: int
    verse: int
    content: str
    source: str


class ChatResponse(BaseModel):
    person_id: str
    person_name: str
    answer: str
    verses: list[Verse]
