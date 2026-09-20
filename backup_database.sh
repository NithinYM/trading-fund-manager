#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

: "${POSTGRES_DB:=trading_fund}"
: "${POSTGRES_USER:=postgres}"
: "${POSTGRES_PASSWORD:=postgres}"
: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${BACKUP_DIR:=./backups}"

mkdir -p "${BACKUP_DIR}"
TS=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TS}.dump"

export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc -f "${DUMP_FILE}"

printf 'Database backup created: %s\n' "${DUMP_FILE}"
