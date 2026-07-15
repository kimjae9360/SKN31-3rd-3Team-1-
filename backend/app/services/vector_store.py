"""
app/services/vector_store.py
────────────────────────────────────────────────────────────────────────
성경 Vector DB 서비스.

기존 database.py의 로직을 모듈로 옮기고 다음을 개선했습니다.
  - Chroma 외 백엔드로 교체 가능 (config.VECTOR_BACKEND)
  - Streamlit 의존 제거 (순수 파이썬 → FastAPI/CLI 어디서든 사용)
  - graph-guided filtering을 위한 metadata 필터 검색 지원
    (그래프가 고른 성경서 목록으로 검색 범위를 좁힘)

핵심 함수
  build_vector_store()   : 최초 1회 성경 JSON → 임베딩 → 저장
  get_vector_store()     : 저장된 DB 로드 (싱글턴)
  search(query, k, books): 유사도 검색 (+ 선택적 성경서 필터)
"""

import os
import re
import json
from functools import lru_cache

from app.core.config import settings
from app.services.embeddings import get_embeddings
from app.services.bible_books import normalize_books
# 참고: langchain_core / langchain_chroma 등은 각 함수 안에서 지연 import 합니다.
#       (라이브러리 미설치 환경에서도 앱이 로드되고, 상위에서 목업 폴백 가능)


# ── 텍스트 정제 (기존 clean_text 이식) ──────────────────────────────────
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    # 의미 전달용 최소 문장부호와 한글/영문/숫자만 남김
    text = re.sub(r"[^가-힣a-zA-Z0-9\s.,?!]", "", text)
    return text


# ── 백엔드별 store 로더/빌더 ────────────────────────────────────────────
def _load_chroma():
    from langchain_chroma import Chroma
    # collection_name 명시 — 빼먹으면 langchain 기본값으로 "빈 컬렉션"을 새로
    # 만들어버려서, 인덱스가 있어도 검색 결과가 0건으로 나온다.
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        persist_directory=settings.CHROMA_DB_DIR,
        embedding_function=get_embeddings(),
    )


def _load_qdrant():
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )
    return QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=get_embeddings(),
    )


_LOADERS = {
    "chroma": _load_chroma,
    "qdrant": _load_qdrant,
    # "faiss": _load_faiss,   # 필요 시 추가
}


@lru_cache
def get_vector_store():
    """저장된 Vector DB를 로드해 싱글턴으로 반환."""
    backend = settings.VECTOR_BACKEND.lower()
    if backend not in _LOADERS:
        raise ValueError(f"지원하지 않는 VECTOR_BACKEND='{backend}'")
    return _LOADERS[backend]()


def build_vector_store(batch_size: int = 500):
    """
    성경 JSON을 읽어 구절(Verse) 단위로 청킹 후 임베딩·저장.
    (기존 전처리 명세 그대로: 1구절 = 1청크, 500개씩 배치 저장)
    최초 1회 또는 재빌드 시에만 실행합니다.
    """
    from langchain_core.documents import Document   # 지연 import

    if not os.path.exists(settings.BIBLE_FILE):
        raise FileNotFoundError(f"성경 파일 없음: {settings.BIBLE_FILE}")

    with open(settings.BIBLE_FILE, "r", encoding="utf-8") as f:
        bible = json.load(f)

    documents = []
    for item in bible:
        content = clean_text(item.get("content", ""))
        # 검색 정확도를 위해 출처+본문을 함께 임베딩
        page_content = f"[{item['book']} {item['chapter']}:{item['verse']}] {content}"
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "book": item["book"],
                    "chapter": item["chapter"],
                    "verse": item["verse"],
                    "content": content,
                },
            )
        )

    store = get_vector_store()
    for i in range(0, len(documents), batch_size):
        store.add_documents(documents[i : i + batch_size])
        print(f"임베딩 중... {i + min(batch_size, len(documents) - i)} / {len(documents)}")
    return len(documents)


def count() -> int:
    """인덱싱된 구절 수. 백엔드별로 카운트 방법이 다르다."""
    try:
        store = get_vector_store()
        backend = settings.VECTOR_BACKEND.lower()
        if backend == "qdrant":
            return store.client.count(collection_name=store.collection_name).count
        return store._collection.count()
    except Exception:
        return 0


