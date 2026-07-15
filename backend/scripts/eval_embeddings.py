"""
backend/scripts/eval_embeddings.py
────────────────────────────────────────────────────────────────────────
HuggingFace(ko-sroberta-multitask) vs OpenAI(text-embedding-3-small)
임베딩 검색 정확도 비교 스크립트.

결과와 방법론 설명은 docs/embedding_eval_report.md 를 참고하세요.

전제조건:
  1. <프로젝트 루트>/data/chroma_db/chroma.sqlite3 가 존재할 것
     (로컬 HuggingFace 임베딩으로 빌드된 Chroma DB. Chroma의 HNSW 벡터
      인덱스가 손상되어 있어도 무방합니다 — 이 스크립트는 Chroma의 검색
      API를 쓰지 않고 SQLite에서 원문 텍스트만 직접 읽습니다.)
  2. backend/.env 또는 루트 .env 에 OPENAI_API_KEY 가 설정되어 있을 것

실행 (어느 위치에서 실행해도 결과 경로는 동일합니다):
  python backend/scripts/eval_embeddings.py
  python backend/scripts/eval_embeddings.py --n-queries 40 --seed 42

동작 방식:
  1. chroma.sqlite3 에서 (book, chapter, verse, content)를 직접 추출해
     검색 후보 코퍼스 풀을 구성합니다 (기본: 전체).
  2. 족보/율법 목록 위주 책(레/민/대상/대하/스/느)은 "질문 생성 대상"에서만
     제외합니다 — 자연어 고민 질문과 의미적으로 매칭되기 어렵기 때문입니다.
     검색 후보 풀에는 그대로 남겨 실제 노이즈로 유지합니다.
  3. GPT-4o-mini로 질문 N개를 생성한 뒤, 같은 코퍼스를 HuggingFace/OpenAI
     두 모델로 각각 새로 임베딩해 코사인 유사도 검색 정확도를 비교합니다.
  4. Recall@1/3/5, MRR 을 계산해 콘솔에 출력하고 JSON으로 저장합니다.
"""

import argparse
import json
import random
import sqlite3
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

import numpy as np  # noqa: E402
from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: E402

HF_MODEL = "jhgan/ko-sroberta-multitask"
OPENAI_MODEL = "text-embedding-3-small"

# 족보/율법 목록 위주 책은 "질문 생성 대상"에서만 제외 (검색 후보 풀에는 유지).
EXCLUDE_QUERY_BOOKS = {"레", "민", "대상", "대하", "스", "느"}

QGEN_PROMPT = (
    "다음은 성경 구절입니다.\n\n구절: {verse}\n\n"
    "이 구절의 핵심 상황·인물·감정·교훈 중 최소 하나는 구체적으로 담아서, "
    "사용자가 챗봇에게 자연스럽게 물어볼 법한 한국어 질문을 한 문장으로 만들어줘. "
    "구절 문장을 그대로 인용하지는 말되, 검색으로 이 구절을 다시 찾아낼 수 있을 만큼 "
    "구체적인 상황/인물/키워드는 반드시 살려줘 (너무 막연하고 일반적인 고민 문장으로만 쓰지 말 것). "
    "질문 문장만 출력하고 다른 설명은 붙이지 마."
)


def load_corpus(chroma_sqlite_path: Path) -> list[dict]:
    """chroma.sqlite3 에서 (book, chapter, verse, content)를 직접 추출한다.
    Chroma의 HNSW 벡터 인덱스가 손상돼 있어도 동작한다 (검색 API 미사용)."""
    con = sqlite3.connect(str(chroma_sqlite_path))
    cur = con.cursor()
    cur.execute("""
        SELECT id, key, string_value, int_value
        FROM embedding_metadata
        WHERE key IN ('book','chapter','verse','content')
    """)
    per_id: dict[int, dict] = {}
    for _id, key, sval, ival in cur.fetchall():
        per_id.setdefault(_id, {})[key] = sval if sval is not None else ival
    con.close()

    records = []
    for d in per_id.values():
        if "content" in d and "book" in d:
            records.append({
                "vid": f"{d.get('book')}_{d.get('chapter')}_{d.get('verse')}",
                "book": d.get("book"),
                "content": d["content"],
            })
    return records


def generate_queries(llm: ChatOpenAI, docs: list[str], verse_keys: list[str],
                      eligible_idx: list[int], n: int, seed: int) -> tuple[list[str], list[str]]:
    """샘플 구절마다 GPT로 자연어 고민 질문을 하나씩 생성한다 (self-supervised eval query)."""
    random.seed(seed)
    sample_idx = random.sample(eligible_idx, n)
    queries, truth = [], []
    for i in sample_idx:
        resp = llm.invoke(QGEN_PROMPT.format(verse=docs[i]))
        queries.append(resp.content.strip().strip('"'))
        truth.append(verse_keys[i])
    return queries, truth


def embed_corpus_openai(oa_emb: OpenAIEmbeddings, docs: list[str], batch: int = 500) -> np.ndarray:
    vecs = []
    for start in range(0, len(docs), batch):
        vecs.extend(oa_emb.embed_documents(docs[start:start + batch]))
    return np.array(vecs, dtype=np.float32)


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def top_k(query_vec: np.ndarray, doc_norms: np.ndarray, verse_keys: list[str], k: int = 5) -> list[str]:
    qn = query_vec / np.linalg.norm(query_vec)
    sims = doc_norms @ qn
    idx = np.argsort(-sims)[:k]
    return [verse_keys[i] for i in idx]


