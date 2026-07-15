"""
════════════════════════════════════════════════════════════════════════
 Eden 포털 — Streamlit 프로토타입
════════════════════════════════════════════════════════════════════════

 [시스템 아키텍처 — 기존과 100% 동일]

   사용자 발화
        │
        ├─▶ emotion.infer_emotion()          감정 추론 (키워드 + LLM 폴백)
        │
        ├─▶ graph_store.recommend_disciples() Graph: 누가 답할지 (MBTI 궁합)
        │        └─ 실패 시 mock_data 폴백
        │
        ├─▶ vector_store.search()             Vector: 무엇으로 답할지 (성경 구절)
        │        └─ graph-guided book 필터
        │
        └─▶ llm.get_llm() + prompts           LLM: 제자 페르소나로 답변
                 └─ 실패 시 mock 페르소나 폴백

 [대화 흐름]
   예수님과 자유롭게 몇 턴 대화 → LLM이 "추천해도 될 만큼 깊어졌는지" 판단
   → 제자 추천 카드 → 수락하면 예수님과 나눈 대화 요약을 들고 제자에게 인계.
   각 상대(예수님/제자)와의 대화는 서로 섞이지 않도록 완전히 분리해 기록한다.

 실행:  streamlit run streamlit_app.py
════════════════════════════════════════════════════════════════════════
"""

import base64
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ── 경로 설정: backend/ 를 import 가능하게 ─────────────────────────────
ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Streamlit Cloud의 secrets(.streamlit/secrets.toml, 대시보드 Secrets 입력)를
# 로컬 .env와 동일한 환경변수 경로로 흘려보낸다 (config.py는 os.environ만 봄).
# 로컬에는 secrets.toml이 없는 게 정상이라 예외는 조용히 무시한다.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

# .env 로드 (OPENAI_API_KEY 등). backend/.env 우선, 없으면 루트.
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

# ── 백엔드 서비스 직접 import (HTTP 없음) ─────────────────────────────
from app.services import auth, hybrid_rag, mock_data, vector_store  # noqa: E402

ASSETS = ROOT / "assets"

# 홈 중앙 멘트 (마태복음 11:28)
HOME_VERSE = "수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라."


@st.cache_resource(show_spinner="성경 말씀 인덱스를 준비하는 중입니다 (최초 실행 시 몇 분 걸릴 수 있어요)…")
def _ensure_vector_store_ready() -> int:
    """앱 프로세스당 최초 1회만 실행. chroma_db가 비어있으면(첫 배포/콜드스타트)
    bible_structured.json으로부터 자동 재생성한다. 실패해도 앱은 mock 구절로 계속 동작."""
    try:
        return vector_store.ensure_vector_store()
    except Exception:
        return -1


_ensure_vector_store_ready()

# ══════════════════════════════════════════════════════════════════════
#  디자인 토큰 (시안2: 에덴 정원 + Codapress 타이포)
# ══════════════════════════════════════════════════════════════════════
INK, MUTED, ACCENT, DEEP = "#22301C", "#5E6B52", "#5B7B3A", "#3A4A28"
CARD, LINE, CREAM = "#FFFEFB", "#E4E5D6", "#EEF0DF"

st.set_page_config(page_title="Eden · 말씀 상담", page_icon="✝️", layout="wide")


@st.cache_data
def img_b64(name: str) -> str:
    """이미지를 base64로 (Streamlit은 로컬 경로를 HTML에 못 박으므로)."""
    p = ASSETS / name
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()


def avatar_uri(person_id: str) -> str:
    b = img_b64(f"{person_id}.webp")
    return f"data:image/webp;base64,{b}" if b else ""


