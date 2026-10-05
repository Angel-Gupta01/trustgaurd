# services/api/trustguard_api/modules/auth/router.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from trustguard_api.db.session import get_db
from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.core.config import settings
from trustguard_api.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    AuthTokenResponse,
    UserProfileDTO,
)
from trustguard_api.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=None, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await AuthService.register_user(db, payload)
    token_response = AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileDTO.model_validate(user),
    )
    return build_envelope_response(
        data=token_response.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_201_CREATED,
    )

@router.post("/login", response_model=None, status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await AuthService.authenticate_user(db, payload)
    token_response = AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileDTO.model_validate(user),
    )
    return build_envelope_response(
        data=token_response.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )

@router.post("/refresh", response_model=None, status_code=status.HTTP_200_OK)
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await AuthService.rotate_refresh_token(db, payload.refresh_token)
    token_response = AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserProfileDTO.model_validate(user),
    )
    return build_envelope_response(
        data=token_response.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )
