# Testing Guide

## Backend tests

From the repository root on Windows PowerShell:

```powershell
cd backend
python -m pytest -q
```

From macOS/Linux:

```bash
cd backend
python -m pytest -q
```

The suite covers:

- Decimal-safe calculation and fee rules
- Status-period overlap validation
- Repository CRUD and date normalization
- Auth, JWT validation, and role restrictions
- Client, trading, status-history, and fund-movement APIs
- Dashboard and report summaries
- Workbook preview and transactional commit/rollback
- Health and database readiness
- Ledger recalculation and reconciliation

## Migration checks

Use a separate database URL for migration validation:

```powershell
cd backend
$env:DATABASE_URL = "sqlite:///./migration_check.db"
python -m alembic upgrade head
python -m alembic check
Remove-Item migration_check.db -ErrorAction SilentlyContinue
```

`alembic check` should report `No new upgrade operations detected`.

## Frontend checks

Install Node.js LTS, then run:

```powershell
cd frontend
npm install
npm run build
```

The build runs TypeScript compilation followed by Vite production bundling. `npm audit --omit=dev` checks production dependencies.

## Docker smoke check

After configuring `.env`, verify the Compose configuration and running services:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
Invoke-WebRequest http://localhost:8000/health/ready
docker compose down
```

Use `docker compose down -v` only for an intentional test-data reset because it deletes the PostgreSQL volume.

## Manual smoke test

1. Start the backend and frontend.
2. Open `http://127.0.0.1:5173`.
3. Confirm the sidebar says `Backend connected`.
4. Confirm `/health/ready` returns status `ready` and database `ok`.
5. Select the reference workbook in the Workbook Intake panel.
6. Confirm the preview reports four populated client rows and 365 daily-trading rows.
7. Sign in with an active user and commit only after reviewing the preview.
8. Save one new, non-duplicate daily trade and inspect its generated allocation.
9. Use `/reports/reconciliation/{trading_date}` to verify allocation and fee-transfer checks.
10. Choose a manager account and the same date in the dashboard drill-down; confirm its expected fees, credited fees, balance, and reconciliation status match the API.

## Known non-blocking warning

The backend test suite may report a Starlette/AnyIO deprecation warning from a third-party dependency. It does not indicate an application test failure.
