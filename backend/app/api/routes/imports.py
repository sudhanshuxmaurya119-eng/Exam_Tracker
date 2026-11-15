"""Phase 3 Excel Database Import Pipeline routes (Upload, Validate, Preview, Confirm, Rollback)."""

from datetime import datetime, timezone
import logging
import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_write_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import (
    AdminUser,
    Dataset,
    Examination,
    ImportJob,
    SeatingRecord,
    Student,
)
from app.schemas.schemas import (
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportJobResponse,
    ImportPreviewResponse,
)
from app.services.excel_service import (
    generate_sample_excel_template,
    parse_and_validate_excel,
    validate_upload_file_metadata,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/imports", tags=["Excel Import Pipeline"])
settings = get_settings()


@router.get(
    "/template",
    summary="Download official Excel (.xlsx) seating dataset template",
)
def download_excel_template(_: AdminUser = Depends(get_current_admin)) -> Response:
    content = generate_sample_excel_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="Examination_Seating_Template.xlsx"'
        },
    )


@router.post(
    "/upload",
    response_model=ImportPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 1-9: Upload Excel to Supabase Storage, validate schema/rows, detect duplicates, and return preview",
)
async def upload_and_validate_excel(
    examination_id: int = Form(..., description="Target examination ID"),
    replace_existing: bool = Form(True, description="Replace existing seating records on confirm"),
    file: UploadFile = File(..., description="Excel (.xlsx/.xls) or .csv dataset file"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(require_write_admin),
) -> ImportPreviewResponse:
    # 1. Verify target examination exists
    exam = db.scalar(select(Examination).where(Examination.id == examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination with ID {examination_id} not found.",
        )

    # 2. Read file bytes and validate file type, size, magic header, and SHA-256 checksum
    file_bytes = await file.read()
    filename = file.filename or "seating_dataset.xlsx"
    _, file_checksum = validate_upload_file_metadata(
        filename=filename,
        content_type=file.content_type,
        file_bytes=file_bytes,
    )

    # 3. Store original Excel file in private Supabase Storage bucket 'seating-datasets'
    job_token = secrets.token_hex(24)
    storage_path, processing_storage_path = storage_service.build_dataset_paths(
        examination_id=examination_id,
        job_token=job_token,
        original_filename=filename,
    )

    mime_type = (
        file.content_type
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    storage_service.upload_file(
        storage_path=storage_path,
        file_bytes=file_bytes,
        content_type=mime_type,
    )

    # Determine next dataset version for this examination
    max_version = (
        db.scalar(
            select(func.max(Dataset.version)).where(Dataset.examination_id == examination_id)
        )
        or 0
    )

    # Create inactive dataset metadata record & import job record
    dataset = Dataset(
        examination_id=examination_id,
        original_filename=filename,
        storage_bucket=settings.SUPABASE_STORAGE_BUCKET,
        storage_path=storage_path,
        processing_storage_path=processing_storage_path,
        file_size_bytes=len(file_bytes),
        mime_type=mime_type,
        file_checksum=file_checksum,
        is_active=False,
        version=int(max_version) + 1,
        uploaded_by=current_admin.id,
    )
    db.add(dataset)
    db.flush()

    import_job = ImportJob(
        job_token=job_token,
        examination_id=examination_id,
        dataset_id=dataset.id,
        initiated_by=current_admin.id,
        status="validating",
        replace_existing=replace_existing,
    )
    db.add(import_job)
    db.commit()
    db.refresh(dataset)
    db.refresh(import_job)

    # 4-8. Read Excel with Pandas, validate columns, preview records, detect duplicates & invalid rows.
    # IMPORTANT: Existing seating records are NOT deleted during validation.
    existing_rolls_list = db.scalars(
        select(SeatingRecord.roll_number).where(SeatingRecord.examination_id == examination_id)
    ).all()
    existing_roll_numbers = {r.strip().upper() for r in existing_rolls_list}

    try:
        validation_result = parse_and_validate_excel(
            file_bytes=file_bytes,
            filename=filename,
            existing_roll_numbers=existing_roll_numbers,
            replace_existing=replace_existing,
            default_shift=exam.shift,
        )
    except HTTPException as exc:
        import_job.status = "failed"
        import_job.error_message = str(exc.detail)
        import_job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    except Exception as exc:
        import_job.status = "failed"
        import_job.error_message = f"Unexpected Excel validation error: {exc}"
        import_job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Excel validation failed: {exc}",
        ) from exc

    # 9. Save processing summary to Supabase Storage and update dataset & import_job
    summary_payload: Dict[str, Any] = {
        "job_token": job_token,
        "examination_id": examination_id,
        "dataset_id": dataset.id,
        "original_filename": filename,
        "replace_existing": replace_existing,
        "existing_records_count": len(existing_roll_numbers),
        "total_rows": validation_result["total_rows"],
        "valid_rows": validation_result["valid_rows"],
        "invalid_rows": validation_result["invalid_rows"],
        "duplicate_rows": validation_result["duplicate_rows"],
        "detected_columns": validation_result["detected_columns"],
        "preview_records": [p.model_dump() for p in validation_result["preview_records"]],
        "duplicates": [d.model_dump() for d in validation_result["duplicates"]],
        "invalid_records": [i.model_dump() for i in validation_result["invalid_records"]],
        "warnings": validation_result["warnings"],
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }

    storage_service.upload_processing_artifact(
        storage_path=processing_storage_path,
        summary_data=summary_payload,
    )

    dataset.total_rows = validation_result["total_rows"]
    dataset.valid_rows = validation_result["valid_rows"]
    dataset.invalid_rows = validation_result["invalid_rows"]
    dataset.duplicate_rows = validation_result["duplicate_rows"]

    import_job.total_rows = validation_result["total_rows"]
    import_job.valid_rows = validation_result["valid_rows"]
    import_job.invalid_rows = validation_result["invalid_rows"]
    import_job.duplicate_rows = validation_result["duplicate_rows"]
    import_job.validation_summary = summary_payload
    import_job.staged_records = validation_result["staged_records"]
    import_job.status = (
        "awaiting_confirmation" if validation_result["can_confirm"] else "failed"
    )
    if not validation_result["can_confirm"]:
        import_job.error_message = "No valid rows available to import."
        import_job.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(import_job)

    return ImportPreviewResponse(
        job_token=import_job.job_token,
        job_id=import_job.id,
        dataset_id=dataset.id,
        examination_id=exam.id,
        examination_title=exam.title,
        examination_code=exam.exam_code,
        original_filename=dataset.original_filename,
        storage_path=dataset.storage_path,
        replace_existing=replace_existing,
        existing_records_count=len(existing_roll_numbers),
        total_rows=validation_result["total_rows"],
        valid_rows=validation_result["valid_rows"],
        invalid_rows=validation_result["invalid_rows"],
        duplicate_rows=validation_result["duplicate_rows"],
        detected_columns=validation_result["detected_columns"],
        preview_records=validation_result["preview_records"],
        duplicates=validation_result["duplicates"],
        invalid_records=validation_result["invalid_records"],
        can_confirm=validation_result["can_confirm"],
        status=import_job.status,
        warnings=validation_result["warnings"],
    )


@router.post(
    "/{job_token}/confirm",
    response_model=ImportConfirmResponse,
    summary="Step 10-11: Confirm validated Excel import and commit records in an atomic PostgreSQL transaction",
)
def confirm_excel_import(
    job_token: str,
    payload: Optional[ImportConfirmRequest] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_write_admin),
) -> ImportConfirmResponse:
    import_job = db.scalar(select(ImportJob).where(ImportJob.job_token == job_token))
    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found.",
        )

    if import_job.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This import job has already been confirmed and committed.",
        )

    if import_job.status != "awaiting_confirmation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import job cannot be confirmed from status '{import_job.status}'.",
        )

    staged_records: List[Dict[str, Any]] = import_job.staged_records or []
    if not staged_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import job has no valid staged records to commit.",
        )

    dataset = db.scalar(select(Dataset).where(Dataset.id == import_job.dataset_id))
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated dataset record not found.",
        )

    exam = db.scalar(select(Examination).where(Examination.id == import_job.examination_id))
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target examination not found.",
        )

    # Execute dataset replacement and insertion inside a single atomic transaction
    try:
        replaced_count = 0
        if import_job.replace_existing:
            existing_count = (
                db.scalar(
                    select(func.count(SeatingRecord.id)).where(
                        SeatingRecord.examination_id == exam.id
                    )
                )
                or 0
            )
            replaced_count = int(existing_count)

            # Delete existing seating records for this examination inside the transaction
            db.execute(
                delete(SeatingRecord).where(SeatingRecord.examination_id == exam.id)
            )

            # Deactivate previous active datasets for this examination
            previous_datasets = db.scalars(
                select(Dataset).where(
                    Dataset.examination_id == exam.id,
                    Dataset.id != dataset.id,
                    Dataset.is_active.is_(True),
                )
            ).all()
            for prev_ds in previous_datasets:
                prev_ds.is_active = False

        # Upsert shared student master profiles by roll_number
        roll_numbers = [rec["roll_number"] for rec in staged_records]
        existing_students = db.scalars(
            select(Student).where(Student.roll_number.in_(roll_numbers))
        ).all()
        student_map: Dict[str, Student] = {s.roll_number: s for s in existing_students}

        for rec in staged_records:
            r_no = rec["roll_number"]
            if r_no in student_map:
                st = student_map[r_no]
                st.student_name = rec["student_name"]
                if rec.get("registration_number"):
                    st.registration_number = rec["registration_number"]
                if rec.get("department"):
                    st.department = rec["department"]
                if rec.get("branch"):
                    st.branch = rec["branch"]
                if rec.get("semester"):
                    st.semester = rec["semester"]
            else:
                st = Student(
                    roll_number=r_no,
                    student_name=rec["student_name"],
                    registration_number=rec.get("registration_number"),
                    department=rec.get("department"),
                    branch=rec.get("branch"),
                    semester=rec.get("semester"),
                )
                db.add(st)
                student_map[r_no] = st

        db.flush()

        # Insert validated SeatingRecord rows
        new_seating_rows: List[SeatingRecord] = []
        for rec in staged_records:
            st_obj = student_map.get(rec["roll_number"])
            new_seating_rows.append(
                SeatingRecord(
                    examination_id=exam.id,
                    dataset_id=dataset.id,
                    student_id=st_obj.id if st_obj else None,
                    roll_number=rec["roll_number"],
                    student_name=rec["student_name"],
                    registration_number=rec.get("registration_number"),
                    department=rec.get("department") or exam.department,
                    branch=rec.get("branch"),
                    semester=rec.get("semester") or exam.semester,
                    subject_code=rec.get("subject_code") or exam.subject_code,
                    subject_name=rec.get("subject_name") or exam.subject_name,
                    building_name=rec.get("building_name"),
                    floor_number=rec.get("floor_number"),
                    room_number=rec["room_number"],
                    bench_number=rec.get("bench_number"),
                    seat_number=rec["seat_number"],
                    row_number=rec.get("grid_row"),
                    column_number=rec.get("grid_column"),
                    shift=rec.get("shift") or exam.shift,
                )
            )

        db.add_all(new_seating_rows)

        dataset.is_active = True
        completed_time = datetime.now(timezone.utc)
        import_job.status = "completed"
        import_job.inserted_rows = len(new_seating_rows)
        import_job.completed_at = completed_time
        # Clear bulky staged_records JSON after successful transactional commit
        import_job.staged_records = None

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Import transaction failed and rolled back for job %s: %s", job_token, exc)
        # Record rollback status in a clean transaction
        try:
            failed_job = db.scalar(select(ImportJob).where(ImportJob.job_token == job_token))
            if failed_job:
                failed_job.status = "rolled_back"
                failed_job.error_message = f"Transaction rolled back: {exc}"
                failed_job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database import failed and was safely rolled back. Existing records were preserved. Error: {exc}",
        ) from exc

    return ImportConfirmResponse(
        job_token=import_job.job_token,
        job_id=import_job.id,
        dataset_id=dataset.id,
        examination_id=exam.id,
        status="completed",
        inserted_rows=import_job.inserted_rows,
        replaced_previous_rows=replaced_count,
        completed_at=completed_time,
        message=(
            f"Successfully imported {import_job.inserted_rows} seating record(s)"
            + (f" (replaced {replaced_count} previous record(s))." if replaced_count else ".")
        ),
    )


