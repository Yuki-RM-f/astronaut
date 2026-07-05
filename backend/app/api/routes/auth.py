from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.persona import Persona
from app.models.user import User, uuid_str
from app.schemas.auth import (
    DemoTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.services.default_personas import ensure_default_personas_for_user


router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _token_for_user(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


def _demo_token_for_user(user: User, persona: Persona) -> DemoTokenResponse:
    return DemoTokenResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
        demo_persona_id=persona.id,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_for_user(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return _token_for_user(user)


@router.post(
    "/demo",
    response_model=DemoTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def demo_session(db: Session = Depends(get_db)):
    user = User(
        email=f"demo-{uuid_str()}@local.demo",
        password_hash=hash_password("demo-session"),
        display_name="演示用户",
        plan_type="guest_demo",
    )
    db.add(user)
    db.flush()

    personas = ensure_default_personas_for_user(db, user)
    persona = personas["grandmother"]
    db.commit()
    db.refresh(user)
    db.refresh(persona)
    return _demo_token_for_user(user, persona)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
