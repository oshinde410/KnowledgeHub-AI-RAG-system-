"""jobs and logs

Revision ID: a4f7c1b2d9e0
Revises: 843fa66d4d09
Create Date: 2026-06-19 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f7c1b2d9e0"
down_revision: Union[str, Sequence[str], None] = "843fa66d4d09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_processing_jobs_document", "processing_jobs", ["document_id"])
    op.create_index("idx_processing_jobs_status", "processing_jobs", ["status"])
    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("retrieval_latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_retrieval_logs_message", "retrieval_logs", ["message_id"])
    op.create_table(
        "ai_response_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("generation_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_response_logs_message", "ai_response_logs", ["message_id"])


def downgrade() -> None:
    op.drop_index("idx_ai_response_logs_message", table_name="ai_response_logs")
    op.drop_table("ai_response_logs")
    op.drop_index("idx_retrieval_logs_message", table_name="retrieval_logs")
    op.drop_table("retrieval_logs")
    op.drop_index("idx_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("idx_processing_jobs_document", table_name="processing_jobs")
    op.drop_table("processing_jobs")
