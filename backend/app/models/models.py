"""SQLAlchemy 2.0 production database models for the Examination Seating Plan Portal."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Standard created_at and updated_at timestamps for all production tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )


class AdminUser(Base, TimestampMixin):
    """Table 1: admin_users - Administrators and Examination Controllers."""

    __tablename__ = "admin_users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_admin_users_username"),
        UniqueConstraint("email", name="uq_admin_users_email"),
        Index("ix_admin_users_username", "username"),
        Index("ix_admin_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    created_examinations: Mapped[List["Examination"]] = relationship(
        "Examination",
        back_populates="creator",
        passive_deletes=True,
    )
    uploaded_datasets: Mapped[List["Dataset"]] = relationship(
        "Dataset",
        back_populates="uploader",
        passive_deletes=True,
    )
    import_jobs: Mapped[List["ImportJob"]] = relationship(
        "ImportJob",
        back_populates="initiator",
        passive_deletes=True,
    )


class Examination(Base, TimestampMixin):
    """Table 2: examinations - Scheduled examination sessions and shifts."""

    __tablename__ = "examinations"
    __table_args__ = (
        UniqueConstraint("exam_code", name="uq_examinations_exam_code"),
        Index("ix_examinations_exam_code", "exam_code"),
        Index("ix_examinations_exam_date", "exam_date"),
        Index("ix_examinations_status_date", "status", "exam_date"),
        Index("ix_examinations_shift", "shift"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_code: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    academic_session: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    creator: Mapped[Optional["AdminUser"]] = relationship("AdminUser", back_populates="created_examinations")
    datasets: Mapped[List["Dataset"]] = relationship(
        "Dataset",
        back_populates="examination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    seating_records: Mapped[List["SeatingRecord"]] = relationship(
        "SeatingRecord",
        back_populates="examination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    import_jobs: Mapped[List["ImportJob"]] = relationship(
        "ImportJob",
        back_populates="examination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Dataset(Base, TimestampMixin):
    """Table 3: datasets - Metadata for Excel files stored in Supabase Storage."""

    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("storage_path", name="uq_datasets_storage_path"),
        Index("ix_datasets_examination_id", "examination_id"),
        Index("ix_datasets_examination_active", "examination_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    examination_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False, default="seating-datasets")
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    processing_storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    examination: Mapped["Examination"] = relationship("Examination", back_populates="datasets")
    uploader: Mapped[Optional["AdminUser"]] = relationship("AdminUser", back_populates="uploaded_datasets")
    seating_records: Mapped[List["SeatingRecord"]] = relationship(
        "SeatingRecord",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    import_jobs: Mapped[List["ImportJob"]] = relationship("ImportJob", back_populates="dataset")


class Student(Base, TimestampMixin):
    """Table 4: students - Shared student profile records across multiple examinations."""

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("roll_number", name="uq_students_roll_number"),
        Index("ix_students_roll_number", "roll_number"),
        Index("ix_students_registration_number", "registration_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(String(100), nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    seating_records: Mapped[List["SeatingRecord"]] = relationship(
        "SeatingRecord",
        back_populates="student",
    )


class SeatingRecord(Base, TimestampMixin):
    """Table 5: seating_records - Student seating allocations per examination.

    CRITICAL DATABASE RULE:
    A student can have different seating arrangements in different examinations.
    Therefore, roll_number is NOT globally unique in seating_records.
    Enforces UNIQUE(examination_id, roll_number) and index on (examination_id, roll_number).
    """

    __tablename__ = "seating_records"
    __table_args__ = (
        UniqueConstraint("examination_id", "roll_number", name="uq_seating_examination_roll_number"),
        Index("ix_seating_examination_roll_number", "examination_id", "roll_number"),
        Index("ix_seating_records_roll_number", "roll_number"),
        Index("ix_seating_records_dataset_id", "dataset_id"),
        Index("ix_seating_records_exam_room", "examination_id", "room_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    examination_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
    )
    roll_number: Mapped[str] = mapped_column(String(100), nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subject_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subject_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    building_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    floor_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    room_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bench_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seat_number: Mapped[str] = mapped_column(String(50), nullable=False)
    row_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    column_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    shift: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    examination: Mapped["Examination"] = relationship("Examination", back_populates="seating_records")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="seating_records")
    student: Mapped[Optional["Student"]] = relationship("Student", back_populates="seating_records")


class ImportJob(Base, TimestampMixin):
    """Table 6: import_jobs - Audit log and staging state for Excel dataset imports."""

    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("job_token", name="uq_import_jobs_job_token"),
        Index("ix_import_jobs_job_token", "job_token"),
        Index("ix_import_jobs_examination_id", "examination_id"),
        Index("ix_import_jobs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_token: Mapped[str] = mapped_column(String(64), nullable=False)
    examination_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiated_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    replace_existing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    staged_records: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    examination: Mapped["Examination"] = relationship("Examination", back_populates="import_jobs")
    dataset: Mapped[Optional["Dataset"]] = relationship("Dataset", back_populates="import_jobs")
    initiator: Mapped[Optional["AdminUser"]] = relationship("AdminUser", back_populates="import_jobs")
