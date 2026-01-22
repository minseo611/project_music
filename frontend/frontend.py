# frontend/frontend.py

import streamlit as st
import requests
import base64
import re
import time
from streamlit_lottie import st_lottie

# =============================================================================
# 1. 페이지 설정
# =============================================================================
st.set_page_config(
    page_title="EasyScore AI - 악보 변환",
    page_icon="🎹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# 2. 세션 및 유틸리티 설정
# =============================================================================
DEFAULT_BACKEND = "http://127.0.0.1:8000"

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "token" not in st.session_state: st.session_state.token = ""
if "username" not in st.session_state: st.session_state.username = ""
if "show_auth" not in st.session_state: st.session_state.show_auth = False
if "backend_url" not in st.session_state: st.session_state.backend_url = DEFAULT_BACKEND
if "last_result" not in st.session_state: st.session_state.last_result = None

def safe_b64_decode(b64: str) -> bytes:
    if not b64: return b""
    b64 = re.sub(r"\s+", "", b64)
    return base64.b64decode(b64)

def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        return r.json() if r.status_code == 200 else None
    except: return None

# ✅ [수정됨] 원래 나오던 피아노/음악 애니메이션으로 복구 완료!
lottie_music = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_w51pcehl.json")
lottie_processing = load_lottieurl("https://lottie.host/5b630713-3333-4009-81cd-58a529944c33/lC71X2hL9r.json") 

# =============================================================================
# 3. CSS 디자인 (입력창/버튼 가시성 완벽 고정)
# =============================================================================
st.markdown("""
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css");
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
    
    /* 1. 전체 배경 무조건 흰색 고정 */
    .stApp {
        background-color: #ffffff;
        background-image: 
            radial-gradient(at 0% 0%, rgba(102, 126, 234, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(118, 75, 162, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(255, 117, 140, 0.1) 0px, transparent 50%),
            radial-gradient(at 0% 100%, rgba(102, 126, 234, 0.05) 0px, transparent 50%);
        background-attachment: fixed;
    }

    /* 2. 텍스트 색상 강제 검정 (다크모드 방지) */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, span, div {
        color: #31333F !important;
    }
    
    /* 3. [입력창 수정] 배경 흰색, 글씨 검정 무조건 고정 */
    div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 1px solid #d1d1d1 !important;
    }
    div[data-baseweb="base-input"] {
        background-color: #ffffff !important;
    }
    /* 실제 입력되는 텍스트 색상 */
    input[type="text"], input[type="password"] {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
    }

    /* 4. 파일 업로더 박스 스타일 */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #f7f9fc !important;
        border: 1px dashed #a0a0a0 !important;
    }
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {
        color: #31333F !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #ffffff !important;
        color: #31333F !important;
        border: 1px solid #d1d1d1 !important;
    }

    /* 5. [버튼 수정] 진한 회색 배경 + 흰색 글씨로 통일 */
    .stButton > button {
        width: 100%; 
        border-radius: 10px; 
        height: 3rem; 
        font-weight: bold;
        background-color: #333333 !important; /* 진한 회색 배경 */
        color: #ffffff !important;             /* 흰색 글씨 */
        border: none !important;
    }
    
    .stButton > button:hover {
        background-color: #555555 !important; /* 호버 시 약간 밝게 */
        color: #ffffff !important;
    }

    /* 버튼 안의 텍스트 강제 흰색 */
    .stButton > button p {
        color: #ffffff !important;
    }

    /* 6. Primary 버튼 안전장치 */
    button[kind="primary"] {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }

    /* 타이틀 스타일 */
    .hero-title {
        font-size: 4.5rem; font-weight: 900;
        background: linear-gradient(135deg, #2c3e50 30%, #667eea 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.2; margin-bottom: 20px;
        color: transparent !important; 
    }
    .hero-subtitle { font-size: 1.4rem; color: #546e7a !important; line-height: 1.6; margin-bottom: 2rem; }
    
    /* 스텝 카드 */
    .step-container { display: flex; justify-content: space-between; gap: 20px; margin-top: 40px; margin-bottom: 60px; }
    .step-card {
        background: #fff; border-radius: 20px; padding: 30px 20px; text-align: center; width: 32%;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #f0f2f5;
        transition: transform 0.3s;
    }
    .step-card:hover { transform: translateY(-10px); }
    .step-icon { font-size: 3rem; margin-bottom: 15px; }
    .step-title { font-size: 1.2rem; font-weight: 800; margin-bottom: 10px; color: #333 !important; }
    .step-desc { font-size: 0.95rem; color: #7f8c8d !important; }

    /* 탭 스타일 */
    [data-testid="stTabs"] {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        border: 1px solid #eee;
        backdrop-filter: blur(10px);
        max-width: 100%;
        margin: 20px auto;
    }
    
    /* 잠금 박스 & 캡션 */
    .lock-box {
        text-align: center; padding: 60px 20px; background: rgba(255,255,255,0.7);
        border-radius: 20px; border: 2px dashed #bdc3c7; margin-top: 20px;
    }
    .caption-box {
        text-align: center; padding: 15px; background: #ffffff; border-radius: 12px;
        font-weight: 800; color: #455a64 !important; margin-bottom: 20px; border: 1px solid #eee;
    }
    </style>
""", unsafe_allow_html=True)


# =============================================================================
# 4. 화면 렌더링 함수
# =============================================================================

def render_login_page():
    """로그인/회원가입 페이지"""
    
    st.markdown("<h2 style='text-align: center;'>🔐 EasyScore 로그인</h2>", unsafe_allow_html=True)
    
    tab_login, tab_register = st.tabs(["로그인", "회원가입"])
    
    with tab_login:
        st.write("") 
        l_id = st.text_input("아이디", key="login_id")
        l_pw = st.text_input("비밀번호", type="password", key="login_pw")
        
        st.write("") 
        if st.button("로그인하기", use_container_width=True, key="btn_login"):
            try:
                r = requests.post(
                    f"{st.session_state.backend_url}/auth/login",
                    json={"username": l_id, "password": l_pw}
                )
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.logged_in = True
                    st.session_state.token = data["access_token"]
                    st.session_state.username = l_id
                    st.session_state.show_auth = False
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error(f"실패: {r.json().get('detail')}")
            except Exception as e:
                st.error(f"오류: {e}")
        
        st.markdown("---")
        if st.button("메인으로 돌아가기", key="btn_back_1"):
            st.session_state.show_auth = False
            st.rerun()

    with tab_register:
        st.write("")
        r_id = st.text_input("새 아이디", key="reg_id")
        r_pw = st.text_input("새 비밀번호", type="password", key="reg_pw")
        
        st.write("")
        if st.button("가입하기", use_container_width=True, key="btn_reg"):
            try:
                r = requests.post(
                    f"{st.session_state.backend_url}/auth/register",
                    json={"username": r_id, "password": r_pw}
                )
                if r.status_code == 200:
                    st.success("가입 완료! 로그인 탭에서 로그인하세요. ")
                else:
                    st.error(f"실패: {r.json().get('detail')}")
            except Exception as e:
                st.error(f"오류: {e}")

def render_main_page():
    """메인 페이지"""
    
    # [헤더]
    col_hero1, col_hero2 = st.columns([1.5, 1])
    with col_hero1:
        st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
        st.markdown('<h1 class="hero-title">어려운 악보,<br>다양한 난이도로 뚝딱.</h1>', unsafe_allow_html=True)
        st.markdown('<p class="hero-subtitle"><b>EasyScore</b>가 당신의 연주를 다시 시작하게 해드립니다.<br>복잡한 리듬과 화음을 Easyscore가 자동으로 쉽게 바꿔줍니다.</p>', unsafe_allow_html=True)
        
        if st.session_state.logged_in:
            st.success(f"👋 환영합니다, **{st.session_state.username}**님!")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.token = ""
                st.session_state.last_result = None
                st.rerun()
        else:
            if st.button("로그인 / 회원가입하고 시작하기", type="primary"):
                st.session_state.show_auth = True
                st.rerun()

    with col_hero2:
        if lottie_music:
            st_lottie(lottie_music, height=400, key="music_ani")

    # [스텝 가이드]
    st.markdown("""
    <div class="step-container">
        <div class="step-card"><div class="step-icon">📤</div><div class="step-title">STEP 1. 업로드</div><div class="step-desc">악보 사진을 올려주세요.</div></div>
        <div class="step-card"><div class="step-icon">✨</div><div class="step-title">STEP 2. 악보 변환</div><div class="step-desc">버튼만 누르면 편곡됩니다.</div></div>
        <div class="step-card"><div class="step-icon">🎼</div><div class="step-title">STEP 3. 다운로드</div><div class="step-desc">쉬운 악보를 저장하세요.</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # [기능 섹션]
    st.subheader("나만의 쉬운 악보 만들기")

    if not st.session_state.logged_in:
        st.markdown('<div class="lock-box"><h2>🔒 로그인이 필요한 기능입니다</h2><p>악보를 변환하려면 먼저 로그인을 해주세요.</p></div>', unsafe_allow_html=True)
        
        # 예시 보여주기
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.subheader("변환 예시 미리보기")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="caption-box">BEFORE : 원본</div>', unsafe_allow_html=True)
            st.image("frontend/before.png", use_container_width=True)
        with c2:
            st.markdown('<div class="caption-box">AFTER : 변환 결과</div>', unsafe_allow_html=True)
            st.image("frontend/after.png", use_container_width=True)
        return

    # === 로그인한 사용자 영역 ===
    with st.container():
        uploaded_file = st.file_uploader("악보 이미지를 업로드하세요 (JPG, PNG)", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        col_l, col_m, col_r = st.columns([2, 0.5, 2])
        with col_l:
            st.caption("📄 원본 악보")
            st.image(uploaded_file, use_container_width=True)
        with col_m:
            st.markdown("<div style='text-align: center; font-size: 3rem; padding-top: 100px;'>➡️</div>", unsafe_allow_html=True)
        
        with col_r:
            st.caption("🎹 변환 결과")
            
            if st.button("변환 시작", type="primary", use_container_width=True):
                
                # 상태 표시 컨테이너
                status_container = st.empty()
                progress_bar = st.progress(0)
                status_text = st.empty()

                with status_container.container():
                    if lottie_processing:
                        st_lottie(lottie_processing, height=200, key="proc_ani")
                    else:
                        st.spinner("작업 중...")
                
                try:
                    status_text.text("서버에 파일을 전송하고 있습니다...")
                    progress_bar.progress(10)
                    time.sleep(0.5)
                    
                    status_text.text("AI가 악보를 분석 중입니다... (OMR)")
                    progress_bar.progress(30)
                    
                    API_URL = f"{st.session_state.backend_url}/simplify"
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    
                    r = requests.post(API_URL, files=files, headers=headers, timeout=300)
                    
                    status_text.text("쉬운 악보를 생성하고 있습니다...")
                    progress_bar.progress(80)
                    time.sleep(0.5)
                    progress_bar.progress(100)
                    
                    if r.status_code == 200:
                        st.session_state.last_result = r.json()
                        st.balloons()
                    elif r.status_code == 401:
                        st.error("로그인이 만료되었습니다.")
                        st.session_state.logged_in = False
                        st.rerun()
                    else:
                        st.error(f"실패: {r.text}")
                except Exception as e:
                    st.error(f"연결 오류: {e}")
                finally:
                    status_container.empty()
                    progress_bar.empty()
                    status_text.empty()

            # 결과 표시
            if st.session_state.last_result:
                result = st.session_state.last_result
                
                # ✅ [수정됨] Hard 탭 제거 -> Easy, Super Easy만 남김
                t_easy, t_super = st.tabs(["🙂 Easy", "👶 Super Easy"])
                
                def show_res(ikey, mkey, pre):
                    ib64 = result.get(ikey) or result.get("simplified_image_base64")
                    mb64 = result.get(mkey) or result.get("simplified_midi_base64")
                    
                    if ib64:
                        st.image(safe_b64_decode(ib64), use_container_width=True)
                        c_a, c_b = st.columns(2)
                        c_a.download_button("🖼️ 이미지 다운", safe_b64_decode(ib64), f"{pre}.png", "image/png", use_container_width=True)
                        if mb64:
                            c_b.download_button("🎵 MIDI 다운", safe_b64_decode(mb64), f"{pre}.mid", "audio/midi", use_container_width=True)

                with t_easy: show_res("easy_image_base64", "easy_midi_base64", "easy_score")
                with t_super: show_res("super_easy_image_base64", "super_easy_midi_base64", "super_easy_score")
    
    else:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.subheader("변환 예시 미리보기")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="caption-box">BEFORE : 원본</div>', unsafe_allow_html=True)
            st.image("frontend/before.png", use_container_width=True)
        with c2:
            st.markdown('<div class="caption-box">AFTER : 변환 결과</div>', unsafe_allow_html=True)
            st.image("frontend/after.png", use_container_width=True)

# =============================================================================
# 5. 실행
# =============================================================================
if st.session_state.show_auth and not st.session_state.logged_in:
    render_login_page()
else:
    render_main_page()

st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color: #90a4ae; border-top: 1px solid #f1f3f5; margin-top: 50px;">
        <p>© 2026 EasyScore Project.</p>
    </div>
""", unsafe_allow_html=True)