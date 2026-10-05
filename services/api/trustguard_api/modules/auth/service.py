# services/api/trustguard_api/modules/auth/service.py
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from trustguard_api.db.models import User, RefreshToken
from trustguard_api.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthTokenResponse,
    UserProfileDTO,
)
from trustguard_api.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from trustguard_api.core.exceptions import (
    ValidationError,
    UnauthenticatedError,
    NotFoundError,
)
from trustguard_api.core.config import settings

class AuthService:
    @classmethod
    async def register_user(cls, db: AsyncSession, payload: RegisterRequest) -> Tuple[User, str, str]:
        # Check if email is already taken
        stmt = select(User).where(User.email == payload.email.lower())
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError(message="Email address already registered", field="email")

        user = User(
            email=payload.email.lower(),
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        access_token, refresh_token = await cls._issue_token_pair(db, user)
        return user, access_token, refresh_token

    @classmethod
    async def authenticate_user(cls, db: AsyncSession, payload: LoginRequest) -> Tuple[User, str, str]:
        stmt = select(User).where(User.email == payload.email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise UnauthenticatedError(message="Invalid email or password")

        if not user.is_active:
            raise UnauthenticatedError(message="Account is deactivated")

        access_token, refresh_token = await cls._issue_token_pair(db, user)
        return user, access_token, refresh_token

    @classmethod
    async def rotate_refresh_token(cls, db: AsyncSession, raw_refresh_token: str) -> Tuple[User, str, str]:
        token_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise UnauthenticatedError(message="Invalid refresh token")

        if token_record.revoked_at is not None:
            # Token reuse detected! Revoke all tokens for this user for security
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == token_record.user_id)
                .values(revoked_at=datetime.utcnow())
            )
            await db.flush()
            raise UnauthenticatedError(message="Revoked token reuse detected. Please log in again.")

        if token_record.expires_at < datetime.utcnow():
            raise UnauthenticatedError(message="Refresh token has expired")

        # Fetch associated user
        user_stmt = select(User).where(User.id == token_record.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthenticatedError(message="User not found or inactive")

        # Revoke old refresh token and issue new pair
        token_record.revoked_at = datetime.utcnow()
        new_raw_refresh = generate_refresh_token()
        new_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_raw_refresh),
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(new_record)
        await db.flush()

        token_record.replaced_by = new_record.id

        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )

        return user, new_access_token, new_raw_refresh

    @classmethod
    async def _issue_token_pair(cls, db: AsyncSession, user: User) -> Tuple[str, str]:
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        raw_refresh = generate_refresh_token()
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(refresh_record)
        await db.flush()
        return access_token, raw_refresh
