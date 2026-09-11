"""Initial persistent orchestration schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

role = sa.Enum("viewer", "operator", "admin", name="role")
mission_status = sa.Enum(
    "draft", "queued", "running", "waiting_approval", "completed", "failed", "rejected",
    name="missionstatus",
)
step_status = sa.Enum(
    "pending", "running", "waiting_approval", "completed", "failed", "rejected",
    name="stepstatus",
)
approval_status = sa.Enum("pending", "approved", "rejected", name="approvalstatus")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "missions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", mission_status, nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_missions_status", "missions", ["status"])
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column("risk", sa.String(20), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("status", step_status, nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("mission_id", "key", name="uq_step_mission_key"),
    )
    op.create_index("ix_workflow_steps_mission_id", "workflow_steps", ["mission_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(36), sa.ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", approval_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("step_id"),
    )
    op.create_index("ix_approvals_mission_id", "approvals", ["mission_id"])
    op.create_table(
        "handoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_step_id", sa.String(36), sa.ForeignKey("workflow_steps.id"), nullable=False),
        sa.Column("to_step_id", sa.String(36), sa.ForeignKey("workflow_steps.id"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_handoffs_mission_id", "handoffs", ["mission_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])


def downgrade() -> None:
    for table in ("audit_events", "handoffs", "approvals", "workflow_steps", "documents", "missions", "agents", "users"):
        op.drop_table(table)
    approval_status.drop(op.get_bind(), checkfirst=True)
    step_status.drop(op.get_bind(), checkfirst=True)
    mission_status.drop(op.get_bind(), checkfirst=True)
    role.drop(op.get_bind(), checkfirst=True)
