# Eden 포털 — Streamlit 프로토타입

성경 인물(예수 + 12제자)과 MBTI 궁합으로 대화하는 **말씀 상담 포털**.
발표/시연용 단일 프로세스 버전입니다.

## 시스템 아키텍처 (기존과 동일)

```
사용자 발화
   │
   ├─▶ emotion.infer_emotion()           감정 추론 (키워드 + LLM 폴백)
   │
   ├─▶ graph_store.recommend_disciples()  Graph: 누가 답할지 (MBTI 궁합)
   │       └─ 실패 시 mock_data 폴백
   │
   ├─▶ vector_store.search()              Vector: 무엇으로 답할지 (성경 구절)
   │       └─ graph-guided book 필터
   │
   └─▶ llm.get_llm() + prompts            LLM: 제자 페르소나로 답변
           └─ 실패 시 mock 페르소나 폴백
```

**FastAPI 버전과 달라진 점은 HTTP 계층뿐입니다.**
`backend/app/services/` 이하 로직은 **한 줄도 수정하지 않았습니다.**

| | FastAPI + React | Streamlit |
|---|---|---|
| 프론트 | React (Vite) | Streamlit |
| 통신 | HTTP (`/api/chat/answer`) | **직접 import** (`hybrid_rag.answer()`) |
| 상태 | React useState | `st.session_state` |
| 배포 | Vercel + Render (2곳) | Streamlit Cloud (1곳) |
| services/ | 동일 | **동일** |

## 구조

```
├── streamlit_app.py     ★ 진입점 (UI 전체)
├── assets/              인물 14명 + 배경 (webp, 208KB)
├── requirements.txt
├── .env.example         → .env 로 복사해 키 입력
└── backend/
    └── app/
        ├── core/config.py       모델·DB 교체는 전부 여기
        └── services/            ★ 수정 없이 그대로 재사용
            ├── hybrid_rag.py     오케스트레이터
            ├── graph_store.py    Neo4j 궁합
            ├── vector_store.py   Chroma 성경 검색
            ├── emotion.py        감정 추론
            ├── llm.py            LLM 팩토리
            └── mock_data.py      폴백 데이터
```

`api/*_router.py`, `models/schemas.py`, `services/auth.py` 는
Streamlit 버전에서 쓰지 않습니다(FastAPI 전용). 남겨둬도 무방합니다.

## 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env        # OPENAI_API_KEY 입력
streamlit run streamlit_app.py
```
→ http://localhost:8501

## 배포 (Streamlit Community Cloud, 무료)

로컬 `data/chroma_db`(152MB), Qdrant 스냅샷(253MB), Neo4j Desktop(로컬 전용)은
그대로 올릴 수 없거나 클라우드에서 접속할 수 없습니다. 대신:
- **벡터DB**: 배포판은 **Qdrant Cloud**(무료 티어)를 씁니다. 로컬에 미리 OpenAI
  `text-embedding-3-small`로 임베딩해 둔 31,077개 구절 스냅샷을 그대로 복원해
  쓰므로, 배포 때마다 다시 임베딩할 필요가 없습니다. (`VECTOR_BACKEND="qdrant"`)
  - 로컬 개발 중에는 `chroma_db`(자동 재생성, `data/bible_structured.json` 기반)를
    계속 써도 됩니다 — 로컬 `.env`는 그대로 두고 Streamlit Cloud secrets에서만
    `VECTOR_BACKEND=qdrant`로 오버라이드합니다.
- **그래프DB**: 팀원 모두가 접속 가능한 **Neo4j Aura**(무료 티어)가 필요합니다.
  로컬 데이터를 그대로 옮기려면 `backend/scripts/migrate_neo4j_to_aura.py` 참고.

### 단계

1. **Neo4j Aura 인스턴스 생성**: https://neo4j.com/product/auradb/ → 무료 인스턴스
   생성 후 발급되는 Connection URI/사용자명/비밀번호를 **그 자리에서 바로 저장**해
   둔다 (재확인이 안 되므로, 놓치면 인스턴스를 삭제하고 새로 만들어야 함).
2. **로컬 그래프 데이터를 Aura로 복사**: `backend/scripts/migrate_neo4j_to_aura.py`
   참고 (또는 Aura Query 콘솔에 직접 Cypher를 붙여넣어도 됨).
3. **Qdrant Cloud 클러스터 생성**: https://cloud.qdrant.io → 무료 클러스터(1GB)
   생성 후 URL과 API 키를 저장해 둔다.
4. **로컬 Qdrant 스냅샷을 Qdrant Cloud로 복원**: 로컬 Qdrant(Docker)의
   `bible_verses` 컬렉션 스냅샷을 만들어 Qdrant Cloud의 snapshot recovery API로
   업로드한다 (컬렉션이 이미 OpenAI 임베딩 기준이라 재임베딩 불필요).
5. https://share.streamlit.io → **New app** → 레포 선택 → Main file path: `streamlit_app.py`
6. **Advanced settings → Secrets** 에 아래 내용 입력 (`.env`가 아니라 이 Secrets가
   배포판의 유일한 설정 소스입니다):
   ```toml
   OPENAI_API_KEY = "sk-..."
   LLM_PROVIDER = "openai"
   LLM_MODEL = "gpt-4o-mini"

   # 배포판은 무거운 로컬 임베딩 모델(sentence-transformers) 대신 OpenAI 임베딩을 씁니다.
   EMBEDDING_PROVIDER = "openai"
   EMBEDDING_MODEL = "text-embedding-3-small"

   # 벡터DB: Qdrant Cloud
   VECTOR_BACKEND = "qdrant"
   QDRANT_URL = "https://xxxx.cloud.qdrant.io"
   QDRANT_API_KEY = "..."
   QDRANT_COLLECTION = "bible_verses"

   # 그래프DB: Neo4j Aura (1번에서 만든 접속 정보)
   NEO4J_URI = "neo4j+s://xxxx.databases.neo4j.io"
   NEO4J_USER = "..."
   NEO4J_PASSWORD = "..."
   NEO4J_DATABASE = "..."
   ```
7. Deploy.

**이후 `git push` 할 때마다 자동 재배포됩니다.** 팀원 전체가 같은 공유 URL로
실시간 결과를 봅니다 — 별도로 각자 로컬을 띄울 필요가 없습니다.

## 폴백 동작 (발표 중 끊기지 않게)

각 단계가 독립적으로 폴백합니다.

| 없을 때 | 동작 |
|---|---|
| Neo4j (Aura 미설정 포함) | `mock_data.SCORES` 궁합으로 추천 |
| Qdrant/Chroma 연결 실패 | 감정별 목업 구절 |
| OPENAI_API_KEY | 목업 페르소나 문장 |

→ **아무것도 없어도 앱은 끝까지 돕니다.**
키만 넣으면 답변이 실제 LLM으로 바뀝니다.
