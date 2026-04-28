#!/usr/bin/env bash
# Create the `mlflow` database (separate from politikast app DB) inside the
# postgres service so the MLflow tracking server can use it as backend store.
#
# Idempotent: safe to re-run. Skips if DB already exists.
#
# Usage:
#   bash tools/init_mlflow_db.sh
#
# Env (overridable):
#   POSTGRES_USER     (default: politikast)
#   POSTGRES_PASSWORD (default: politikast)
#   POSTGRES_DB       (default: politikast — used for the bootstrap connection)
#   POSTGRES_HOST     (default: postgres if running inside docker, else localhost)
#   POSTGRES_PORT     (default: 5432 inside docker, 5433 from host)
#   MLFLOW_DB_NAME    (default: mlflow)
#   PG_CONTAINER      (default: politikast-postgres) — `docker exec` target when
#                     run from host without a local psql client.

set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-politikast}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-politikast}"
POSTGRES_DB="${POSTGRES_DB:-politikast}"
MLFLOW_DB_NAME="${MLFLOW_DB_NAME:-mlflow}"
PG_CONTAINER="${PG_CONTAINER:-politikast-postgres}"

run_psql() {
  local sql="$1"
  if command -v psql >/dev/null 2>&1; then
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
      -h "${POSTGRES_HOST:-localhost}" \
      -p "${POSTGRES_PORT:-5433}" \
      -U "${POSTGRES_USER}" \
      -d "${POSTGRES_DB}" \
      -tA -c "${sql}"
  else
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" "${PG_CONTAINER}" \
      psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tA -c "${sql}"
  fi
}

EXISTS=$(run_psql "SELECT 1 FROM pg_database WHERE datname='${MLFLOW_DB_NAME}'" | tr -d '[:space:]' || true)

if [ "${EXISTS}" = "1" ]; then
  echo "[init_mlflow_db] database '${MLFLOW_DB_NAME}' already exists — skip."
  exit 0
fi

echo "[init_mlflow_db] creating database '${MLFLOW_DB_NAME}' owned by '${POSTGRES_USER}'..."
run_psql "CREATE DATABASE ${MLFLOW_DB_NAME} OWNER ${POSTGRES_USER};"
echo "[init_mlflow_db] done."
