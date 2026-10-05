# services/api/trustguard_api/modules/incidents/router.py
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.db.session import get_db
from trustguard_api.db.models import Incident, User
from trustguard_api.modules.shared.schemas import (
    IncidentOut,
    UserRole,
    IncidentSourceType,
)
from trustguard_api.modules.auth.deps import get_current_user

router = APIRouter(prefix="/incidents", tags=["Incidents Feed"])

@router.get("", response_model=None, status_code=status.HTTP_200_OK)
async def list_incidents(
    request: Request,
    source_type: Optional[IncidentSourceType] = Query(None, description="Filter by VISHING or DEEPFAKE"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified incident feed across both detectors.
    Emits the identical RiskSignal shape for single-component frontend consumption.
    Normal users retrieve their own raised signals; ADMINs can monitor the global incident log.
    """
    stmt = select(Incident)

    # Authorization filtering
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Incident.user_id == current_user.id)

    # Source type filtering
    if source_type is not None:
        stmt = stmt.where(Incident.source_type == source_type)

    # Ordering & pagination
    stmt = stmt.order_by(desc(Incident.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    records = result.scalars().all()

    incidents_out: List[dict] = [
        IncidentOut(
            id=rec.id,
            source_type=rec.source_type.value,
            risk_score=rec.risk_score,
            category=rec.category,
            evidence=rec.evidence,
            created_at=rec.created_at,
        ).model_dump(mode="json")
        for rec in records
    ]

    return build_envelope_response(
        data=incidents_out,
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )
