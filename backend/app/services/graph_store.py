"""
app/services/graph_store.py
────────────────────────────────────────────────────────────────────────
Neo4j Graph DB 서비스.

실제 팀 스키마 (2026-07, 라이브 Neo4j에 직접 접속해 확인 + 팀 스냅샷 병합):
  (:Disciple {id, name, title, speech_style, quote, quote_ref, traits, role,
              epithet, person_order})
  (:Jesus {name, quote, quote_ref, traits, role, epithet, person_order, mbti})
  (:MBTI {type})
  (:Trait {name})
  (:Verse {ref, text})
  (:User {name, mbti, created_at})

  (Disciple)-[:FOLLOWS]->(Jesus)
  (Disciple)-[:HAS_MBTI {rank}]->(MBTI)          제자 자신과 어울리는 MBTI (1,2순위)
  (MBTI)-[:MATCHES]->(Disciple)                  사용자 MBTI → 직접 매칭되는 제자 (16종 1:1)
  (MBTI)-[:MBTI_COMPATIBILITY {score}]->(MBTI)   16×16 전체 궁합 매트릭스 (팀 curated 데이터)
  (Disciple)-[:HAS_TRAIT]->(Trait)
  (Disciple)-[:RELATED_VERSE]->(Verse)
  (Disciple)-[:BROTHER_OF]->(Disciple)
  (User)-[:MATCHED_WITH {matched_at}]->(Disciple)

주의: Person/Book/APPEAR 라벨은 예전 설계 문서에 있었지만 이 그래프에는 없다
(팀 스냅샷도 별도 Person/Book 그래프였고, person_id로 매칭해서 quote/traits/
role/epithet 속성만 기존 Disciple/Jesus 노드에 병합했다 — 라벨 구조는 그대로).

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

# 사용자 MBTI → 16개 MBTI 전체와의 curated 궁합 점수 (자기 자신 포함, 0~100)
_MBTI_COMPAT_CYPHER = """
MATCH (:MBTI {type: $user_mbti})-[c:MBTI_COMPATIBILITY]->(m:MBTI)
RETURN m.type AS type, c.score AS score
"""

_ALL_DISCIPLES_CYPHER = """
MATCH (d:Disciple)
OPTIONAL MATCH (d)-[h:HAS_MBTI]->(dm:MBTI)
WITH d, collect({type: dm.type, rank: h.rank}) AS mbtis
OPTIONAL MATCH (d)-[:HAS_TRAIT]->(t:Trait)
WITH d, mbtis, collect(DISTINCT t.name) AS trait_nodes
OPTIONAL MATCH (d)-[:RELATED_VERSE]->(v:Verse)
RETURN d.id AS id, d.name AS name, d.title AS role, d.speech_style AS speech_style,
       d.quote AS quote, d.quote_ref AS quote_ref, d.traits AS traits_text,
       d.epithet AS epithet,
       mbtis, trait_nodes,
       collect(DISTINCT {ref: v.ref, text: v.text}) AS verses
"""

_ONE_DISCIPLE_CYPHER = """
MATCH (d:Disciple {id: $pid})
OPTIONAL MATCH (d)-[:HAS_TRAIT]->(t:Trait)
OPTIONAL MATCH (d)-[:RELATED_VERSE]->(v:Verse)
RETURN d.id AS id, d.name AS name, d.title AS role, d.speech_style AS speech_style,
       d.quote AS quote, d.quote_ref AS quote_ref, d.traits AS traits_text,
       d.epithet AS epithet,
       collect(DISTINCT t.name) AS trait_nodes,
       collect(DISTINCT {ref: v.ref, text: v.text}) AS verses
"""


def _row_to_person(row: dict) -> dict:
    """Neo4j 조회 결과 + mock_data(팀 원본 성경서 목록)를 합쳐 카드/프롬프트용 dict로 만든다.
    quote/quote_ref/traits/role은 이제 그래프 노드 자체에 있으므로(팀 스냅샷 병합) 그래프 값을
    우선 쓰고, 혹시 비어 있으면(향후 새 인물 추가 등) mock_data로 보완한다."""
    pid = row["id"]
    mock = mock_data.PEOPLE.get(pid, {})
    verses = [v for v in (row.get("verses") or []) if v.get("ref")]
    return {
        "id": pid,
        "name": row["name"],
        "role": row.get("role") or mock.get("role", ""),
        "epithet": row.get("epithet", ""),
        "speech_style": row.get("speech_style", ""),
        "traits": row.get("traits_text") or " · ".join(row.get("trait_nodes") or []) or mock.get("traits", "—"),
        "quote": row.get("quote") or mock.get("quote") or (verses[0]["text"] if verses else ""),
        "quote_ref": row.get("quote_ref") or mock.get("quote_ref") or (verses[0]["ref"] if verses else ""),
        "books": mock.get("books", []),
        "verses": verses,
    }


def recommend_disciples(user_mbti: str, limit: int = 12) -> list[dict]:
    """
    사용자 MBTI로 궁합 좋은 제자 상위 N명을 반환.
    (MBTI)-[:MATCHES]->(Disciple) 직접 매칭이 있으면 최고점(100)을 주고,
    나머지는 제자 자신의 HAS_MBTI(1,2순위) 타입과 사용자 MBTI 사이의 실제
    MBTI_COMPATIBILITY curated 점수로 순위를 매긴다(글자 유사도 근사가 아님).
    각 항목의 verses(연관 구절)가 hybrid 검색 컨텍스트 보강에 쓰인다.
    """
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        direct_ids = {r["id"] for r in session.run(_DIRECT_MATCH_CYPHER, user_mbti=user_mbti).data()}
        compat_rows = session.run(_MBTI_COMPAT_CYPHER, user_mbti=user_mbti).data()
        rows = session.run(_ALL_DISCIPLES_CYPHER).data()

    compat = {r["type"]: r["score"] for r in compat_rows if r["type"] and r["score"] is not None}

    def _compat_score(mbti_type: str) -> float:
        if mbti_type in compat:
            return compat[mbti_type]
        return _mbti_overlap(user_mbti, mbti_type) * 100  # 매트릭스에 없는 타입 대비 폴백

    ranked = []
    for row in rows:
        mbtis = sorted((m for m in row["mbtis"] if m.get("type")), key=lambda m: m.get("rank") or 9)
        best = 0.0
        for m in mbtis:
            weight = 1.0 if m.get("rank") == 1 else 0.85
            best = max(best, _compat_score(m["type"]) * weight)
        score = 100.0 if row["id"] in direct_ids else round(min(best, 99.0), 1)

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
    """해당 MBTI와 궁합 좋은 상위 MBTI 코드. MBTI_COMPATIBILITY curated 매트릭스 기반
    (그래프에 병합됨). 조회 실패 시에만 글자 유사도로 근사한다."""
    try:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            rows = session.run(
                """
                MATCH (:MBTI {type: $mbti})-[c:MBTI_COMPATIBILITY]->(m:MBTI)
                WHERE m.type <> $mbti
                RETURN m.type AS code ORDER BY c.score DESC LIMIT $limit
                """,
                mbti=mbti, limit=limit,
            ).data()
        if rows:
            return [r["code"] for r in rows]
    except Exception:
        pass
    pairs = sorted(
        ((t, _mbti_overlap(mbti, t)) for t in TYPE_ORDER if t != mbti),
        key=lambda x: x[1], reverse=True,
    )
    return [t for t, _ in pairs[:limit]]
