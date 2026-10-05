# services/api/trustguard_api/modules/provenance/router.py
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.core.exceptions import MediaAlreadyRegisteredError
from trustguard_api.db.session import get_db
from trustguard_api.db.models import ProvenanceRecord, ProvenanceVerification, User
from trustguard_api.modules.shared.schemas import (
    ProvenanceRegisterRequest,
    ProvenanceRegisterResponse,
    ProvenanceVerifyRequest,
    ProvenanceVerifyResponse,
    VerificationResult,
    AnchorStatus,
    UserRole,
)
from trustguard_api.modules.auth.deps import require_role, get_current_user_optional

router = APIRouter(prefix="/provenance", tags=["Content Provenance"])

@router.post("/register", response_model=None, status_code=status.HTTP_201_CREATED)
async def register_provenance(
    payload: ProvenanceRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    creator_user: User = Depends(require_role(UserRole.CREATOR, UserRole.ADMIN)),
):
    """
    Creator registration of media commitment hash.
    Checks PostgreSQL for uniqueness BEFORE queueing or touching the chain (Rule 5 & §2.1 Path C).
    Prevents gas waste and worker retry issues.
    """
    stmt = select(ProvenanceRecord).where(ProvenanceRecord.media_hash == payload.media_hash)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise MediaAlreadyRegisteredError("Media hash has already been registered on-chain.")

    record_id = uuid.uuid4()
    record = ProvenanceRecord(
        id=record_id,
        creator_id=creator_user.id,
        media_hash=payload.media_hash,
        media_type=payload.media_type,
        metadata_json=payload.metadata.model_dump(mode="json"),
        anchor_status=AnchorStatus.PENDING,
    )
    db.add(record)
    await db.flush()

    # Worker dispatch will be handled asynchronously via Redis/Celery:
    # blockchain_anchor.submit_registration.delay(str(record_id))

    response_dto = ProvenanceRegisterResponse(
        record_id=record_id,
        anchor_status=AnchorStatus.PENDING,
        tx_hash=None,
    )

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_201_CREATED,
    )

@router.post("/verify", response_model=None, status_code=status.HTTP_200_OK)
async def verify_provenance(
    payload: ProvenanceVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    requester: Optional[User] = Depends(get_current_user_optional),
):
    """
    Public content provenance verification lookup.
    Synchronous read checking database cache mirror of on-chain commitments.
    Logs every check into provenance_verifications for audit trail.
    """
    stmt = select(ProvenanceRecord).where(ProvenanceRecord.media_hash == payload.media_hash)
    record = (await db.execute(stmt)).scalar_one_or_none()

    if record:
        creator_stmt = select(User.display_name).where(User.id == record.creator_id)
        creator_name = (await db.execute(creator_stmt)).scalar_one_or_none() or "Verified Creator"

        result_enum = VerificationResult.EXACT_MATCH
        response_dto = ProvenanceVerifyResponse(
            result=result_enum,
            creator_name=creator_name,
            registered_at=record.registered_at,
            tx_hash=record.tx_hash,
            near_match_record_id=None,
        )
    else:
        result_enum = VerificationResult.NO_MATCH
        response_dto = ProvenanceVerifyResponse(
            result=result_enum,
            creator_name=None,
            registered_at=None,
            tx_hash=None,
            near_match_record_id=None,
        )

    # Log verification check
    audit_log = ProvenanceVerification(
        media_hash=payload.media_hash,
        requester_id=requester.id if requester else None,
        result=result_enum,
        matched_record_id=record.id if record else None,
    )
    db.add(audit_log)
    await db.flush()

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )
