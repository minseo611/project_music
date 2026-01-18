# AI 쉬운 악보 변환기 (AI Music Simplifier)

Audiveris(OMR)와 music21을 활용해 악보 이미지를 단순화된 악보와 MIDI로 변환해주는 프로젝트입니다.

## 실행 방법

### 1. 필수 프로그램 설치
- **Java 24 이상** (Audiveris 실행용)
- **Audiveris**: `/Applications/Audiveris.app` 경로에 설치되어 있어야 합니다.
- **Tesseract OCR**: `brew install tesseract`

### 2. 라이브러리 설치
pip install -r requirements.txt

### 3. 서버 실행
# 터미널 1
cd backend
python3 main.py

# 터미널 2
streamlit run frontend/frontend.py
