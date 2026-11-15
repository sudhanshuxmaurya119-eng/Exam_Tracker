"""Examination schedule, shift, and admin seating inspection routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_write_admin
from app.core.database import get_db
from app.models.models import AdminUser, Dataset, Examination, SeatingRecord
from app.schemas.schemas import (
    ExaminationCreate,
    ExaminationResponse,
    ExaminationUpdate,
    PublicExaminationResponse,
    SeatingRecordAdminResponse,
)
from app.services.storage_service import storage_service

router = APIRouter(prefix="/examinations", tags=["Examinations"])


def _enrich_examination(db: Session, exam: Examination) -> ExaminationResponse:
    seated_count = (
        db.scalar(
            select(func.count(SeatingRecord.id)).where(SeatingRecord.examination_id == exam.id)
        )
        or 0
    )
    active_ds = db.scalar(
        select(Dataset)
        .where(Dataset.examination_id == exam.id, Dataset.is_active.is_(True))
        .order_by(Dataset.id.desc())
    )
    resp = ExaminationResponse.model_validate(exam)
    resp.total_seated_students = int(seated_count)
    if active_ds:
        resp.active_dataset_id = active_ds.id
        resp.active_dataset_filename = active_ds.original_filename
    return resp


@router.get(
    "/public",
    response_model=List[PublicExaminationResponse],
    summary="List published examinations for the public student portal",
)
def list_public_examinations(
    shift: Optional[str] = Query(None, max_length=100),
    db: Session = Depends(get_db),
) -> List[PublicExaminationResponse]:
    stmt = select(Examination).where(Examination.status == "published")
    if shift:
        stmt = stmt.where(func.lower(Examination.shift) == shift.strip().lower())
    stmt = stmt.order_by(Examination.exam_date.desc(), Examination.id.desc())
    exams = db.scalars(stmt).all()
    return [PublicExaminationResponse.model_validate(e) for e in exams]


@router.get(
    "",
    response_model=List[ExaminationResponse],
    summary="List all examinations (Admin only)",
)
def list_all_examinations(
    status_filter: Optional[str] = Query(None, alias="status"),
    shift: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> List[ExaminationResponse]:
    stmt = select(Examination)
    if status_filter:
        stmt = stmt.where(Examination.status == status_filter.strip().lower())
    if shift:
        stmt = stmt.where(func.lower(Examination.shift) == shift.strip().lower())
    stmt = stmt.order_by(Examination.exam_date.desc(), Examination.id.desc())
    exams = db.scalars(stmt).all()
    return [_enrich_examination(db, e) for e in exams]


@router.post(
    "",
    response_model=ExaminationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new examination session/shift (Admin only)",
)
def create_examination(
    payload: ExaminationCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_write_admin),
) -> ExaminationResponse:
    existing = db.scalar(
        select(Examination).where(func.upper(Examination.exam_code) == payload.exam_code.upper())
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An examination with code '{payload.exam_code}' already exists.",
        )

    exam = Examination(
        title=payload.title.strip(),
        exam_code=payload.exam_code.strip().upper(),
        subject_name=payload.subject_name.strip() if payload.subject_name else None,
        subject_code=payload.subject_code.strip().upper() if payload.subject_code else None,
        exam_date=payload.exam_date,
        shift=payload.shift.strip(),
        start_time=payload.start_time.strip() if payload.start_time else None,
        end_time=payload.end_time.strip() if payload.end_time else None,
        academic_session=payload.academic_session.strip() if payload.academic_session else None,
        semester=payload.semester.strip() if payload.semester else None,
        department=payload.department.strip() if payload.department else None,
        status=payload.status,
        instructions=payload.instructions.strip() if payload.instructions else None,
        created_by=current_admin.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _enrich_examination(db, exam)


@router.get(
    "/{examination_id}",
    response_model=ExaminationResponse,
    summary="Get examination details by ID (Admin only)",
)
def get_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> ExaminationResponse:
    exam = db.scalar(select(Examination).where(Examination.id == examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination with ID {examination_id} not found.",
        )
    return _enrich_examination(db, exam)


@router.put(
    "/{examination_id}",
    response_model=ExaminationResponse,
    summary="Update examination metadata or publication status (Admin only)",
)
def update_examination(
    examination_id: int,
    payload: ExaminationUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_write_admin),
) -> ExaminationResponse:
    exam = db.scalar(select(Examination).where(Examination.id == examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination with ID {examination_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "exam_code" in update_data and update_data["exam_code"]:
        new_code = update_data["exam_code"].strip().upper()
        conflict = db.scalar(
            select(Examination).where(
                func.upper(Examination.exam_code) == new_code,
                Examination.id != examination_id,
            )
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Examination code '{new_code}' is already in use.",
            )
        update_data["exam_code"] = new_code

    for field, value in update_data.items():
        setattr(exam, field, value)

    db.commit()
    db.refresh(exam)
    return _enrich_examination(db, exam)


@router.delete(
    "/{examination_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an examination, its datasets, and associated Supabase Storage objects (Admin only)",
)
def delete_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_write_admin),
) -> dict:
    exam = db.scalar(select(Examination).where(Examination.id == examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination with ID {examination_id} not found.",
        )

    datasets = db.scalars(select(Dataset).where(Dataset.examination_id == examination_id)).all()
    storage_paths: List[str] = []
    for ds in datasets:
        if ds.storage_path:
            storage_paths.append(ds.storage_path)
        if ds.processing_storage_path:
            storage_paths.append(ds.processing_storage_path)

    exam_title = exam.title
    db.delete(exam)
    db.commit()

    if storage_paths:
        storage_service.delete_files(storage_paths)

    return {
        "deleted": True,
        "examination_id": examination_id,
        "title": exam_title,
        "deleted_storage_objects": len(storage_paths),
    }


@router.get(
    "/{examination_id}/seating",
    response_model=List[SeatingRecordAdminResponse],
    summary="Inspect seating records for a specific examination (Admin only, paginated)",
)
def list_examination_seating_records(
    examination_id: int,
    query: Optional[str] = Query(None, max_length=100, description="Filter by roll_number, student_name, or room_number"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> List[SeatingRecordAdminResponse]:
    exam = db.scalar(select(Examination).where(Examination.id == examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination with ID {examination_id} not found.",
        )

    stmt = select(SeatingRecord).where(SeatingRecord.examination_id == examination_id)
    if query and query.strip():
        q = f"%{query.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(SeatingRecord.roll_number).like(q),
                func.lower(SeatingRecord.student_name).like(q),
                func.lower(SeatingRecord.room_number).like(q),
            )
        )
    stmt = stmt.order_by(SeatingRecord.room_number.asc(), SeatingRecord.seat_number.asc(), SeatingRecord.roll_number.asc())
    stmt = stmt.offset(offset).limit(limit)
    records = db.scalars(stmt).all()
    return [SeatingRecordAdminResponse.model_validate(r) for r in records]
