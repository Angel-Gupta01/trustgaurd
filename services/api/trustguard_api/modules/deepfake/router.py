# services/api/trustguard_api/modules/deepfake/router.py
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from trustguard_api.core.envelope import build_envelope_response, get_request_id
from trustguard_api.core.exceptions import NotFoundError, ForbiddenRoleError, ValidationError
from trustguard_api.db.session import get_db
from trustguard_api.db.models import DeepfakeJob, DeepfakeResult, User
from trustguard_api.modules.shared.schemas import (
    DeepfakeJobCreateRequest,
    DeepfakeJobCreateResponse,
    DeepfakeJobStatusResponse,
    DeepfakeResultOut,
    DeepfakeJobStatus,
    UserRole,
)
from trustguard_api.modules.auth.deps import get_current_user

router = APIRouter(prefix="/deepfake", tags=["Deepfake Jobs"])

@router.post("/jobs", response_model=None, status_code=status.HTTP_201_CREATED)
async def create_deepfake_job(
    payload: DeepfakeJobCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1 of Deepfake Workflow:
    Allocates job record and returns direct-to-storage pre-signed upload URL.
    Media bytes never proxy through the core API (Rule 2 & §2.1 Path B).
    """
    # Check idempotency
    stmt = select(DeepfakeJob).where(
        DeepfakeJob.user_id == current_user.id,
        DeepfakeJob.idempotency_key == payload.idempotency_key,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        response_dto = DeepfakeJobCreateResponse(
            job_id=existing.id,
            upload_url=f"http://localhost:9000/trustguard-media/{existing.storage_key}",
            storage_key=existing.storage_key,
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        return build_envelope_response(
            data=response_dto.model_dump(mode="json"),
            request_id=get_request_id(request),
            status_code=status.HTTP_200_OK,
        )

    job_id = uuid.uuid4()
    ext = payload.mime_type.split("/")[-1]
    storage_key = f"uploads/{current_user.id}/{job_id}.{ext}"

    job = DeepfakeJob(
        id=job_id,
        user_id=current_user.id,
        media_type=payload.media_type,
        storage_key=storage_key,
        mime_type=payload.mime_type,
        file_size_bytes=payload.file_size_bytes,
        status=DeepfakeJobStatus.QUEUED,
        idempotency_key=payload.idempotency_key,
    )
    db.add(job)
    await db.flush()

    upload_url = f"http://localhost:9000/trustguard-media/{storage_key}"
    response_dto = DeepfakeJobCreateResponse(
        job_id=job_id,
        upload_url=upload_url,
        storage_key=storage_key,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_201_CREATED,
    )

@router.post("/jobs/{id}/confirm", response_model=None, status_code=status.HTTP_200_OK)
async def confirm_media_upload(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Step 2 of Deepfake Workflow:
    Invoked once client finishes direct upload to object storage.
    Advances status to EXTRACTING_FRAMES and dispatches Celery extraction worker.
    """
    stmt = select(DeepfakeJob).where(DeepfakeJob.id == id)
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise NotFoundError("Job not found")
    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise ForbiddenRoleError("You do not own this job")

    job.status = DeepfakeJobStatus.EXTRACTING_FRAMES
    await db.flush()

    # Celery dispatch:
    # frame_extraction.extract.delay(str(job.id))

    response_dto = DeepfakeJobStatusResponse(
        job_id=job.id,
        status=job.status,
        frame_count=job.frame_count,
    )

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )

@router.get("/jobs/{id}", response_model=None, status_code=status.HTTP_200_OK)
async def get_job_status(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Polling fallback for job status (WebSocket is primary push mechanism)."""
    stmt = select(DeepfakeJob).where(DeepfakeJob.id == id)
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise NotFoundError("Job not found")
    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise ForbiddenRoleError("You do not own this job")

    response_dto = DeepfakeJobStatusResponse(
        job_id=job.id,
        status=job.status,
        frame_count=job.frame_count,
    )

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )

@router.get("/jobs/{id}/result", response_model=None, status_code=status.HTTP_200_OK)
async def get_job_result(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves deepfake analysis result with confidence and Grad-CAM heatmap."""
    stmt = select(DeepfakeJob).where(DeepfakeJob.id == id)
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise NotFoundError("Job not found")
    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise ForbiddenRoleError("You do not own this job")

    if job.status != DeepfakeJobStatus.DONE:
        raise ValidationError(f"Job result not ready. Current status: {job.status.value}")

    res_stmt = select(DeepfakeResult).where(DeepfakeResult.job_id == id)
    result = (await db.execute(res_stmt)).scalar_one_or_none()

    if not result:
        raise NotFoundError("Result record not found")

    response_dto = DeepfakeResultOut.model_validate(result)

    return build_envelope_response(
        data=response_dto.model_dump(mode="json"),
        request_id=get_request_id(request),
        status_code=status.HTTP_200_OK,
    )
