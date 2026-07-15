"""
app/services/mock_data.py
────────────────────────────────────────────────────────────────────────
Neo4j / Chroma / LLM 이 아직 안 붙은 환경에서도 데모가 끝까지 돌도록
하는 폴백 데이터·로직. 실제 서비스가 연결되면 자동으로 우선 사용되고
이 목업은 예외 상황에서만 쓰입니다.

인물/궁합 데이터는 팀 파일(인물들.json, neo4j_seed.py)과 동일한 값을 사용합니다.
"""

# 인물들.json 과 동일 (12제자 + 예수)
PEOPLE = {
    "jesus": {"id": "jesus", "name": "예수 그리스도", "mbti": "INFJ", "role": "선한 목자",
              "traits": "통찰 · 사랑 · 사명", "quote": "수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라",
              "quote_ref": "마태복음 11:28", "books": ["마", "요"], "book_full_names": ["마태복음", "요한복음"]},
    "peter": {"id": "peter", "name": "베드로", "mbti": "ESFP", "role": "반석",
              "traits": "열정 · 회복 · 행동", "quote": "주는 그리스도시요 살아 계신 하나님의 아들이시니이다",
              "quote_ref": "마태복음 16:16", "books": ["마", "벧전"], "book_full_names": ["마태복음", "베드로전서"]},
    "john": {"id": "john", "name": "요한", "mbti": "INFP", "role": "사랑받는 제자",
             "traits": "사랑 · 관계 · 깊은 묵상", "quote": "사랑하는 자들아 우리가 서로 사랑하자 사랑은 하나님께 속한 것이니",
             "quote_ref": "요한1서 4:7", "books": ["요", "요일"], "book_full_names": ["요한복음", "요한1서"]},
    "james": {"id": "james", "name": "야고보", "mbti": "ENTJ", "role": "천둥의 아들",
              "traits": "신념 · 추진력", "quote": "주여 우리가 하늘로부터 불을 명하여 저들을 멸하라 하기를 원하시나이까",
              "quote_ref": "누가복음 9:54", "books": ["눅", "막"], "book_full_names": ["누가복음", "마가복음"]},
    "andrew": {"id": "andrew", "name": "안드레", "mbti": "ISFJ", "role": "연결자",
               "traits": "조용한 섬김 · 소개", "quote": "우리가 메시야를 만났다",
               "quote_ref": "요한복음 1:41", "books": ["요"], "book_full_names": ["요한복음"]},
    "philip": {"id": "philip", "name": "빌립", "mbti": "ISTJ", "role": "확인하는 자",
               "traits": "현실적 · 계산 · 확인", "quote": "주여 아버지를 우리에게 보여 주옵소서 그리하면 족하겠나이다",
               "quote_ref": "요한복음 14:8", "books": ["요"], "book_full_names": ["요한복음"]},
    "bartholomew": {"id": "bartholomew", "name": "바돌로매", "mbti": "ISTJ", "role": "참된 자",
                    "traits": "정직 · 순수 · 원칙", "quote": "랍비여 당신은 하나님의 아들이시요 당신은 이스라엘의 임금이로소이다",
                    "quote_ref": "요한복음 1:49", "books": ["요"], "book_full_names": ["요한복음"]},
    "matthew": {"id": "matthew", "name": "마태", "mbti": "INTJ", "role": "기록하는 자",
                "traits": "분석 · 기록 · 변화 경험", "quote": "일어나 그를 좇으니라",
                "quote_ref": "마태복음 9:9", "books": ["마"], "book_full_names": ["마태복음"]},
    "thomas": {"id": "thomas", "name": "도마", "mbti": "INTP", "role": "묻는 자",
               "traits": "의심 · 검증 · 확신 추구", "quote": "나의 주님이시요 나의 하나님이시니이다",
               "quote_ref": "요한복음 20:28", "books": ["요"], "book_full_names": ["요한복음"]},
    "james_alph": {"id": "james_alph", "name": "작은 야고보", "mbti": "ISFJ", "role": "조용한 증인",
                   "traits": "드러나지 않는 충성", "quote": "행함이 없는 믿음은 그 자체가 죽은 것이라",
                   "quote_ref": "야고보서 2:17", "books": ["약"], "book_full_names": ["야고보서"]},
    "thaddaeus": {"id": "thaddaeus", "name": "다대오", "mbti": "ENFP", "role": "질문하는 자",
                  "traits": "질문 · 공동체 관심", "quote": "주여 어찌하여 자기를 우리에게는 나타내시고 세상에는 아니하려 하시나이까",
                  "quote_ref": "요한복음 14:22", "books": ["요"], "book_full_names": ["요한복음"]},
    "simon": {"id": "simon", "name": "시몬", "mbti": "ESTP", "role": "열심당원",
              "traits": "열정 · 신념 · 행동파", "quote": "열심으로 하나님을 섬기던 자, 이제 그 열심을 복음에 쏟다",
              "quote_ref": "누가복음 6:15", "books": ["눅"], "book_full_names": ["누가복음"]},
    "judas": {"id": "judas", "name": "가룟 유다", "mbti": "ENTJ", "role": "회계",
              "traits": "계산 · 현실 감각", "quote": "내가 무죄한 피를 팔고 죄를 범하였도다",
              "quote_ref": "마태복음 27:4", "books": ["마"], "book_full_names": ["마태복음"]},
}

