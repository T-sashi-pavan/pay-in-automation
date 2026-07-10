# Pay-In Automation

Insurance commission-grid extraction and management dashboard. Upload broker
Excel grids, get parsed/normalized commission rules, browse and edit them.

## Stack

- **Backend**: FastAPI + SQLAlchemy + Alembic, PostgreSQL, pandas/openpyxl for parsing.
- **Frontend**: React 19 + Vite + TypeScript + TanStack Query/Table + Tailwind.

## Local development

**Backend** (from repo root, so `backend.app.*` imports resolve):

```bash
pip install -r backend/requirements.txt
# backend/.env must define DATABASE_URL (see below) — never commit this file
cd backend && alembic upgrade head && cd ..
uvicorn backend.app.main:app --reload --port 8000
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

`backend/.env` (create this file, it's gitignored):

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

The frontend defaults to `http://localhost:8000/api` in dev — no `.env` needed locally.

## Deploying to Render (Blueprint)

This repo includes a `render.yaml` defining two services: `payin-backend`
(FastAPI web service) and `payin-frontend` (static site). To deploy:

1. Push this repo to GitHub/GitLab.
2. In Render, **New → Blueprint**, point it at the repo. Render reads `render.yaml`
   and creates both services.
3. Both services need one manually-entered env var each (marked `sync: false`
   in `render.yaml` so they're never committed) — set these in the Render
   dashboard under each service's **Environment** tab:

   | Service | Env Var | Value |
   |---|---|---|
   | `payin-backend` | `DATABASE_URL` | Your Postgres connection string (e.g. from Neon) |
   | `payin-backend` | `CORS_ORIGINS` | The frontend's Render URL, e.g. `https://payin-frontend.onrender.com` (set *after* step 4) |
   | `payin-frontend` | `VITE_API_BASE_URL` | The backend's Render URL + `/api`, e.g. `https://payin-backend.onrender.com/api` (set *after* step 4) |

4. First deploy: both services will build, but the frontend won't be able to
   reach the backend yet (its URL isn't known until it exists) and the
   backend will reject the frontend's requests (CORS not yet configured).
   Once both services have their Render-assigned URLs, fill in
   `CORS_ORIGINS` and `VITE_API_BASE_URL` above and trigger a **manual
   redeploy** on each (the frontend one matters most — `VITE_API_BASE_URL`
   is baked in at build time, so a dashboard-only env var change doesn't
   take effect until the next build).
5. Confirm `payin-backend`'s start command ran `alembic upgrade head`
   successfully (check the deploy log) — this creates all tables on a fresh
   database automatically.

### Build/start commands (already set via render.yaml, shown here for reference)

| Service | Build Command | Start Command |
|---|---|---|
| `payin-backend` | `pip install -r backend/requirements.txt` | `cd backend && alembic upgrade head && cd .. && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| `payin-frontend` | `cd frontend && npm install && npm run build` | *(static site — served from `frontend/dist`)* |

### Notes

- Uploaded Excel files are only ever staged briefly on local disk during
  parsing, then deleted — Render's ephemeral filesystem is fine here, no
  persistent disk add-on needed.
- The `payin-backend` free plan spins down after inactivity (cold start on
  the next request); upgrade the plan if that's not acceptable.
