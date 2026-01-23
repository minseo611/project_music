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
    page_title="EasyScore - 악보 변환",
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

def safe_b64_decode(b64: str) -> bytes:
    if not b64: return b""
    b64 = re.sub(r"\s+", "", b64)
    return base64.b64decode(b64)

def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=3)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_music = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_w51pcehl.json")
lottie_processing = load_lottieurl("https://lottie.host/5b630713-3333-4009-81cd-58a529944c33/lC71X2hL9r.json") 

# =============================================================================
# 3. CSS 디자인
# =============================================================================
st.markdown("""
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css");
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
    
    /* 1. 기본 배경 */
    .stApp {
        background-color: #ffffff;
        background-image: 
            radial-gradient(at 0% 0%, rgba(102, 126, 234, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(118, 75, 162, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(255, 117, 140, 0.1) 0px, transparent 50%),
            radial-gradient(at 0% 100%, rgba(102, 126, 234, 0.05) 0px, transparent 50%);
        background-attachment: fixed;
    }

    /* 2. 텍스트 가시성 */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, label, span, div {
        color: #31333F !important;
    }
    
    /* 3. 기본 UI 요소 스타일 */
    div[data-baseweb="input"] { background-color: #ffffff !important; border: 1px solid #d1d1d1 !important; }
    input[type="text"], input[type="password"] { color: #000000 !important; caret-color: #000000 !important; }
    [data-testid="stFileUploaderDropzone"] { background-color: #f7f9fc !important; border: 1px dashed #a0a0a0 !important; }

    /* 4. 버튼 스타일 */
    .stButton > button {
        width: 100%; border-radius: 10px; height: 3rem; font-weight: bold;
        background-color: #333333 !important; color: #ffffff !important; border: none !important;
    }
    .stButton > button:hover { background-color: #555555 !important; color: #ffffff !important; }
    .stButton > button p { color: #ffffff !important; }
    button[kind="primary"] { background-color: #1a1a1a !important; color: #ffffff !important; }

    /* =========================================================
       🔥 결과 화면 전용 UI
       ========================================================= */
    .control-panel-box {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        padding: 30px;
        border-radius: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.03);
        text-align: left;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .info-label { font-size: 0.85rem; color: #888 !important; margin-bottom: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .info-value { font-size: 1.2rem; color: #333 !important; font-weight: 800; margin-bottom: 20px; display: block; }
    .success-badge {
        display: inline-block;
        background-color: #e6fcf5;
        color: #0ca678 !important;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 20px;
        border: 1px solid #c3fae8;
    }

    img.score-image-shadow {
        border-radius: 12px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.12);
        border: 1px solid #eaeaea;
        background-color: white;
    }

    /* 🔥 [복구 완료] 타이틀 왼쪽 정렬 (오른쪽 밀기 제거) */
    .hero-title {
        font-size: 5.5rem; 
        font-weight: 900;
        background: linear-gradient(135deg, #2c3e50 30%, #667eea 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.1; 
        margin-bottom: 20px;
        color: transparent !important; 
        
        /* 왼쪽 정렬 */
        text-align: left !important;
        padding-left: 0 !important;
        margin-left: 0 !important;
    }
    
    .hero-subtitle { 
        font-size: 1.6rem; 
        color: #546e7a !important; 
        line-height: 1.5; 
        margin-bottom: 2rem; 
        
        /* 왼쪽 정렬 */
        text-align: left !important;
        padding-left: 0 !important;
        margin-left: 0 !important;
    }

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

    [data-testid="stTabs"] {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.08);
        border: 1px solid #eee;
    }
    
    .lock-box {
        text-align: center; padding: 60px 20px; background: rgba(255,255,255,0.7);
        border-radius: 20px; border: 2px dashed #bdc3c7; margin-top: 20px;
    }
    .caption-box {
        text-align: center; padding: 15px; background: #ffffff; border-radius: 12px;
        font-weight: 800; color: #455a64 !important; margin-bottom: 20px; border: 1px solid #eee;
    }

    .nav-button-container { margin-top: -10px; }
    
    /* 애니메이션 위치 (약간 왼쪽 유지) */
    .hero-lottie-container { 
        margin-left: -60px !important; 
    }

    /* 🔥 [NEW] Lottie 애니메이션 배경 투명하게 만들기 */
    .hero-lottie-container > div > iframe,
    .hero-lottie-container > div {
        background: transparent !important;
        background-color: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)


# =============================================================================
# 4. 화면 렌더링 함수
# =============================================================================

def render_login_page():
    st.markdown("<h2 style='text-align: center;'>🔐 EasyScore 로그인</h2>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["로그인", "회원가입"])
    with tab_login:
        st.write(""); l_id = st.text_input("아이디", key="login_id"); l_pw = st.text_input("비밀번호", type="password", key="login_pw"); st.write("") 
        if st.button("로그인하기", use_container_width=True, key="btn_login"):
            try:
                r = requests.post(f"{st.session_state.backend_url}/auth/login", json={"username": l_id, "password": l_pw})
                if r.status_code == 200:
                    data = r.json(); st.session_state.logged_in = True; st.session_state.token = data["access_token"]; st.session_state.username = l_id; st.session_state.show_auth = False; st.success("로그인 성공!"); st.rerun()
                else: st.error(f"실패: {r.json().get('detail')}")
            except Exception as e: st.error(f"오류: {e}")
        st.markdown("---")
        if st.button("메인으로 돌아가기", key="btn_back_1"): st.session_state.show_auth = False; st.rerun()
    with tab_register:
        st.write(""); r_id = st.text_input("새 아이디", key="reg_id"); r_pw = st.text_input("새 비밀번호", type="password", key="reg_pw"); st.write("")
        if st.button("가입하기", use_container_width=True, key="btn_reg"):
            try:
                r = requests.post(f"{st.session_state.backend_url}/auth/register", json={"username": r_id, "password": r_pw})
                if r.status_code == 200: st.success("가입 완료! 로그인 탭에서 로그인하세요. ")
                else: st.error(f"실패: {r.json().get('detail')}")
            except Exception as e: st.error(f"오류: {e}")

def render_main_page():
    # 상단 네비게이션
    col_nav1, col_nav2 = st.columns([6, 1])
    with col_nav2:
        st.markdown('<div class="nav-button-container">', unsafe_allow_html=True)
        if st.session_state.logged_in:
            if st.button("로그아웃", use_container_width=True):
                st.session_state.logged_in = False; st.session_state.token = ""; st.session_state.last_result = None; st.rerun()
        else:
            if st.button("로그인 / 회원가입", type="primary", use_container_width=True): st.session_state.show_auth = True; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 🔥 [중요] 컬럼 비율 1.1 : 1.1 유지 (두 요소 간 거리 좁힘)
    col_hero1, col_hero2 = st.columns([1.1, 1.1])
    
    with col_hero1:
        st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
        st.markdown('<h1 class="hero-title">세상 모든 악보를,<br>당신의 손에 맞게.</h1>', unsafe_allow_html=True)
        st.markdown('<p class="hero-subtitle"><b>EasyScore</b>가 당신의 연주를 다시 시작하게 해드립니다.<br>복잡한 리듬과 화음을 Easyscore가 자동으로 쉽게 바꿔줍니다.</p>', unsafe_allow_html=True)
        if st.session_state.logged_in: st.success(f"환영합니다, **{st.session_state.username}**님!")
    with col_hero2:
        if lottie_music:
            st.markdown('<div class="hero-lottie-container">', unsafe_allow_html=True)
            st_lottie(lottie_music, height=400, key="music_ani")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="step-container">
        <div class="step-card"><div class="step-icon">📤</div><div class="step-title">STEP 1. 업로드</div><div class="step-desc">여러 장의 악보를<br>한 번에 올려보세요.</div></div>
        <div class="step-card"><div class="step-icon">✨</div><div class="step-title">STEP 2. 변환</div><div class="step-desc">버튼 한 번으로<br>모두 변환됩니다.</div></div>
        <div class="step-card"><div class="step-icon">🎼</div><div class="step-title">STEP 3. 다운로드</div><div class="step-desc">각각의 결과를<br>확인하고 저장하세요.</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.subheader("나만의 쉬운 악보 만들기")

    if not st.session_state.logged_in:
        st.markdown('<div class="lock-box"><h2>🔒 로그인이 필요한 기능입니다</h2><p>악보를 변환하려면 먼저 로그인을 해주세요.</p></div>', unsafe_allow_html=True)
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

    with st.container():
        uploaded_files = st.file_uploader("악보 이미지를 업로드하세요 (JPG, PNG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if uploaded_files:
        st.write(f"총 **{len(uploaded_files)}장**의 악보가 선택되었습니다.")
        
        if st.button("일괄 변환 시작", type="primary", use_container_width=True):
            total_progress = st.progress(0)
            status_text = st.empty()
            result_containers = [st.container() for _ in range(len(uploaded_files))]

            for idx, uploaded_file in enumerate(uploaded_files):
                current_num = idx + 1
                total_count = len(uploaded_files)
                status_text.markdown(f"### 🔄 [{current_num}/{total_count}] **{uploaded_file.name}** 변환 중...")
                
                try:
                    API_URL = f"{st.session_state.backend_url}/simplify"
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    r = requests.post(API_URL, files=files, headers=headers, timeout=300)
                    
                    if r.status_code == 200:
                        result = r.json()
                        with result_containers[idx]:
                            with st.expander(f"완료: {uploaded_file.name}", expanded=True):
                                t_easy, t_super = st.tabs(["Easy", "Super Easy"])
                                
                                def show_res(ikey, mkey, pre):
                                    ib64 = result.get(ikey) or result.get("simplified_image_base64")
                                    mb64 = result.get(mkey) or result.get("simplified_midi_base64")
                                    
                                    if ib64:
                                        # =================================================
                                        # 🔥 레이아웃 조정: 왼쪽 여백 추가로 전체를 오른쪽으로 이동
                                        # [0.4(빈칸), 1.2(컨트롤), 3.0(악보)] 비율로 조정
                                        # =================================================
                                        _, c_control, c_sheet = st.columns([0.4, 1.2, 3.0], vertical_alignment="center")
                                        filename_prefix = f"{uploaded_file.name}_{pre}"
                                        
                                        with c_control:
                                            st.markdown(f"""
                                            <div class="control-panel-box">
                                                <div class="success-badge">✨ Conversion Success</div>
                                                <span class="info-label">File Name</span>
                                                <span class="info-value">{uploaded_file.name}</span>
                                                <span class="info-label">Mode</span>
                                                <span class="info-value">{pre.replace('_', ' ').title()}</span>
                                                <hr style="margin: 15px 0; border: 0; border-top: 1px solid #ddd;">
                                                <p style="font-size:0.9rem; color:#666;">아래 버튼을 눌러 저장하세요.</p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            st.write("")
                                            st.download_button("🖼️ 이미지 다운로드", safe_b64_decode(ib64), f"{filename_prefix}.png", "image/png", use_container_width=True)
                                            if mb64:
                                                st.write("")
                                                st.download_button("🎵 MIDI 다운로드", safe_b64_decode(mb64), f"{filename_prefix}.mid", "audio/midi", use_container_width=True)
                                        
                                        with c_sheet:
                                            clean_b64 = re.sub(r"\s+", "", ib64)
                                            img_html = f'<img src="data:image/png;base64,{clean_b64}" class="score-image-shadow" style="max-height: 80vh; width: auto; max-width: 100%; display: block; margin: 0 auto;">'
                                            st.markdown(img_html, unsafe_allow_html=True)

                                with t_easy: show_res("easy_image_base64", "easy_midi_base64", "easy_score")
                                with t_super: show_res("super_easy_image_base64", "super_easy_midi_base64", "super_easy_score")
                    
                    elif r.status_code == 401:
                        st.error("로그인이 만료되었습니다."); st.session_state.logged_in = False; st.rerun(); break
                    else:
                        with result_containers[idx]: st.error(f"❌ {uploaded_file.name} 실패: {r.text}")
                except Exception as e:
                    with result_containers[idx]: st.error(f"❌ {uploaded_file.name} 에러: {e}")
                
                total_progress.progress(int((current_num / total_count) * 100))

            status_text.success("모든 변환 작업이 완료되었습니다!"); st.balloons()

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