"""Supabase Storage service for private bucket 'seating-datasets'.

In production, all files (original Excel files, uploaded examination datasets, and
dataset processing summaries) are stored exclusively in Supabase Storage using the
backend service-role key, with zero permanent files stored on the local filesystem.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent path traversal and invalid object keys."""
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", filename.strip())
    return clean[:180] or "dataset.xlsx"


class SupabaseStorageService:
    """Manages private object storage in the 'seating-datasets' Supabase Storage bucket."""

    def __init__(self) -> None:
        # In-memory store used ONLY in local dev/testing when SUPABASE_URL is not configured.
        # Never writes permanent files to the local filesystem.
        self._memory_bucket: Dict[str, Tuple[bytes, str]] = {}

    @property
    def is_remote_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.SUPABASE_URL.strip() and settings.SUPABASE_SERVICE_ROLE_KEY.strip())

    def _headers(self, content_type: Optional[str] = None, upsert: bool = True) -> Dict[str, str]:
        settings = get_settings()
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers

    def _base_storage_url(self) -> str:
        settings = get_settings()
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1"

    def build_dataset_paths(
        self,
        examination_id: int,
        job_token: str,
        original_filename: str,
    ) -> Tuple[str, str]:
        """Build deterministic, collision-free paths inside 'seating-datasets' bucket."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = sanitize_filename(original_filename)
        excel_path = f"examinations/{examination_id}/original/{timestamp}_{job_token[:10]}_{safe_name}"
        processing_path = f"examinations/{examination_id}/processing/{timestamp}_{job_token[:10]}_summary.json"
        return excel_path, processing_path

    def ensure_bucket_exists(self) -> None:
        """Ensure private bucket 'seating-datasets' exists in Supabase Storage."""
        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET

        if not self.is_remote_configured:
            if settings.APP_ENV.lower() == "production":
                raise RuntimeError(
                    "Supabase Storage credentials are missing in production environment."
                )
            return

        url = f"{self._base_storage_url()}/bucket/{bucket}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    return
                # Create private bucket if not found
                create_url = f"{self._base_storage_url()}/bucket"
                payload = {
                    "id": bucket,
                    "name": bucket,
                    "public": False,
                    "file_size_limit": settings.max_upload_size_bytes,
                }
                create_resp = client.post(
                    create_url,
                    headers=self._headers("application/json"),
                    json=payload,
                )
                if create_resp.status_code not in (200, 201, 409):
                    logger.warning(
                        "Supabase bucket creation returned status %s: %s",
                        create_resp.status_code,
                        create_resp.text,
                    )
        except Exception as exc:
            logger.error("Failed to verify/create Supabase bucket '%s': %s", bucket, exc)

    def upload_file(
        self,
        storage_path: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        """Upload raw file bytes to 'seating-datasets' bucket."""
        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET

        if not self.is_remote_configured:
            if settings.APP_ENV.lower() == "production":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase Storage is not configured in production.",
                )
            self._memory_bucket[storage_path] = (file_bytes, content_type)
            logger.info("Stored object '%s' (%d bytes) in dev memory bucket '%s'", storage_path, len(file_bytes), bucket)
            return storage_path

        encoded_path = "/".join(quote(part, safe="") for part in storage_path.split("/"))
        url = f"{self._base_storage_url()}/object/{bucket}/{encoded_path}"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url,
                    headers=self._headers(content_type=content_type, upsert=True),
                    content=file_bytes,
                )
                if resp.status_code not in (200, 201):
                    logger.error(
                        "Supabase Storage upload failed (%s): %s",
                        resp.status_code,
                        resp.text,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to upload file to Supabase Storage bucket '{bucket}'.",
                    )
            return storage_path
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Supabase Storage upload error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error communicating with Supabase Storage during upload.",
            ) from exc

    def upload_processing_artifact(self, storage_path: str, summary_data: Dict[str, Any]) -> str:
        """Store dataset processing JSON report in 'seating-datasets' bucket."""
        raw_bytes = json.dumps(summary_data, indent=2, default=str).encode("utf-8")
        return self.upload_file(
            storage_path=storage_path,
            file_bytes=raw_bytes,
            content_type="application/json",
        )

    def download_file(self, storage_path: str) -> Tuple[bytes, str]:
        """Download object bytes and content-type from 'seating-datasets' bucket."""
        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET

        if not self.is_remote_configured:
            if storage_path not in self._memory_bucket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requested dataset object not found in storage.",
                )
            return self._memory_bucket[storage_path]

        encoded_path = "/".join(quote(part, safe="") for part in storage_path.split("/"))
        url = f"{self._base_storage_url()}/object/{bucket}/{encoded_path}"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=self._headers())
                if resp.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Dataset file not found in Supabase Storage.",
                    )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to retrieve dataset file from Supabase Storage.",
                    )
                content_type = resp.headers.get(
                    "content-type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                return resp.content, content_type
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Supabase Storage download error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error downloading file from Supabase Storage.",
            ) from exc

    def create_signed_url(
        self,
        dataset_id: int,
        storage_path: str,
        expires_in: Optional[int] = None,
    ) -> Tuple[str, int]:
        """Generate a time-limited signed download URL for an object in 'seating-datasets'."""
        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        ttl = expires_in or settings.SIGNED_URL_EXPIRES_SECONDS

        if not self.is_remote_configured:
            if storage_path not in self._memory_bucket:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset object not found in storage.",
                )
            exp_ts = int(time.time()) + ttl
            signature = self._sign_local_token(dataset_id=dataset_id, storage_path=storage_path, exp_ts=exp_ts)
            signed_path = f"{settings.API_V1_PREFIX}/datasets/{dataset_id}/download?expires={exp_ts}&signature={signature}"
            return signed_path, ttl

        encoded_path = "/".join(quote(part, safe="") for part in storage_path.split("/"))
        url = f"{self._base_storage_url()}/object/sign/{bucket}/{encoded_path}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    url,
                    headers=self._headers("application/json"),
                    json={"expiresIn": ttl},
                )
                if resp.status_code != 200:
                    logger.error("Supabase signed URL error (%s): %s", resp.status_code, resp.text)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to generate signed download URL from Supabase Storage.",
                    )
                data = resp.json()
                signed_relative = data.get("signedURL") or data.get("signedUrl") or ""
                if signed_relative.startswith("http"):
                    full_signed_url = signed_relative
                else:
                    full_signed_url = f"{self._base_storage_url()}{signed_relative}"
                return full_signed_url, ttl
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error generating Supabase signed URL: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate signed URL from Supabase Storage.",
            ) from exc

    def verify_local_signed_token(self, dataset_id: int, storage_path: str, expires: int, signature: str) -> bool:
        """Verify HMAC signature for dev-mode signed download URLs."""
        if int(time.time()) > expires:
            return False
        expected = self._sign_local_token(dataset_id=dataset_id, storage_path=storage_path, exp_ts=expires)
        return hmac.compare_digest(expected, signature)

    def _sign_local_token(self, dataset_id: int, storage_path: str, exp_ts: int) -> str:
        settings = get_settings()
        msg = f"{dataset_id}:{storage_path}:{exp_ts}".encode("utf-8")
        return hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def delete_files(self, paths: List[str]) -> bool:
        """Delete one or more objects from 'seating-datasets' bucket."""
        clean_paths = [p for p in paths if p]
        if not clean_paths:
            return True

        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET

        if not self.is_remote_configured:
            for p in clean_paths:
                self._memory_bucket.pop(p, None)
            return True

        url = f"{self._base_storage_url()}/object/{bucket}"
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.request(
                    "DELETE",
                    url,
                    headers=self._headers("application/json"),
                    json={"prefixes": clean_paths},
                )
                if resp.status_code not in (200, 204):
                    logger.warning(
                        "Supabase Storage delete returned %s: %s",
                        resp.status_code,
                        resp.text,
                    )
                    return False
                return True
        except Exception as exc:
            logger.error("Failed to delete objects from Supabase Storage: %s", exc)
            return False

    def get_storage_health(self) -> Dict[str, Any]:
        """Return health status of the storage subsystem."""
        settings = get_settings()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        if self.is_remote_configured:
            return {
                "provider": "supabase_storage",
                "bucket": bucket,
                "private": True,
                "configured": True,
            }
        return {
            "provider": "in_memory_dev_adapter",
            "bucket": bucket,
            "private": True,
            "configured": settings.APP_ENV.lower() != "production",
            "objects_in_memory": len(self._memory_bucket),
        }


storage_service = SupabaseStorageService()
