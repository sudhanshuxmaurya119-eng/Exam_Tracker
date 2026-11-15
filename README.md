# Examination Seating Plan Finder Portal

A production-ready full-stack web application for managing university examination schedules, validating and importing Excel seating plans with duplicate/invalid row detection, storing datasets in private **Supabase Storage** (`seating-datasets`), persisting relational data in **Supabase PostgreSQL**, and enabling fast student roll-number searches with official downloadable PDF seating slips.

---

## Architecture Overview

- **Frontend (Vercel)**: React 18, TypeScript, Tailwind CSS, Vite, React Router v6
- **Backend (Render)**: Python 3.12, FastAPI, SQLAlchemy 2.0 (with `QueuePool`), Alembic Migrations, Pandas, OpenPyXL, Bcrypt, PyJWT
- **Database**: Supabase PostgreSQL (6 relational tables with `UNIQUE(examination_id, roll_number)` and composite index `(examination_id, roll_number)`)
- **File Storage**: Supabase Storage Private Bucket (`seating-datasets`) with time-limited Signed URLs

---

## Repository Structure

```text
Exam Tracker/
├── backend/
│   ├── alembic/                        # Alembic migration environment & versions
│   │   └── versions/0001_initial_production_schema.py
│   ├── app/
│   │   ├── api/                        # Auth, Examinations, Imports, Datasets, Search, Maintenance routes
│   │   ├── core/                       # Config, PostgreSQL connection pooling, JWT/Bcrypt, Rate Limiting
│   │   ├── models/                     # SQLAlchemy 2.0 ORM models (6 tables)
│   │   ├── schemas/                    # Pydantic v2 request/response validation schemas
│   │   ├── services/                   # Supabase Storage, Pandas/OpenPyXL Excel parser, PDF generator
│   │   └── main.py                     # FastAPI application entrypoint & /health endpoint
│   ├── scripts/                        # Admin provisioning & backup verification CLI tools
│   ├── sql/supabase_schema.sql         # Complete PostgreSQL DDL & Supabase Storage bucket setup
│   ├── tests/test_e2e_production.py    # Automated test suite for all 15 Phase 10 scenarios
│   ├── alembic.ini
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts               # VITE_API_BASE_URL client with connection error & auth handling
│   │   ├── components/                 # Navbar, SeatingCard, StatusBanner
│   │   ├── context/AuthContext.tsx     # JWT session provider
│   │   ├── pages/                      # StudentPortal, AdminLogin, AdminDashboard (5 tabs)
│   │   └── types/index.ts              # TypeScript interfaces
│   ├── .env.example
│   ├── package.json
│   ├── vercel.json                     # Vercel SPA rewrite & security headers configuration
│   └── vite.config.ts
├── docs/
│   ├── SUPABASE_SETUP.md               # Supabase PostgreSQL & 'seating-datasets' bucket instructions
│   ├── GITHUB_RENDER_VERCEL_DEPLOYMENT.md
│   └── DATABASE_BACKUP_AND_RECOVERY.md # Backup, migration, monitoring & restore documentation
├── render.yaml                         # Render Blueprint configuration
├── vercel.json                         # Root Vercel configuration
├── requirements.txt
└── .env.example
```

---

## Quick Start (Local Development & Verification)

### 1. Backend Setup
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\pip install -r backend/requirements.txt

# Provision an administrator account:
cd backend
..\.venv\Scripts\python scripts/create_admin.py --username admin --email admin@examportal.edu --password "StrongAdminPass#2026"

# Start FastAPI server:
..\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Run the 15-Scenario End-to-End Test Suite
```bash
.\.venv\Scripts\pytest backend/tests/test_e2e_production.py -v
```

---

## Cloud Deployment Documentation

- **[Supabase Setup Instructions](docs/SUPABASE_SETUP.md)**
- **[GitHub, Render & Vercel Deployment Guide](docs/GITHUB_RENDER_VERCEL_DEPLOYMENT.md)**
- **[Database Backup & Recovery Documentation](docs/DATABASE_BACKUP_AND_RECOVERY.md)**
