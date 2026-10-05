# services/api/trustguard_api/modules/auth/deps.py
import uuid
from typing import Optional, Callable
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustguard_api.core.security import decode_access_token
from trustguard_api.core.exceptions import UnauthenticatedError, ForbiddenRoleError
from trustguard_api.db.session import get_db
from trustguard_api.db.models import User
from trustguard_api.modules.shared.schemas import UserRole

async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split("Bearer ")[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user if (user and user.is_active) else None

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthenticatedError(message="Missing or malformed Authorization header")

    token = authorization.split("Bearer ")[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthenticatedError(message="Invalid or expired access token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthenticatedError(message="Invalid user identifier in token")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthenticatedError(message="User not found or account deactivated")

    return user

def require_role(*allowed_roles: UserRole) -> Callable:
    """RBAC dependency enforcing permitted UserRole values."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenRoleError(
                message=f"Access denied. Requires one of roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker
