"""
app/services/hybrid_rag.py
════════════════════════════════════════════════════════════════════════
★ Eden의 심장 — Hybrid RAG(Graph + Vector) 오케스트레이터 ★

한 문장 요약:
  "Graph가 '누가·어떤 렌즈로' 답할지 정하고,
   Vector가 '무슨 말씀으로' 답할지 채운 뒤,
   LLM이 그 제자의 목소리로 답한다."

전체 흐름 (recommend + answer 2단계로 분리 → 프론트 카드 UX와 맞물림)

  [1] recommend(user_mbti, message)
      ├─ 감정 추론            (emotion.infer_emotion)
      ├─ Graph 추천           (graph_store.recommend_disciples)
      │    → 궁합 점수 + 감정 바이어스로 상위 제자 정렬
      └─ 반환: 추천 제자 순위 리스트(+연관 성경서)   → 프론트가 프로필 카드로 표시

  [2] answer(person_id, user_mbti, message, history)
      ├─ (선택) HyDE          질문을 이상적 답변으로 확장해 recall↑
      ├─ Vector 검색          person의 연관 성경서로 필터 (graph-guided)
      ├─ (선택) Rerank        1차 결과 재정렬로 정밀도↑
      └─ LLM 생성             제자 페르소나 + 검색 구절 + 대화기록으로 답변

각 단계는 config 토글(USE_HYDE / USE_RERANK / GRAPH_GUIDED_FILTER)로 on/off.
실제 DB/LLM이 없어도 상위 API가 목업으로 대체할 수 있도록, 이 모듈은
순수하게 서비스 함수만 노출합니다(사이드이펙트 최소화).
"""

import re

from app.core.config import settings
from app.services import graph_store, vector_store, prompts
from app.services.emotion import infer_emotion, EMOTION_LABELS
from app.services.llm import get_llm


# 감정별로 특히 어울리는 제자 (그래프 점수에 가산). id 순서 = 우선순위
EMOTION_BIAS = {
    "anxiety": ["john", "andrew", "james_alph"],
    "sadness": ["john", "andrew", "peter"],
    "anger": ["james", "simon", "matthew"],
    "joy": ["peter", "thaddaeus"],
    "doubt": ["thomas", "matthew", "philip"],
    "decision": ["matthew", "james", "philip"],
    "neutral": ["john", "peter", "thaddaeus"],
}


# ══════════════════════════════════════════════════════════════════════
# [1] 추천 단계
# ══════════════════════════════════════════════════════════════════════
def recommend(user_mbti: str, message: str, emo_weight: float = 1.0) -> dict:
    """
    사용자 MBTI + 발화 감정으로 제자 추천 순위를 만든다.
    emo_weight: 프론트에서 '다른 벗 추천'을 반복하면 키워서 감정 반영을 높임.
    """
    emotion = infer_emotion(message, use_llm_fallback=False)
    bias = EMOTION_BIAS.get(emotion, [])

    # Graph에서 궁합 상위 제자 + 연관 성경서/성향 조회
    # Neo4j 미연결/오류 시 목업 데이터로 폴백 (데모가 끊기지 않도록)
    try:
        graph_rows = graph_store.recommend_disciples(user_mbti, limit=12)
        if not graph_rows:
            raise RuntimeError("empty graph result")
    except Exception:
        from app.services import mock_data
        graph_rows = mock_data.recommend_disciples(user_mbti, limit=12)

    ranked = []
    for row in graph_rows:
        # 궁합 점수(0~100)를 0~4 스케일로 정규화
        compat = (row.get("score") or 0) / 25.0
        rank = 3 - bias.index(row["id"]) if row["id"] in bias else 0
        score = compat + rank * 0.6 * emo_weight
        ranked.append({**row, "compat": round(compat, 2), "score": round(score, 3)})

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return {
        "emotion": emotion,
        "emotion_label": EMOTION_LABELS[emotion],
        "ranked": ranked,
    }


# ══════════════════════════════════════════════════════════════════════
# [1.5] 예수님과의 자유 대화 → 제자 추천 시점 판단
# ══════════════════════════════════════════════════════════════════════
MIN_JESUS_TURNS = 2   # 이보다 적으면 아직 추천하지 않음 (최소 대화 보장)
MAX_JESUS_TURNS = 6   # 이보다 많으면 LLM 판단 없이 강제 추천 (무한 대화 방지)


