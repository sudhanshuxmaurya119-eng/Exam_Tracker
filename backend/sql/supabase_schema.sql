-- =============================================================================
-- EXAMINATION SEATING PLAN PORTAL - PRODUCTION POSTGRESQL SCHEMA (SUPABASE)
-- =============================================================================
-- Target Database: Supabase PostgreSQL 15+
-- Storage Bucket:  seating-datasets (Private)
-- =============================================================================

BEGIN;

-- 1. Automatic updated_at timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TABLE 1: admin_users
-- =============================================================================
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin' CHECK (role IN ('super_admin', 'admin', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_admin_users_username UNIQUE (username),
    CONSTRAINT uq_admin_users_email UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS ix_admin_users_username ON admin_users (username);
CREATE INDEX IF NOT EXISTS ix_admin_users_email ON admin_users (email);

DROP TRIGGER IF EXISTS trg_admin_users_updated_at ON admin_users;
CREATE TRIGGER trg_admin_users_updated_at
    BEFORE UPDATE ON admin_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLE 2: examinations
-- =============================================================================
CREATE TABLE IF NOT EXISTS examinations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    exam_code VARCHAR(100) NOT NULL,
    subject_name VARCHAR(255) NULL,
    subject_code VARCHAR(100) NULL,
    exam_date DATE NOT NULL,
    shift VARCHAR(100) NOT NULL,
    start_time VARCHAR(50) NULL,
    end_time VARCHAR(50) NULL,
    academic_session VARCHAR(100) NULL,
    semester VARCHAR(50) NULL,
    department VARCHAR(150) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'completed', 'archived')),
    instructions TEXT NULL,
    created_by INTEGER NULL REFERENCES admin_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_examinations_exam_code UNIQUE (exam_code)
);

CREATE INDEX IF NOT EXISTS ix_examinations_exam_code ON examinations (exam_code);
CREATE INDEX IF NOT EXISTS ix_examinations_exam_date ON examinations (exam_date);
CREATE INDEX IF NOT EXISTS ix_examinations_status_date ON examinations (status, exam_date);
CREATE INDEX IF NOT EXISTS ix_examinations_shift ON examinations (shift);

DROP TRIGGER IF EXISTS trg_examinations_updated_at ON examinations;
CREATE TRIGGER trg_examinations_updated_at
    BEFORE UPDATE ON examinations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLE 3: datasets
-- =============================================================================
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    storage_bucket VARCHAR(100) NOT NULL DEFAULT 'seating-datasets',
    storage_path VARCHAR(512) NOT NULL,
    processing_storage_path VARCHAR(512) NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    mime_type VARCHAR(150) NOT NULL,
    file_checksum VARCHAR(64) NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows INTEGER NOT NULL DEFAULT 0,
    invalid_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    uploaded_by INTEGER NULL REFERENCES admin_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_datasets_storage_path UNIQUE (storage_path)
);

CREATE INDEX IF NOT EXISTS ix_datasets_examination_id ON datasets (examination_id);
CREATE INDEX IF NOT EXISTS ix_datasets_examination_active ON datasets (examination_id, is_active);

DROP TRIGGER IF EXISTS trg_datasets_updated_at ON datasets;
CREATE TRIGGER trg_datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLE 4: students (Shared student master records across examinations)
-- =============================================================================
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    roll_number VARCHAR(100) NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    registration_number VARCHAR(100) NULL,
    department VARCHAR(150) NULL,
    branch VARCHAR(150) NULL,
    semester VARCHAR(50) NULL,
    section VARCHAR(50) NULL,
    email VARCHAR(255) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_students_roll_number UNIQUE (roll_number)
);

CREATE INDEX IF NOT EXISTS ix_students_roll_number ON students (roll_number);
CREATE INDEX IF NOT EXISTS ix_students_registration_number ON students (registration_number);

