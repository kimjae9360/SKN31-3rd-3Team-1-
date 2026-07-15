"""
backend/scripts/build_vector_db.py
────────────────────────────────────────────────────────────────────────
Chroma 벡터DB를 로컬에서 재구축하는 CLI 스크립트.

★ 경로를 프로젝트 루트(streamlit_app.py 기준) 절대경로로 고정합니다. ★
  config.py의 CHROMA_DB_DIR / BIBLE_FILE은 상대경로라서, 어디서 실행하느냐에
  따라(backend/ vs 프로젝트 루트) 서로 다른 폴더를 가리키는 문제가 있습니다.
  이 스크립트는 항상 "프로젝트 루트/data" 를 기준으로 절대경로를 강제해서,
  실제 서비스 중인 streamlit_app.py(루트에서 실행)가 읽는 위치와 100% 일치시킵니다.

전제조건:
  1. backend/.env 에 OPENAI_API_KEY 등 필요한 값이 설정되어 있을 것
  2. <프로젝트 루트>/data/bible_structured.json 원본 파일이 존재할 것
     (팀 공유 폴더/드라이브에서 받아 이 경로에 두세요. git에는 올라가지 않습니다.)

실행 (어느 위치에서 실행해도 결과 경로는 동일합니다):
  python backend/scripts/build_vector_db.py

기존에 이미 만들어진 <루트>/data/chroma_db 가 있다면, 스크립트가 먼저
비워서 중복 삽입을 막습니다(재실행해도 안전).
"""

import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

from app.core.config import settings  # noqa: E402
from app.services import vector_store  # noqa: E402

# 상대경로 설정을 프로젝트 루트 기준 절대경로로 강제 (CWD 의존성 제거)
settings.CHROMA_DB_DIR = str(ROOT / "data" / "chroma_db")
settings.BIBLE_FILE = str(ROOT / "data" / "bible_structured.json")


def main():
    bible_path = Path(settings.BIBLE_FILE)
    if not bible_path.exists():
        print(f"[에러] 성경 원본 파일을 찾을 수 없습니다: {bible_path}")
        print("       팀 공유 폴더에서 bible_structured.json 을 받아 위 경로에 두세요.")
        sys.exit(1)

    db_dir = Path(settings.CHROMA_DB_DIR)
    if db_dir.exists():
        print(f"기존 벡터DB 삭제 후 재생성: {db_dir}")
        shutil.rmtree(db_dir)
    vector_store.get_vector_store.cache_clear()

    print(f"임베딩 모델: {settings.EMBEDDING_PROVIDER} / {settings.EMBEDDING_MODEL}")
    print(f"원본: {bible_path}")
    print(f"저장 위치: {db_dir}  (streamlit_app.py가 읽는 위치와 동일)")

    n = vector_store.build_vector_store()
    print(f"완료: 총 {n}개 구절 임베딩 저장됨 -> {db_dir}")


if __name__ == "__main__":
    main()
