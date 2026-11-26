import time
from typing import Optional
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import httpx

from app.core.config import settings
from app.core.errors import AppException

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


async def verify_token_via_supabase_api(token: str) -> Optional[AuthenticatedUser]:
    """Fallback verification against Supabase Auth endpoint if local verification fails."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None
    try:
        url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
        headers = {
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return AuthenticatedUser(
                    id=data.get("id"),
                    email=data.get("email"),
                    role=data.get("role", "authenticated"),
                )
    except Exception:
        pass
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        raise AppException(
            code="UNAUTHORIZED",
            message="Missing authentication credentials.",
            status_code=401,
        )

    token = credentials.credentials

    # 1. Try local verification with SUPABASE_JWT_SECRET
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            sub = payload.get("sub")
            if not sub:
                raise AppException(
                    code="UNAUTHORIZED",
                    message="Invalid token claims: subject missing.",
                    status_code=401,
                )
            return AuthenticatedUser(
                id=sub,
                email=payload.get("email"),
                role=payload.get("role", "authenticated"),
            )
        except jwt.ExpiredSignatureError:
            raise AppException(
                code="TOKEN_EXPIRED",
                message="Authentication token has expired.",
                status_code=401,
            )
        except jwt.PyJWTError:
            # If local verification failed, attempt fallback to Supabase API
            pass

    # 2. Fallback verification via Supabase Auth API
    user = await verify_token_via_supabase_api(token)
    if user:
        return user

    raise AppException(
        code="UNAUTHORIZED",
        message="Invalid or malformed authentication token.",
        status_code=401,
    )

