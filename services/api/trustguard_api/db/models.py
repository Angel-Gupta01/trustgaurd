# services/api/trustguard_api/db/models.py
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Numeric,
    Integer,
    BigInteger,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    Enum as SAEnum,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

from trustguard_api.modules.shared.schemas import (
    UserRole,
    VishingSourceType,
    VishingCategory,
    IncidentSourceType,
    MediaType,
    DeepfakeJobStatus,
    ManipulationType,
    ChainNetwork,
    AnchorStatus,
    VerificationResult,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    role = Column(
        SAEnum(UserRole, name="user_role", native_enum=True),
        nullable=False,
        default=UserRole.USER,
        index=True,
    )
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    vishing_scans = relationship("VishingScan", back_populates="user")
    deepfake_jobs = relationship("DeepfakeJob", back_populates="user")
    provenance_records = relationship("ProvenanceRecord", back_populates="creator")
    incidents = relationship("Incident", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class KeywordCluster(Base):
    __tablename__ = "keyword_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(
        SAEnum(VishingCategory, name="vishing_category", native_enum=True),
        nullable=False,
        index=True,
    )
    phrase = Column(String, nullable=False)
    weight = Column(Numeric(4, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("category", "phrase", name="uq_keyword_cluster_phrase"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="chk_keyword_cluster_weight"),
    )


class VishingScan(Base):
    __tablename__ = "vishing_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    source_type = Column(
        SAEnum(VishingSourceType, name="vishing_source_type", native_enum=True),
        nullable=False,
    )
    text_snippet = Column(String(4000), nullable=False)
    # Stored after PII redaction of digit runs length >= 6
    matched_categories = Column(
        ARRAY(SAEnum(VishingCategory, name="vishing_category", native_enum=True)),
        nullable=False,
        default=[],
    )
    rule_score = Column(Numeric(5, 2), nullable=False)
    ml_score = Column(Numeric(5, 2), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=False)
    is_critical = Column(Boolean, nullable=False, default=False)
    model_version = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("rule_score >= 0 AND rule_score <= 100", name="chk_vishing_rule_score"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="chk_vishing_risk_score"),
        Index("idx_vishing_scans_critical", "created_at", postgresql_where=text("is_critical = TRUE")),
    )

    user = relationship("User", back_populates="vishing_scans")
    incidents = relationship("Incident", back_populates="vishing_scan")


class DeepfakeJob(Base):
    __tablename__ = "deepfake_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    media_type = Column(
        SAEnum(MediaType, name="media_type", native_enum=True),
        nullable=False,
    )
    storage_key = Column(String, nullable=False)
    mime_type = Column(String(60), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(
        SAEnum(DeepfakeJobStatus, name="deepfake_job_status", native_enum=True),
        nullable=False,
        default=DeepfakeJobStatus.QUEUED,
        index=True,
    )
    frame_count = Column(Integer, nullable=True)
    idempotency_key = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_deepfake_job_idempotency"),
        CheckConstraint("file_size_bytes > 0 AND file_size_bytes <= 104857600", name="chk_deepfake_file_size"),
    )

    user = relationship("User", back_populates="deepfake_jobs")
    result = relationship("DeepfakeResult", back_populates="job", uselist=False, cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="deepfake_job")


class DeepfakeResult(Base):
    __tablename__ = "deepfake_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("deepfake_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    is_synthetic = Column(Boolean, nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    manipulation_type = Column(
        SAEnum(ManipulationType, name="manipulation_type", native_enum=True),
        nullable=False,
        default=ManipulationType.UNKNOWN,
    )
    per_frame_scores = Column(JSONB, nullable=True)
    heatmap_storage_key = Column(String, nullable=True)
    model_version = Column(String(40), nullable=False)
    inference_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("job_id", "model_version", name="uq_deepfake_result_job"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="chk_deepfake_confidence"),
    )

    job = relationship("DeepfakeJob", back_populates="result")


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    media_hash = Column(String(64), nullable=False, unique=True, index=True)
    phash = Column(BigInteger, nullable=True, index=True)
    media_type = Column(
        SAEnum(MediaType, name="media_type", native_enum=True),
        nullable=False,
    )
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    chain_network = Column(
        SAEnum(ChainNetwork, name="chain_network", native_enum=True),
        nullable=False,
        default=ChainNetwork.POLYGON_AMOY,
    )
    tx_hash = Column(String(66), nullable=True)
    block_number = Column(BigInteger, nullable=True)
    anchor_status = Column(
        SAEnum(AnchorStatus, name="anchor_status", native_enum=True),
        nullable=False,
        default=AnchorStatus.PENDING,
        index=True,
    )
    registered_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    creator = relationship("User", back_populates="provenance_records")
    tx_logs = relationship("BlockchainTxLog", back_populates="provenance_record", cascade="all, delete-orphan")


class ProvenanceVerification(Base):
    __tablename__ = "provenance_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_hash = Column(String(64), nullable=False, index=True)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    result = Column(
        SAEnum(VerificationResult, name="verification_result", native_enum=True),
        nullable=False,
    )
    matched_record_id = Column(UUID(as_uuid=True), ForeignKey("provenance_records.id"), nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    matched_record = relationship("ProvenanceRecord")


class BlockchainTxLog(Base):
    __tablename__ = "blockchain_tx_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provenance_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("provenance_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    signer_address = Column(String(42), nullable=False)
    chain_network = Column(
        SAEnum(ChainNetwork, name="chain_network", native_enum=True),
        nullable=False,
    )
    nonce = Column(BigInteger, nullable=False)
    tx_hash = Column(String(66), nullable=True)
    status = Column(
        SAEnum(AnchorStatus, name="anchor_status", native_enum=True),
        nullable=False,
        default=AnchorStatus.PENDING,
        index=True,
    )
    attempt = Column(Integer, nullable=False, default=1)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("signer_address", "chain_network", "nonce", name="uq_blockchain_tx_nonce"),
    )

    provenance_record = relationship("ProvenanceRecord", back_populates="tx_logs")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(
        SAEnum(IncidentSourceType, name="incident_source_type", native_enum=True),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    risk_score = Column(Numeric(5, 2), nullable=False)
    category = Column(String(60), nullable=False)
    evidence = Column(JSONB, nullable=False, default=dict)
    related_vishing_scan_id = Column(UUID(as_uuid=True), ForeignKey("vishing_scans.id"), nullable=True)
    related_deepfake_job_id = Column(UUID(as_uuid=True), ForeignKey("deepfake_jobs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="chk_incident_risk_score"),
        CheckConstraint(
            """(source_type = 'VISHING' AND related_vishing_scan_id IS NOT NULL AND related_deepfake_job_id IS NULL) OR
               (source_type = 'DEEPFAKE' AND related_deepfake_job_id IS NOT NULL AND related_vishing_scan_id IS NULL)""",
            name="chk_incident_source_exclusive",
        ),
    )

    user = relationship("User", back_populates="incidents")
    vishing_scan = relationship("VishingScan", back_populates="incidents")
    deepfake_job = relationship("DeepfakeJob", back_populates="incidents")
