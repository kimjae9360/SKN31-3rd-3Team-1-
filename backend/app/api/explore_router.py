"""
app/api/explore_router.py
────────────────────────────────────────────────────────────────────────
포털 사이드 콘텐츠용 엔드포인트.

  GET  /api/explore/people           : 인물 12제자+예수 목록 (탐색/관계도용)
  GET  /api/explore/person/{id}      : 인물 상세 (프로필 카드)
  GET  /api/explore/match/{mbti}     : MBTI 진단 결과 - 가장 잘 맞는 제자
  GET  /api/explore/graph            : MBTI-제자 관계 그래프 데이터 (시각화용)

Graph DB가 있으면 그걸, 없으면 목업을 사용합니다.
"""

from fastapi import APIRouter, HTTPException
from app.services import graph_store, mock_data

router = APIRouter(prefix="/api/explore", tags=["explore"])


@router.get("/people")
def people():
    """인물 목록 (탐색 그리드/관계도)."""
    return list(mock_data.PEOPLE.values())


@router.get("/person/{person_id}")
def person(person_id: str):
    try:
        p = graph_store.get_person(person_id)
    except Exception:
        p = None
    if not p:
        p = mock_data.PEOPLE.get(person_id)
    if not p:
        raise HTTPException(status_code=404, detail="인물을 찾을 수 없습니다.")
    p = {**p, "best_mbti": mock_data.best_matching_mbti(p["mbti"])}
    return p


@router.get("/match/{mbti}")
def match(mbti: str):
    """MBTI 진단 결과: 궁합 순 제자 상위 3명 (공유 카드용)."""
    ranked = mock_data.recommend_disciples(mbti.upper(), limit=3)
    for r in ranked:
        r["best_mbti"] = mock_data.best_matching_mbti(r["mbti"])
    return {"mbti": mbti.upper(), "matches": ranked}


@router.get("/graph")
def graph():
    """
    관계 그래프 시각화용 노드/엣지.
    노드: MBTI 16 + 인물 13
    엣지: 인물-(HAS_MBTI)-MBTI, MBTI-(궁합 top)-MBTI
    """
    nodes, edges = [], []
    # MBTI 노드
    for t in mock_data.TYPE_ORDER:
        nodes.append({"id": f"mbti:{t}", "label": t, "type": "mbti"})
    # 인물 노드 + 인물→MBTI 엣지
    for pid, p in mock_data.PEOPLE.items():
        nodes.append({"id": f"person:{pid}", "label": p["name"], "type": "person", "mbti": p["mbti"]})
        edges.append({"source": f"person:{pid}", "target": f"mbti:{p['mbti']}", "kind": "has_mbti"})
    # MBTI 간 최고 궁합 엣지 (top1)
    for t in mock_data.TYPE_ORDER:
        best = mock_data.best_matching_mbti(t, limit=1)
        if best:
            edges.append({"source": f"mbti:{t}", "target": f"mbti:{best[0]}", "kind": "compat"})
    return {"nodes": nodes, "edges": edges}