def should_recommend(jesus_history: str) -> bool:
    """
    예수님과 나눈 대화가 제자를 추천할 만큼 충분히 깊어졌는지 판단.
    사용자 턴 수로 최소/최대 안전장치를 두고, 그 사이 구간은 LLM이 판단한다.
    """
    user_turns = jesus_history.count("사용자:")
    if user_turns < MIN_JESUS_TURNS:
        return False
    if user_turns >= MAX_JESUS_TURNS:
        return True

    llm = get_llm(temperature=0)
    prompt = (
        "다음은 사용자가 예수님과 나눈 상담 대화다. 사용자가 자신의 고민과 감정을 "
        "구체적으로 충분히 털어놓아서, 이제 그에게 맞는 제자(상담을 이어갈 파트너)를 "
        "추천해도 괜찮은 시점인지 판단하라. 고민의 실체가 아직 불명확하거나 대화가 "
        "너무 표면적이면 '아니오'라고 답하라.\n\n"
        f"[대화]\n{jesus_history}\n\n"
        "'예' 또는 '아니오' 한 단어로만 답하라."
    )
    try:
        out = llm.invoke(prompt)
        text = (out.content if hasattr(out, "content") else str(out)).strip()
        return text.startswith("예")
    except Exception:
        return user_turns >= 3  # LLM 실패 시 턴수 휴리스틱으로 폴백


# ══════════════════════════════════════════════════════════════════════
# [2] 응답 생성 단계
# ══════════════════════════════════════════════════════════════════════
def _hyde_expand(message: str) -> str:
    """HyDE: 질문을 '이상적인 성경적 답변'으로 가상 생성해 검색어로 사용."""
    llm = get_llm(temperature=0.3)
    prompt = (
        "다음 고민에 성경이 건넬 법한 위로의 한 문단을 상상해서 써라. "
        "성경 구절 문체로, 두세 문장.\n"
        f"고민: {message}\n답변:"
    )
    try:
        out = llm.invoke(prompt)
        return out.content if hasattr(out, "content") else str(out)
    except Exception:
        return message  # 실패 시 원문으로 검색


def _rerank(query: str, docs: list[dict], top_k: int) -> list[dict]:
    """1차 검색 결과를 cross-encoder로 재정렬 (정밀도↑)."""
    try:
        from sentence_transformers import CrossEncoder
        ce = CrossEncoder(settings.RERANK_MODEL)
        pairs = [(query, d["content"]) for d in docs]
        scores = ce.predict(pairs)
        ranked = [d for _, d in sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)]
        return ranked[:top_k]
    except Exception:
        return docs[:top_k]  # rerank 불가 시 원순서 유지


def retrieve_verses(message: str, books: list[str] | None) -> list[dict]:
    """제자 연관 성경서로 필터링된 성경 구절 검색 (HyDE·Rerank 옵션 반영)."""
    query = _hyde_expand(message) if settings.USE_HYDE else message
    fetch_k = settings.RETRIEVAL_FETCH_K if settings.USE_RERANK else settings.RETRIEVAL_K
    docs = vector_store.search(query, k=fetch_k, books=books)
    if settings.USE_RERANK:
        docs = _rerank(message, docs, settings.RETRIEVAL_K)
    return docs


def _persona_prompt(
    person: dict,
    verses: list[dict],
    user_mbti: str,
    message: str,
    history: str,
    user_name: str = "",
    shared_memory: str = "",
    gender: str = "adam",
) -> str:
    """예수님/제자 페르소나 + 검색 구절 + 대화기록을 담은 최종 프롬프트."""
    context = "\n".join(f"- {v['source']} {v['content']}" for v in verses) or "관련 구절 없음"
    return prompts.build_prompt(
        person=person,
        user_mbti=user_mbti,
        message=message,
        history=history,
        context=context,
        user_name=user_name,
        shared_memory=shared_memory,
        gender=gender,
    )


