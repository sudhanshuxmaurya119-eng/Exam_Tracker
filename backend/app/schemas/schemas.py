"""Pydantic v2 request and response validation schemas."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# =============================================================================
# Authentication & Administrator Schemas
# =============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100, description="Admin username or email")
    password: str = Field(..., min_length=6, max_length=128)


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["super_admin", "admin", "viewer"] = "admin"


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: str
    user: AdminUserResponse


# =============================================================================
# Examination Schemas
# =============================================================================

class ExaminationBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    exam_code: str = Field(..., min_length=2, max_length=100)
    subject_name: Optional[str] = Field(None, max_length=255)
    subject_code: Optional[str] = Field(None, max_length=100)
    exam_date: date
    shift: str = Field(..., min_length=2, max_length=100)
    start_time: Optional[str] = Field(None, max_length=50)
    end_time: Optional[str] = Field(None, max_length=50)
    academic_session: Optional[str] = Field(None, max_length=100)
    semester: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=150)
    status: Literal["draft", "published", "completed", "archived"] = "published"
    instructions: Optional[str] = Field(None, max_length=4000)

    @field_validator("exam_code")
    @classmethod
    def normalize_exam_code(cls, v: str) -> str:
        return v.strip().upper()


class ExaminationCreate(ExaminationBase):
    pass


class ExaminationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    exam_code: Optional[str] = Field(None, min_length=2, max_length=100)
    subject_name: Optional[str] = Field(None, max_length=255)
    subject_code: Optional[str] = Field(None, max_length=100)
    exam_date: Optional[date] = None
    shift: Optional[str] = Field(None, min_length=2, max_length=100)
    start_time: Optional[str] = Field(None, max_length=50)
    end_time: Optional[str] = Field(None, max_length=50)
    academic_session: Optional[str] = Field(None, max_length=100)
    semester: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=150)
    status: Optional[Literal["draft", "published", "completed", "archived"]] = None
    instructions: Optional[str] = Field(None, max_length=4000)

    @field_validator("exam_code")
    @classmethod
    def normalize_exam_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v is not None else None


class ExaminationResponse(ExaminationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by: Optional[int] = None
    total_seated_students: int = 0
    active_dataset_id: Optional[int] = None
    active_dataset_filename: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PublicExaminationResponse(BaseModel):
    """Public metadata for published examinations (no sensitive internal IDs)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    exam_code: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    exam_date: date
    shift: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    academic_session: Optional[str] = None
    semester: Optional[str] = None
    department: Optional[str] = None
    status: str


# =============================================================================
# Dataset & Supabase Storage Schemas
# =============================================================================

class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    examination_id: int
    examination_title: Optional[str] = None
    examination_code: Optional[str] = None
    original_filename: str
    storage_bucket: str
    storage_path: str
    processing_storage_path: Optional[str] = None
    file_size_bytes: int
    mime_type: str
    file_checksum: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    is_active: bool
    version: int
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SignedUrlResponse(BaseModel):
    dataset_id: int
    original_filename: str
    storage_bucket: str
    storage_path: str
    signed_url: str
    expires_in_seconds: int


# =============================================================================
# Excel Import Pipeline Schemas
# =============================================================================

class ImportRecordPreview(BaseModel):
    row_number: int
    roll_number: str
    student_name: str
    registration_number: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None
    room_number: str
    bench_number: Optional[str] = None
    seat_number: str
    grid_row: Optional[str] = None
    grid_column: Optional[str] = None
    shift: Optional[str] = None


class DuplicateRecordInfo(BaseModel):
    row_number: int
    roll_number: str
    student_name: Optional[str] = None
    first_seen_row: Optional[int] = None
    source: Literal["within_excel", "existing_database", "seat_collision"]
    reason: str


class InvalidRecordInfo(BaseModel):
    row_number: int
    raw_roll_number: Optional[str] = None
    raw_student_name: Optional[str] = None
    errors: List[str]


class ImportPreviewResponse(BaseModel):
    job_token: str
    job_id: int
    dataset_id: int
    examination_id: int
    examination_title: str
    examination_code: str
    original_filename: str
    storage_path: str
    replace_existing: bool
    existing_records_count: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    detected_columns: Dict[str, str]
    preview_records: List[ImportRecordPreview]
    duplicates: List[DuplicateRecordInfo]
    invalid_records: List[InvalidRecordInfo]
    can_confirm: bool
    status: str
    warnings: List[str] = []


class ImportConfirmRequest(BaseModel):
    skip_invalid_and_duplicates: bool = True


class ImportConfirmResponse(BaseModel):
    job_token: str
    job_id: int
    dataset_id: int
    examination_id: int
    status: str
    inserted_rows: int
    replaced_previous_rows: int
    completed_at: datetime
    message: str


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_token: str
    examination_id: int
    examination_title: Optional[str] = None
    examination_code: Optional[str] = None
    dataset_id: Optional[int] = None
    original_filename: Optional[str] = None
    initiated_by: Optional[int] = None
    status: str
    replace_existing: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    inserted_rows: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Student Search & Seating Record Schemas
# =============================================================================

class StudentSeatingAllocation(BaseModel):
    seating_id: int
    examination_id: int
    examination_title: str
    exam_code: str
    exam_date: date
    shift: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    academic_session: Optional[str] = None
    roll_number: str
    student_name: str
    registration_number: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None
    room_number: str
    bench_number: Optional[str] = None
    seat_number: str
    row_number: Optional[str] = None
    column_number: Optional[str] = None
    instructions: Optional[str] = None


class StudentSearchResponse(BaseModel):
    query_roll_number: str
    student_name: Optional[str] = None
    department: Optional[str] = None
    total_allocations: int
    allocations: List[StudentSeatingAllocation]


class SeatingRecordAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    examination_id: int
    dataset_id: int
    roll_number: str
    student_name: str
    registration_number: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[str] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    building_name: Optional[str] = None
    floor_number: Optional[str] = None
    room_number: str
    bench_number: Optional[str] = None
    seat_number: str
    row_number: Optional[str] = None
    column_number: Optional[str] = None
    shift: Optional[str] = None
    created_at: datetime


# =============================================================================
# System Health, Maintenance & Dashboard Schemas
# =============================================================================

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    database: Dict[str, Any]
    storage: Dict[str, Any]


class DashboardStatsResponse(BaseModel):
    total_examinations: int
    published_examinations: int
    active_datasets: int
    total_datasets: int
    total_seating_records: int
    total_unique_students: int
    recent_imports: List[ImportJobResponse]
