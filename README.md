# Eden 포털

성경 인물(예수 + 12제자)과 MBTI 궁합으로 대화하는 **말씀 상담 포털**.
Graph(궁합·인물) + Vector(성경 구절) + LLM(제자 페르소나)을 엮은 **Hybrid RAG** 데모입니다.

## 이번 데모에서 바뀐 점
- 초반 온보딩(이름·성별·MBTI 조사) **삭제** → **회원가입 폼**에서 수집
- 단일 챗봇 → **포털 구조**: 홈 / 말씀 상담 / 제자 진단 / 인물 탐색 / 관계도
- 프론트+백엔드 **연동 설계**를 모듈로 분리, **임베딩·LLM 모델은 config에서 교체**
- 백엔드 없이도 **목업으로 완결 동작**(시연용), `API_BASE`만 채우면 실서버 연결

---

## 구조

```
eden-portal/
├── frontend/
│   ├── EdenPortal.jsx   # ★ 단일 파일 데모 (그대로 열면 실행). 이미지 내장.
│   ├── api.js           # 백엔드 호출 클라이언트 (배포용, 목업 폴백 내장)
│   └── mock.js          # 오프라인 목업 로직 (백엔드와 동일 궁합/감정)
└── backend/
    ├── app/
    │   ├── core/config.py         # ★ 모델·DB 교체는 전부 여기
    │   ├── services/
    │   │   ├── embeddings.py       # 임베딩 프로바이더 팩토리 (hf/openai/ollama)
    │   │   ├── llm.py              # LLM 프로바이더 팩토리 (ollama/openai/anthropic)
    │   │   ├── vector_store.py     # 성경 Vector DB (Chroma, graph-guided 필터)
    │   │   ├── graph_store.py      # Neo4j 궁합·제자·성경서
    │   │   ├── emotion.py          # 감정 추론 (키워드 + LLM 폴백)
    │   │   ├── hybrid_rag.py       # ★ 오케스트레이터 (recommend/answer)
    │   │   ├── auth.py             # 회원가입·로그인·JWT
    │   │   └── mock_data.py        # DB 미연결 시 폴백
    │   ├── api/                    # auth / chat / explore 라우터
    │   ├── models/schemas.py       # 요청·응답 스키마
    │   └── main.py                 # FastAPI 진입점
    ├── requirements.txt
    └── .env.example
```

## Hybrid RAG 흐름

```
사용자 발화
   │
   ├─ 감정 추론 (emotion.py)
   ├─ Graph 추천 (graph_store) ── 궁합점수 + 감정 바이어스 → 제자 순위 + 연관 성경서
   │        └─ 프론트: 프로필 카드로 표시 → "이 벗과 대화하기"
   └─ 응답 생성 (answer)
         ├─ (opt) HyDE 확장
         ├─ Vector 검색 (vector_store) ── 그래프가 고른 성경서로 범위 제한
         ├─ (opt) Rerank
         └─ LLM ── 제자 페르소나 + 검색 구절로 답변
```
= **Graph가 '누가' 답할지, Vector가 '무슨 말씀으로' 답할지, LLM이 '그 제자 목소리로' 답한다.**

---

## 실행

### 프론트 데모 (백엔드 없이)
`frontend/EdenPortal.jsx` 를 React 환경에 넣으면 바로 실행됩니다. 목업으로 전 기능 동작.

### 백엔드 연결
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 값 채우기 (모델/DB)
uvicorn app.main:app --reload --port 8000
# 문서: http://localhost:8000/docs
```
그 뒤 `EdenPortal.jsx` 상단의 `CONFIG.API_BASE = "http://localhost:8000"` 로 설정.
(배포용 `api.js`를 쓸 경우 `api.js`의 `API_BASE` 설정)

## 모델 교체 (요청 사항)
`backend/app/core/config.py` 또는 `.env` 에서만 바꾸면 됩니다. 다른 코드 수정 불필요.

| 목적 | 바꿀 값 |
|---|---|
| 임베딩 모델 | `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` |
| LLM | `LLM_PROVIDER`, `LLM_MODEL` |
| Vector DB | `VECTOR_BACKEND` |
| 하이브리드 옵션 | `USE_HYDE`, `USE_RERANK`, `GRAPH_GUIDED_FILTER` |

예) OpenAI 임베딩으로: `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-small`
예) Anthropic LLM으로: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-...`

## 팀 코드 연결 지점
- `graph_store.py` 의 Cypher는 팀 Neo4j 스키마에 맞춰 조정 (HAS_TRAIT / RELATED_TO(Versus{book}) 등)
- `vector_store.py` 는 팀 Chroma(`chroma_db/`, ko-sroberta)를 그대로 로드
- 궁합 SCORES·인물 데이터는 `neo4j_seed.py` / `인물들.json` 과 동일
