"""Initial production schema for Examination Seating Plan Portal

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-03 11:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_admin_users_username"),
        sa.UniqueConstraint("email", name="uq_admin_users_email"),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=False)
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=False)

    # 2. examinations
    op.create_table(
        "examinations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("exam_code", sa.String(length=100), nullable=False),
        sa.Column("subject_name", sa.String(length=255), nullable=True),
        sa.Column("subject_code", sa.String(length=100), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.String(length=50), nullable=True),
        sa.Column("end_time", sa.String(length=50), nullable=True),
        sa.Column("academic_session", sa.String(length=100), nullable=True),
        sa.Column("semester", sa.String(length=50), nullable=True),
        sa.Column("department", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_code", name="uq_examinations_exam_code"),
    )
    op.create_index("ix_examinations_exam_code", "examinations", ["exam_code"], unique=False)
    op.create_index("ix_examinations_exam_date", "examinations", ["exam_date"], unique=False)
    op.create_index("ix_examinations_status_date", "examinations", ["status", "exam_date"], unique=False)
    op.create_index("ix_examinations_shift", "examinations", ["shift"], unique=False)

    # 3. datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("examination_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False, server_default="seating-datasets"),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("processing_storage_path", sa.String(length=512), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_checksum", sa.String(length=64), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["examination_id"], ["examinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path", name="uq_datasets_storage_path"),
    )
    op.create_index("ix_datasets_examination_id", "datasets", ["examination_id"], unique=False)
    op.create_index("ix_datasets_examination_active", "datasets", ["examination_id", "is_active"], unique=False)

    # 4. students
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roll_number", sa.String(length=100), nullable=False),
        sa.Column("student_name", sa.String(length=255), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=150), nullable=True),
        sa.Column("branch", sa.String(length=150), nullable=True),
        sa.Column("semester", sa.String(length=50), nullable=True),
        sa.Column("section", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roll_number", name="uq_students_roll_number"),
    )
    op.create_index("ix_students_roll_number", "students", ["roll_number"], unique=False)
    op.create_index("ix_students_registration_number", "students", ["registration_number"], unique=False)

    # 5. seating_records
    op.create_table(
        "seating_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("examination_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("roll_number", sa.String(length=100), nullable=False),
        sa.Column("student_name", sa.String(length=255), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("department", sa.String(length=150), nullable=True),
        sa.Column("branch", sa.String(length=150), nullable=True),
        sa.Column("semester", sa.String(length=50), nullable=True),
        sa.Column("subject_code", sa.String(length=100), nullable=True),
        sa.Column("subject_name", sa.String(length=255), nullable=True),
        sa.Column("building_name", sa.String(length=150), nullable=True),
        sa.Column("floor_number", sa.String(length=50), nullable=True),
        sa.Column("room_number", sa.String(length=100), nullable=False),
        sa.Column("bench_number", sa.String(length=50), nullable=True),
        sa.Column("seat_number", sa.String(length=50), nullable=False),
        sa.Column("row_number", sa.String(length=50), nullable=True),
        sa.Column("column_number", sa.String(length=50), nullable=True),
        sa.Column("shift", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["examination_id"], ["examinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("examination_id", "roll_number", name="uq_seating_examination_roll_number"),
    )
    op.create_index(
        "ix_seating_examination_roll_number",
        "seating_records",
        ["examination_id", "roll_number"],
        unique=False,
    )
    op.create_index("ix_seating_records_roll_number", "seating_records", ["roll_number"], unique=False)
    op.create_index("ix_seating_records_dataset_id", "seating_records", ["dataset_id"], unique=False)
    op.create_index(
        "ix_seating_records_exam_room",
        "seating_records",
        ["examination_id", "room_number"],
        unique=False,
    )

    # 6. import_jobs
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_token", sa.String(length=64), nullable=False),
        sa.Column("examination_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("initiated_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("replace_existing", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_summary", sa.JSON(), nullable=True),
        sa.Column("staged_records", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["examination_id"], ["examinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_token", name="uq_import_jobs_job_token"),
    )
    op.create_index("ix_import_jobs_job_token", "import_jobs", ["job_token"], unique=False)
    op.create_index("ix_import_jobs_examination_id", "import_jobs", ["examination_id"], unique=False)
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("import_jobs")
    op.drop_table("seating_records")
    op.drop_table("students")
    op.drop_table("datasets")
    op.drop_table("examinations")
    op.drop_table("admin_users")
