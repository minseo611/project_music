# backend/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 👇 동료의 auth.py를 가져옵니다 (이제 파일이 있으니 에러 안 남!)
import ai_engine
from auth import router as auth_router, get_current_user

app = FastAPI(title="EasyScore AI Backend")

origins = [
    "http://localhost",
    "http://localhost:8501",
    "http://127.0.0.1",
    "http://127.0.0.1:8501",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 로그인/회원가입 기능 활성화
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "EasyScore Backend is ready!"}

@app.post("/simplify")
async def simplify_score(
    file: UploadFile = File(...),
    # 👇 이 부분이 핵심! 로그인한 사람(user)만 통과시킴
    user=Depends(get_current_user) 
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    try:
        # 로그인한 사용자 이름 출력 (동료 코드와 연동 확인용)
        print(f"👤 요청 사용자: {user['username']}") 

        image_bytes = await file.read()
        print(f"📥 파일 수신: {file.filename} ({len(image_bytes)} bytes)")

        # AI 엔진 실행
        print("⚙️ OMR 및 단순화 작업 시작...")
        music_xml_content = ai_engine.run_audiveris(image_bytes)
        result_files = ai_engine.simplify_and_generate(music_xml_content)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "original_filename": file.filename,
                "easy_image_base64": result_files.get("easy_image_base64"),
                "easy_midi_base64": result_files.get("easy_midi_base64"),
                "super_easy_image_base64": result_files.get("super_easy_image_base64"),
                "super_easy_midi_base64": result_files.get("super_easy_midi_base64"),
                # 호환성용
                "simplified_image_base64": result_files.get("simplified_image_base64"),
                "simplified_midi_base64": result_files.get("simplified_midi_base64"),
            },
        )

    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)