# AI SEO & Social Media Manager

Local-first Instagram SEO and social media manager built with FastAPI, SQLAlchemy, Alembic, React, Vite, and Tailwind.

## Cost Model

The current Phase 1 stack is `FREE + OPEN SOURCE`. SQLite is `LOCAL ONLY`; Docker/Postgres/Chroma are self-hosted. Instagram OAuth/API usage is free but `REQUIRES INTERNET` and a Meta Developer app.

## Current Phase

Phase 1 Foundation is in progress:
- Backend skeleton, logging, DB session, full SQLAlchemy schema, Alembic initial migration.
- Single-operator auth.
- Instagram social account OAuth callback structure with encrypted token storage.
- Settings/model config CRUD.
- React scaffold with login and dashboard summary.

## Prerequisites

- Python 3.12
- Node.js 20+
- Docker Desktop or Docker Engine, optional for the container workflow

## Configuration

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

Update at least:
- `JWT_SECRET`
- `ENCRYPTION_KEY`

Keep `INSTAGRAM_APP_ID` and `INSTAGRAM_APP_SECRET` blank until you have Meta tester app credentials.

## Backend: Local SQLite

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Open:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

Register the single operator account with:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/register -ContentType application/json -Body '{"email":"owner@example.com","password":"local-password","full_name":"Owner"}'
```

Login:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login -ContentType application/json -Body '{"email":"owner@example.com","password":"local-password"}'
```

## Frontend: Local Vite

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Note: package installation did not complete inside this sandbox during Step 6, but these are the intended commands for a normal npm registry connection.

## Docker Workflow

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:
- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

The backend container runs `alembic upgrade head` before starting Uvicorn.

## Tests

Run current backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.unit.test_phase1_models_batch tests.api.test_auth_social_accounts tests.api.test_settings_model_configs tests.api.test_dashboard
```

## Important URLs

- Health: `GET /health`
- Auth: `/auth/register`, `/auth/login`, `/auth/me`
- Social accounts: `/social-accounts`
- Instagram OAuth start: `/social-accounts/instagram/connect`
- Instagram OAuth callback: `/social-accounts/callback`
- Settings: `/settings`
- Model configs: `/settings/model-configs`
- Dashboard summary: `/dashboard/summary`
- Content upload: `POST /content/upload`

## Notes

- OAuth tokens are encrypted before storage using `ENCRYPTION_KEY`.
- The first Alembic migration creates the full current schema.
- Chroma is present in Docker Compose for later RAG work, but Phase 1 does not yet call it.
- Local media storage uses `STORAGE_ROOT` and creates `raw`, `processed`, `generated`, `published`, `thumbnails`, and `audio`.
