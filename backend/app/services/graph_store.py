"""
app/services/graph_store.py
────────────────────────────────────────────────────────────────────────
Neo4j Graph DB 서비스.

역할: "이 사용자에게 어떤 제자가 맞는가"를 그래프 관계로 계산.
      기존 app2.py의 궁합 쿼리를 확장해, 추천 제자와 함께
      그 제자의 성향(Trait)·연관 성경서(Versus)까지 한 번에 가져옵니다.
      → 이 성경서 목록이 vector_store.search(books=...) 의 필터로 넘어갑니다.
        (Hybrid RAG의 'Graph가 Vector를 안내' 하는 연결고리)

연결은 드라이버를 싱글턴으로 재사용합니다.
"""

from functools import lru_cache
from app.core.config import settings


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


# ── 궁합 기반 제자 추천 (+ 성향/성경서) ─────────────────────────────────
# 팀 Neo4j 스키마:
#   (Person)-[:HAS_MBTI]->(MBTI)  또는 Person.mbti 프로퍼티
#   (MBTI)-[:MBTI_COMPATIBILITY {score}]->(MBTI)
#   (Person)-[:HAS_TRAIT]->(Trait)          (팀원1)
#   (Person)-[:RELATED_TO]->(Versus{book})  (팀원2)
# 스키마가 확정되면 이 Cypher만 팀 구조에 맞게 손보면 됩니다.
_RECOMMEND_CYPHER = """
MATCH (u:MBTI {code: $user_mbti})
      -[c:MBTI_COMPATIBILITY]->(target:MBTI)
MATCH (p:Person)
WHERE p.mbti = target.code AND coalesce(p.role,'') <> '선한 목자'
OPTIONAL MATCH (p)-[:HAS_TRAIT]->(t:Trait)
OPTIONAL MATCH (p)-[:RELATED_TO]->(v:Versus)
RETURN p.person_id      AS id,
       p.name           AS name,
       p.mbti           AS mbti,
       p.role           AS role,
       p.traits         AS traits,
       p.quote          AS quote,
       p.quote_ref      AS quote_ref,
       c.score          AS score,
       collect(DISTINCT t.name) AS trait_nodes,
       collect(DISTINCT v.book) AS books
ORDER BY score DESC, p.person_order
LIMIT $limit
"""


def recommend_disciples(user_mbti: str, limit: int = 3) -> list[dict]:
    """
    사용자 MBTI로 궁합 좋은 제자 상위 N명을 반환.
    각 항목에 연관 성경서(books)가 포함되어 hybrid 검색 필터로 쓰입니다.
    """
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        rows = session.run(_RECOMMEND_CYPHER, user_mbti=user_mbti, limit=limit).data()
    return rows


def get_person(person_id: str) -> dict | None:
    """단일 인물 프로필 조회 (프로필 카드용)."""
    cypher = """
    MATCH (p:Person {person_id: $pid})
    OPTIONAL MATCH (p)-[:RELATED_TO]->(v:Versus)
    RETURN p.person_id AS id, p.name AS name, p.mbti AS mbti, p.role AS role,
           p.traits AS traits, p.quote AS quote, p.quote_ref AS quote_ref,
           collect(DISTINCT v.book) AS books
    """
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        rec = session.run(cypher, pid=person_id).data()
    return rec[0] if rec else None


def best_matching_mbti(mbti: str, limit: int = 3) -> list[str]:
    """해당 MBTI와 궁합 좋은 상위 MBTI 코드 (프로필 카드 '잘 맞는 MBTI')."""
    cypher = """
    MATCH (:MBTI {code: $mbti})-[c:MBTI_COMPATIBILITY]->(m:MBTI)
    WHERE m.code <> $mbti
    RETURN m.code AS code ORDER BY c.score DESC LIMIT $limit
    """
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        rows = session.run(cypher, mbti=mbti, limit=limit).data()
    return [r["code"] for r in rows]