@router.post(
    "/{job_token}/cancel",
    summary="Cancel a pending/awaiting_confirmation import job and remove its unconfirmed storage files",
)
def cancel_excel_import(
    job_token: str,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_write_admin),
) -> Dict[str, Any]:
    import_job = db.scalar(select(ImportJob).where(ImportJob.job_token == job_token))
    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found.",
        )

    if import_job.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an already completed import job. Delete or replace the dataset instead.",
        )

    storage_paths_to_remove: List[str] = []
    if import_job.dataset_id:
        ds = db.scalar(select(Dataset).where(Dataset.id == import_job.dataset_id))
        if ds and not ds.is_active:
            if ds.storage_path:
                storage_paths_to_remove.append(ds.storage_path)
            if ds.processing_storage_path:
                storage_paths_to_remove.append(ds.processing_storage_path)
            import_job.dataset_id = None
            db.delete(ds)

    import_job.status = "cancelled"
    import_job.staged_records = None
    import_job.completed_at = datetime.now(timezone.utc)
    db.commit()

    if storage_paths_to_remove:
        storage_service.delete_files(storage_paths_to_remove)

    return {
        "job_token": job_token,
        "status": "cancelled",
        "message": "Staged import job cancelled and unconfirmed storage files cleaned up.",
    }


@router.get(
    "/jobs",
    response_model=List[ImportJobResponse],
    summary="List Excel dataset import jobs and audit history (Admin only)",
)
def list_import_jobs(
    examination_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> List[ImportJobResponse]:
    stmt = select(ImportJob)
    if examination_id is not None:
        stmt = stmt.where(ImportJob.examination_id == examination_id)
    stmt = stmt.order_by(ImportJob.id.desc()).limit(limit)
    jobs = db.scalars(stmt).all()

    results: List[ImportJobResponse] = []
    for job in jobs:
        resp = ImportJobResponse.model_validate(job)
        if job.examination:
            resp.examination_title = job.examination.title
            resp.examination_code = job.examination.exam_code
        if job.dataset:
            resp.original_filename = job.dataset.original_filename
        results.append(resp)
    return results
