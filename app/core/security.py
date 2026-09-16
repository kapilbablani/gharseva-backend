import logging
from typing import Any, Optional

import httpx
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: Optional[dict[str, Any]] = None


async def get_jwks() -> dict[str, Any]:
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
    except Exception as e:
        logger.error(f"failed to fetch jwks: {type(e).__name__}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_public_key(token: str, keys: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        return None

    kid = unverified_header.get("kid")
    if not kid:
        return None

    for key in keys.get("keys", []):
        if key.get("kid") == kid:
            return key

    return None


async def verify_token(token: str, expected_token_use: str) -> dict[str, Any]:
    keys = await get_jwks()
    public_key = get_public_key(token, keys)

    if not public_key:
        logger.info("token verification failed: key not found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    try:
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}",
            options={"verify_aud": False},
        )
    except JWTError:
        logger.info("token verification failed: invalid signature or expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if decoded.get("token_use") != expected_token_use:
        logger.info(f"token verification failed: wrong token_use (expected {expected_token_use})")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if expected_token_use == "id":
        if decoded.get("aud") != settings.cognito_app_client_id:
            logger.info("token verification failed: wrong audience")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    elif expected_token_use == "access":
        if decoded.get("client_id") != settings.cognito_app_client_id:
            logger.info("token verification failed: wrong client_id")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return decoded


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization:
        logger.info("token verification failed: missing header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.info("token verification failed: malformed header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    token = parts[1]
    return await verify_token(token, expected_token_use="id")


async def get_current_access_token(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    if not authorization:
        logger.info("token verification failed: missing header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.info("token verification failed: malformed header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    token = parts[1]
    return await verify_token(token, expected_token_use="access")
