# services/api/trustguard_api/modules/vishing/router.py
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from trustguard_api.modules.shared.schemas import VishingScanRequest, VishingScanResponse, UserRole
from trustguard_api.modules.vishing.service import perform_vishing_scan, VishingScorer
from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.core.exceptions import NotFoundError, ForbiddenRoleError
from trustguard_api.db.session import get_db
from trustguard_api.db.models import VishingScan, User
from trustguard_api.modules.auth.deps import get_current_user_optional, get_current_user

router = APIRouter(prefix="/vishing", tags=["Vishing Detection"])

@router.post("/scan", response_model=None, status_code=status.HTTP_200_OK)
async def scan_vishing_text(
    payload: VishingScanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Synchronous (<150ms budget) vishing scan.
    Anonymous-friendly: No authentication required.
    Saves scan to vishing_scans (fraud registry) and automatically logs an incident if critical.
    """
    result: VishingScanResponse = await perform_vishing_scan(payload, db=db, user=current_user)
    return build_envelope_response(
        data=result.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK
    )

@router.get("/scans/{id}", response_model=None, status_code=status.HTTP_200_OK)
async def get_vishing_scan_by_id(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve past scan result (Owner or ADMIN only)."""
    stmt = select(VishingScan).where(VishingScan.id == id)
    res = await db.execute(stmt)
    scan = res.scalar_one_or_none()

    if not scan:
        raise NotFoundError("Vishing scan record not found")

    if current_user.role != UserRole.ADMIN and scan.user_id != current_user.id:
        raise ForbiddenRoleError("You do not have permission to view this scan")

    response_dto = VishingScanResponse(
        scan_id=scan.id,
        risk_score=scan.risk_score,
        is_critical=scan.is_critical,
        matched_categories=scan.matched_categories,
        flagged_phrases=[],
        recommendation=VishingScorer.get_recommendation(scan.risk_score)
    )

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK
    )
