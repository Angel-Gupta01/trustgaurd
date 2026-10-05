-- =====================================================================
-- TrustGuard Canonical Schema
-- PostgreSQL 16  (no PostGIS needed -- no geospatial data in this domain)
-- Generated artifact: produced by scripts/dump_schema.sh from the head
-- of migrations/versions/. Do NOT hand-edit this file or .ai/SCHEMA.sql.
-- =====================================================================
 
-- gen_random_uuid() is built into PostgreSQL core since v13; no
-- extension is required.
 
-- ---------------------------------------------------------------------
-- ENUM TYPES  (mirror exactly in Pydantic + TypeScript, see §§3.3/3.4)
-- ---------------------------------------------------------------------
CREATE TYPE user_role AS ENUM ('USER', 'CREATOR', 'ADMIN');
CREATE TYPE vishing_source_type AS ENUM (
    'PASTED_TEXT', 'LIVE_PAGE_SCAN', 'UPLOADED_TRANSCRIPT'
);
CREATE TYPE vishing_category AS ENUM (
    'URGENCY_PRESSURE', 'CREDENTIAL_REQUEST', 'FINANCIAL_LURE',
    'AUTHORITY_IMPERSONATION', 'THREAT_OF_LOSS', 'LINK_BAIT'
);
CREATE TYPE incident_source_type AS ENUM ('VISHING', 'DEEPFAKE');
CREATE TYPE media_type AS ENUM ('IMAGE', 'VIDEO');
CREATE TYPE deepfake_job_status AS ENUM (
    'QUEUED', 'EXTRACTING_FRAMES', 'ANALYZING', 'DONE', 'FAILED'
);
CREATE TYPE manipulation_type AS ENUM (
    'FACE_SWAP', 'FACE_REENACTMENT', 'FULL_SYNTHESIS',
    'AUDIO_SYNC_MISMATCH', 'NONE', 'UNKNOWN'
);
CREATE TYPE chain_network AS ENUM ('POLYGON_AMOY', 'LOCAL_DEV');
CREATE TYPE anchor_status AS ENUM (
    'PENDING', 'SUBMITTED', 'CONFIRMED', 'FAILED'
);
CREATE TYPE verification_result AS ENUM (
    'EXACT_MATCH', 'NEAR_MATCH_TAMPERED', 'NO_MATCH'
);
 
-- ---------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    display_name    VARCHAR(120) NOT NULL,
    role            user_role NOT NULL DEFAULT 'USER',
    password_hash   TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_email UNIQUE (email)
);
CREATE INDEX idx_users_role ON users (role);
 
-- ---------------------------------------------------------------------
-- refresh_tokens  (JWT rotation & revocation; raw token never stored)
-- ---------------------------------------------------------------------
CREATE TABLE refresh_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT NOT NULL,
    issued_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ,
    replaced_by  UUID REFERENCES refresh_tokens(id),
    CONSTRAINT uq_refresh_token_hash UNIQUE (token_hash)
);
CREATE INDEX idx_refresh_tokens_user
    ON refresh_tokens (user_id) WHERE revoked_at IS NULL;
 
-- ---------------------------------------------------------------------
-- keyword_clusters  (admin-editable vishing rule layer -- updating a
-- scam pattern must not require a redeploy)
-- ---------------------------------------------------------------------
CREATE TABLE keyword_clusters (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category    vishing_category NOT NULL,
    phrase      TEXT NOT NULL,
    weight      NUMERIC(4,2) NOT NULL CHECK (weight BETWEEN 0 AND 1),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_keyword_cluster_phrase UNIQUE (category, phrase)
);
CREATE INDEX idx_keyword_clusters_active
    ON keyword_clusters (category) WHERE is_active = TRUE;
 
-- ---------------------------------------------------------------------
-- vishing_scans  (anonymous-friendly: user_id is nullable by design --
-- scanning should not require login; see §6.2 privacy rationale)
-- ---------------------------------------------------------------------
CREATE TABLE vishing_scans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id),
    source_type         vishing_source_type NOT NULL,
    text_snippet        TEXT NOT NULL CHECK (char_length(text_snippet) <= 4000),
    matched_categories  vishing_category[] NOT NULL DEFAULT '{}',
    rule_score          NUMERIC(5,2) NOT NULL
        CHECK (rule_score BETWEEN 0 AND 100),
    ml_score            NUMERIC(5,2) CHECK (ml_score BETWEEN 0 AND 100),
    risk_score          NUMERIC(5,2) NOT NULL
        CHECK (risk_score BETWEEN 0 AND 100),
    is_critical         BOOLEAN NOT NULL DEFAULT FALSE,
    model_version       VARCHAR(40),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- text_snippet is stored AFTER redaction of digit runs length >= 6
-- (card/account/OTP numbers) by the API layer before INSERT -- see
-- .ai/CONVENTIONS.md PII rule. This table IS the fraud registry.
CREATE INDEX idx_vishing_scans_user ON vishing_scans (user_id);
CREATE INDEX idx_vishing_scans_critical
    ON vishing_scans (created_at DESC) WHERE is_critical = TRUE;
 
-- ---------------------------------------------------------------------
-- deepfake_jobs  (auth required -- heavier compute, needs identity for
-- rate limiting; contrast with anonymous-friendly vishing_scans above)
-- ---------------------------------------------------------------------
CREATE TABLE deepfake_jobs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id),
    media_type        media_type NOT NULL,
    storage_key       TEXT NOT NULL,
    mime_type         VARCHAR(60) NOT NULL,
    file_size_bytes   INTEGER NOT NULL
        CHECK (file_size_bytes > 0 AND file_size_bytes <= 104857600),
    status            deepfake_job_status NOT NULL DEFAULT 'QUEUED',
    frame_count       INTEGER,
    idempotency_key   VARCHAR(64) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    CONSTRAINT uq_deepfake_job_idempotency UNIQUE (user_id, idempotency_key)
);
-- 100MB cap covers short vertical-video clips typical of social feeds;
-- longer submissions are rejected client-side before upload (§6.1).
CREATE INDEX idx_deepfake_jobs_user ON deepfake_jobs (user_id);
CREATE INDEX idx_deepfake_jobs_status ON deepfake_jobs (status)
    WHERE status IN ('QUEUED', 'EXTRACTING_FRAMES', 'ANALYZING');
 
