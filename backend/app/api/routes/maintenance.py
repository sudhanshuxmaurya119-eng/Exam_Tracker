"""Database maintenance, dashboard statistics, and backup manifest routes."""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_super_admin
from app.core.database import get_db, verify_database_connection
from app.models.models import (
    AdminUser,
    Dataset,
    Examination,
    ImportJob,
    SeatingRecord,
    Student,
)
from app.schemas.schemas import DashboardStatsResponse, ImportJobResponse
from app.services.storage_service import storage_service

router = APIRouter(prefix="/maintenance", tags=["Database Maintenance & Monitoring"])


@router.get(
    "/dashboard",
    response_model=DashboardStatsResponse,
    summary="Get administrator dashboard metrics and recent import jobs (Admin only)",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> DashboardStatsResponse:
    total_exams = db.scalar(select(func.count(Examination.id))) or 0
    published_exams = (
        db.scalar(
            select(func.count(Examination.id)).where(Examination.status == "published")
        )
        or 0
    )
    active_datasets = (
        db.scalar(select(func.count(Dataset.id)).where(Dataset.is_active.is_(True)))
        or 0
    )
    total_datasets = db.scalar(select(func.count(Dataset.id))) or 0
    total_seating = db.scalar(select(func.count(SeatingRecord.id))) or 0
    total_students = db.scalar(select(func.count(Student.id))) or 0

    recent_jobs = db.scalars(
        select(ImportJob).order_by(ImportJob.id.desc()).limit(10)
    ).all()

    recent_imports = []
    for job in recent_jobs:
        resp = ImportJobResponse.model_validate(job)
        if job.examination:
            resp.examination_title = job.examination.title
            resp.examination_code = job.examination.exam_code
        if job.dataset:
            resp.original_filename = job.dataset.original_filename
        recent_imports.append(resp)

    return DashboardStatsResponse(
        total_examinations=int(total_exams),
        published_examinations=int(published_exams),
        active_datasets=int(active_datasets),
        total_datasets=int(total_datasets),
        total_seating_records=int(total_seating),
        total_unique_students=int(total_students),
        recent_imports=recent_imports,
    )


@router.get(
    "/backup-manifest",
    summary="Generate a database and storage metadata backup verification manifest (Admin only)",
)
def generate_backup_manifest(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Dict[str, Any]:
    db_health = verify_database_connection()
    storage_health = storage_service.get_storage_health()

    examinations = db.scalars(select(Examination).order_by(Examination.id.asc())).all()
    datasets = db.scalars(select(Dataset).order_by(Dataset.id.asc())).all()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_health": db_health,
        "storage_health": storage_health,
        "table_counts": {
            "admin_users": int(db.scalar(select(func.count(AdminUser.id))) or 0),
            "examinations": len(examinations),
            "datasets": len(datasets),
            "students": int(db.scalar(select(func.count(Student.id))) or 0),
            "seating_records": int(db.scalar(select(func.count(SeatingRecord.id))) or 0),
            "import_jobs": int(db.scalar(select(func.count(ImportJob.id))) or 0),
        },
        "examinations": [
            {
                "id": e.id,
                "exam_code": e.exam_code,
                "title": e.title,
                "exam_date": e.exam_date.isoformat(),
                "shift": e.shift,
                "status": e.status,
            }
            for e in examinations
        ],
        "datasets": [
            {
                "id": d.id,
                "examination_id": d.examination_id,
                "original_filename": d.original_filename,
                "storage_bucket": d.storage_bucket,
                "storage_path": d.storage_path,
                "file_checksum": d.file_checksum,
                "file_size_bytes": d.file_size_bytes,
                "valid_rows": d.valid_rows,
                "is_active": d.is_active,
                "version": d.version,
            }
            for d in datasets
        ],
    }
