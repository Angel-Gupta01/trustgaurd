"""initial_canonical_schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-01 14:48:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Read and apply .ai/SCHEMA.sql or execute raw DDL
    with open("../../.ai/SCHEMA.sql", "r", encoding="utf-8") as f:
        ddl_script = f.read()
    
    # Execute full DDL script directly in migration
    op.execute(ddl_script)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS incidents CASCADE;")
    op.execute("DROP TABLE IF EXISTS blockchain_tx_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS provenance_verifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS provenance_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS deepfake_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS deepfake_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS vishing_scans CASCADE;")
    op.execute("DROP TABLE IF EXISTS keyword_clusters CASCADE;")
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")

    op.execute("DROP TYPE IF EXISTS verification_result;")
    op.execute("DROP TYPE IF EXISTS anchor_status;")
    op.execute("DROP TYPE IF EXISTS chain_network;")
    op.execute("DROP TYPE IF EXISTS manipulation_type;")
    op.execute("DROP TYPE IF EXISTS deepfake_job_status;")
    op.execute("DROP TYPE IF EXISTS media_type;")
    op.execute("DROP TYPE IF EXISTS incident_source_type;")
    op.execute("DROP TYPE IF EXISTS vishing_category;")
    op.execute("DROP TYPE IF EXISTS vishing_source_type;")
    op.execute("DROP TYPE IF EXISTS user_role;")
