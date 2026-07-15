/*
 * frontend/api.js
 * ───────────────────────────────────────────────────────────────────────
 * 백엔드(FastAPI) 호출을 한곳에 모은 클라이언트.
 *
 * 핵심 설계:
 *   - API_BASE 가 설정돼 있고 서버가 응답하면 실제 백엔드를 사용.
 *   - 서버가 없거나 실패하면 mock.js 의 목업으로 자동 폴백.
 *   → 데모는 백엔드 없이도 끝까지 돌아가고, 배포 시 API_BASE만 채우면 실서비스.
 *
 * 컴포넌트는 이 파일의 함수만 부르고, 실제/목업 여부는 신경 쓰지 않습니다.
 */

import * as mock from "./mock.js";

// 배포 시 여기(또는 빌드 환경변수)를 실제 주소로. 비우면 목업 모드.
export const API_BASE = "http://localhost:8000"; // 예: "http://localhost:8000"

let token = null;
export function setToken(t) { token = t; }
export function getToken() { return token; }

async function call(path, { method = "GET", body, mbti } = {}) {
  if (!API_BASE) throw new Error("NO_BACKEND"); // 목업으로 폴백시키는 신호
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (mbti) headers["X-User-Mbti"] = mbti;
  const res = await fetch(API_BASE + path, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ── 인증 ────────────────────────────────────────────────────────────── */
export async function signup(payload) {
  try { return await call("/api/auth/signup", { method: "POST", body: payload }); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.signup(payload); throw e; }
}
export async function login(payload) {
  try { return await call("/api/auth/login", { method: "POST", body: payload }); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.login(payload); throw e; }
}

/* ── 추천 / 채팅 (Hybrid RAG) ────────────────────────────────────────── */
export async function recommend(message, mbti, emoWeight = 1) {
  try { return await call("/api/chat/recommend", { method: "POST", body: { message, emo_weight: emoWeight }, mbti }); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.recommend(message, mbti, emoWeight); throw e; }
}
export async function answer(personId, message, mbti, history = "") {
  try { return await call("/api/chat/answer", { method: "POST", body: { person_id: personId, message, history }, mbti }); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.answer(personId, message, mbti); throw e; }
}

/* ── 탐색 / 진단 (사이드 콘텐츠) ─────────────────────────────────────── */
export async function getPeople() {
  try { return await call("/api/explore/people"); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.getPeople(); throw e; }
}
export async function matchMbti(mbti) {
  try { return await call(`/api/explore/match/${mbti}`); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.matchMbti(mbti); throw e; }
}
export async function getGraph() {
  try { return await call("/api/explore/graph"); }
  catch (e) { if (e.message === "NO_BACKEND") return mock.getGraph(); throw e; }
}
