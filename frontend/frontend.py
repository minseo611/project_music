# frontend/frontend.py

import streamlit as st
import requests
import base64
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="AI 쉬운 악보 변환기", page_icon="🎹", layout="centered")

st.title("🎹 AI 쉬운 악보 변환기")
st.markdown("어려운 악보를 올리면 **쉽게 칠 수 있는 악보**로 바꿔드립니다!")
st.info("💡 팁: 해상도가 높은 깨끗한 악보 이미지를 사용해주세요.")

# --- 사이드바 ---
with st.sidebar:
    st.header("사용 방법")
    st.markdown("1. 악보 이미지(PNG, JPG)를 업로드하세요.")
    st.markdown("2. **'변환하기'** 버튼을 누르세요.")
    st.markdown("3. 잠시 기다리면 **쉬운 악보**와 **소리**가 나옵니다!")

# --- 파일 업로더 ---
uploaded_file = st.file_uploader("악보 이미지를 선택하세요", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 업로드된 이미지 미리보기
    st.image(uploaded_file, caption="원본 악보", use_column_width=True)

    # 변환 버튼
    if st.button("✨ 쉬운 악보로 변환하기", type="primary"):
        
        # 스피너(로딩 표시)
        with st.status("AI가 악보를 분석하고 있습니다...", expanded=True) as status:
            
            # 백엔드 API 주소
            API_URL = "http://127.0.0.1:8000/simplify"
            
            try:
                # 1. 파일 전송
                status.write("📤 서버로 악보 전송 중...")
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                
                # 2. 분석 시작 (시간이 좀 걸립니다)
                status.write("🎼 Audiveris가 악보를 읽는 중... (최대 1~2분 소요)")
                start_time = time.time()
                
                response = requests.post(API_URL, files=files)
                
                if response.status_code == 200:
                    status.update(label="변환 완료!", state="complete", expanded=False)
                    result = response.json()
                    
                    st.success(f"변환 성공! (소요 시간: {time.time() - start_time:.1f}초)")
                    st.divider()

                    # --- 결과 화면 표시 ---
                    
                    # 1. 쉬운 악보 이미지 (PNG)
                    st.subheader("🖼️ 변환된 악보")
                    img_base64 = result.get("simplified_image_base64")
                    
                    if img_base64:
                        image_bytes = base64.b64decode(img_base64)
                        st.image(image_bytes, caption="AI가 만든 쉬운 악보", use_column_width=True)
                        
                        # 다운로드 버튼
                        st.download_button(
                            label="📥 악보 이미지 다운로드",
                            data=image_bytes,
                            file_name="easy_score.png",
                            mime="image/png"
                        )
                    else:
                        st.warning("⚠️ 악보 이미지를 생성하지 못했습니다. (MuseScore 설정 필요)")
                        st.caption("하지만 음악 데이터 분석은 성공했습니다! 아래 소리를 들어보세요.")

                    st.divider()

                    # 2. MIDI 오디오 (소리)
                    st.subheader("🎹 미리 듣기")
                    midi_base64 = result.get("simplified_midi_base64")
                    
                    if midi_base64:
                        midi_bytes = base64.b64decode(midi_base64)
                        
                        # MIDI 다운로드 버튼 (브라우저에서 직접 재생은 지원이 잘 안됨)
                        st.download_button(
                            label="🎵 MIDI 파일 다운로드 (클릭해서 듣기)",
                            data=midi_bytes,
                            file_name="easy_score.mid",
                            mime="audio/midi"
                        )
                        st.info("다운로드한 MIDI 파일을 실행하면 소리를 들을 수 있습니다.")
                    else:
                        st.error("오디오 파일을 생성하지 못했습니다.")

                else:
                    status.update(label="오류 발생", state="error")
                    st.error("변환에 실패했습니다.")
                    # 백엔드가 보낸 에러 메시지 표시
                    try:
                        error_detail = response.json().get('detail')
                        st.error(f"서버 메시지: {error_detail}")
                    except:
                        st.error(f"상태 코드: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("🚫 백엔드 서버에 연결할 수 없습니다.")
                st.info("터미널에서 'python3 main.py'로 백엔드 서버를 먼저 실행해주세요.")