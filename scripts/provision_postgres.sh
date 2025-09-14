#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ .env not found at $ENV_FILE"
  echo "Usage: $0 path/to/.env"
  exit 1
fi

# Load .env (simple KEY=VALUE format)
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

# Required vars
: "${DB_NAME:?Missing DB_NAME in .env}"
: "${DB_USER:?Missing DB_USER in .env}"
: "${DB_PASSWORD:?Missing DB_PASSWORD in .env}"
: "${DB_HOST:?Missing DB_HOST in .env}"
: "${DB_PORT:?Missing DB_PORT in .env}"

# Superuser connection (override in .env if needed)
PG_SUPER_USER="${PG_SUPER_USER:-postgres}"
PG_SUPER_DB="${PG_SUPER_DB:-postgres}"
# PG_SUPER_PASSWORD can be empty if peer/ident auth is used

echo "🔎 Using superuser ${PG_SUPER_USER}@${DB_HOST}:${DB_PORT}"

psql_super() {
  PGPASSWORD="${PG_SUPER_PASSWORD:-}" psql \
    -h "$DB_HOST" -p "$DB_PORT" \
    -U "$PG_SUPER_USER" -d "$PG_SUPER_DB" \
    -v "ON_ERROR_STOP=1" -Atq "$@"
}

psql_db() {
  PGPASSWORD="${PG_SUPER_PASSWORD:-}" psql \
    -h "$DB_HOST" -p "$DB_PORT" \
    -U "$PG_SUPER_USER" -d "$DB_NAME" \
    -v "ON_ERROR_STOP=1" -Atq "$@"
}

# 1) Ensure role exists (ALTER if exists so password is synced)
echo "🔎 Ensuring role '${DB_USER}' exists…"
psql_super <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;
SQL

# 2) Ensure database exists (must be done OUTSIDE a DO block)
echo "🔎 Ensuring database '${DB_NAME}' exists…"
DB_EXISTS="$(psql_super -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | tr -d '[:space:]' || true)"
if [[ "$DB_EXISTS" != "1" ]]; then
  # Create DB with desired owner/locale
  PGPASSWORD="${PG_SUPER_PASSWORD:-}" psql \
    -h "$DB_HOST" -p "$DB_PORT" \
    -U "$PG_SUPER_USER" -d "$PG_SUPER_DB" \
    -v "ON_ERROR_STOP=1" -qc "CREATE DATABASE ${DB_NAME}
      WITH OWNER = ${DB_USER}
           ENCODING = 'UTF8'
           TEMPLATE = template0
           LC_COLLATE = 'C'
           LC_CTYPE   = 'C';"
fi

# 3) Grants/ownership inside the DB
echo "🛠  Applying privileges in '${DB_NAME}'…"
psql_db <<SQL
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ${DB_USER};
SQL

echo "✅ Done. Database '${DB_NAME}' and role '${DB_USER}' are ready."
