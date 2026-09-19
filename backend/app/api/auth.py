from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import User
from ..schemas import LoginRequest, TokenResponse
from ..security import create_access_token, login_limiter, verify_password

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, session: Session = Depends(get_session)):
    login_limiter.check(request)
    user = session.exec(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверная почта или пароль")
    return TokenResponse(
        access_token=create_access_token(user),
        user={"id": user.id, "email": user.email, "role": user.role},
    )