# ══════════════════════════════════════════════════════════════════════
#  전역 스타일
# ══════════════════════════════════════════════════════════════════════
def inject_css():
    bg = img_b64("bg.webp")
    st.markdown(
        f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Inter:wght@300;400;500;600;700&family=Noto+Serif+KR:wght@400;500;600;700&display=swap');

  .stApp {{
    background: linear-gradient(180deg, rgba(238,240,223,.55), rgba(238,240,223,.9)),
                url("data:image/webp;base64,{bg}") center/cover fixed no-repeat;
  }}
  #MainMenu, footer, header {{ visibility: hidden; }}

  /* 배경은 와이드인데 본문만 좁게 몰려 있으면 모바일처럼 보인다.
     화면 폭에 맞춰 넓게 쓰되, 초광폭 모니터에서 글줄이 너무 길어지지 않게 상한만 둔다. */
  .block-container {{
    padding-top: 1.6rem; padding-bottom: 3rem;
    max-width: 1360px; width: 100%;
    padding-left: clamp(16px, 4vw, 56px); padding-right: clamp(16px, 4vw, 56px);
  }}

  html, body, [class*="css"] {{ font-family: Inter, 'Noto Serif KR', sans-serif; }}

  .ed-display {{
    font-family: Cormorant, serif; font-weight: 600;
    font-size: clamp(30px, 3.6vw, 52px); line-height: 1.14;
    letter-spacing: -.02em; color: {INK}; margin: 0 0 14px;
    text-shadow: 0 1px 16px rgba(255,252,240,.7);
  }}
  .ed-display em {{ font-style: italic; font-weight: 500; color: {ACCENT}; }}
  .ed-eyebrow {{
    font-size: 12px; font-weight: 600; letter-spacing: .26em;
    color: {ACCENT}; text-transform: uppercase; margin-bottom: 18px;
  }}
  .ed-sub {{ font-size: 15.5px; line-height: 1.6; color: {MUTED}; margin-bottom: 26px; }}

  /* 홈 히어로: 중앙 멘트 + 바로 아래 채팅바 */
  .ed-hero {{ max-width: 900px; margin: clamp(18px, 5vh, 64px) auto 0; text-align: center; }}
  .ed-hero-verse {{
    font-family: Cormorant, serif; font-weight: 600; color: {INK};
    font-size: clamp(26px, 3.2vw, 44px); line-height: 1.3; letter-spacing: -.01em;
    margin: 0 0 10px; text-shadow: 0 1px 16px rgba(255,252,240,.75);
    word-break: keep-all;                 /* 한글 단어 중간에서 안 끊기게 */
  }}
  .ed-hero-ref {{
    font-size: 12px; font-weight: 600; letter-spacing: .18em;
    color: {ACCENT}; margin-bottom: 26px;
  }}

  .ed-card {{
    background: {CARD}; border: 1px solid {LINE}; border-radius: 18px;
    padding: 18px 20px; margin-bottom: 12px;
  }}
  .ed-quote {{
    border-left: 3px solid {ACCENT}; background: #F6F8EF;
    border-radius: 0 10px 10px 0; padding: 12px 16px;
    font-family: Cormorant, serif; font-size: 17px; line-height: 1.5; color: {INK};
    overflow-wrap: anywhere; word-break: break-word;
  }}

  /* 답변 밑에 붙는 핵심 구절. 폭 제한/줄바꿈 규칙이 없으면 긴 구절이
     말풍선을 뚫고 나가 깨진다 — 명시적으로 막는다. */
  .ed-verse {{
    display: block; box-sizing: border-box;
    margin: 12px 0 4px 0; padding: 14px 16px;
    border: 1px solid {LINE}; border-left: 4px solid {ACCENT};
    border-radius: 8px; background: #F6F8EF;
    font-size: 14.5px; line-height: 1.6; color: #56634A;
    white-space: normal;
    overflow-wrap: break-word; word-break: keep-all;
  }}
  .ed-verse .ref {{
    display: inline; font-size: 14.5px; font-weight: 700; letter-spacing: .02em;
    color: {ACCENT}; margin-right: 8px;
  }}

  .ed-badge {{
    display: inline-block; font-size: 11.5px; font-weight: 700; color: {ACCENT};
    background: #EAF0DE; padding: 2px 9px; border-radius: 20px;
  }}
  .ed-name {{ font-family: Cormorant, serif; font-size: 22px; font-weight: 700; color: {INK}; }}
  .ed-role {{ font-size: 12.5px; color: {MUTED}; }}

  /* 버튼 기본: 올리브 톤 */
  .stButton > button {{
    border-radius: 100px; border: 1px solid {LINE}; background: {CARD};
    color: {MUTED}; font-weight: 600; font-size: 13.5px; padding: 8px 18px;
  }}
  .stButton > button:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
  .stButton > button[kind="primary"] {{ background: {DEEP}; color: #F5F7EC; border: none; }}

  /* ── 헤더 ─────────────────────────────────────────────────────────
     로고 자체가 홈 버튼이다(별도 '홈' 탭 없음).
     st.button(key="logo_home") → 래퍼 div 에 .st-key-logo_home 클래스가 붙는다. */
  .st-key-logo_home button,
  .st-key-logo_home button div,
  .st-key-logo_home button p {{
    background: transparent !important; border: none !important; box-shadow: none !important;
    padding: 0 !important; height: 56px !important;
    font-family: Cormorant, serif !important; font-size: 38px !important;
    font-weight: 700 !important; color: {INK} !important;
    justify-content: flex-start !important; letter-spacing: -.01em;
    margin: 0 !important; line-height: 56px !important;
  }}
  .st-key-logo_home button:hover,
  .st-key-logo_home button:hover p {{ color: {ACCENT} !important; }}

  /* 메뉴 탭 사이즈 통일 + 글자 밀림 방지.
     모든 nav 버튼 높이/폰트를 고정하고 줄바꿈을 막아 한 줄로 크게 쓴다. */
  [class*="st-key-nav_"] button {{
    height: 46px !important; min-height: 46px !important;
    padding: 0 20px !important;
    font-size: 15px !important; font-weight: 600 !important;
    white-space: nowrap !important;      /* '말씀 상담' 이 두 줄로 밀리지 않게 */
    letter-spacing: -.01em;
    border-radius: 12px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    color: {MUTED} !important;
    transition: background .15s ease, color .15s ease;
  }}
  [class*="st-key-nav_"] button:hover {{
    background: rgba(255,254,251,.75) !important; color: {INK} !important;
  }}
  [class*="st-key-nav_"] button[kind="primary"] {{
    background: {CARD} !important; color: {DEEP} !important;
    border: 1px solid {LINE} !important;
    box-shadow: 0 1px 3px rgba(34,48,28,.06) !important;
  }}
  .st-key-auth_btn button, .st-key-logout button {{ height: 46px !important; }}

  /* 홈 프롬프트 칩: 채팅바 아래 (GPT/Claude 스타일) */
  [class*="st-key-chip_"] button {{
    height: 40px !important; border-radius: 100px !important;
    background: rgba(255,254,251,.8) !important;
    font-size: 13.5px !important; white-space: nowrap !important;
  }}

  [data-testid="stChatMessage"] {{
    background: rgba(255,255,252,.86); border: 1px solid {LINE};
    border-radius: 16px; padding: 6px 12px;
  }}
  /* 말풍선 안 콘텐츠가 밖으로 새지 않도록 */
  [data-testid="stChatMessage"] * {{ overflow-wrap: anywhere; }}

  [data-testid="stBottom"] > div {{
    padding-bottom: 24px;
    background: transparent !important;
  }}
  [data-testid="stChatInput"] {{
    border-radius: 24px; border: 1px solid {LINE}; background: {CARD};
    max-width: 760px; margin: 0 auto;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  }}
</style>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
#  세션 상태 (React state 대체)
# ══════════════════════════════════════════════════════════════════════
def init_state():
    ss = st.session_state
    ss.setdefault("user", None)        # {email, name, gender, mbti, title}
    ss.setdefault("page", "home")      # home|chat|diagnose|explore|graph
    ss.setdefault("msgs", [])          # [{role, person_id, text, verses}]
    ss.setdefault("card", None)        # 추천 프로필 카드 상태
    ss.setdefault("active", None)      # 대화 중인 제자 id
    ss.setdefault("seed", None)        # 홈에서 넘어온 첫 문장
    ss.setdefault("auth_open", False)
    ss.setdefault("shared_memory", "")  # 예수님과 나눈 대화 요약 (제자에게 인계)


def go(page: str):
    st.session_state.page = page
    st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  헤더 (로고=홈 / 메뉴 / 로그인)
# ══════════════════════════════════════════════════════════════════════
NAV = [("chat", "말씀 상담"), ("diagnose", "제자 진단"),
       ("explore", "인물 탐색"), ("graph", "관계도")]


def header():
    ss = st.session_state
    left, mid, right = st.columns([1.0, 3.6, 1.4], vertical_alignment="center")

    with left:
        if st.button("✝ Eden", key="logo_home", help="홈으로"):
            go("home")

    with mid:
        cols = st.columns(len(NAV))          # 균등 분할 → 탭 폭 동일
        for c, (key, label) in zip(cols, NAV):
            with c:
                if st.button(label, key=f"nav_{key}", use_container_width=True,
                             type="primary" if ss.page == key else "secondary"):
                    go(key)

    with right:
        if ss.user:
            st.markdown(
                f'<div style="text-align:right;font-size:13px;color:{MUTED};line-height:1.35;margin-bottom:6px">'
                f'{ss.user["name"]} {ss.user["title"]} <span style="opacity:0.4;margin:0 4px">|</span> '
                f'<b style="color:{ACCENT}">{ss.user["mbti"]}</b></div>',
                unsafe_allow_html=True,
            )
            if st.button("로그아웃", key="logout", use_container_width=True):
                ss.user = None
                ss.msgs, ss.active, ss.card, ss.seed = [], None, None, None
                ss.shared_memory = ""
                go("home")
        else:
            if st.button("로그인 · 회원가입", key="auth_btn",
                         type="primary", use_container_width=True):
                ss.auth_open = True
                st.rerun()

    st.markdown(f'<hr style="border:none;border-top:1px solid {LINE};margin:6px 0 18px">',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  회원가입 / 로그인
# ══════════════════════════════════════════════════════════════════════
QUIZ = [
    ("사람을 만나면서 기운을 회복하나요?", "E", "I"),
    ("혼자 있을 때, 상상이나 가능성을 자주 떠올리나요?", "N", "S"),
    ("결정할 때 감정보다 논리를 먼저 따지나요?", "T", "F"),
    ("계획대로보다 즉흥적으로 움직이는 게 편한가요?", "P", "J"),
]

UNKNOWN = "모름 (간단 테스트로 찾기)"


def _login_user(profile: dict):
    ss = st.session_state
    ss.user = profile
    ss.auth_open = False
    if ss.seed:
        ss.page = "chat"


@st.dialog("에덴에 오신 걸 환영합니다")
def auth_dialog():
    """상담은 회원 전용 → 가입 폼에서 이름·성별·MBTI 수집."""
    ss = st.session_state
    tab_signup, tab_login = st.tabs(["회원가입", "로그인"])

    # ── 회원가입 ──────────────────────────────────────────────────────
    with tab_signup:
        # MBTI 선택은 값에 따라 화면이 즉시 바뀌어야 하므로 form 밖에 둔다
        # (form 안에서는 제출 전까지 rerun이 일어나지 않는다).
        mbti_pick = st.selectbox(
            "MBTI", list(mock_data.TYPE_ORDER) + [UNKNOWN],
            index=len(mock_data.TYPE_ORDER),      # 기본값 = 모름
            key="su_mbti_pick",
        )

        mbti = mbti_pick
        if mbti_pick == UNKNOWN:
            st.caption("4문항이면 충분해요. 편하게 고르시면 됩니다.")
            letters = []
            for i, (q, yes, no) in enumerate(QUIZ):
                a = st.radio(f"{i+1}. {q}", ["그렇다", "아니다"],
                             horizontal=True, key=f"su_q{i}")
                letters.append(yes if a == "그렇다" else no)
            mbti = "".join(letters)
            st.markdown(f'<span class="ed-badge">예상 유형 · {mbti}</span>',
                        unsafe_allow_html=True)
            st.write("")

        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("이름")
            email = st.text_input("이메일")
            pw = st.text_input("비밀번호", type="password")
            gender = st.radio("당신은", ["아담의 후손 ♂", "하와의 후손 ♀"], horizontal=True)
            submitted = st.form_submit_button("가입하고 에덴 들어가기",
                                              type="primary", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("이름을 입력해 주세요.")
            else:
                try:
                    profile = auth.signup(
                        email=email, password=pw, name=name.strip(),
                        gender="adam" if "아담" in gender else "eve",
                        mbti=mbti,
                    )
                    _login_user(profile)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # ── 로그인 ────────────────────────────────────────────────────────
    with tab_login:
        # st.form 안에서는 입력창에서 Enter를 치면 폼이 제출된다.
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("이메일")
            pw = st.text_input("비밀번호", type="password")
            st.caption("입력 후 Enter로도 로그인됩니다.")
            submitted = st.form_submit_button("로그인", type="primary",
                                              use_container_width=True)
        if submitted:
            try:
                _login_user(auth.login(email, pw))
                st.rerun()
            except ValueError as e:
                st.error(str(e))


# ══════════════════════════════════════════════════════════════════════
#  홈
# ══════════════════════════════════════════════════════════════════════
CHIPS = [
    ("불안할 때", "요즘 마음이 많이 불안하고 초조해요"),
    ("감사하고 싶을 때", "감사한 마음을 나누고 싶어요"),
    ("길을 정할 때", "어떤 길로 가야 할지 고민이에요"),
]


def page_home():
    ss = st.session_state

    st.markdown(
        f'<div class="ed-hero">'
        f'<div class="ed-hero-verse">{HOME_VERSE}</div>'
        f'<div class="ed-hero-ref">마태복음 11:28</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    text = None
    _, mid, _ = st.columns([1, 3.2, 1])
    with mid:
        # st.chat_input을 컨테이너 안에서 호출하면 화면 하단 고정이 아니라
        # '그 자리에' 인라인으로 렌더링된다 → 중앙 멘트 바로 밑에 놓을 수 있다.
        with st.container():
            typed = st.chat_input(
                f"{ss.user['name']} {ss.user['title']}, 오늘의 마음을 적어보세요…"
                if ss.user else "마음에 있는 것을 적어보세요…"
            )
        if typed:
            text = typed

        st.write("")
        cols = st.columns(4)
        for c, (label, seed) in zip(cols, CHIPS):
            with c:
                if st.button(label, key=f"chip_{label}", use_container_width=True):
                    text = seed
        with cols[3]:
            if st.button("제자 진단", key="chip_diag", use_container_width=True):
                go("diagnose")

    if text:
        ss.seed = text
        if not ss.user:
            ss.auth_open = True      # 비로그인 → 회원가입 유도 (상담은 회원 전용)
        else:
            ss.page = "chat"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  말씀 상담 — ★ 백엔드 hybrid_rag 직접 호출 ★
# ══════════════════════════════════════════════════════════════════════
def render_msg(m: dict):
    if m["role"] == "user":
        with st.chat_message("user", avatar="🙂"):
            st.write(m["text"])
        return
    p = mock_data.PEOPLE.get(m["person_id"], {})
    with st.chat_message("assistant", avatar=avatar_uri(m["person_id"]) or "✝️"):
        st.markdown(
            f'<div style="font-size:11.5px;color:{MUTED};margin-bottom:2px">'
            f'{p.get("name","")} · {p.get("mbti","")}</div>',
            unsafe_allow_html=True,
        )
        st.write(m["text"])
        # hybrid_rag가 이미 '이번 답변에서 가장 중요하게 쓴 구절' 1개로 줄여 준다.
        for v in (m.get("verses") or [])[:1]:
            st.markdown(
                f'<div class="ed-verse"><span class="ref">{v["source"]}</span>'
                f'{v["content"]}</div>',
                unsafe_allow_html=True,
            )


def profile_card(person: dict):
    """추천된 제자 프로필 → '이 벗과 대화하기' / '다른 벗 추천'."""
    ss = st.session_state
    with st.container(border=True):
        c1, c2 = st.columns([1, 2.6])
        with c1:
            uri = avatar_uri(person["id"])
            if uri:
                st.markdown(f'<img src="{uri}" style="width:100%;border-radius:14px">',
                            unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'<span class="ed-name">{person["name"]}</span> '
                f'<span class="ed-badge">{person["mbti"]}</span>'
                f'<div class="ed-role">{person.get("role","")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size:13px;color:{MUTED};margin-top:8px">'
                f'<b>성향</b> {person.get("traits","—")}<br>'
                f'<b>잘 맞는 MBTI</b> '
                f'{" · ".join(mock_data.best_matching_mbti(person["mbti"]))}<br>'
                f'<b>연관 성경서</b> '
                f'{" · ".join(person.get("book_full_names") or person.get("books") or []) or "—"}</div>',
                unsafe_allow_html=True,
            )
        if person.get("quote"):
            st.markdown(
                f'<div class="ed-quote">“{person["quote"]}”'
                f'<div style="font-size:11.5px;color:#8A9578;margin-top:6px">'
                f'— {person.get("quote_ref","")}</div></div>',
                unsafe_allow_html=True,
            )

        seen, total = ss.card["idx"] + 1, len(ss.card["order"])
        st.caption(f"추천 {seen} / {total}"
                   + (" · 후보를 한 바퀴 다 보셨어요" if ss.card.get("wrapped") else ""))

        b1, b2 = st.columns([1, 1.4])
        with b1:
            if st.button("다른 벗 추천", use_container_width=True, key="card_next"):
                _next_disciple()
                st.rerun()
        with b2:
            if st.button("이 벗과 대화하기", type="primary",
                         use_container_width=True, key="card_accept"):
                _accept_disciple()
                st.rerun()


def _current_person():
    """카드가 가리키는 제자를 '항상 안전하게' 꺼낸다.

    추천 목록이 비거나 idx가 어긋나면 IndexError(list index out of range)가
    화면에 그대로 터질 수 있었다. 범위를 클램프하고, 빈 목록이면 카드를 닫는다.
    """
    card = st.session_state.card
    if not card:
        return None
    order = card.get("order") or []
    if not order:
        st.session_state.card = None
        return None
    card["idx"] = max(0, min(card.get("idx", 0), len(order) - 1))
    return order[card["idx"]]


def _format_history(person_id: str, max_lines: int = 20) -> str:
    """ss.msgs에서 이 화자(person_id)와 나눈 대화만 골라 LLM 프롬프트용 히스토리 문자열로 만든다.
    사용자 메시지도 어느 대화 상대에게 한 말인지 person_id로 태그되어 있어야
    다른 상대와의 대화가 섞여 들어가지 않는다. (전환 안내 멘트 등 meta 메시지는 제외)"""
    ss = st.session_state
    name = "예수님" if person_id == "jesus" else mock_data.PEOPLE.get(person_id, {}).get("name", person_id)
    lines = []
    for m in ss.msgs:
        if m.get("meta") or m.get("person_id") != person_id:
            continue
        speaker = "사용자" if m["role"] == "user" else name
        lines.append(f"{speaker}: {m['text']}")
    return "\n".join(lines[-max_lines:])


def _ask(person_id: str, text: str) -> dict:
    """hybrid_rag.answer 호출부 — 이 대화 상대와의 히스토리만 골라 전달."""
    ss = st.session_state
    return hybrid_rag.answer(
        person_id=person_id,
        user_mbti=ss.user["mbti"],
        message=text,
        history=_format_history(person_id),
        user_name=ss.user["name"],
        shared_memory=ss.shared_memory if person_id != "jesus" else "",
        gender=ss.user["gender"],
    )


def _next_disciple():
    """추천 거절 → 다음 후보. 다 보면 감정 가중치를 키워 새 후보를 이어붙인다.

    매 클릭마다 order를 통째로 재구성하면서 idx를 0으로 되돌리면
    (1) 같은 두 사람 사이를 무한히 왔다갔다 하고,
    (2) 재추천 결과가 비면 idx가 음수가 되어 IndexError가 터진다.
    'order는 계속 누적, idx는 앞으로만'이라는 규칙으로 중복 추천과 인덱스
    오류를 원천적으로 없앤다.
    """
    ss = st.session_state
    card = ss.card
    if not card:
        return
    card["pass"] = card.get("pass", 0) + 1
    order = card.get("order") or []

    if card["idx"] + 1 < len(order):
        card["idx"] += 1                     # 아직 안 본 후보가 남음
    else:
        # 후보 소진 → 감정 반영을 키워 재추천하고, '아직 안 본 사람'만 뒤에 붙임
        card["w"] = min(3.0, card.get("w", 1.0) + 0.8)
        seen = {p["id"] for p in order}
        try:
            r = hybrid_rag.recommend(ss.user["mbti"], card.get("jesus_summary") or card["last_text"], card["w"])
            fresh = [p for p in (r.get("ranked") or []) if p["id"] not in seen]
        except Exception:
            fresh = []
        if fresh:
            card["order"] = order + fresh
            card["idx"] += 1
        else:
            # 정말 더 볼 사람이 없으면 처음으로 한 바퀴 (에러 대신 순환)
            card["idx"] = 0
            card["wrapped"] = True

    card["idx"] = max(0, min(card["idx"], len(card["order"]) - 1))
    ss.card = card


def _accept_disciple():
    """제자 수락 → 예수님과 나눈 대화 요약을 shared_memory로 넘기고 hybrid_rag.answer()로 응답."""
    ss = st.session_state
    p = _current_person()
    if not p:
        return
    last = ss.card["last_text"]
    ss.shared_memory = ss.card.get("jesus_summary", "")
    ss.card = None
    ss.active = p["id"]
    ss.msgs.append({"role": "bot", "person_id": "jesus", "meta": True,
                    "text": f'그래, {p["name"]}와 마음을 나눠보거라. 나는 늘 곁에 있으마.'})
    out = _ask(p["id"], last)
    ss.msgs.append({"role": "bot", "person_id": p["id"],
                    "text": out["answer"], "verses": out.get("verses")})


def _jesus_turn(text: str):
    """예수님과의 자유 대화 한 턴. 대화가 충분히 깊어졌다고 판단되면 제자 추천 카드를 띄운다."""
    ss = st.session_state
    history = _format_history("jesus")  # 현재 발화를 append 하기 전에 만들어야 중복 안 됨
    ss.msgs.append({"role": "user", "text": text, "person_id": "jesus"})
    out = hybrid_rag.answer(
        person_id="jesus", user_mbti=ss.user["mbti"], message=text,
        history=history, user_name=ss.user["name"], gender=ss.user["gender"],
    )
    ss.msgs.append({"role": "bot", "person_id": "jesus",
                    "text": out["answer"], "verses": out.get("verses")})

    full_history = _format_history("jesus")
    if hybrid_rag.should_recommend(full_history):
        rec = hybrid_rag.recommend(ss.user["mbti"], full_history, 1.0)
        ranked = rec.get("ranked") or []
        if ranked:
            ss.card = {"order": ranked, "idx": 0, "pass": 0, "w": 1.0,
                       "last_text": text, "jesus_summary": full_history, "wrapped": False}


@st.cache_data(ttl=60)
def _verse_db_health() -> dict:
    """벡터 인덱스 상태 (구절이 왜 안 붙는지 화면에서 바로 보이게)."""
    try:
        return vector_store.health()
    except Exception as e:
        return {"ready": False, "count": 0, "db_error": repr(e)}


def page_chat():
    ss = st.session_state
    if not ss.user:
        st.markdown('<div class="ed-eyebrow">회원 전용</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="ed-display">말씀 상담은<br><em>회원 전용</em>이에요</h1>',
                    unsafe_allow_html=True)
        st.markdown('<div class="ed-sub">가입하면 당신의 MBTI에 맞는 제자가 '
                    '성경으로 마음을 나눠드립니다.</div>', unsafe_allow_html=True)
        if st.button("회원가입 하기", type="primary"):
            ss.auth_open = True
            st.rerun()
        return

    health = _verse_db_health()
    if not health.get("ready"):
        st.warning(
            f"성경 Vector DB({health.get('backend','?')})에 연결되지 않아 답변에 구절이 "
            f"붙지 않을 수 있습니다 — 인덱싱된 구절 {health.get('count', 0)}개"
            + (f", 임베딩 오류: {health['embedding_error']}" if health.get("embedding_error") else "")
            + ".",
            icon="⚠️",
        )

    # 대화는 가운데 정렬하되, 예전보다 넓게
    _, mid, _ = st.columns([1, 4.4, 1])
    with mid:
        if ss.seed:
            seed, ss.seed = ss.seed, None
            with st.spinner("마음을 살피는 중…"):
                _jesus_turn(seed)
            st.rerun()

        if not ss.msgs:
            st.markdown(
                f'<div style="text-align:center;padding:30px 0 10px">'
                f'<img src="{avatar_uri("jesus")}" style="width:96px;border-radius:50%">'
                f'<div style="font-family:Cormorant,serif;font-size:25px;font-weight:600;'
                f'color:{INK};margin-top:14px">나의 {ss.user["name"]}아, 편히 말해보거라.</div>'
                f'<div style="font-size:13px;color:{MUTED};margin-top:4px">'
                f'마음을 나누면, 어울리는 벗이 성경으로 답합니다.</div></div>',
                unsafe_allow_html=True,
            )

        for m in ss.msgs:
            render_msg(m)

        if ss.card:
            person = _current_person()
            if person:
                profile_card(person)
                st.caption("추천된 벗을 먼저 확인해보세요.")
                return

    text = st.chat_input("마음에 있는 것을 적어보세요…")
    if text:
        if ss.active:
            with st.spinner("말씀을 찾는 중…"):
                out = _ask(ss.active, text)
            ss.msgs.append({"role": "user", "text": text, "person_id": ss.active})
            ss.msgs.append({"role": "bot", "person_id": ss.active,
                            "text": out["answer"], "verses": out.get("verses")})
        else:
            with st.spinner("마음을 살피는 중…"):
                _jesus_turn(text)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  제자 진단
# ══════════════════════════════════════════════════════════════════════
def page_diagnose():
    ss = st.session_state
    st.markdown('<div class="ed-eyebrow">제자 진단</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="ed-display">나와 닮은 <em>제자</em></h1>', unsafe_allow_html=True)
    st.markdown('<div class="ed-sub">MBTI로 12제자와의 궁합을 봅니다.</div>',
                unsafe_allow_html=True)

    default = ss.user["mbti"] if ss.user else "INFJ"
    if default not in mock_data.TYPE_ORDER:
        default = "INFJ"
    mbti = st.selectbox("내 유형", mock_data.TYPE_ORDER,
                        index=mock_data.TYPE_ORDER.index(default))

    ranked = hybrid_rag.recommend(mbti, "", 0.0)["ranked"][:3]
    top = ranked[0]

    with st.container(border=True):
        c1, c2 = st.columns([1, 2.6])
        with c1:
            st.markdown(f'<img src="{avatar_uri(top["id"])}" '
                        f'style="width:100%;border-radius:14px">', unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'<div style="font-size:11.5px;color:#8A9578;font-weight:700;'
                f'letter-spacing:.1em">가장 잘 맞는 제자</div>'
                f'<span class="ed-name">{top["name"]}</span> '
                f'<span class="ed-badge">{top["mbti"]}</span>'
                f'<div class="ed-role">{top.get("role","")}</div>'
                f'<div style="margin-top:8px"><span class="ed-badge">'
                f'궁합 {top.get("score",0)}점</span></div>',
                unsafe_allow_html=True,
            )

    st.caption("다음으로 잘 맞는")
    for p in ranked[1:]:
        c1, c2, c3 = st.columns([0.6, 4, 1])
        with c1:
            st.markdown(f'<img src="{avatar_uri(p["id"])}" '
                        f'style="width:100%;border-radius:50%">', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<b style="color:{INK}">{p["name"]}</b> '
                        f'<span class="ed-badge">{p["mbti"]}</span><br>'
                        f'<span style="font-size:12.5px;color:{MUTED}">'
                        f'{p.get("traits","")}</span>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="text-align:right;color:{ACCENT};font-weight:700">'
                        f'{p.get("score",0)}점</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  인물 탐색
# ══════════════════════════════════════════════════════════════════════
def page_explore():
    st.markdown('<div class="ed-eyebrow">인물 탐색</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="ed-display">예수와 <em>12제자</em></h1>', unsafe_allow_html=True)
    st.markdown('<div class="ed-sub">인물을 눌러 성향·명언·연관 성경서를 살펴보세요.</div>',
                unsafe_allow_html=True)

    people = list(mock_data.PEOPLE.values())
    per_row = 7                     # 와이드 레이아웃에 맞춰 한 줄에 더 많이
    for row_start in range(0, len(people), per_row):
        cols = st.columns(per_row)
        for c, p in zip(cols, people[row_start:row_start + per_row]):
            with c:
                uri = avatar_uri(p["id"])
                if uri:
                    st.markdown(f'<img src="{uri}" style="width:100%;border-radius:50%">',
                                unsafe_allow_html=True)
                st.markdown(
                    f'<div style="text-align:center;font-size:12.5px;font-weight:600;'
                    f'color:{INK};margin-top:6px">{p["name"]}</div>'
                    f'<div style="text-align:center;font-size:10.5px;color:#8A9578">'
                    f'{p["mbti"]}</div>',
                    unsafe_allow_html=True,
                )
                with st.popover("보기", use_container_width=True):
                    st.markdown(f'<span class="ed-name">{p["name"]}</span> '
                                f'<span class="ed-badge">{p["mbti"]}</span>',
                                unsafe_allow_html=True)
                    st.write(f'**성향** {p.get("traits","—")}')
                    st.write(f'**잘 맞는 MBTI** '
                             f'{" · ".join(mock_data.best_matching_mbti(p["mbti"]))}')
                    st.write(f'**연관 성경서** '
                             f'{" · ".join(p.get("book_full_names") or p.get("books") or []) or "—"}')
                    st.markdown(f'<div class="ed-quote">“{p.get("quote","")}”'
                                f'<div style="font-size:11.5px;color:#8A9578;margin-top:6px">'
                                f'— {p.get("quote_ref","")}</div></div>',
                                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  관계도 (MBTI 16유형 ↔ 제자)
# ══════════════════════════════════════════════════════════════════════
def page_graph():
    import math

    st.markdown('<div class="ed-eyebrow">관계도</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="ed-display">MBTI · <em>제자</em> 관계도</h1>',
                unsafe_allow_html=True)
    st.markdown('<div class="ed-sub">16가지 유형과 제자가 어떻게 이어지는지 '
                '보여줍니다. (Neo4j 그래프의 축소판)</div>', unsafe_allow_html=True)

    cx, cy, R = 380, 300, 210
    types = mock_data.TYPE_ORDER
    pos = {}
    for i, t in enumerate(types):
        a = (i / len(types)) * math.tau - math.pi / 2
        pos[t] = (cx + R * math.cos(a), cy + R * math.sin(a))

    people = [p for p in mock_data.PEOPLE.values() if p["id"] != "jesus"]
    parts = ['<svg viewBox="0 0 760 600" '
             'style="width:100%;max-width:860px;display:block;margin:0 auto">']

    for p in people:
        tx, ty = pos[p["mbti"]]
        a = math.atan2(ty - cy, tx - cx)
        px, py = cx + (R + 70) * math.cos(a), cy + (R + 70) * math.sin(a)
        parts.append(f'<line x1="{tx}" y1="{ty}" x2="{px}" y2="{py}" '
                     f'stroke="#D6DCC4" stroke-width="1.5"/>')
    for t in types:
        x, y = pos[t]
        parts.append(f'<circle cx="{x}" cy="{y}" r="20" fill="#EAF0DE" '
                     f'stroke="{ACCENT}"/>'
                     f'<text x="{x}" y="{y+3.5}" text-anchor="middle" '
                     f'font-size="9" font-weight="700" fill="{DEEP}">{t}</text>')
    for p in people:
        tx, ty = pos[p["mbti"]]
        a = math.atan2(ty - cy, tx - cx)
        px, py = cx + (R + 70) * math.cos(a), cy + (R + 70) * math.sin(a)
        parts.append(f'<circle cx="{px}" cy="{py}" r="15" fill="{DEEP}"/>'
                     f'<text x="{px}" y="{py+3}" text-anchor="middle" '
                     f'font-size="8.5" font-weight="600" fill="#F5F7EC">'
                     f'{p["name"][:2]}</text>')
    parts.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                 f'font-family="Cormorant,serif" font-size="16" font-weight="700" '
                 f'fill="#B7C29E">Eden</text></svg>')

    st.markdown(f'<div class="ed-card">{"".join(parts)}</div>', unsafe_allow_html=True)
    st.caption("안쪽 원 = MBTI 16유형 · 바깥 = 해당 유형의 제자")


# ══════════════════════════════════════════════════════════════════════
#  라우팅
# ══════════════════════════════════════════════════════════════════════
PAGES = {
    "home": page_home,
    "chat": page_chat,
    "diagnose": page_diagnose,
    "explore": page_explore,
    "graph": page_graph,
}


def main():
    init_state()
    inject_css()
    header()

    if st.session_state.auth_open:
        auth_dialog()

    PAGES.get(st.session_state.page, page_home)()


if __name__ == "__main__":
    main()
