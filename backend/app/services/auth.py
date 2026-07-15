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

_STORE_PATH = "./data/users.json"


# ── 간이 사용자 저장소 (교체 지점) ──────────────────────────────────────
class _UserStore:
    def __init__(self, path: str):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._write({})

    def _read(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, email: str) -> dict | None:
        return self._read().get(email)

    def create(self, email: str, record: dict):
        data = self._read()
        data[email] = record
        self._write(data)


_store = _UserStore(_STORE_PATH)


# ── 공개 함수 ──────────────────────────────────────────────────────────
def signup(email, password, name, gender, mbti) -> dict:
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


def _public(record: dict) -> dict:
    """비밀번호 등 민감정보를 제외한 공개 프로필."""
    return {
        "email": record["email"],
        "name": record["name"],
        "gender": record["gender"],
        "mbti": record["mbti"],
    }
