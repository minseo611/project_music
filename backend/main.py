# backend/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import ai_engine  # 👈 우리가 만든 '엔진룸' 연결!

app = FastAPI(title="AI 악보 변환기 Backend")

# --- CORS 설정 (프론트엔드 연동용) ---
origins = [
    "http://localhost",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Audiveris Backend is ready!"}

@app.post("/simplify")
async def simplify_score(file: UploadFile = File(...)):
    """
    1. 이미지를 받아서
    2. ai_engine (Audiveris)으로 분석하고
    3. ai_engine (music21)으로 단순화하여
    4. 결과(MIDI, PNG Base64)를 반환
    """
    
    # 이미지 파일인지 확인
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    try:
        # 파일 읽기
        image_bytes = await file.read()
        print(f"📥 파일 수신: {file.filename} ({len(image_bytes)} bytes)")

        # ==========================================
        # 1. 1차 엔진 호출 (Audiveris)
        # ==========================================
        print("⚙️ 1단계: Audiveris OMR 실행 중...")
        music_xml_content = ai_engine.run_audiveris(image_bytes)
        
        # ==========================================
        # 2. 2차 엔진 호출 (music21 단순화)
        # ==========================================
        print("⚙️ 2단계: 악보 단순화 및 파일 생성 중...")
        result_files = ai_engine.simplify_and_generate(music_xml_content)

        # 3. 결과 반환
        final_result = {
            "status": "success",
            "original_filename": file.filename,
            "simplified_midi_base64": result_files.get("simplified_midi_base64"),
            "simplified_image_base64": result_files.get("simplified_image_base64")
        }
        
        print("✅ 변환 완료! 결과 전송.")
        return JSONResponse(content=final_result, status_code=200)

    except Exception as e:
        print(f"❌ 서버 에러 발생: {str(e)}")
        # 에러 내용을 프론트엔드로 전달
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)