TYPE_ORDER = ("INFJ", "INFP", "INTJ", "INTP", "ENFJ", "ENFP", "ENTJ", "ENTP",
              "ISFJ", "ISFP", "ISTJ", "ISTP", "ESFJ", "ESFP", "ESTJ", "ESTP")

# neo4j_seed.py SCORES 와 동일
SCORES = {
    "INFJ": (72, 92, 78, 85, 92, 100, 85, 98, 49, 56, 42, 49, 56, 63, 49, 56),
    "INFP": (92, 72, 85, 78, 100, 92, 98, 85, 56, 49, 49, 42, 63, 56, 56, 49),
    "INTJ": (78, 85, 72, 92, 85, 98, 92, 100, 42, 49, 49, 56, 49, 56, 56, 63),
    "INTP": (85, 78, 92, 72, 98, 85, 100, 92, 49, 42, 56, 49, 56, 49, 63, 56),
    "ENFJ": (92, 100, 85, 98, 72, 92, 78, 85, 56, 63, 49, 56, 49, 56, 42, 49),
    "ENFP": (100, 92, 98, 85, 92, 72, 85, 78, 63, 56, 56, 49, 56, 49, 49, 42),
    "ENTJ": (85, 98, 92, 100, 78, 85, 72, 92, 49, 56, 56, 63, 42, 49, 49, 56),
    "ENTP": (98, 85, 100, 92, 85, 78, 92, 72, 56, 49, 63, 56, 49, 42, 56, 49),
    "ISFJ": (49, 56, 42, 49, 56, 63, 49, 56, 72, 92, 78, 85, 92, 100, 85, 98),
    "ISFP": (56, 49, 49, 42, 63, 56, 56, 49, 92, 72, 85, 78, 100, 92, 98, 85),
    "ISTJ": (42, 49, 49, 56, 49, 56, 56, 63, 78, 85, 72, 92, 85, 98, 92, 100),
    "ISTP": (49, 42, 56, 49, 56, 49, 63, 56, 85, 78, 92, 72, 98, 85, 100, 92),
    "ESFJ": (56, 63, 49, 56, 49, 56, 42, 49, 92, 100, 85, 98, 72, 92, 78, 85),
    "ESFP": (63, 56, 56, 49, 56, 49, 49, 42, 100, 92, 98, 85, 92, 72, 85, 78),
    "ESTJ": (49, 56, 56, 63, 42, 49, 49, 56, 85, 98, 92, 100, 78, 85, 72, 92),
    "ESTP": (56, 49, 63, 56, 49, 42, 56, 49, 98, 85, 100, 92, 85, 78, 92, 72),
}


