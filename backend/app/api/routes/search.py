"""Public student roll-number seating search and PDF seating slip generation routes."""

import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit_dependency
from app.models.models import Examination, SeatingRecord
from app.schemas.schemas import StudentSearchResponse, StudentSeatingAllocation
from app.services.pdf_service import generate_student_seating_slip_pdf

router = APIRouter(prefix="/search", tags=["Student Seating Search"])
settings = get_settings()

search_rate_limiter = rate_limit_dependency(
    bucket="student_search",
    max_requests=settings.RATE_LIMIT_SEARCH_PER_MINUTE,
    window_seconds=60,
)

SAFE_ROLL_REGEX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_-]{1,63}$")


def _validate_and_normalize_roll(roll_number: str) -> str:
    normalized = (roll_number or "").strip().upper()
    if not normalized or not SAFE_ROLL_REGEX.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid alphanumeric Roll Number (wildcards and special characters are not permitted).",
        )
    return normalized


def _query_student_allocations(
    db: Session,
    normalized_roll: str,
    examination_id: Optional[int] = None,
    shift: Optional[str] = None,
) -> List[StudentSeatingAllocation]:
    stmt = (
        select(SeatingRecord, Examination)
        .join(Examination, SeatingRecord.examination_id == Examination.id)
        .where(
            SeatingRecord.roll_number == normalized_roll,
            Examination.status == "published",
        )
    )
    if examination_id is not None:
        stmt = stmt.where(SeatingRecord.examination_id == examination_id)
    if shift and shift.strip():
        stmt = stmt.where(func.lower(Examination.shift) == shift.strip().lower())

    stmt = stmt.order_by(Examination.exam_date.asc(), Examination.id.asc())
    rows = db.execute(stmt).all()

    allocations: List[StudentSeatingAllocation] = []
    for seating, exam in rows:
        allocations.append(
            StudentSeatingAllocation(
                seating_id=seating.id,
                examination_id=exam.id,
                examination_title=exam.title,
                exam_code=exam.exam_code,
                exam_date=exam.exam_date,
                shift=seating.shift or exam.shift,
                start_time=exam.start_time,
                end_time=exam.end_time,
                academic_session=exam.academic_session,
                roll_number=seating.roll_number,
                student_name=seating.student_name,
                registration_number=seating.registration_number,
                department=seating.department or exam.department,
                branch=seating.branch,
                semester=seating.semester or exam.semester,
                subject_code=seating.subject_code or exam.subject_code,
                subject_name=seating.subject_name or exam.subject_name,
                building_name=seating.building_name,
                floor_number=seating.floor_number,
                room_number=seating.room_number,
                bench_number=seating.bench_number,
                seat_number=seating.seat_number,
                row_number=seating.row_number,
                column_number=seating.column_number,
                instructions=exam.instructions,
            )
        )
    return allocations


@router.get(
    "/student",
    response_model=StudentSearchResponse,
    dependencies=[Depends(search_rate_limiter)],
    summary="Search seating arrangement(s) for a specific student Roll Number",
)
def search_student_seating(
    roll_number: str = Query(..., min_length=2, max_length=64, description="Exact student roll number"),
    examination_id: Optional[int] = Query(None, description="Optional examination ID filter"),
    shift: Optional[str] = Query(None, max_length=100, description="Optional examination shift filter"),
    db: Session = Depends(get_db),
) -> StudentSearchResponse:
    normalized_roll = _validate_and_normalize_roll(roll_number)
    allocations = _query_student_allocations(
        db=db,
        normalized_roll=normalized_roll,
        examination_id=examination_id,
        shift=shift,
    )
    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published seating arrangement found for Roll Number '{normalized_roll}'.",
        )

    first = allocations[0]
    return StudentSearchResponse(
        query_roll_number=normalized_roll,
        student_name=first.student_name,
        department=first.department,
        total_allocations=len(allocations),
        allocations=allocations,
    )


@router.get(
    "/seating-slip/pdf",
    dependencies=[Depends(search_rate_limiter)],
    summary="Generate and download official PDF Seating Slip for a student Roll Number",
)
def download_student_seating_slip_pdf(
    roll_number: str = Query(..., min_length=2, max_length=64, description="Exact student roll number"),
    examination_id: Optional[int] = Query(None, description="Optional examination ID filter"),
    shift: Optional[str] = Query(None, max_length=100, description="Optional examination shift filter"),
    db: Session = Depends(get_db),
) -> Response:
    normalized_roll = _validate_and_normalize_roll(roll_number)
    allocations = _query_student_allocations(
        db=db,
        normalized_roll=normalized_roll,
        examination_id=examination_id,
        shift=shift,
    )
    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published seating arrangement found for Roll Number '{normalized_roll}'.",
        )

    pdf_bytes = generate_student_seating_slip_pdf(
        roll_number=normalized_roll,
        allocations=allocations,
    )
    safe_file_roll = re.sub(r"[^A-Z0-9_-]", "_", normalized_roll)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Seating_Slip_{safe_file_roll}.pdf"'
        },
    )