def health() -> dict:
    """
    상태 점검용. '왜 구절이 안 나오는지' DB 문제와 임베딩(API 키) 문제를
    구분해서 화면/CLI에 바로 보여준다 — 둘 다 "구절 0건"으로만 보이면
    원인을 못 찾고 헤매기 쉽다.
    """
    backend = settings.VECTOR_BACKEND.lower()
    n, db_error = 0, None
    try:
        n = count()
    except Exception as e:
        db_error = repr(e)

    embedding_ok, embedding_error = True, None
    try:
        get_embeddings().embed_query("ping")
    except Exception as e:
        embedding_ok = False
        embedding_error = repr(e)

    return {
        "backend": backend,
        "location": settings.QDRANT_URL if backend == "qdrant" else settings.CHROMA_DB_DIR,
        "collection": settings.QDRANT_COLLECTION if backend == "qdrant" else settings.CHROMA_COLLECTION,
        "count": n,
        "db_ok": db_error is None and n > 0,
        "db_error": db_error,
        "embedding": f"{settings.EMBEDDING_PROVIDER}:{settings.EMBEDDING_MODEL}",
        "embedding_ok": embedding_ok,
        "embedding_error": embedding_error,
        "ready": db_error is None and n > 0 and embedding_ok,
    }


def vector_store_is_empty() -> bool:
    """저장된 chroma_db가 없거나 구절이 0개인지 확인 (자동 재생성 트리거 조건)."""
    return count() == 0


def ensure_vector_store() -> int:
    """
    벡터DB가 비어있으면(최초 배포/클라우드 콜드스타트 등) bible_structured.json으로부터
    자동으로 재생성한다. 이미 구절이 있으면 아무 것도 하지 않고 0을 반환.

    Qdrant 백엔드는 대상이 아니다 — Qdrant Cloud는 미리 임베딩된 스냅샷을 복원해
    쓰는 방식이라(build_vector_store가 로컬 임베딩 모델 경로를 가정), 여기서 자동
    재생성을 시도하지 않는다.
    반환값: 새로 임베딩한 구절 수 (재생성 없었거나 대상이 아니면 0).
    """
    if settings.VECTOR_BACKEND.lower() != "chroma":
        return 0
    if not vector_store_is_empty():
        return 0
    get_vector_store.cache_clear()  # 재생성 후 새 컬렉션을 다시 로드하도록
    n = build_vector_store()
    get_vector_store.cache_clear()
    return n


def _build_filter(books: list[str]):
    """graph-guided book 필터를 백엔드별 문법으로 변환.

    books는 mock_data 등에서 온 값이라 전체 이름/약어가 섞여 들어올 수 있다.
    normalize_books()로 인덱스가 실제로 쓰는 표기(약어)로 맞춰 준다 — 안 맞으면
    필터가 0건이 되어 구절이 통째로 사라진다(조용한 실패라 찾기 어려움).
    """
    norm = normalize_books(books) or books
    backend = settings.VECTOR_BACKEND.lower()
    if backend == "qdrant":
        from qdrant_client import models
        return models.Filter(
            must=[models.FieldCondition(key="metadata.book", match=models.MatchAny(any=norm))]
        )
    # chroma metadata 필터 문법
    return {"book": {"$in": norm}} if len(norm) > 1 else {"book": norm[0]}


def _strip_source_prefix(text: str) -> str:
    """"[마태복음 11:28] 수고하고..." 형태에서 본문만 떼어냄."""
    return re.sub(r"^\s*\[[^\]]+\]\s*", "", text or "").strip()


def search(query: str, k: int | None = None, books: list[str] | None = None):
    """
    성경 구절 유사도 검색.

    query : 검색어(사용자 고민 또는 HyDE 가상답변)
    k     : 반환 개수 (기본 config.RETRIEVAL_K)
    books : ★ graph-guided filter ★
            그래프가 고른 성경서 목록. 주어지면 해당 책들로만 범위를 좁힘.
            (예: 베드로 추천 → ["마태복음","요한복음"] 안에서만 검색)

    반환: [{book, chapter, verse, content, source}] 리스트
    """
    store = get_vector_store()
    k = k or settings.RETRIEVAL_K

    flt = _build_filter(books) if (books and settings.GRAPH_GUIDED_FILTER) else None

    docs = store.similarity_search(query, k=k, filter=flt)

    # 필터 결과가 비면(그 책에 관련 구절이 없으면) 필터 없이 재검색 (안전장치)
    if not docs and flt is not None:
        docs = store.similarity_search(query, k=k)

    out = []
    from app.services.bible_books import to_full
    for d in docs:
        m = d.metadata or {}
        book = m.get("book", "")
        full_book = to_full(book) if book else book
        chapter = m.get("chapter", "")
        verse = m.get("verse", "")
        # 인덱스 스키마가 달라 metadata["content"]가 없어도(page_content만 있어도)
        # 화면이 깨지지 않도록 폴백을 둔다.
        content = m.get("content") or _strip_source_prefix(d.page_content)
        out.append({
            "book": full_book,
            "chapter": chapter,
            "verse": verse,
            "content": content,
            "source": f"{full_book} {chapter}:{verse}".strip(),
        })
    return out