DROP TRIGGER IF EXISTS trg_students_updated_at ON students;
CREATE TRIGGER trg_students_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLE 5: seating_records
-- =============================================================================
-- IMPORTANT DATABASE RULE:
-- A student can have different seating arrangements in different examinations.
-- Therefore, roll_number is NOT globally unique in seating_records.
-- Enforces UNIQUE(examination_id, roll_number) and index on (examination_id, roll_number).
-- =============================================================================
CREATE TABLE IF NOT EXISTS seating_records (
    id SERIAL PRIMARY KEY,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    student_id INTEGER NULL REFERENCES students(id) ON DELETE SET NULL,
    roll_number VARCHAR(100) NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    registration_number VARCHAR(100) NULL,
    department VARCHAR(150) NULL,
    branch VARCHAR(150) NULL,
    semester VARCHAR(50) NULL,
    subject_code VARCHAR(100) NULL,
    subject_name VARCHAR(255) NULL,
    building_name VARCHAR(150) NULL,
    floor_number VARCHAR(50) NULL,
    room_number VARCHAR(100) NOT NULL,
    bench_number VARCHAR(50) NULL,
    seat_number VARCHAR(50) NOT NULL,
    row_number VARCHAR(50) NULL,
    column_number VARCHAR(50) NULL,
    shift VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_seating_examination_roll_number UNIQUE (examination_id, roll_number)
);

-- Required composite index on (examination_id, roll_number)
CREATE INDEX IF NOT EXISTS ix_seating_examination_roll_number ON seating_records (examination_id, roll_number);
-- Additional indexes for fast student search across examinations and room lookup
CREATE INDEX IF NOT EXISTS ix_seating_records_roll_number ON seating_records (roll_number);
CREATE INDEX IF NOT EXISTS ix_seating_records_dataset_id ON seating_records (dataset_id);
CREATE INDEX IF NOT EXISTS ix_seating_records_exam_room ON seating_records (examination_id, room_number);

DROP TRIGGER IF EXISTS trg_seating_records_updated_at ON seating_records;
CREATE TRIGGER trg_seating_records_updated_at
    BEFORE UPDATE ON seating_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- TABLE 6: import_jobs
-- =============================================================================
CREATE TABLE IF NOT EXISTS import_jobs (
    id SERIAL PRIMARY KEY,
    job_token VARCHAR(64) NOT NULL,
    examination_id INTEGER NOT NULL REFERENCES examinations(id) ON DELETE CASCADE,
    dataset_id INTEGER NULL REFERENCES datasets(id) ON DELETE SET NULL,
    initiated_by INTEGER NULL REFERENCES admin_users(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'validating',
            'awaiting_confirmation',
            'committing',
            'completed',
            'failed',
            'rolled_back',
            'cancelled'
        )
    ),
    replace_existing BOOLEAN NOT NULL DEFAULT TRUE,
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows INTEGER NOT NULL DEFAULT 0,
    invalid_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    inserted_rows INTEGER NOT NULL DEFAULT 0,
    validation_summary JSONB NULL,
    staged_records JSONB NULL,
    error_message TEXT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_import_jobs_job_token UNIQUE (job_token)
);

CREATE INDEX IF NOT EXISTS ix_import_jobs_job_token ON import_jobs (job_token);
CREATE INDEX IF NOT EXISTS ix_import_jobs_examination_id ON import_jobs (examination_id);
CREATE INDEX IF NOT EXISTS ix_import_jobs_status ON import_jobs (status);

DROP TRIGGER IF EXISTS trg_import_jobs_updated_at ON import_jobs;
CREATE TRIGGER trg_import_jobs_updated_at
    BEFORE UPDATE ON import_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SUPABASE STORAGE PRIVATE BUCKET INITIALIZATION (Run in Supabase SQL Editor)
-- =============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'seating-datasets',
            'seating-datasets',
            FALSE,
            10485760, -- 10 MB limit
            ARRAY[
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel',
                'text/csv',
                'application/json'
            ]
        )
        ON CONFLICT (id) DO UPDATE
        SET public = FALSE,
            file_size_limit = 10485760;
    END IF;
END $$;

COMMIT;
