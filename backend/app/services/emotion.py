"""
app/services/emotion.py
────────────────────────────────────────────────────────────────────────
사용자 발화의 감정 추론.

1차: 빠르고 무료인 키워드 규칙 (지연 0, 비용 0)
2차: 규칙이 'neutral'일 때만 LLM에 물어보는 폴백 (선택)
     → 대부분의 명확한 감정은 규칙에서 걸러지므로 LLM 호출을 아낍니다.

감정 라벨은 제자 추천의 '감정 바이어스'와 프론트 표시에 쓰입니다.
"""

from app.services.llm import get_llm

EMOTION_LABELS = {
    "anxiety": "불안",
    "sadness": "슬픔",
    "anger": "분노",
    "joy": "기쁨",
    "doubt": "의문",
    "decision": "고민",
    "neutral": "이야기",
}

_KEYWORDS = {
    "anxiety": ["불안", "걱정", "두렵", "무서", "초조", "막막", "긴장"],
    "sadness": ["슬프", "우울", "눈물", "외로", "공허", "지치", "힘들", "지쳐", "허무"],
    "anger": ["화", "짜증", "억울", "분노", "열받", "미워", "원망"],
    "joy": ["감사", "기쁘", "행복", "설레", "좋아", "고마", "뿌듯"],
    "doubt": ["의심", "확신", "정말", "증거", "왜", "이해가", "믿기"],
    "decision": ["결정", "선택", "고민", "어떻게", "방향", "진로", "갈림길"],
}


def infer_emotion(text: str, use_llm_fallback: bool = False) -> str:
    """텍스트에서 감정 키 반환 (EMOTION_LABELS의 키)."""
    for emo, words in _KEYWORDS.items():
        if any(w in text for w in words):
            return emo

    if not use_llm_fallback:
        return "neutral"

    # LLM 폴백: 규칙으로 못 잡은 미묘한 감정만
    llm = get_llm(temperature=0.0)
    labels = ", ".join(EMOTION_LABELS.keys())
    prompt = (
        f"다음 문장의 핵심 감정을 [{labels}] 중 하나의 영어 키로만 답하라. "
        f"설명 금지.\n문장: {text}\n감정:"
    )
    try:
        out = llm.invoke(prompt)
        key = (out.content if hasattr(out, "content") else str(out)).strip().lower()
        return key if key in EMOTION_LABELS else "neutral"
    except Exception:
        return "neutral"
