import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: str
    email: str | None = None
    phone_number: str | None = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/me", response_model=UserResponse)
async def create_or_get_user(
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    sub = claims["sub"]
    cognito_groups = claims.get("cognito:groups", [])

    if not cognito_groups:
        logger.info(f"profile creation rejected for {sub}: missing cognito:groups")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a group",
        )

    existing_user = db.query(User).filter(User.id == sub).first()
    if existing_user:
        logger.info(f"profile already exists for {sub}")
        return UserResponse.model_validate(existing_user)

    role = cognito_groups[0]
    email = claims.get("email")
    phone_number = claims.get("phone_number")

    new_user = User(
        id=sub,
        email=email,
        phone_number=phone_number,
        role=role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"profile created for {sub} with role {role}")
    return UserResponse.model_validate(new_user)