def compute_metrics(rank_lists: list[list[str]], truths: list[str]) -> dict:
    r1 = r3 = r5 = 0
    mrr_sum = 0.0
    for ranked, t in zip(rank_lists, truths):
        if t in ranked:
            pos = ranked.index(t) + 1
            mrr_sum += 1.0 / pos
            r1 += pos <= 1
            r3 += pos <= 3
            r5 += pos <= 5
    n = len(truths)
    return {
        "Recall@1": round(r1 / n, 4),
        "Recall@3": round(r3 / n, 4),
        "Recall@5": round(r5 / n, 4),
        "MRR": round(mrr_sum / n, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-queries", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pool-size", type=int, default=0, help="0이면 전체 코퍼스 사용")
    parser.add_argument("--chroma-sqlite", type=Path, default=ROOT / "data" / "chroma_db" / "chroma.sqlite3")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "embedding_eval_results.json")
    args = parser.parse_args()

    if not args.chroma_sqlite.exists():
        print(f"[에러] chroma.sqlite3 를 찾을 수 없습니다: {args.chroma_sqlite}")
        sys.exit(1)

    print("[1/6] chroma.sqlite3에서 원문 직접 추출 중...", flush=True)
    records = load_corpus(args.chroma_sqlite)
    print(f"    추출된 구절 수: {len(records)}", flush=True)

    random.seed(args.seed)
    random.shuffle(records)
    pool = records[: args.pool_size] if args.pool_size else records
    docs = [r["content"] for r in pool]
    verse_keys = [r["vid"] for r in pool]
    print(f"    검색 후보 코퍼스(pool) 크기: {len(docs)}", flush=True)

    print("[2/6] 테스트 쿼리용 구절 샘플링 (족보/율법 목록 책 제외)...", flush=True)
    eligible_idx = [i for i, r in enumerate(pool) if r["book"] not in EXCLUDE_QUERY_BOOKS]
    print(f"    질문 생성 대상 후보: {len(eligible_idx)} / {len(pool)}", flush=True)

    print("[3/6] GPT-4o-mini로 자연어 질문 생성 중...", flush=True)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    queries, truth = generate_queries(llm, docs, verse_keys, eligible_idx, args.n_queries, args.seed)
    for n, (q, t) in enumerate(zip(queries, truth), 1):
        print(f"    ({n}/{args.n_queries}) {t} -> {q}", flush=True)

    print(f"[4/6] HuggingFace({HF_MODEL})로 코퍼스({len(docs)}개) 임베딩 중...", flush=True)
    hf_emb = HuggingFaceEmbeddings(
        model_name=HF_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    t0 = time.time()
    hf_norms = normalize_rows(np.array(hf_emb.embed_documents(docs), dtype=np.float32))
    print(f"    완료: {hf_norms.shape}  ({time.time() - t0:.0f}s)", flush=True)

    print(f"[5/6] OpenAI({OPENAI_MODEL})로 코퍼스({len(docs)}개) 임베딩 중...", flush=True)
    oa_emb = OpenAIEmbeddings(model=OPENAI_MODEL)
    t0 = time.time()
    oa_norms = normalize_rows(embed_corpus_openai(oa_emb, docs))
    print(f"    완료: {oa_norms.shape}  ({time.time() - t0:.0f}s)", flush=True)

    print("[6/6] 검색 평가 실행 중...", flush=True)
    hf_results, oa_results, per_query = [], [], []
    for q, t in zip(queries, truth):
        hf_r = top_k(np.array(hf_emb.embed_query(q), dtype=np.float32), hf_norms, verse_keys)
        oa_r = top_k(np.array(oa_emb.embed_query(q), dtype=np.float32), oa_norms, verse_keys)
        hf_results.append(hf_r)
        oa_results.append(oa_r)
        per_query.append({"query": q, "truth": t, "huggingface_top5": hf_r, "openai_top5": oa_r})

    hf_metrics = compute_metrics(hf_results, truth)
    oa_metrics = compute_metrics(oa_results, truth)

    print("\n" + "=" * 60)
    print(f"코퍼스 풀 크기: {len(docs)}개 구절 / 테스트 쿼리: {args.n_queries}개")
    print(f"{'Metric':<12}{'HuggingFace(ko-sroberta)':<28}{'OpenAI(text-embedding-3-small)'}")
    for key in ["Recall@1", "Recall@3", "Recall@5", "MRR"]:
        print(f"{key:<12}{hf_metrics[key]:<28}{oa_metrics[key]}")
    print("=" * 60)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "pool_size": len(docs),
                "n_queries": args.n_queries,
                "seed": args.seed,
                "huggingface_model": HF_MODEL,
                "openai_model": OPENAI_MODEL,
                "huggingface_metrics": hf_metrics,
                "openai_metrics": oa_metrics,
                "per_query": per_query,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n저장됨: {args.out}")


if __name__ == "__main__":
    main()
