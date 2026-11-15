# GitHub, Render (Backend), and Vercel (Frontend) Deployment Guide

This guide covers end-to-end cloud deployment of the Examination Seating Plan Portal across **GitHub**, **Render**, and **Vercel**.

---

## Part 1: Push Source Code to GitHub

1. Initialize the Git repository in the workspace root (if not already initialized):
   ```bash
   git init
   git add .
   git commit -m "feat: production database, Supabase storage, Excel pipeline, and cloud configs"
   ```
2. Create a new private or public repository on GitHub (e.g., `exam-seating-plan-portal`).
3. Push the `main` branch:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/exam-seating-plan-portal.git
   git push -u origin main
   ```
4. Verify that `.env` files are excluded by `.gitignore` and never committed.

---

## Part 2: Deploy FastAPI Backend on Render

### Option A: One-Click Blueprint Deployment (`render.yaml`)
1. Log in to [https://dashboard.render.com](https://dashboard.render.com).
2. Click **New + → Blueprint** and connect your GitHub repository (`exam-seating-plan-portal`).
3. Render automatically detects [`render.yaml`](../render.yaml) at the repository root with:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --proxy-headers --forwarded-allow-ips="*"`
   - **Health Check Path**: `/health`
4. Enter the prompted secret environment variables:
   - `DATABASE_URL`: Your Supabase PostgreSQL connection string (`postgresql+psycopg2://...`)
   - `SUPABASE_URL`: `https://<project-ref>.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase `service_role` secret key
   - `INITIAL_ADMIN_PASSWORD`: A strong password (>= 8 chars) for the initial `super_admin` user
   - `FRONTEND_URL`: Your Vercel domain (e.g., `https://exam-seating-portal.vercel.app`)
   - `CORS_ORIGINS`: Your Vercel domain (e.g., `https://exam-seating-portal.vercel.app`)
5. Click **Apply**.

### Option B: Manual Web Service Setup on Render
1. Click **New + → Web Service** and select your GitHub repository.
2. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --proxy-headers --forwarded-allow-ips="*"`
   - **Health Check Path**: `/health`
3. Add the environment variables from [`backend/.env.example`](../backend/.env.example).

### Verify Backend Deployment
Once deployed, test the health-check endpoint:
```bash
curl https://<your-render-service>.onrender.com/health
```
Expected response (`200 OK`):
```json
{
  "status": "healthy",
  "service": "Examination Seating Plan Portal API",
  "version": "1.0.0",
  "environment": "production",
  "database": {
    "connected": true,
    "dialect": "postgresql"
  },
  "storage": {
    "provider": "supabase_storage",
    "bucket": "seating-datasets",
    "private": true,
    "configured": true
  }
}
```

---

## Part 3: Deploy React + TypeScript Frontend on Vercel

1. Log in to [https://vercel.com/dashboard](https://vercel.com/dashboard) and click **Add New… → Project**.
2. Import your GitHub repository (`exam-seating-plan-portal`).
3. Configure the build settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   ```text
   VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api/v1
   ```
5. Click **Deploy**.
6. Once Vercel assigns your production domain (e.g., `https://exam-seating-portal.vercel.app`), ensure `FRONTEND_URL` and `CORS_ORIGINS` on Render match that exact domain (without trailing slash).
7. Verify SPA routing (`frontend/vercel.json`): Refreshing `/admin/login` or `/admin/dashboard` directly in the browser will cleanly load the React route without a 404 error.
