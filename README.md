# Trading Fund Manager

An auditable web application for replacing the reference Excel trading-fund workbook with database-backed calculations, ledger entries, reporting, and controlled workbook imports.

## What it does

- Maintains clients, status periods, fund movements, and daily trading records.
- Allocates daily net P&L proportionally across active capital using `Decimal` arithmetic.
- Applies percentage and fixed fee rules and tracks manager fee credits.
- Generates persistent client ledger rows and reconciliation reports.
- Previews the reference workbook before import and commits validated data transactionally.
- Provides JWT authentication and role restrictions for sensitive operations.

## Technology

- Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic
- Frontend: React, TypeScript, Vite, Tailwind CSS, Recharts
- Database: SQLite for local development, PostgreSQL for deployment
- Runtime: Node.js LTS and Python 3.12+
- Deployment: Docker Compose

## Local development

Prerequisites:

- Python 3.12 or later
- Node.js 20 LTS or later
- Docker Desktop only when using the Compose stack

The local backend defaults to SQLite at `backend/app.db`. Docker Compose uses PostgreSQL.

### 1. Configure Python

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Copy `.env.example` to `.env` before changing the local database, secrets, or allowed frontend origins. For the SQLite default, omit `DATABASE_URL` from `.env` or set it to a SQLite URL.

### 2. Start the backend

From the repository root:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health/ready` before using the UI.

Create the first login user in a separate terminal. The command prompts twice for a password:

```powershell
cd backend
python -m scripts.create_user --username manager --email manager@example.com --role ADMIN
```

### 3. Install and start the frontend

Install Node.js LTS, then:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Set `VITE_API_URL` before starting Vite when the backend uses another host or port:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:8000"
```

## How to use

1. Open the dashboard and confirm `Backend connected` appears in the sidebar.
2. Review the portfolio metrics, client book, and net P&L chart.
3. Under **Client administration**, add or update a client, configure percentage/fixed fees, record active/inactive periods, and record deposits or withdrawals. Select a client to inspect its historical ledger and audit events.
4. Under **Manager accounts**, choose an account and an as-of date to inspect its opening capital, credited fees, expected client fees, balance, and fee-transfer reconciliation status.
5. Under **Reconciliation view**, select a trading date, export the daily report as CSV, and confirm allocation and fee statuses are `Reconciled` before closing the day.
6. Under **Daily trade**, enter the gross P&L, transaction charges, and remarks, then save. A valid authenticated user is required. The system prevents duplicate trading dates.
7. Use **Workbook Intake** to select an `.xlsx` file. Preview is read-only; review recognized sheets and row counts before committing. A successful commit rebuilds the imported historical client ledger automatically.
8. Sign in with an active `ADMIN` or `MANAGER` user to commit an import, read audit history, or recalculate a ledger. Commits are transactional: an invalid row rejects the complete workbook.

Every financial and administrative write is recorded in the audit log. CSV exports are available from the daily and monthly report endpoints.

API documentation is available at `http://127.0.0.1:8000/docs`.

## API essentials

- `POST /auth/login` returns a JWT access token.
- `GET /auth/me` validates the current user.
- `GET /dashboard` returns live portfolio aggregates.
- `POST /import/excel` previews a workbook.
- `POST /import/excel/commit` transactionally imports validated workbook data.
- `POST /reports/recalculate/{trading_date}` rebuilds a date's ledger.
- `GET /reports/reconciliation/{trading_date}` exposes allocation and fee-transfer checks.
- `GET /reports/daily/export` and `GET /reports/monthly/export` download CSV reports.
- `GET /audit-logs` exposes protected financial change history.

See the [API guide](docs/api.md) for the complete endpoint list and authorization rules.

## Docker deployment

Docker Compose starts PostgreSQL, applies database migrations in the backend container, and starts the API and frontend. First create a production `.env`; do not use the example secrets:

```powershell
Copy-Item .env.example .env
# Edit .env: set unique SECRET_KEY, JWT_SECRET, POSTGRES_PASSWORD,
# CORS_ORIGINS to the browser origins allowed to call the API, and
# VITE_API_URL to the public URL of the API (baked into the frontend build).
docker compose up --build -d
docker compose ps
```

Check readiness and create the initial administrator:

```powershell
Invoke-WebRequest http://localhost:8000/health/ready
docker compose exec backend python scripts/create_user.py --username manager --email manager@example.com --role ADMIN
```

For a public deployment, put the frontend and API behind an HTTPS reverse proxy, set `CORS_ORIGINS` to the public frontend URL, keep PostgreSQL off the public network, and back up its named volume or managed database.

## Publish to GitHub

This repository includes GitHub Actions CI and ignores local secrets, virtual environments, build output, databases, and backups. Initialize and publish it after creating an empty GitHub repository:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial release"
git remote add origin https://github.com/<your-account>/<your-repository>.git
git push -u origin main
```

Never commit `.env`, database files, backups, or real JWT secrets. GitHub Pages can host the static frontend but cannot run this FastAPI API or PostgreSQL; use a Docker-capable host for the backend and database, then build the frontend with `VITE_API_URL` set to that public API URL.

See [docs/deployment.md](docs/deployment.md) for production configuration, backup, and security guidance.

For a shared online deployment with an administrator who controls daily results and viewers who follow live balances, see the [online hosting guide](docs/hosting.md).

## Testing

Backend regression suite:

```powershell
cd backend
python -m pytest -q
```

Migration drift check:

```powershell
python -m alembic upgrade head
python -m alembic check
```

Frontend typecheck and production build:

```powershell
cd frontend
npm run build
```

Manual smoke test: start both services, sign in, save one non-duplicate daily trade, then verify its date in the daily reconciliation and selected manager-account drill-down. Exercise workbook preview before attempting a commit.

See [docs/testing.md](docs/testing.md) for coverage, smoke testing, and migration validation details.

## Business rules

- Active clients receive proportional daily P&L allocation.
- Inactive clients receive no allocated P&L.
- Percentage fees are charged only on positive allocated P&L.
- Fixed fees are charged on eligible trading days.
- Manager fee transfers reconcile to zero.
- Ledger entries are generated by backend calculations, not Excel formulas.
- Workbook imports validate all rows and roll back completely on failure.

## Documentation

- [Architecture](docs/architecture.md)
- [Business rules](docs/business-rules.md)
- [Calculations](docs/calculations.md)
- [Data model](docs/data-model.md)
- [API guide](docs/api.md)
- [Deployment guide](docs/deployment.md)
- [Online hosting guide](docs/hosting.md)
- [Testing guide](docs/testing.md)