# ── 핵심 구절 1개 추출 ─────────────────────────────────────────────────
# LLM이 답변 끝에 남기는 "[핵심구절: 마태복음 11:28]" 표시를 읽어,
# 검색된 여러 구절 중 '이번 답변에서 실제로 가장 중요하게 쓴 1개'만 화면에 붙입니다.
_KEY_RE = re.compile(r"\[\s*핵심\s*구절\s*[:：]\s*([^\]]*)\]")


def _split_key_verse(text: str, verses: list[dict]) -> tuple[str, list[dict]]:
    """LLM 출력에서 핵심구절 표시를 떼어내고, 그 구절 1개만 골라 돌려준다."""
    matches = _KEY_RE.findall(text or "")
    body = _KEY_RE.sub("", text or "").strip()

    if not verses:
        return body, []

    if not matches:
        # LLM이 표시를 빼먹은 경우 → 검색 1순위 구절로 폴백 (구절이 사라지지 않게)
        return body, verses[: settings.SHOW_VERSE_COUNT]

    ref = matches[-1].strip()
    if ref in ("", "없음", "None", "-"):
        # 이번 턴은 말씀 없이 들어주기만 한 경우 → 구절을 붙이지 않음
        return body, []

    def norm(x: str) -> str:
        return re.sub(r"\s+", "", (x or "")).replace("장", ":").replace("절", "")

    target = norm(ref)
    # 1) 출처 완전/부분 일치
    for v in verses:
        if norm(v["source"]) == target:
            return body, [v]
    for v in verses:
        if target and (target in norm(v["source"]) or norm(v["source"]) in target):
            return body, [v]
    # 2) 못 찾으면 검색 1순위(가장 유사한 구절)로 폴백
    return body, verses[: settings.SHOW_VERSE_COUNT]


def answer(
    person_id: str,
    user_mbti: str,
    message: str,
    history: str = "",
    user_name: str = "",
    shared_memory: str = "",
    gender: str = "adam",
) -> dict:
    """
    선택된 제자(person_id)가 사용자 발화에 응답.
    반환: {person, verses, answer, verse_source}

    · verses 는 '이번 답변에서 LLM이 가장 중요하게 삼은 구절 1개'만 담습니다.
      (config.SHOW_VERSE_COUNT)
    · config.ALLOW_MOCK_VERSES=False(기본)이면 검색 결과가 없을 때 구절을
      지어내지 않고 빈 리스트를 돌려줍니다.
    각 단계는 실제 서비스 → 실패 시 목업 순으로 폴백합니다.
    """
    from app.services import mock_data

    # 1) 인물 프로필 (Graph → 목업)
    try:
        person = graph_store.get_person(person_id)
    except Exception:
        person = None
    if not person:
        person = mock_data.PEOPLE.get(person_id, {"id": person_id, "name": person_id})
    books = person.get("books") or None

    # 2) 성경 구절 (Vector → 목업/빈 값)
    verse_source = "search"
    try:
        verses = retrieve_verses(message, books)
    except Exception:
        verses = []
    if not verses:
        if settings.ALLOW_MOCK_VERSES:
            verses = mock_data.mock_verses(infer_emotion(message))
            verse_source = "mock"
        else:
            verse_source = "none"

    # 3) 응답 생성 (LLM → 목업 페르소나)
    try:
        llm = get_llm(temperature=settings.LLM_TEMPERATURE)

        prompt = _persona_prompt(
            person=person,
            verses=verses,
            user_mbti=user_mbti,
            message=message,
            history=history,
            user_name=user_name,
            shared_memory=shared_memory,
            gender=gender,
        )

        out = llm.invoke(prompt)
        text = (out.content if hasattr(out, "content") else str(out)).strip()

    except Exception:
        emotion = infer_emotion(message)
        text = mock_data.mock_persona_answer(
            person,
            EMOTION_LABELS[emotion],
            message
        )
        return {"person": person, "verses": verses[: settings.SHOW_VERSE_COUNT],
                "answer": text, "verse_source": verse_source}

    # 4) 답변 끝의 [핵심구절: ...] 표시를 떼고, 그 구절 1개만 화면용으로 남김
    text, key_verses = _split_key_verse(text, verses)
    return {"person": person, "verses": key_verses,
            "answer": text, "verse_source": verse_source}