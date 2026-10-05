# services/api/trustguard_api/modules/admin/router.py
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.core.exceptions import ValidationError
from trustguard_api.db.session import get_db
from trustguard_api.db.models import KeywordCluster, User
from trustguard_api.modules.shared.schemas import UserRole
from trustguard_api.modules.auth.deps import require_role
from trustguard_api.modules.admin.schemas import KeywordClusterCreateRequest, KeywordClusterOut

router = APIRouter(prefix="/admin", tags=["Admin Rule Management"])

@router.get("/keyword-clusters", response_model=None, status_code=status.HTTP_200_OK)
async def list_keyword_clusters(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Admin-only listing of all configured scam phrases and weights."""
    stmt = select(KeywordCluster).order_by(KeywordCluster.category, KeywordCluster.phrase)
    result = await db.execute(stmt)
    records = result.scalars().all()
    dtos = [KeywordClusterOut.model_validate(r).model_dump(mode="json") for r in records]
    return build_envelope_response(
        data=dtos,
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )

@router.post("/keyword-clusters", response_model=None, status_code=status.HTTP_201_CREATED)
async def create_keyword_cluster(
    payload: KeywordClusterCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Admin-editable rule layer.
    Allows updating scam vocabulary without redeploying code.
    """
    # Check for duplicate phrase under category
    stmt = select(KeywordCluster).where(
        KeywordCluster.category == payload.category,
        KeywordCluster.phrase == payload.phrase.strip().lower(),
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise ValidationError(message="Phrase already registered under this category", field="phrase")

    cluster = KeywordCluster(
        category=payload.category,
        phrase=payload.phrase.strip().lower(),
        weight=payload.weight,
        is_active=payload.is_active,
        created_by=admin_user.id,
    )
    db.add(cluster)
    await db.flush()

    dto = KeywordClusterOut.model_validate(cluster).model_dump(mode="json")
    return build_envelope_response(
        data=dto,
        request_id=get_request_id(request),
        status_code=status.HTTP_201_CREATED,
    )
