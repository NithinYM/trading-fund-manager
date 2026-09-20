# Deployment Guide

This project is designed to run in Docker for local development and production-style deployment.

## Docker Compose

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
   On Windows PowerShell use `Copy-Item .env.example .env`.
2. Replace the example secrets in `.env`. At minimum set unique values for `SECRET_KEY`, `JWT_SECRET`, and `POSTGRES_PASSWORD`. Set `CORS_ORIGINS` to a JSON array containing every browser origin allowed to call the API, for example:
   ```text
   CORS_ORIGINS=["https://fund.example.com"]
   ```
   Then start the stack:
   ```bash
   docker compose up --build -d
   ```
3. Confirm services and logs:
   ```bash
   docker compose ps
   docker compose logs -f backend
   ```
4. Confirm services:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - OpenAPI docs: http://localhost:8000/docs
   - Readiness: http://localhost:8000/health/ready
   - PostgreSQL: localhost:5432

The backend waits for healthy PostgreSQL, applies `alembic upgrade head`, and then starts Uvicorn. The frontend waits for backend readiness.

After the first deployment, create an initial administrator from the backend container. The command prompts for the password and confirmation:

```bash
docker compose exec backend python -m scripts.create_user --username manager --email manager@example.com --role ADMIN
```

Stop the stack with `docker compose down`. Use `docker compose down -v` only when intentionally deleting the local PostgreSQL volume.

## Environment variables

The application expects the following configuration values:

- DATABASE_URL
- SECRET_KEY
- JWT_SECRET
- CORS_ORIGINS as a JSON array, for example `["http://localhost:5173"]`
- VITE_API_URL as the public API URL compiled into the production frontend, for example `https://api.fund.example.com`
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

`docker-compose.yml` passes `CORS_ORIGINS` through to the backend, so the `.env` value must include the exact public frontend scheme, host, and port. `VITE_API_URL` is a build argument, so rebuild the frontend container after changing it. See [.env.example](../.env.example) for development defaults.

## Database migration

Run migrations after starting PostgreSQL when deploying outside the supplied Compose backend command:

```bash
cd backend
python -m alembic upgrade head
```

The Docker backend container runs this migration command before starting the API.

## Production deployment

Recommended production pattern:

- Keep PostgreSQL in a persistent volume or managed Postgres service.
- Run the backend as a stateless container.
- Build the frontend with `npm run build`, then serve its `dist` directory behind a reverse proxy or static host.
- Place Nginx, Traefik, or a managed load balancer in front of the services.
- Enable HTTPS termination at the reverse proxy.
- Store secrets in a secure secret manager or environment injection layer.
- Do not publish port `5432` outside a trusted network in production.

### Example production architecture

- Reverse proxy / TLS terminator
- Frontend container
- Backend container
- PostgreSQL service with backups

## Persistent data

Use a named Docker volume for Postgres:

```yaml
volumes:
  postgres_data:
```

This keeps database state across container restarts and deployments.

## Backup and restore

Use PostgreSQL-native backups with the credentials from the environment:

```bash
pg_dump --format=custom --file=trading_fund.dump "$DATABASE_URL"
pg_restore --clean --if-exists --dbname="$DATABASE_URL" trading_fund.dump
```

For the Compose database, run the tools inside the PostgreSQL container instead of exposing credentials to the host shell:

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > trading_fund.dump
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < trading_fund.dump
```

Test both backup creation and restore in a non-production environment before relying on a recovery procedure.

## Recommended hosting options

This project does not depend on a single vendor. It is compatible with:

- Docker-enabled VPS providers
- Linux servers managed by the team
- Managed PostgreSQL services
- Kubernetes or Compose-based internal deployments

## Security notes

- Never commit secrets to Git.
- Use environment variables or secret injection for production credentials.
- Restrict CORS to the expected domain list.
- Use HTTPS in production.
- Keep database backups encrypted and access controlled.
