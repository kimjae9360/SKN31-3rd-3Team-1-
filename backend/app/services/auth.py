"""
app/services/auth.py
────────────────────────────────────────────────────────────────────────
회원가입·로그인·토큰 검증.

데모 단계라 사용자 저장소는 JSON 파일(간이). 실서비스에서는
_UserStore 인터페이스만 유지한 채 내부를 Postgres/Supabase 등으로 교체하면 됩니다.
비밀번호는 bcrypt 해시로 저장하고, 로그인 성공 시 JWT를 발급합니다.
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone

import jwt
from passlib.hash import bcrypt

from app.core.config import settings

# 실행 위치(CWD)에 따라 루트에 빈 users.json이 생기던 문제 →
# config.USER_STORE_PATH(프로젝트 루트 data/ 기준 절대경로)로 고정.
_STORE_PATH = settings.USER_STORE_PATH


# ── 간이 사용자 저장소 (교체 지점) ──────────────────────────────────────
class _UserStore:
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._write({})

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 파일이 없거나 깨졌으면 조용히 초기화 (데모가 멈추지 않도록)
            return {}

    def _write(self, data: dict):
        # 원자적 쓰기: 중간에 죽어도 users.json이 깨지지 않게 임시파일 후 교체
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def get(self, email: str) -> dict | None:
        return self._read().get(email)

    def create(self, email: str, record: dict):
        data = self._read()
        data[email] = record
        self._write(data)

    def update(self, email: str, **fields):
        data = self._read()
        if email not in data:
            raise ValueError("사용자를 찾을 수 없습니다.")
        data[email].update(fields)
        self._write(data)
        return data[email]


_store = _UserStore(_STORE_PATH)


# ── 공개 함수 ──────────────────────────────────────────────────────────
def signup(email, password, name, gender, mbti) -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("이메일 형식이 올바르지 않습니다.")
    if not password:
        raise ValueError("비밀번호를 입력해 주세요.")
    if gender not in ("adam", "eve"):
        raise ValueError("성별 값이 올바르지 않습니다.")
    if _store.get(email):
        raise ValueError("이미 가입된 이메일입니다.")
    record = {
        "email": email,
        "password_hash": bcrypt.hash(password),
        "name": name,
        "gender": gender,
        "mbti": mbti.upper(),
        "created_at": time.time(),
    }
    _store.create(email, record)
    return _public(record)


def login(email, password) -> dict:
    email = (email or "").strip().lower()
    record = _store.get(email)
    if not record or not bcrypt.verify(password, record["password_hash"]):
        raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")
    return _public(record)


def issue_token(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """토큰 → 사용자 프로필. 실패 시 예외."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    record = _store.get(payload["sub"])
    if not record:
        raise ValueError("사용자를 찾을 수 없습니다.")
    return _public(record)


def update_profile(email: str, **fields) -> dict:
    """이름/성별/MBTI 수정 (비밀번호·이메일은 여기서 못 바꿉니다)."""
    allowed = {k: v for k, v in fields.items() if k in ("name", "gender", "mbti")}
    return _public(_store.update(email, **allowed))


def store_path() -> str:
    """실제로 회원정보가 저장되는 파일 경로 (디버깅/확인용)."""
    return _store.path


def _public(record: dict) -> dict:
    """비밀번호 등 민감정보를 제외한 공개 프로필."""
    return {
        "email": record["email"],
        "name": record["name"],
        "gender": record["gender"],
        "mbti": record["mbti"],
        # 프롬프트에서 "형제님/자매님" 호칭에 쓰입니다.
        "title": "자매님" if record.get("gender") == "eve" else "형제님",
    }
