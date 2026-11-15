"""Dataset metadata and private Supabase Storage management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_write_admin
from app.core.database import get_db
from app.models.models import AdminUser, Dataset
from app.schemas.schemas import DatasetResponse, SignedUrlResponse
from app.services.storage_service import storage_service

router = APIRouter(prefix="/datasets", tags=["Datasets & Storage"])


def _enrich_dataset(ds: Dataset) -> DatasetResponse:
    resp = DatasetResponse.model_validate(ds)
    if ds.examination:
        resp.examination_title = ds.examination.title
        resp.examination_code = ds.examination.exam_code
    return resp


@router.get(
    "",
    response_model=List[DatasetResponse],
    summary="List uploaded datasets and storage metadata (Admin only)",
)
def list_datasets(
    examination_id: Optional[int] = Query(None),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> List[DatasetResponse]:
    stmt = select(Dataset)
    if examination_id is not None:
        stmt = stmt.where(Dataset.examination_id == examination_id)
    if active_only:
        stmt = stmt.where(Dataset.is_active.is_(True))
    stmt = stmt.order_by(Dataset.id.desc())
    datasets = db.scalars(stmt).all()
    return [_enrich_dataset(ds) for ds in datasets]


@router.get(
    "/{dataset_id}/signed-url",
    response_model=SignedUrlResponse,
    summary="Generate a time-limited signed download URL for a dataset in 'seating-datasets' (Admin only)",
)
def create_dataset_signed_url(
    dataset_id: int,
    expires_in: Optional[int] = Query(300, ge=30, le=3600),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> SignedUrlResponse:
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id))
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID {dataset_id} not found.",
        )

    signed_url, ttl = storage_service.create_signed_url(
        dataset_id=ds.id,
        storage_path=ds.storage_path,
        expires_in=expires_in,
    )
    return SignedUrlResponse(
        dataset_id=ds.id,
        original_filename=ds.original_filename,
        storage_bucket=ds.storage_bucket,
        storage_path=ds.storage_path,
        signed_url=signed_url,
        expires_in_seconds=ttl,
    )


@router.get(
    "/{dataset_id}/download",
    summary="Download original Excel file using a verified HMAC signed URL",
)
def download_dataset_with_signed_token(
    dataset_id: int,
    expires: int = Query(...),
    signature: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id))
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found.",
        )

    if not storage_service.verify_local_signed_token(
        dataset_id=ds.id,
        storage_path=ds.storage_path,
        expires=expires,
        signature=signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired signed download token.",
        )

    file_bytes, content_type = storage_service.download_file(ds.storage_path)
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{ds.original_filename}"'
        },
    )


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a dataset, its seating records, and its objects in Supabase Storage (Admin only)",
)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_write_admin),
) -> dict:
    ds = db.scalar(select(Dataset).where(Dataset.id == dataset_id))
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID {dataset_id} not found.",
        )

    paths_to_delete = [p for p in [ds.storage_path, ds.processing_storage_path] if p]
    filename = ds.original_filename
    exam_id = ds.examination_id

    # Cascade deletes associated seating_records in a transaction
    db.delete(ds)
    db.commit()

    storage_deleted = storage_service.delete_files(paths_to_delete)

    return {
        "deleted": True,
        "dataset_id": dataset_id,
        "examination_id": exam_id,
        "original_filename": filename,
        "storage_objects_deleted": storage_deleted,
    }
