#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="health"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

with_lock "health" bash -c '
  latest_dir="${BACKUP_ROOT}/latest"
  if [[ ! -d "${latest_dir}" ]]; then die "No latest snapshot"; fi
  ts=$(basename "$(readlink "${latest_dir}" || echo "${latest_dir}")")
  log "Latest snapshot: ${ts}"
  ok=0
  if [[ -f "${latest_dir}/db.dump" ]]; then log "db.dump: $(file_size "${latest_dir}/db.dump")"; fi
  if [[ -f "${latest_dir}/schema.sql" ]]; then log "schema.sql: $(file_size "${latest_dir}/schema.sql")"; fi
  if [[ -f "${latest_dir}/roles.sql" ]]; then log "roles.sql: $(file_size "${latest_dir}/roles.sql")"; fi
  if [[ -f "${latest_dir}/media.tar.gz" ]]; then log "media.tar.gz: $(file_size "${latest_dir}/media.tar.gz")"; else if [[ -d "${latest_dir}/media" ]]; then log "media dir present"; fi; fi
  if [[ -f "${latest_dir}/SHA256SUMS.txt" ]]; then log "SHA256SUMS present"; else warn "SHA256SUMS.txt missing"; ok=1; fi
  if command -v pg_restore >/dev/null 2>&1; then
    if pg_restore -l "${latest_dir}/db.dump" >/dev/null 2>&1; then log "pg_restore -l OK"; else warn "pg_restore -l FAILED"; ok=1; fi
  else
    warn "pg_restore not found; skipping check"; ok=1
  fi
  if [[ -f "${latest_dir}/VERIFY_STATUS.txt" ]]; then log "Last verify: $(cat "${latest_dir}/VERIFY_STATUS.txt")"; else warn "VERIFY_STATUS.txt missing"; ok=1; fi
  if (( ok != 0 )); then exit 1; fi
'
