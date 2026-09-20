# API Guide

The backend runs on `http://localhost:8000` and exposes OpenAPI documentation at `/docs`.

## Authentication

`POST /auth/login` accepts JSON credentials:

```json
{"username": "manager", "password": "..."}
```

The response contains `access_token`, `token_type`, and `role`. Send the token on protected requests:

```text
Authorization: Bearer <access_token>
```

`GET /auth/me` resolves the active user from the token. Invalid or inactive users receive `401`.

There is no public user-registration endpoint. Create the first administrator with `backend/scripts/create_user.py`, then manage credentials through the deployment environment and database administration workflow.

## Public reads

- `GET /health`
- `GET /health/ready`
- `GET /dashboard`
- `GET /clients`
- `GET /trading`
- `GET /status-history`
- `GET /fund-movements`
- `GET /reports/daily?trading_date=YYYY-MM-DD`
- `GET /reports/daily/export?trading_date=YYYY-MM-DD` downloads the daily report as CSV
- `GET /reports/monthly?year=YYYY&month=MM`
- `GET /reports/monthly/export?year=YYYY&month=MM` downloads the monthly report as CSV
- `GET /reports/reconciliation/YYYY-MM-DD`
- `GET /manager-accounts`
- `GET /manager-accounts/{code}/reconciliation?trading_date=YYYY-MM-DD`
- `POST /import/excel` for workbook preview only

`GET /audit-logs?entity_type=CLIENT&entity_id={client_id}` is available to `ADMIN` and `MANAGER` users. It returns immutable audit events for tracked financial and administrative writes.

## Authenticated writes

`ADMIN` users may create or update operational records:

- `POST /clients`
- `PUT /clients/{client_id}`
- `DELETE /clients/{client_id}`
- `POST /status-history`
- `POST /trading`
- `POST /fund-movements`

Sensitive operations require `ADMIN` or `MANAGER` role:

- `POST /import/excel/commit`
- `POST /reports/recalculate/YYYY-MM-DD`

Client creation, updates, soft-deletes, status-period changes, fund movements, daily trading entries, workbook commits, and ledger recalculations write audit records.

Daily trading creation and deletion are restricted to `ADMIN`. `DELETE /trading/YYYY-MM-DD` can remove only the latest trading date and writes an audit record. This prevents an administrator from silently changing a prior result after later ledger entries exist.

Workbook commit is transactional. Validation failures, overlapping status periods, unknown clients, duplicate trading dates, and invalid fund movements roll back the entire import.

The workbook preview is read-only. The commit endpoint imports `Clients`, `Status History`, `Fund Movements`, and `Daily Trading`, then rebuilds chronological client-ledger rows before reporting success.

## Docker deployment

Copy `.env.example` to `.env` and replace `SECRET_KEY`, `JWT_SECRET`, and PostgreSQL credentials before using Compose outside local development. The backend container applies `alembic upgrade head` before starting the API; `/health/ready` gates dependent services.
