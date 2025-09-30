#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="verify"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

SNAP_ID="${1:-latest}"

export SNAP_ID

with_lock "verify" bash -c '
  check_host_deps
  if [[ "${SNAP_ID}" == "latest" ]]; then
    snap_dir="${BACKUP_ROOT}/latest"
  else
    snap_dir="${BACKUP_ROOT}/${SNAP_ID}"
  fi
  [[ -f "${snap_dir}/db.dump" ]] || die "db.dump not found in ${snap_dir}"

  log "Starting local verify restore for snapshot ${SNAP_ID}"
  cname="verify_pg_$(date +%s)"
  dbname="${PG_DB}"
  dbuser="${PG_USER}"
  port=$(python3 - <<PY
import socket,random
def free_port():
  s=socket.socket(); s.bind(("127.0.0.1",0)); p=s.getsockname()[1]; s.close(); print(p)
free_port()
PY
)
  log "Launching temporary postgres:16 container ${cname} on port ${port}"
  docker run -d --rm --name "${cname}" -e POSTGRES_DB="${dbname}" -e POSTGRES_USER="${dbuser}" -e POSTGRES_PASSWORD="testpass" -p "${port}:5432" postgres:16 >/dev/null

  # wait for readiness
  for i in {1..30}; do
    if docker exec "${cname}" pg_isready -U "${dbuser}" -d "${dbname}" >/dev/null 2>&1; then break; fi; sleep 1; done

  log "Restoring db.dump into temp container"
  # Exec pg_restore inside the same postgres container with password to avoid host networking issues
  if ! cat "${snap_dir}/db.dump" | docker exec -i -e PGPASSWORD="testpass" "${cname}" pg_restore --clean --if-exists -U "${dbuser}" -d "${dbname}"; then
    warn "pg_restore failed"
    docker rm -f "${cname}" >/dev/null 2>&1 || true
    exit 2
  fi

  log "Running smoke queries"
  docker exec -u "${dbuser}" "${cname}" psql -d "${dbname}" -c "\\dt" >/dev/null
  if docker exec -u "${dbuser}" "${cname}" psql -d "${dbname}" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='django_migrations'" | grep -q 1; then
    docker exec -u "${dbuser}" "${cname}" psql -d "${dbname}" -tAc "SELECT count(*) FROM django_migrations;" >/dev/null
  fi

  docker rm -f "${cname}" >/dev/null 2>&1 || true
  log "Verify restore succeeded for ${SNAP_ID}"
'
