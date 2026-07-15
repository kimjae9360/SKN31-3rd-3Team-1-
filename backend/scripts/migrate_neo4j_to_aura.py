"""
backend/scripts/migrate_neo4j_to_aura.py
────────────────────────────────────────────────────────────────────────
로컬 Neo4j(Desktop/Docker)의 데이터를 Neo4j Aura(클라우드)로 그대로 복사한다.

왜 필요한가:
  Streamlit Cloud에 배포된 앱은 팀원의 로컬 PC에 떠 있는 Neo4j에 접속할 수
  없다. 배포판에서도 실제 그래프 기반 추천이 동작하려면, 어디서든 접근 가능한
  Neo4j Aura(무료 티어)에 같은 데이터가 있어야 한다.

  팀에 별도 시드 스크립트가 없어(데이터가 Neo4j Browser 등에서 수동으로
  만들어진 것으로 보임), 있는 그대로 export → import 하는 범용 방식을 쓴다.

사용법:
  1. https://neo4j.com/product/auradb/ 에서 무료 인스턴스 생성
     (생성 직후에만 보여주는 비밀번호를 반드시 저장해 둘 것)
  2. 아래 환경변수를 채운 뒤 실행:

     # 원본(로컬) — 비워두면 backend/.env의 NEO4J_* 값을 그대로 사용
     SOURCE_NEO4J_URI=bolt://localhost:7687
     SOURCE_NEO4J_USER=neo4j
     SOURCE_NEO4J_PASSWORD=...

     # 대상(Aura) — Aura 콘솔에서 발급받은 값
     AURA_NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
     AURA_NEO4J_USER=neo4j
     AURA_NEO4J_PASSWORD=...

  3. python backend/scripts/migrate_neo4j_to_aura.py

  재실행해도 안전합니다 (대상 DB를 먼저 비우고 다시 씁니다).
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

from neo4j import GraphDatabase  # noqa: E402

SRC_URI = os.getenv("SOURCE_NEO4J_URI") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
SRC_USER = os.getenv("SOURCE_NEO4J_USER") or os.getenv("NEO4J_USER", "neo4j")
SRC_PW = os.getenv("SOURCE_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD", "password")

DST_URI = os.getenv("AURA_NEO4J_URI")
DST_USER = os.getenv("AURA_NEO4J_USER", "neo4j")
DST_PW = os.getenv("AURA_NEO4J_PASSWORD")

_MIGRATION_KEY = "_migration_id"  # 대상 DB에 임시로 붙였다가 마지막에 지우는 표식


def export_graph(src_driver, database: str):
    """원본 DB의 모든 노드와 관계를 파이썬 객체로 읽어온다."""
    with src_driver.session(database=database) as session:
        nodes = session.run(
            "MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props"
        ).data()
        rels = session.run(
            """
            MATCH (a)-[r]->(b)
            RETURN elementId(a) AS start_id, elementId(b) AS end_id,
                   type(r) AS type, properties(r) AS props
            """
        ).data()
    return nodes, rels


def import_graph(dst_driver, database: str, nodes: list[dict], rels: list[dict]):
    """대상 DB를 비우고, 노드 → 관계 순으로 그대로 재생성한다."""
    with dst_driver.session(database=database) as session:
        session.run("MATCH (n) DETACH DELETE n")

        for n in nodes:
            labels = ":".join(n["labels"]) if n["labels"] else ""
            label_clause = f":{labels}" if labels else ""
            props = {**n["props"], _MIGRATION_KEY: n["id"]}
            session.run(f"CREATE (n{label_clause}) SET n = $props", props=props)

        for r in rels:
            session.run(
                f"""
                MATCH (a {{{_MIGRATION_KEY}: $start_id}}), (b {{{_MIGRATION_KEY}: $end_id}})
                CREATE (a)-[rel:{r['type']}]->(b)
                SET rel = $props
                """,
                start_id=r["start_id"], end_id=r["end_id"], props=r["props"],
            )

        session.run(f"MATCH (n) REMOVE n.{_MIGRATION_KEY}")


def main():
    if not DST_URI or not DST_PW:
        print("[에러] AURA_NEO4J_URI / AURA_NEO4J_PASSWORD 환경변수가 없습니다.")
        print("       Aura 콘솔에서 인스턴스를 만들고 접속 정보를 채운 뒤 다시 실행하세요.")
        sys.exit(1)

    print(f"원본: {SRC_URI}")
    print(f"대상: {DST_URI}")

    src = GraphDatabase.driver(SRC_URI, auth=(SRC_USER, SRC_PW))
    dst = GraphDatabase.driver(DST_URI, auth=(DST_USER, DST_PW))

    try:
        src.verify_connectivity()
        dst.verify_connectivity()

        nodes, rels = export_graph(src, database="neo4j")
        print(f"내보낸 노드: {len(nodes)}개 / 관계: {len(rels)}개")

        import_graph(dst, database="neo4j", nodes=nodes, rels=rels)
        print("Aura로 복사 완료.")

        with dst.session(database="neo4j") as session:
            cnt = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            print(f"검증: Aura에 총 {cnt}개 노드 확인됨.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()
