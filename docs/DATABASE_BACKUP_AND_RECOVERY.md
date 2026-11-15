# Database Backup, Migration, Monitoring, and Disaster Recovery Guide

This document details the production backup strategy, Alembic migration workflow, dataset import audit logging, health monitoring, and step-by-step disaster recovery procedures for the Examination Seating Plan Portal.

---

## 1. Database Backup Strategy

### Layer 1: Automated Supabase Daily Backups & PITR
- **Daily Snapshots**: Supabase Pro automatically takes daily backups of the PostgreSQL cluster and retains them for 7–30 days.
- **Point-in-Time Recovery (PITR)**: Write-Ahead Log (WAL) archiving allows restoring the database to any second within the retention window.

### Layer 2: Logical `pg_dump` Backups (Pre-Migration & Scheduled)
Run logical backups before any major schema change or examination cycle using `pg_dump`:
```bash
# Export compressed custom-format backup (.dump)
pg_dump "$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="backups/exam_portal_$(date -u +%Y%m%dT%H%M%SZ).dump"

# Export plain SQL schema + data backup (.sql)
pg_dump "$DATABASE_URL" \
  --no-owner \
  --no-acl \
  --file="backups/exam_portal_$(date -u +%Y%m%dT%H%M%SZ).sql"
```

### Layer 3: Original Excel Preservation in Private Supabase Storage (`seating-datasets`)
- Every uploaded seating spreadsheet is stored permanently in the private `seating-datasets` bucket (`examinations/{examination_id}/original/...`) along with its SHA-256 checksum (`datasets.file_checksum`) and validation summary JSON (`examinations/{examination_id}/processing/...`).
- Even if a table is accidentally truncated, any examination's seating records can be re-imported deterministically from its stored Excel workbook in seconds.

### Layer 4: Backup Verification Manifest
Administrators can export a real-time backup verification manifest via:
- **Admin UI**: **Import History & Backup → Export Backup Manifest (.json)**
- **API**: `GET /api/v1/maintenance/backup-manifest`
- **CLI**: `python backend/scripts/backup_verify.py`

---

## 2. Database Migration Process (Alembic)

All schema changes are version-controlled under `backend/alembic/versions/`.

### Checking Current Migration Revision
```bash
cd backend
alembic current
```

### Generating a New Migration
```bash
cd backend
alembic revision --autogenerate -m "describe_schema_change"
```

### Applying Migrations to Production
```bash
cd backend
alembic upgrade head
```

### Rolling Back a Migration
```bash
cd backend
alembic downgrade -1
```

---

## 3. Dataset Import Audit History & Transactional Rollback

- Every Excel upload creates an immutable audit record in the `import_jobs` table (`pending` → `validating` → `awaiting_confirmation` → `completed` / `failed` / `rolled_back` / `cancelled`).
- **Two-Phase Confirmation**:
  1. `POST /api/v1/imports/upload` validates the workbook, detects duplicate roll numbers and invalid rows, and stores the staged records in `import_jobs` **without deleting or modifying existing `seating_records`**.
  2. `POST /api/v1/imports/{job_token}/confirm` executes dataset replacement and record insertion inside a single atomic PostgreSQL transaction. If any constraint violation or database error occurs, `db.rollback()` restores all previous records untouched and logs the error in `import_jobs.error_message`.

---

## 4. Database Health Monitoring & Error Logging

- **Health Endpoint**: `GET /health` executes `SELECT 1` against PostgreSQL, measures round-trip query latency in milliseconds (`latency_ms`), inspects the SQLAlchemy `QueuePool` status (`pool_status`), and verifies `seating-datasets` storage configuration.
- Render polls `GET /health` continuously and automatically alerts or restarts unhealthy instances.
- All unhandled database exceptions (`SQLAlchemyError`) and validation failures are logged with UTC ISO-8601 timestamps, HTTP method, request path, and processing time (`X-Process-Time-Ms`).

---

## 5. Step-by-Step Database Restore Procedure

### Scenario A: Restore from a `pg_dump` Custom Backup File (`.dump`)
1. Put the backend service in maintenance mode (or pause traffic on Render).
2. Verify the backup file integrity:
   ```bash
   pg_restore --list backups/exam_portal_YYYYMMDDTHHMMSSZ.dump
   ```
3. Restore cleanly into the target Supabase PostgreSQL database:
   ```bash
   pg_restore \
     --clean \
     --if-exists \
     --no-owner \
     --no-acl \
     --dbname="$DATABASE_URL" \
     backups/exam_portal_YYYYMMDDTHHMMSSZ.dump
   ```
4. Verify schema revision and row counts:
   ```bash
   cd backend
   alembic current
   python scripts/backup_verify.py
   ```

### Scenario B: Restore from a Plain SQL Backup (`.sql`)
```bash
psql "$DATABASE_URL" -f backups/exam_portal_YYYYMMDDTHHMMSSZ.sql
```

### Scenario C: Reconstruct Examination Seating from Supabase Storage (`seating-datasets`)
If a single examination's seating records need to be restored to an earlier version:
1. Open **Admin Dashboard → Storage Datasets (`seating-datasets`)**.
2. Locate the previous dataset version (`v1`, `v2`, etc.) for that examination and click **Signed URL** to download the original `.xlsx` file.
3. Navigate to **Excel Import Pipeline**, select the examination, upload the `.xlsx` file with **Safe Replace Dataset** enabled, verify the preview summary, and click **Confirm & Commit**.
