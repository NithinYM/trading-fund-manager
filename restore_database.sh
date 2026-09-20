#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

BACKUP_FILE="${1:-}"
if [ -z "${BACKUP_FILE}" ]; then
  echo "Usage: ./restore_database.sh /path/to/backup.dump"
  exit 1
fi

: "${POSTGRES_DB:=trading_fund}"
: "${POSTGRES_USER:=postgres}"
: "${POSTGRES_PASSWORD:=postgres}"
: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"

export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_restore -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists "${BACKUP_FILE}"

printf 'Database restored from: %s\n' "${BACKUP_FILE}"