-- ---------------------------------------------------------------------
-- deepfake_results
-- ---------------------------------------------------------------------
CREATE TABLE deepfake_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID NOT NULL
        REFERENCES deepfake_jobs(id) ON DELETE CASCADE,
    is_synthetic        BOOLEAN NOT NULL,
    confidence          NUMERIC(5,2) NOT NULL
        CHECK (confidence BETWEEN 0 AND 100),
    manipulation_type   manipulation_type NOT NULL DEFAULT 'UNKNOWN',
    per_frame_scores    JSONB,
    heatmap_storage_key TEXT,
    model_version       VARCHAR(40) NOT NULL,
    inference_ms        INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_deepfake_result_job UNIQUE (job_id, model_version)
);
CREATE INDEX idx_deepfake_results_job ON deepfake_results (job_id);
 
-- ---------------------------------------------------------------------
-- provenance_records  (media_hash IS unique here -- unlike a FasalRakshak-
-- style evidence table, registering the same original twice must be
-- rejected/idempotent, not flagged as a fraud signal)
-- ---------------------------------------------------------------------
CREATE TABLE provenance_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id      UUID NOT NULL REFERENCES users(id),
    media_hash      CHAR(64) NOT NULL,
    phash           BIGINT,
    media_type      media_type NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    chain_network   chain_network NOT NULL DEFAULT 'POLYGON_AMOY',
    tx_hash         VARCHAR(66),
    block_number    BIGINT,
    anchor_status   anchor_status NOT NULL DEFAULT 'PENDING',
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_provenance_media_hash UNIQUE (media_hash)
);
CREATE INDEX idx_provenance_creator ON provenance_records (creator_id);
CREATE INDEX idx_provenance_phash ON provenance_records (phash);
CREATE INDEX idx_provenance_pending ON provenance_records (registered_at)
    WHERE anchor_status IN ('PENDING', 'SUBMITTED');
-- NOTE: near-duplicate (tampered-copy) lookup via phash Hamming distance
-- is done in application code over a bounded candidate set for MVP --
-- see §6.1 for the scaling caveat on this approach.
 
-- ---------------------------------------------------------------------
-- provenance_verifications  (lookup log, also abuse-monitoring surface)
-- ---------------------------------------------------------------------
CREATE TABLE provenance_verifications (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_hash         CHAR(64) NOT NULL,
    requester_id       UUID REFERENCES users(id),
    result             verification_result NOT NULL,
    matched_record_id  UUID REFERENCES provenance_records(id),
    checked_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_provenance_verifications_hash
    ON provenance_verifications (media_hash, checked_at DESC);
 
-- ---------------------------------------------------------------------
-- blockchain_tx_log  (nonce ledger -- backs the nonce-allocation
-- manager worker; see §6.1 concurrency discussion)
-- ---------------------------------------------------------------------
CREATE TABLE blockchain_tx_log (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provenance_record_id  UUID NOT NULL
        REFERENCES provenance_records(id) ON DELETE CASCADE,
    signer_address        VARCHAR(42) NOT NULL,
    chain_network         chain_network NOT NULL,
    nonce                 BIGINT NOT NULL,
    tx_hash               VARCHAR(66),
    status                anchor_status NOT NULL DEFAULT 'PENDING',
    attempt               INTEGER NOT NULL DEFAULT 1,
    submitted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at          TIMESTAMPTZ,
    CONSTRAINT uq_blockchain_tx_nonce
        UNIQUE (signer_address, chain_network, nonce)
);
-- The UNIQUE(signer_address, chain_network, nonce) constraint is the
-- actual concurrency-control mechanism: two workers racing to anchor
-- two different records can never commit the same nonce twice.
CREATE INDEX idx_blockchain_tx_pending ON blockchain_tx_log (status)
    WHERE status IN ('PENDING', 'SUBMITTED');
 
-- ---------------------------------------------------------------------
-- incidents  (unified RiskSignal log -- the one table the dashboard and
-- the extension both read, regardless of which module raised the alert)
-- ---------------------------------------------------------------------
CREATE TABLE incidents (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type               incident_source_type NOT NULL,
    user_id                   UUID REFERENCES users(id),
    risk_score                NUMERIC(5,2) NOT NULL
        CHECK (risk_score BETWEEN 0 AND 100),
    category                  VARCHAR(60) NOT NULL,
    evidence                  JSONB NOT NULL DEFAULT '{}',
    related_vishing_scan_id   UUID REFERENCES vishing_scans(id),
    related_deepfake_job_id   UUID REFERENCES deepfake_jobs(id),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_incident_source_exclusive CHECK (
        (source_type = 'VISHING' AND related_vishing_scan_id IS NOT NULL
            AND related_deepfake_job_id IS NULL)
        OR
        (source_type = 'DEEPFAKE' AND related_deepfake_job_id IS NOT NULL
            AND related_vishing_scan_id IS NULL)
    )
);
CREATE INDEX idx_incidents_user ON incidents (user_id, created_at DESC);
CREATE INDEX idx_incidents_source ON incidents (source_type, created_at DESC);
 
-- ---------------------------------------------------------------------
-- updated_at auto-touch trigger
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
CREATE TRIGGER trg_users_touch BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
