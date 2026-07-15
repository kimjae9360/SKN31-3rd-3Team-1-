"""
app/services/graph_store.py
────────────────────────────────────────────────────────────────────────
Neo4j Graph DB 서비스.

실제 팀 스키마 (2026-07 확인):
  (:Disciple {id, name, title, speech_style})
  (:Jesus {name})
  (:MBTI {type})
  (:Trait {name})
  (:Verse {ref, text})
  (:User {name, mbti, created_at})

  (Disciple)-[:FOLLOWS]->(Jesus)
  (Disciple)-[:HAS_MBTI {rank}]->(MBTI)     제자 자신과 어울리는 MBTI (1,2순위)
  (MBTI)-[:MATCHES]->(Disciple)             사용자 MBTI → 직접 매칭되는 제자 (16종 1:1)
  (Disciple)-[:HAS_TRAIT]->(Trait)
  (Disciple)-[:RELATED_VERSE]->(Verse)
  (Disciple)-[:BROTHER_OF]->(Disciple)
  (User)-[:MATCHED_WITH {matched_at}]->(Disciple)

주의: MBTI 코드 간 궁합 관계(예 옛 설계의 MBTI_COMPATIBILITY)는 이 그래프에
존재하지 않습니다. 궁합 순위는 (1) 사용자 MBTI와 직접 MATCHES 되는 제자를
최우선으로, (2) 나머지는 제자 자신의 HAS_MBTI(1,2순위)와 사용자 MBTI의
글자 일치도로 근사해 매깁니다.

연결은 드라이버를 싱글턴으로 재사용합니다.
"""

from functools import lru_cache
from app.core.config import settings
from app.services import mock_data

TYPE_ORDER = mock_data.TYPE_ORDER


@lru_cache
def get_driver():
    """Neo4j 드라이버 싱글턴. (neo4j 미설치 시 여기서 ImportError → 상위에서 목업 폴백)"""
    from neo4j import GraphDatabase   # 지연 import: 미설치 환경에서도 앱 로드 가능
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def close_driver():
    if get_driver.cache_info().currsize:
        get_driver().close()
        get_driver.cache_clear()


def _mbti_overlap(a: str, b: str) -> float:
    """두 MBTI 코드의 글자 일치 비율(0~1). 그래프에 MBTI-MBTI 궁합 관계가 없어 유사도로 근사."""
    if not a or not b or len(a) != 4 or len(b) != 4:
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / 4


_DIRECT_MATCH_CYPHER = """
MATCH (:MBTI {type: $user_mbti})-[:MATCHES]->(d:Disciple)
RETURN d.id AS id
"""

_ALL_DISCIPLES_CYPHER = """
MATCH (d:Disciple)
OPTIONAL MATCH (d)-[h:HAS_MBTI]->(dm:MBTI)
WITH d, collect({type: dm.type, rank: h.rank}) AS mbtis
OPTIONAL MATCH (d)-[:HAS_TRAIT]->(t:Trait)
WITH d, mbtis, collect(DISTINCT t.name) AS trait_nodes
OPTIONAL MATCH (d)-[:RELATED_VERSE]->(v:Verse)
RETURN d.id AS id, d.name AS name, d.title AS role, d.speech_style AS speech_style,
       mbtis, trait_nodes,
       collect(DISTINCT {ref: v.ref, text: v.text}) AS verses
"""

_ONE_DISCIPLE_CYPHER = """
MATCH (d:Disciple {id: $pid})
OPTIONAL MATCH (d)-[:HAS_TRAIT]->(t:Trait)
OPTIONAL MATCH (d)-[:RELATED_VERSE]->(v:Verse)
RETURN d.id AS id, d.name AS name, d.title AS role, d.speech_style AS speech_style,
       collect(DISTINCT t.name) AS trait_nodes,
       collect(DISTINCT {ref: v.ref, text: v.text}) AS verses
"""


def _row_to_person(row: dict) -> dict:
    """Neo4j 조회 결과 + mock_data(팀 원본 성경서/대표 인용구)를 합쳐 카드/프롬프트용 dict로 만든다.
    id로 1:1 매핑되는 정적 표시 데이터(quote, books)는 그래프에 없으므로 mock_data에서 보완한다."""
    pid = row["id"]
    mock = mock_data.PEOPLE.get(pid, {})
    verses = [v for v in (row.get("verses") or []) if v.get("ref")]
    return {
        "id": pid,
        "name": row["name"],
        "role": row.get("role") or mock.get("role", ""),
        "speech_style": row.get("speech_style", ""),
        "traits": " · ".join(row.get("trait_nodes") or []) or mock.get("traits", "—"),
        "quote": mock.get("quote") or (verses[0]["text"] if verses else ""),
        "quote_ref": mock.get("quote_ref") or (verses[0]["ref"] if verses else ""),
        "books": mock.get("books", []),
        "verses": verses,
    }


def recommend_disciples(user_mbti: str, limit: int = 12) -> list[dict]:
    """
    사용자 MBTI로 궁합 좋은 제자 상위 N명을 반환.
    (MBTI)-[:MATCHES]->(Disciple) 직접 매칭이 있으면 최고점(100)을 주고,
    나머지는 제자 자신의 HAS_MBTI(1,2순위)와의 글자 유사도로 순위를 매긴다.
    각 항목의 verses(연관 구절)가 hybrid 검색 컨텍스트 보강에 쓰인다.
    """
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        direct_ids = {r["id"] for r in session.run(_DIRECT_MATCH_CYPHER, user_mbti=user_mbti).data()}
        rows = session.run(_ALL_DISCIPLES_CYPHER).data()

    ranked = []
    for row in rows:
        mbtis = sorted((m for m in row["mbtis"] if m.get("type")), key=lambda m: m.get("rank") or 9)
        best = 0.0
        for m in mbtis:
            weight = 1.2 if m.get("rank") == 1 else 0.8
            best = max(best, _mbti_overlap(user_mbti, m["type"]) * weight)
        score = 100.0 if row["id"] in direct_ids else round(best * 70, 1)

        person = _row_to_person(row)
        person["mbti"] = mbtis[0]["type"] if mbtis else ""
        person["score"] = score
        ranked.append(person)

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:limit]


def get_person(person_id: str) -> dict | None:
    """단일 인물 프로필 조회 (프로필 카드/페르소나 프롬프트용).
    Jesus는 Disciple 라벨이 아니라 여기서 None을 반환 → 상위(hybrid_rag)가 mock_data로 폴백."""
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        rec = session.run(_ONE_DISCIPLE_CYPHER, pid=person_id).data()
    if not rec:
        return None
    return _row_to_person(rec[0])


def best_matching_mbti(mbti: str, limit: int = 3) -> list[str]:
    """해당 MBTI와 궁합 좋은 상위 MBTI 코드. 그래프에 MBTI-MBTI 궁합 관계가 없어 글자 유사도로 근사.
    (현재 프론트는 mock_data.best_matching_mbti의 팀 큐레이션 매트릭스를 우선 사용하고,
     이 함수는 향후 Neo4j 단독 경로가 필요할 때를 위한 대비용이다.)"""
    pairs = sorted(
        ((t, _mbti_overlap(mbti, t)) for t in TYPE_ORDER if t != mbti),
        key=lambda x: x[1], reverse=True,
    )
    return [t for t, _ in pairs[:limit]]
