from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.auth_deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

router = APIRouter()

@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return AuthResponse(access_token=create_access_token(user.id), user=user)


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return AuthResponse(access_token=create_access_token(user.id), user=user)


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
