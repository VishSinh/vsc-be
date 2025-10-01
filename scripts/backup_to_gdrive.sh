#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Remote server backup to Google Drive using rclone
# - Creates a local snapshot under BACKUP_ROOT (UTC timestamped)
# - Uploads snapshot to Google Drive (optionally via crypt remote)
# - Verifies upload with rclone check
# - Prunes remote snapshots to retain last 5 copies

SCRIPT_BASENAME="gdrive-backup"

# Try to source environment early so we can locate _backup_common.sh via REMOTE_PROJECT_DIR
if [[ -n "${BACKUP_ENV:-}" && -f "${BACKUP_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${BACKUP_ENV}"
fi

# Robustly locate and source _backup_common.sh
__fatal() { echo "[ERROR] $*" >&2; exit 1; }
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_candidates=(
  "${_script_dir}/_backup_common.sh"
  "${REMOTE_PROJECT_DIR:-}/scripts/_backup_common.sh"
  "/usr/local/bin/_backup_common.sh"
)
_common_sourced=0
for _c in "${_candidates[@]}"; do
  if [[ -f "${_c}" ]]; then
    # shellcheck disable=SC1090
    source "${_c}"
    _common_sourced=1
    break
  fi
done
[[ ${_common_sourced} -eq 1 ]] || __fatal "Could not locate _backup_common.sh in: ${_candidates[*]}"

# Local compose helpers (server-side)
local_compose_cmd() {
  local proj="${REMOTE_PROJECT_DIR:?REMOTE_PROJECT_DIR not set}"
  local file="${COMPOSE_FILE:?COMPOSE_FILE not set}"
  if docker compose version >/dev/null 2>&1; then
    echo "cd ${proj} && docker compose -f ${file}"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "cd ${proj} && docker-compose -f ${file}"
  else
    die "Neither 'docker compose' nor 'docker-compose' found on server"
  fi
}

local_pg_db() {
  local compose
  compose=$(local_compose_cmd)
  # shellcheck disable=SC2016
  local val
  val=$(${compose} exec -T ${PG_SERVICE} sh -lc 'printenv POSTGRES_DB || printenv PGDATABASE' 2>/dev/null | tr -d "\r" || true)
  if [[ -z "${val}" ]]; then
    # Fallback to .env DB_NAME
    val=$(dotenv_value DB_NAME || true)
  fi
  echo -n "${val}"
}

local_pg_user() {
  local compose
  compose=$(local_compose_cmd)
  # shellcheck disable=SC2016
  local val
  val=$(${compose} exec -T ${PG_SERVICE} sh -lc 'printenv POSTGRES_USER || printenv PGUSER' 2>/dev/null | tr -d "\r" || true)
  if [[ -z "${val}" ]]; then
    # Fallback to .env DB_USER
    val=$(dotenv_value DB_USER || true)
  fi
  echo -n "${val}"
}

dotenv_value() {
  local key="$1"
  local file="${REMOTE_PROJECT_DIR:-}/.env"
  if [[ -f "${file}" ]]; then
    local line
    line=$(grep -E "^[[:space:]]*${key}=" "${file}" | tail -n1 || true)
    if [[ -n "${line}" ]]; then
      local val
      val="${line#*=}"
      val="${val%$'\r'}"
      # strip surrounding quotes if present
      val="${val%\"}"; val="${val#\"}"
      val="${val%\'}"; val="${val#\'}"
      echo -n "${val}"
      return 0
    fi
  fi
  return 1
}

export -f local_compose_cmd local_pg_db local_pg_user dotenv_value

main() {
  with_lock "gdrive-backup" bash -c '
    check_host_deps

    # Required env for rclone
    : "${RCLONE_REMOTE:?Set RCLONE_REMOTE to your rclone remote name, e.g., gdrive or gcrypt}"
    RCLONE_CONFIG_FILE="${RCLONE_CONFIG_FILE:-/etc/rclone/rclone.conf}"
    if [[ ! -f "${RCLONE_CONFIG_FILE}" ]]; then
      die "Rclone config not found: ${RCLONE_CONFIG_FILE}. Configure rclone first."
    fi

    export RCLONE_CONFIG="${RCLONE_CONFIG_FILE}"

    # Tuning flags for rclone to Drive
    RCLONE_COMMON_FLAGS=(
      "--transfers=4"
      "--checkers=8"
      "--tpslimit=8"
      "--fast-list"
      "--retries=5"
      "--low-level-retries=10"
      "--drive-chunk-size=64M"
      "--stats=30s"
    )
    if [[ "${DRY_RUN:-0}" = "1" ]]; then
      RCLONE_COMMON_FLAGS+=("--dry-run")
    fi

    ts=$(ts_utc)
    snap_dir="${BACKUP_ROOT}/${ts}"
    mkdir -p "${snap_dir}"
    log "Starting remote snapshot ${ts} -> ${snap_dir}"

    compose=$(local_compose_cmd)
    mode=$(resolve_media_mode)
    gitrev=$(git -C "${REMOTE_PROJECT_DIR}" rev-parse --short HEAD 2>/dev/null || true)

    # 1) DB dump (custom format)
    PG_DB_RESOLVED="$(local_pg_db)"; PG_USER_RESOLVED="$(local_pg_user)"
    [[ -n "${PG_DB_RESOLVED}" ]] || die "Unable to resolve PG_DB"
    [[ -n "${PG_USER_RESOLVED}" ]] || die "Unable to resolve PG_USER"
    log "Resolved DB: name=${PG_DB_RESOLVED} user=${PG_USER_RESOLVED}"
    log "Dumping Postgres database ${PG_DB_RESOLVED} from service ${PG_SERVICE}"
    ${compose} exec -T ${PG_SERVICE} pg_dump -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED} -Fc > "${snap_dir}/db.dump"

    # 2) Schema-only
    log "Dumping schema-only"
    ${compose} exec -T ${PG_SERVICE} pg_dump -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED} --schema-only > "${snap_dir}/schema.sql"

    # 3) Roles (best effort)
    if ${compose} exec -T ${PG_SERVICE} sh -lc "command -v pg_dumpall >/dev/null" >/dev/null 2>&1; then
      log "Dumping roles (best effort)"
      if ${compose} exec -T ${PG_SERVICE} pg_dumpall --roles-only -U ${PG_USER_RESOLVED} > "${snap_dir}/roles.sql"; then
        :
      else
        warn "Roles dump failed; continuing without roles.sql"
        rm -f "${snap_dir}/roles.sql" || true
      fi
    else
      warn "pg_dumpall not found in container; skipping roles dump"
    fi

    # 4) Media snapshot (align with existing convention: prefer volume tar unless host bind is present)
    if [[ "${mode}" == "rsync" ]]; then
      log "Media mode: rsync incremental from ${MEDIA_BIND_HOST_PATH}"
      mkdir -p "${snap_dir}/media"
      linkdest=""
      if [[ -d "${BACKUP_ROOT}/latest/media" ]]; then linkdest="--link-dest=${BACKUP_ROOT}/latest/media"; fi
      rsync_opts=("-aH" "--delete" "--numeric-ids" "--partial" "--info=stats2,progress2")
      src="${MEDIA_BIND_HOST_PATH%/}/"
      if [[ "${DRY_RUN:-0}" = "1" ]]; then rsync_opts+=("--dry-run"); fi
      run_rsync "${rsync_opts[@]}" ${linkdest:+"${linkdest}"} "${src}" "${snap_dir}/media/"
    else
      log "Media mode: volume-tar from docker volume ${MEDIA_VOLUME_NAME} -> media.tar.gz"
      out_file="${snap_dir}/media.tar.gz"
      if docker volume inspect ${MEDIA_VOLUME_NAME} >/dev/null 2>&1; then
        if [[ "${DRY_RUN:-0}" = "1" ]]; then
          echo "[DRY_RUN] docker run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -c 'cd /data && tar -cz .' > ${out_file}"
        else
          docker run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -c "cd /data && tar -cz ." > "${out_file}"
        fi
      else
        warn "Volume ${MEDIA_VOLUME_NAME} not found, falling back to web container mount at ${MEDIA_MOUNT_PATH_IN_WEB}"
        if [[ "${DRY_RUN:-0}" = "1" ]]; then
          echo "[DRY_RUN] ${compose} exec -T web tar -cz -C ${MEDIA_MOUNT_PATH_IN_WEB} . > ${out_file}"
        else
          ${compose} exec -T web tar -cz -C ${MEDIA_MOUNT_PATH_IN_WEB} . > "${out_file}"
        fi
      fi
    fi

    # 5) Manifest
    manifest="${snap_dir}/manifest.json"
    write_manifest "${manifest}" \
      TS="${ts}" \
      HOSTNAME="${HOSTNAME:-}" \
      COMPOSE_FILE="${COMPOSE_FILE}" \
      COMPOSE_CMD="${compose}" \
      PG_SERVICE="${PG_SERVICE}" \
      MEDIA_MODE="${mode}" \
      MEDIA_VOLUME_NAME="${MEDIA_VOLUME_NAME}" \
      MEDIA_BIND_HOST_PATH="${MEDIA_BIND_HOST_PATH:-}" \
      GIT_REV="${gitrev}"

    # 6) Checksums
    (
      cd "${snap_dir}"
      : > SHA256SUMS.txt
      for f in db.dump schema.sql roles.sql media.tar.gz; do
        if [[ -f "$f" ]]; then
          printf "%s  %s\n" "$(sha256_file "$f")" "$f" >> SHA256SUMS.txt
        fi
      done
    )

    # 7) Update latest symlink and prune local
    update_latest_symlink "${snap_dir}"
    prune_local_snapshots

    # 8) Upload to Google Drive (folder hierarchy by date)
    yyyy=$(date -u -d "@$(date -u +%s)" +%Y 2>/dev/null || date -u +%Y)
    mm=$(date -u -d "@$(date -u +%s)" +%m 2>/dev/null || date -u +%m)
    dd=$(date -u -d "@$(date -u +%s)" +%d 2>/dev/null || date -u +%d)
    remote_base="${RCLONE_REMOTE}:app/snapshots/${yyyy}/${mm}/${dd}/${ts}"
    log "Uploading snapshot to ${remote_base}"
    rclone copy "${snap_dir}" "${remote_base}" "${RCLONE_COMMON_FLAGS[@]}" \
      --log-level INFO --log-file "$(_log_file_for "${SCRIPT_BASENAME}")"

    # 9) Verify upload one-way
    log "Verifying uploaded snapshot"
    rclone check "${snap_dir}" "${remote_base}" --one-way "${RCLONE_COMMON_FLAGS[@]}" \
      --log-level INFO --log-file "$(_log_file_for "${SCRIPT_BASENAME}")"

    # 10) Remote retention: keep last 5 snapshot folders overall
    # List snapshot paths sorted desc, skip first 5, delete the rest
    log "Applying remote retention: keep last 5 snapshots"
    mapfile -t snaps < <(rclone lsf -R "${RCLONE_REMOTE}:app/snapshots" --dirs-only --format p \
      | grep -E "^20[0-9]{2}/[0-1][0-9]/[0-3][0-9]/[0-9TZ-]+/$" \
      | sort -r)
    if (( ${#snaps[@]} > 5 )); then
      for (( i=5; i<${#snaps[@]}; i++ )); do
        old="${snaps[$i]}"
        log "Deleting old remote snapshot: ${old}"
        rclone purge "${RCLONE_REMOTE}:app/snapshots/${old}" "${RCLONE_COMMON_FLAGS[@]}" \
          --log-level INFO --log-file "$(_log_file_for "${SCRIPT_BASENAME}")" || warn "Failed to purge ${old}"
      done
    fi

    log "Backup to Google Drive completed: ${snap_dir} -> ${remote_base}"
  '
}

main "$@"


