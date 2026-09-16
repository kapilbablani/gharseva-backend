import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_current_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    sub: str
    email: str | None = None
    cognito_groups: list[str] | None = Field(None, alias="cognito:groups")

    class Config:
        populate_by_name = True


class LogoutResponse(BaseModel):
    message: str


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(claims: dict[str, Any] = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        sub=claims["sub"],
        email=claims.get("email"),
        cognito_groups=claims.get("cognito:groups"),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    claims: dict[str, Any] = Depends(get_current_access_token),
    authorization: str | None = Header(None),
) -> dict[str, str]:
    parts = authorization.split()
    access_token = parts[1]

    try:
        cognito_client = boto3.client("cognito-idp", region_name=settings.aws_region)
        cognito_client.global_sign_out(AccessToken=access_token)
        logger.info("logout succeeded")
        return {"message": "Logged out"}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NotAuthorizedException":
            logger.info("logout failed: token already invalid")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        else:
            logger.error("logout failed: cognito error")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Service temporarily unavailable")
    except Exception:
        logger.error("logout failed: service error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Service temporarily unavailable")
