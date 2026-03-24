"""Initial schema migration."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # config_versions
    op.create_table(
        "config_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("nbfc_config", sa.Text(), nullable=True),
        sa.Column("comm_sequence", sa.Text(), nullable=True),
        sa.Column("retry_config", sa.Text(), nullable=True),
        sa.Column("journey_config", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("published_by", sa.String(100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["previous_version_id"],
            ["config_versions.id"],
        ),
    )

    # batches
    op.create_table(
        "batches",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("valid_rows", sa.Integer(), nullable=True),
        sa.Column("invalid_rows", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("error_file_url", sa.Text(), nullable=True),
        sa.Column("config_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["config_version_id"], ["config_versions.id"]),
    )

    # leads
    op.create_table(
        "leads",
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_ref", sa.String(255), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phone_e164", sa.String(20), nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("email_hash", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("winning_nbfc_id", sa.String(50), nullable=True),
        sa.Column("config_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dnd", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.batch_id"]),
        sa.ForeignKeyConstraint(["config_version_id"], ["config_versions.id"]),
    )
    op.create_index("ix_leads_external_ref", "leads", ["external_ref"])
    op.create_index("ix_leads_phone_hash", "leads", ["phone_hash"])
    op.create_index("ix_leads_email_hash", "leads", ["email_hash"])
    op.create_index("ix_leads_batch_id", "leads", ["batch_id"])

    # dedupe_logs
    op.create_table(
        "dedupe_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nbfc_id", sa.String(50), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("raw_response_ref", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
    )
    op.create_index("ix_dedupe_logs_lead_id", "dedupe_logs", ["lead_id"])
    op.create_index("ix_dedupe_logs_timestamp", "dedupe_logs", ["timestamp"])

    # journey_instances
    op.create_table(
        "journey_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("definition_version", sa.String(50), nullable=False),
        sa.Column("state", sa.String(30), nullable=False, server_default="started"),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
    )
    op.create_index("ix_journey_instances_lead_id", "journey_instances", ["lead_id"])
    op.create_index(
        "ix_journey_instances_next_action_at", "journey_instances", ["next_action_at"]
    )

    # communication_logs
    op.create_table(
        "communication_logs",
        sa.Column("comm_send_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_instance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("partner", sa.String(50), nullable=False),
        sa.Column("partner_message_id", sa.String(200), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="requested"),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.ForeignKeyConstraint(
            ["journey_instance_id"], ["journey_instances.id"]
        ),
    )
    op.create_index("ix_comm_logs_lead_id", "communication_logs", ["lead_id"])
    op.create_index(
        "ix_comm_logs_journey_instance_id", "communication_logs", ["journey_instance_id"]
    )
    op.create_index(
        "ix_comm_logs_partner_message_id", "communication_logs", ["partner_message_id"]
    )

    # event_logs
    op.create_table(
        "event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("comm_send_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("partner", sa.String(50), nullable=True),
        sa.Column("partner_message_id", sa.String(200), nullable=True),
        sa.Column("idempotency_key", sa.String(300), nullable=False, unique=True),
        sa.Column("payload_ref", sa.Text(), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["comm_send_id"], ["communication_logs.comm_send_id"]
        ),
    )
    op.create_index("ix_event_logs_comm_send_id", "event_logs", ["comm_send_id"])
    op.create_index("ix_event_logs_event_type", "event_logs", ["event_type"])
    op.create_index("ix_event_logs_lead_id", "event_logs", ["lead_id"])
    op.create_index("ix_event_logs_batch_id", "event_logs", ["batch_id"])
    op.create_index("ix_event_logs_timestamp", "event_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("event_logs")
    op.drop_table("communication_logs")
    op.drop_table("journey_instances")
    op.drop_table("dedupe_logs")
    op.drop_table("leads")
    op.drop_table("batches")
    op.drop_table("config_versions")
