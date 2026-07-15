"""
app/api/auth_router.py
────────────────────────────────────────────────────────────────────────
회원가입 / 로그인 / 내 정보 조회 엔드포인트.
회원가입 시 성별·MBTI를 함께 받아 저장합니다(초반 온보딩 대체).
"""

from fastapi import APIRouter, HTTPException, Header
from app.models.schemas import SignupRequest, LoginRequest, AuthResponse, UserProfile
from app.services import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        user = auth.signup(req.email, req.password, req.name, req.gender, req.mbti)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AuthResponse(token=auth.issue_token(user["email"]), user=UserProfile(**user))


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        user = auth.login(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return AuthResponse(token=auth.issue_token(user["email"]), user=UserProfile(**user))


@router.get("/me", response_model=UserProfile)
def me(authorization: str = Header(default="")):
    token = authorization.replace("Bearer ", "").strip()
    try:
        return UserProfile(**auth.verify_token(token))
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
