# backend/auth.py
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError


router = APIRouter(prefix="/auth", tags=["auth"])

# =====================================================
# DB 경로 (backend 폴더에 고정) - Windows/Mac 모두 OK
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================
# 비밀번호 해시 설정
# - bcrypt도 가능하지만, 현재 프로젝트는 pbkdf2_sha256로 충분히 안정적
# =====================================================
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


# =====================================================
# JWT 설정
# - 반드시 환경변수로 바꿔서 쓰는 걸 추천
#   Windows PowerShell:  $env:EASYSCORE_SECRET_KEY="..."
#   macOS/Linux:         export EASYSCORE_SECRET_KEY="..."
# =====================================================
SECRET_KEY = os.getenv("EASYSCORE_SECRET_KEY", "LOCAL_DEV_SECRET_CHANGE_ME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =====================================================
# 테이블 생성
# =====================================================
def create_tables() -> None:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


create_tables()


# =====================================================
# 유틸
# =====================================================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = dict(data)
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization 헤더가 없습니다.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization 형식이 올바르지 않습니다. (Bearer 토큰)")
    token = parts[1]
    payload = decode_token(token)

    username = payload.get("sub")
    uid = payload.get("uid")
    if not username or not uid:
        raise HTTPException(status_code=401, detail="토큰 payload가 올바르지 않습니다.")
    return {"id": uid, "username": username}


# =====================================================
# 요청/응답 모델
# =====================================================
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str


# =====================================================
# 회원가입
# =====================================================
@router.post("/register")
def register(req: RegisterRequest):
    username = (req.username or "").strip()
    password = req.password or ""

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="아이디는 최소 3자 이상이어야 합니다.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 최소 6자 이상이어야 합니다.")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), datetime.utcnow().isoformat()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다.")
    finally:
        conn.close()

    return {"message": "회원가입 성공"}


# =====================================================
# 로그인
# =====================================================
@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    username = (req.username or "").strip()
    password = req.password or ""

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호 오류")

    user_id = int(row["id"])
    pw_hash = row["password_hash"]

    if not verify_password(password, pw_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호 오류")

    token = create_access_token({"sub": username, "uid": user_id})
    return TokenResponse(message="로그인 성공", access_token=token)


# =====================================================
# 토큰 검증(프론트에서 로그인 유지 확인용)
# =====================================================
@router.get("/me", response_model=MeResponse)
def me(user=Depends(get_current_user)):
    return MeResponse(id=int(user["id"]), username=str(user["username"]))