def compat_score(a: str, b: str) -> int:
    if a not in SCORES or b not in TYPE_ORDER:
        return 50
    return SCORES[a][TYPE_ORDER.index(b)]


def best_matching_mbti(mbti: str, limit: int = 3) -> list[str]:
    if mbti not in SCORES:
        return []
    pairs = sorted(zip(TYPE_ORDER, SCORES[mbti]), key=lambda x: x[1], reverse=True)
    return [t for t, _ in pairs if t != mbti][:limit]


def recommend_disciples(user_mbti: str, limit: int = 12) -> list[dict]:
    """graph_store.recommend_disciples 의 목업 버전."""
    rows = []
    for pid, p in PEOPLE.items():
        if pid == "jesus":
            continue
        rows.append({
            "id": pid, "name": p["name"], "mbti": p["mbti"], "role": p["role"],
            "traits": p["traits"], "quote": p["quote"], "quote_ref": p["quote_ref"],
            "score": compat_score(user_mbti, p["mbti"]),
            "books": p["books"], "book_full_names": p["book_full_names"], "trait_nodes": [],
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:limit]


# 성경 구절 목업 (Vector DB 미연결 시). 감정 키 → 대표 구절 몇 개
MOCK_VERSES = {
    "anxiety": [
        {"book": "빌립보서", "chapter": 4, "verse": 6, "content": "아무 것도 염려하지 말고 다만 모든 일에 기도와 간구로 너희 구할 것을 감사함으로 하나님께 아뢰라"},
        {"book": "이사야", "chapter": 41, "verse": 10, "content": "두려워하지 말라 내가 너와 함께 함이라 놀라지 말라 나는 네 하나님이 됨이라"},
    ],
    "sadness": [
        {"book": "시편", "chapter": 34, "verse": 18, "content": "여호와는 마음이 상한 자를 가까이 하시고 충심으로 통회하는 자를 구원하시는도다"},
        {"book": "마태복음", "chapter": 11, "verse": 28, "content": "수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라"},
    ],
    "doubt": [
        {"book": "요한복음", "chapter": 20, "verse": 27, "content": "네 손가락을 이리 내밀어 내 손을 보고 네 손을 내밀어 내 옆구리에 넣어 보라 그리하고 믿음 없는 자가 되지 말고 믿는 자가 되라"},
    ],
    "neutral": [
        {"book": "잠언", "chapter": 3, "verse": 5, "content": "너는 마음을 다하여 여호와를 신뢰하고 네 명철을 의지하지 말라"},
    ],
}


def mock_verses(emotion: str) -> list[dict]:
    vs = MOCK_VERSES.get(emotion) or MOCK_VERSES["neutral"]
    return [{**v, "source": f"{v['book']} {v['chapter']}:{v['verse']}"} for v in vs]


def mock_persona_answer(person: dict, emotion_label: str, message: str) -> str:
    """LLM 미연결 시 제자 페르소나 목업 응답."""
    name = person["name"]
    lines = {
        "peter": f"그 마음 잘 안다네. 나도 파도 앞에서 흔들렸던 사람 아닌가. 그 {emotion_label}, 여기 내려놓게.",
        "john": f"그 {emotion_label}을(를) 여기 다 내려놓아도 괜찮아요. 사랑은 언제나 우리를 먼저 품는답니다.",
        "thomas": f"의심이 드는 게 당연해요. 함께 하나씩 짚어봅시다. 확인하고 나면 마음이 한결 가벼워질 거예요.",
        "james": f"핵심부터 짚어보세. 그 {emotion_label} 뒤에 진짜 원하는 게 무엇인가?",
    }
    return lines.get(person["id"], f"{name}(이)가 당신의 {emotion_label}에 조용히 귀 기울입니다. 편히 이야기해 보세요.")
