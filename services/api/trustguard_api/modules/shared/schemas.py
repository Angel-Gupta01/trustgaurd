# services/api/trustguard_api/modules/shared/schemas.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
 
# ---------- Enums (mirror DB enums in .ai/SCHEMA.sql exactly) ----------
class UserRole(str, Enum):
    USER = "USER"
    CREATOR = "CREATOR"
    ADMIN = "ADMIN"
 
class VishingSourceType(str, Enum):
    PASTED_TEXT = "PASTED_TEXT"
    LIVE_PAGE_SCAN = "LIVE_PAGE_SCAN"
    UPLOADED_TRANSCRIPT = "UPLOADED_TRANSCRIPT"
 
class VishingCategory(str, Enum):
    URGENCY_PRESSURE = "URGENCY_PRESSURE"
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    FINANCIAL_LURE = "FINANCIAL_LURE"
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    THREAT_OF_LOSS = "THREAT_OF_LOSS"
    LINK_BAIT = "LINK_BAIT"
 
class MediaType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
 
class DeepfakeJobStatus(str, Enum):
    QUEUED = "QUEUED"
    EXTRACTING_FRAMES = "EXTRACTING_FRAMES"
    ANALYZING = "ANALYZING"
    DONE = "DONE"
    FAILED = "FAILED"
 
class ManipulationType(str, Enum):
    FACE_SWAP = "FACE_SWAP"
    FACE_REENACTMENT = "FACE_REENACTMENT"
    FULL_SYNTHESIS = "FULL_SYNTHESIS"
    AUDIO_SYNC_MISMATCH = "AUDIO_SYNC_MISMATCH"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
 
class ChainNetwork(str, Enum):
    POLYGON_AMOY = "POLYGON_AMOY"
    LOCAL_DEV = "LOCAL_DEV"

class AnchorStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
 
class VerificationResult(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    NEAR_MATCH_TAMPERED = "NEAR_MATCH_TAMPERED"
    NO_MATCH = "NO_MATCH"
 
# ---------- Vishing ----------
class VishingScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=4000)
    source_type: VishingSourceType
 
class VishingScanResponse(BaseModel):
    scan_id: UUID
    risk_score: Decimal = Field(..., ge=0, le=100)
    is_critical: bool
    matched_categories: list[VishingCategory]
    flagged_phrases: list[str]
    recommendation: str  # e.g. "HANG UP", "PROCEED WITH CAUTION", "LOOKS SAFE"
 
# ---------- Deepfake ----------
class DeepfakeJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_type: MediaType
    mime_type: str = Field(
        ..., pattern=r"^(image/(jpeg|png|webp)|video/(mp4|webm))$"
    )
    file_size_bytes: int = Field(..., gt=0, le=104_857_600)
    idempotency_key: str = Field(..., min_length=8, max_length=64)
 
class DeepfakeJobCreateResponse(BaseModel):
    job_id: UUID
    upload_url: str
    storage_key: str
    expires_at: datetime
 
class DeepfakeJobStatusResponse(BaseModel):
    job_id: UUID
    status: DeepfakeJobStatus
    frame_count: Optional[int] = None
 
class DeepfakeResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    is_synthetic: bool
    confidence: Decimal
    manipulation_type: ManipulationType
    heatmap_url: Optional[str] = None
    model_version: str
 
# ---------- Provenance ----------
class ProvenanceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    capture_device: Optional[str] = Field(None, max_length=120)
 
class ProvenanceRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_hash: str = Field(..., min_length=64, max_length=64)
    media_type: MediaType
    metadata: ProvenanceMetadata
 
    @field_validator("media_hash")
    @classmethod
    def hex_only(cls, v: str) -> str:
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("media_hash must be hex-encoded sha256")
        return v.lower()
 
class ProvenanceRegisterResponse(BaseModel):
    record_id: UUID
    anchor_status: AnchorStatus
    tx_hash: Optional[str] = None
 
class ProvenanceVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    media_hash: str = Field(..., min_length=64, max_length=64)
 
class ProvenanceVerifyResponse(BaseModel):
    result: VerificationResult
    creator_name: Optional[str] = None
    registered_at: Optional[datetime] = None
    tx_hash: Optional[str] = None
    near_match_record_id: Optional[UUID] = None
 
# ---------- Unified incident feed ----------
class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_type: str  # "VISHING" | "DEEPFAKE"
    risk_score: Decimal
    category: str
    evidence: dict[str, Any]
    created_at: datetime
 
# ---------- Standard response envelope (see .ai/CONVENTIONS.md) ----------
class ApiError(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
 
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[ApiError] = None
    request_id: str
