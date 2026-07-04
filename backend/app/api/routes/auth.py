from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.memory_card import MemoryCard
from app.models.persona import Persona
from app.models.user import User, uuid_str
from app.schemas.auth import (
    DemoTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.services.materials import create_manual_material, run_material_parse_job
from app.services.profile import refresh_profile_and_trust


router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_MATERIALS = [
    {
        "manual_text": "外婆喜欢给小铭包馄饨，也常说饭要趁热慢慢吃。",
        "user_description": "关于外婆做饭和照顾小铭的文字故事",
        "location_hint": "家里的餐桌",
    },
    {
        "manual_text": "外婆常说慢慢来，别急，心里难受的时候先把气喘匀。",
        "user_description": "外婆安慰小铭时常用的话",
        "location_hint": "家中客厅",
    },
    {
        "manual_text": "小铭生日那天，外婆准备了蛋糕和一碗热汤，笑着说只要小铭平安就好。",
        "user_description": "生日聚会照片对应的共同回忆",
        "location_hint": "生日聚会",
    },
]


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

    persona = Persona(
        user_id=user.id,
        name="外婆",
        persona_type="deceased_relative",
        status="deceased",
        relationship_to_user="外婆",
        user_nickname_by_persona="小铭",
        age=72,
        gender="female",
        language="zh-CN",
        short_bio="她温柔、朴素，喜欢给小铭做饭，也总是慢慢安慰家里人。",
        speaking_style="温柔、慢慢说，常用朴素家常的话安慰小铭。",
        emotional_style="先接住情绪，再给小铭一点温柔鼓励，避免制造依赖。",
        forbidden_expressions="不要说「我真的回来了」；不要神化、灵异化表达；不要替用户做重大决定。",
        trust_score=0,
    )
    db.add(persona)
    db.commit()
    db.refresh(user)
    db.refresh(persona)

    for material in DEMO_MATERIALS:
        _material, job = create_manual_material(
            db,
            user,
            persona,
            manual_text=material["manual_text"],
            importance="important",
            user_description=material["user_description"],
            material_time=None,
            people_tags=["外婆", "小铭"],
            location_hint=material["location_hint"],
        )
        run_material_parse_job(db, job)

    memories = db.scalars(
        select(MemoryCard).where(MemoryCard.persona_id == persona.id)
    ).all()
    for memory in memories:
        memory.status = "confirmed"
        db.add(memory)
    refresh_profile_and_trust(db, persona)
    db.commit()
    db.refresh(persona)
    db.refresh(user)
    return _demo_token_for_user(user, persona)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
