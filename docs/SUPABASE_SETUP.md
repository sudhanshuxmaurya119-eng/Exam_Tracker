# Supabase PostgreSQL & Private Storage (`seating-datasets`) Setup Guide

This guide walks through configuring **Supabase PostgreSQL** as the primary production database and **Supabase Storage** (`seating-datasets`) as the private file storage backend for the Examination Seating Plan Portal.

---

## 1. Create a Supabase Project

1. Sign in to [https://supabase.com/dashboard](https://supabase.com/dashboard) and click **New Project**.
2. Choose your organization, enter a project name (e.g., `exam-seating-portal`), generate a strong **Database Password** (save it securely), and select the closest region (e.g., `ap-south-1` Mumbai or `ap-southeast-1` Singapore).
3. Wait ~90 seconds for the PostgreSQL 15+ instance and Storage API to provision.

---

## 2. Obtain Your Supabase PostgreSQL Connection URI

1. In your Supabase Project Dashboard, click **Connect** (top bar) or navigate to **Project Settings → Database**.
2. Select **Connection String → URI** and choose **Session Pooler** (port `5432`) or **Transaction Pooler** (port `6543`):
   ```text
   postgresql+psycopg2://postgres.[PROJECT-REF]:[YOUR-DB-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require
   ```
3. Set this value as `DATABASE_URL` in your Render backend environment variables.
   - Note: The FastAPI backend automatically normalizes `postgres://` or `postgresql://` to `postgresql+psycopg2://` and strictly enforces PostgreSQL in `APP_ENV=production` (SQLite is blocked in production).

---

## 3. Apply the Production Schema & Migrations

You can initialize all 6 tables (`admin_users`, `examinations`, `datasets`, `students`, `seating_records`, `import_jobs`), constraints (`UNIQUE(examination_id, roll_number)`), and indexes (`(examination_id, roll_number)`) in either of two ways:

### Option A: Automated via Alembic (Recommended — Runs Automatically on Render Build)
```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require"
alembic upgrade head
```

### Option B: Direct SQL Execution in Supabase SQL Editor
1. Open **SQL Editor** in your Supabase Dashboard.
2. Paste the contents of [`backend/sql/supabase_schema.sql`](../backend/sql/supabase_schema.sql) and click **Run**.
3. This script atomically creates all 6 tables, triggers, foreign keys, `uq_seating_examination_roll_number`, `ix_seating_examination_roll_number`, and initializes the private `seating-datasets` storage bucket.

---

## 4. Configure the Private Storage Bucket (`seating-datasets`)

1. In the Supabase Dashboard, navigate to **Storage → Buckets**.
2. Verify that the bucket **`seating-datasets`** exists and has **Public = OFF (Private)** (the backend also verifies/creates this automatically on startup via `ensure_bucket_exists()`).
3. Set **File size limit** to `10 MB` (`10485760` bytes) and allowed MIME types:
   - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - `application/vnd.ms-excel`
   - `text/csv`
   - `application/json`

### Folder Structure Inside `seating-datasets`
- `examinations/{examination_id}/original/{timestamp}_{token}_{filename}.xlsx`: Original uploaded Excel workbooks.
- `examinations/{examination_id}/processing/{timestamp}_{token}_summary.json`: Validation, duplicate-detection, and row-audit report.

---

## 5. Obtain Backend Storage Credentials (Service-Role Key)

1. Go to **Project Settings → API** in the Supabase Dashboard.
2. Copy:
   - **Project URL** → `SUPABASE_URL` (e.g., `https://abcdefghijklm.supabase.co`)
   - **`service_role` secret key** → `SUPABASE_SERVICE_ROLE_KEY`
3. **CRITICAL SECURITY RULE**:
   - Configure `SUPABASE_SERVICE_ROLE_KEY` **ONLY** in the FastAPI backend environment on Render.
   - **NEVER** place `SUPABASE_SERVICE_ROLE_KEY` in `frontend/.env` or Vercel environment variables.
   - All file uploads, replacements, deletions, and signed download URL generations are performed exclusively by the FastAPI backend after verifying administrator JWT authentication.
