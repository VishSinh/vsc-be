#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="restore-local"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

SNAP_ID="${1:-}"
CONFIRM="${2:-}"

[[ -n "${SNAP_ID}" ]] || die "Usage: $0 <snapshot_id|latest> [--yes]"
[[ "${CONFIRM:-}" == "--yes" ]] || die "Refusing to proceed without --yes"

# Make args available to subshells executed via bash -c
export SNAP_ID CONFIRM

require_local_tools() {
  require_host_tool docker
  require_host_tool tar
}

# Detect local compose command and include both base and dev files
local_compose_cmd() {
  local base="-f ${PROJECT_ROOT}/compose.yaml -f ${PROJECT_ROOT}/compose.dev.yaml"
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose ${base}"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose ${base}"
  else
    die "Neither 'docker compose' nor 'docker-compose' found on host"
  fi
}

# Wait for Postgres inside the db service
wait_for_db_ready() {
  local compose="$1"
  for i in {1..60}; do
    if ${compose} exec -T db sh -lc 'pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# Export helper functions for availability inside bash -c subshell
export -f require_local_tools local_compose_cmd wait_for_db_ready

with_lock "restore-local" bash -c '
  require_local_tools

  # Resolve snapshot directory
  if [[ "${SNAP_ID}" == "latest" ]]; then
    snap_dir="${BACKUP_ROOT}/latest"
  else
    snap_dir="${BACKUP_ROOT}/${SNAP_ID}"
  fi
  [[ -d "${snap_dir}" ]] || die "Snapshot directory not found: ${snap_dir}"

  # Validate presence of db and media artifacts (media can be dir or tar.gz)
  [[ -f "${snap_dir}/db.dump" ]] || die "db.dump not found in ${snap_dir}"
  if [[ ! -f "${snap_dir}/media.tar.gz" && ! -d "${snap_dir}/media" ]]; then
    die "Neither media.tar.gz nor media/ directory found in ${snap_dir}"
  fi

  compose=$(local_compose_cmd)

  log "Bringing up local services (db, web)"
  ${compose} up -d db web | cat

  log "Waiting for local Postgres to be ready"
  if ! wait_for_db_ready "${compose}"; then
    die "Database did not become ready in time"
  fi

  # Resolve DB credentials from container env
  DB_NAME=$(${compose} exec -T db printenv POSTGRES_DB | tr -d "\r")
  DB_USER=$(${compose} exec -T db printenv POSTGRES_USER | tr -d "\r")
  # shellcheck disable=SC2016
  log "Restoring DB into local container: db=${DB_NAME} user=${DB_USER}"
  if [[ "${DRY_RUN:-0}" = "1" ]]; then
    echo "[DRY_RUN] cat ${snap_dir}/db.dump | ${compose} exec -T db sh -lc '"'"'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'"'"'"
  else
    cat "${snap_dir}/db.dump" | ${compose} exec -T db sh -lc '"'"'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'"'"'
  fi
  log "DB restore completed for ${SNAP_ID}"

  log "Restoring media into local volume via web container mount /app/media"
  # Clear existing media to avoid stale files
  ${compose} exec -T web sh -lc "mkdir -p /app/media && find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf {} +"

  if [[ -f "${snap_dir}/media.tar.gz" ]]; then
    if [[ "${DRY_RUN:-0}" = "1" ]]; then
      echo "[DRY_RUN] cat ${snap_dir}/media.tar.gz | ${compose} exec -T web tar -xz -C /app/media"
    else
      cat "${snap_dir}/media.tar.gz" | ${compose} exec -T web tar -xz -C /app/media
    fi
  else
    # Pack and stream the media/ directory to target path
    if [[ "${DRY_RUN:-0}" = "1" ]]; then
      echo "[DRY_RUN] tar -C ${snap_dir}/media -cz . | ${compose} exec -T web tar -xz -C /app/media"
    else
      tar -C "${snap_dir}/media" -cz . | ${compose} exec -T web tar -xz -C /app/media
    fi
  fi
  log "Media restore completed for ${SNAP_ID}"

  # Show a small summary
  log "Local restore complete: db=$(file_size \"${snap_dir}/db.dump\"), media_tar=$(file_size \"${snap_dir}/media.tar.gz\")"
'
