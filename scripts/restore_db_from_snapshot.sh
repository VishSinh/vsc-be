#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="restore-db"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

SNAP_ID="${1:-}"
CONFIRM="${2:-}"

[[ -n "${SNAP_ID}" ]] || die "Usage: $0 <snapshot_id|latest> [--yes]"
[[ "${CONFIRM:-}" == "--yes" ]] || die "Refusing to proceed without --yes"

with_lock "restore-db" bash -c '
  check_host_deps
  if [[ "${SNAP_ID}" == "latest" ]]; then snap_dir="${BACKUP_ROOT}/latest"; else snap_dir="${BACKUP_ROOT}/${SNAP_ID}"; fi
  [[ -f "${snap_dir}/db.dump" ]] || die "db.dump not found in ${snap_dir}"
  log "Restoring DB from ${snap_dir}/db.dump to remote service ${PG_SERVICE} (this may cause downtime)"
  compose=$(remote_compose_cmd)
  PG_DB_RESOLVED="$(resolve_pg_db)"; PG_USER_RESOLVED="$(resolve_pg_user)"
  [[ -n "${PG_DB_RESOLVED}" ]] || die "Unable to resolve PG_DB; set PG_DB or ensure POSTGRES_DB in container"
  [[ -n "${PG_USER_RESOLVED}" ]] || die "Unable to resolve PG_USER; set PG_USER or ensure POSTGRES_USER in container"
  if [[ "${DRY_RUN:-0}" = "1" ]]; then echo "[DRY_RUN] cat ${snap_dir}/db.dump | ssh ${SSH_USER}@${SSH_HOST} \"${compose} exec -T ${PG_SERVICE} pg_restore --clean --if-exists -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED}\""; else cat "${snap_dir}/db.dump" | ssh ${SSH_OPTS:-} "${SSH_USER}@${SSH_HOST}" "${compose} exec -T ${PG_SERVICE} pg_restore --clean --if-exists -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED}"; fi
  log "DB restore completed for ${SNAP_ID}"
'
