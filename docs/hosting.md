# Online Hosting Guide

## Recommended Open Hosting Stack

Use separate services so the application can be updated independently:

- Frontend: Cloudflare Pages or Netlify
- Backend: Render Web Service, Fly.io, or Koyeb
- Database: Neon or Supabase PostgreSQL
- Source and CI: GitHub and GitHub Actions

Free tiers are suitable for a demo or internal trial. Review each provider's current limits, sleep policy, backup guarantees, and data-residency terms before storing real financial data.

## 1. Publish the Repository

Create a private GitHub repository, then push the local repository:

```powershell
git add .
git commit -m "Prepare hosted deployment"
git remote add origin https://github.com/<account>/<repository>.git
git push -u origin main
```

Do not push `.env`, SQLite databases, backups, or workbook files containing real client data.

## 2. Create PostgreSQL

Create a PostgreSQL database with Neon or Supabase and copy its connection string. The backend requires the SQLAlchemy Psycopg form:

```text
postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require
```

## 3. Deploy the Backend

Create a Docker web service from the repository and set its Docker context to `backend`. Configure these environment variables in the hosting provider:

```text
DATABASE_URL=postgresql+psycopg://...
SECRET_KEY=<long-random-secret>
JWT_SECRET=<different-long-random-secret>
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=["https://<your-frontend-domain>"]
```

The backend Docker image runs `alembic upgrade head` before Uvicorn starts. Use `/health/ready` as the service health check.

After the first deployment, open the provider's backend shell and create the administrator. Enter the password directly at the prompts:

```bash
python -m scripts.create_user --username admin --email admin@example.com --role ADMIN
```

Create a view-only operational user with the `TRADER` role:

```bash
python -m scripts.create_user --username viewer --email viewer@example.com --role TRADER
```

`ADMIN` can manage clients, fees, status periods, fund movements, and create or delete the latest daily trading result. `TRADER` users can view dashboard, reports, ledger history, and exported CSVs but cannot change financial records.

## 4. Deploy the Frontend

Create a Cloudflare Pages or Netlify project from the same repository with:

```text
Root directory: frontend
Build command: npm ci && npm run build
Output directory: dist
Node version: 20
```

Set this build-time environment variable:

```text
VITE_API_URL=https://<your-backend-domain>
```

Every frontend redeploy bakes `VITE_API_URL` into the static files. If the backend URL changes, update this variable and redeploy the frontend. Then update the backend `CORS_ORIGINS` value to the deployed frontend URL.

## 5. Verify Production

1. Open `https://<your-backend-domain>/health/ready` and confirm `ready`.
2. Open `https://<your-frontend-domain>` and confirm `Backend connected`.
3. Sign in as `ADMIN`, add a daily result for a new date, and verify reconciliation plus the audit record.
4. Confirm only the latest daily result exposes the delete action.
5. Sign in as the viewer user and confirm dashboard, client balances, ledger history, and CSV reports are visible while daily-entry controls are absent.
6. Create and test a PostgreSQL backup before accepting live financial data.