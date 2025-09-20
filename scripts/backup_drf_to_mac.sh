#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="backup"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

main() {
  with_lock "backup" bash -c '
    check_host_deps
    ts=$(ts_utc)
    snap_dir="${BACKUP_ROOT}/${ts}"
    mkdir -p "${snap_dir}"
    log "Starting backup snapshot ${ts} -> ${snap_dir}"

    compose=$(remote_compose_cmd)
    mode=$(resolve_media_mode)
    gitrev=$(remote_git_rev || true)

    # 1) DB dump (custom format)
    PG_DB_RESOLVED="$(resolve_pg_db)"; PG_USER_RESOLVED="$(resolve_pg_user)"
    [[ -n "${PG_DB_RESOLVED}" ]] || die "Unable to resolve PG_DB; set PG_DB in .backup.env or ensure POSTGRES_DB in container"
    [[ -n "${PG_USER_RESOLVED}" ]] || die "Unable to resolve PG_USER; set PG_USER in .backup.env or ensure POSTGRES_USER in container"
    log "Dumping Postgres database ${PG_DB_RESOLVED} from service ${PG_SERVICE}"
    ssh_exec "${compose} exec -T ${PG_SERVICE} pg_dump -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED} -Fc" > "${snap_dir}/db.dump"

    # 2) Schema-only
    log "Dumping schema-only"
    ssh_exec "${compose} exec -T ${PG_SERVICE} pg_dump -U ${PG_USER_RESOLVED} -d ${PG_DB_RESOLVED} --schema-only" > "${snap_dir}/schema.sql"

    # 3) Roles (best effort)
    if ssh_exec "${compose} exec -T ${PG_SERVICE} sh -lc \"command -v pg_dumpall >/dev/null\"" >/dev/null 2>&1; then
      log "Dumping roles (best effort)"
      if ssh_exec "${compose} exec -T ${PG_SERVICE} pg_dumpall --roles-only -U ${PG_USER_RESOLVED}" > "${snap_dir}/roles.sql"; then
        :
      else
        warn "Roles dump failed; continuing without roles.sql"
        rm -f "${snap_dir}/roles.sql" || true
      fi
    else
      warn "pg_dumpall not found in container; skipping roles dump"
    fi

    # 4) Media snapshot
    if [[ "${mode}" == "rsync" ]]; then
      log "Media mode: rsync incremental from ${MEDIA_BIND_HOST_PATH}"
      mkdir -p "${snap_dir}/media"
      linkdest=""
      if [[ -d "${BACKUP_ROOT}/latest/media" ]]; then linkdest="--link-dest=${BACKUP_ROOT}/latest/media"; fi
      rsync_opts=("-aH" "--delete" "--numeric-ids" "--partial" "--info=stats2,progress2")
      src="${SSH_USER}@${SSH_HOST}:${MEDIA_BIND_HOST_PATH%/}/"
      if [[ "${DRY_RUN:-0}" = "1" ]]; then rsync_opts+=("--dry-run"); fi
      run_rsync ${SSH_OPTS:-} "${rsync_opts[@]}" ${linkdest:+"${linkdest}"} "${src}" "${snap_dir}/media/"
    else
      log "Media mode: volume-tar from docker volume ${MEDIA_VOLUME_NAME} -> media.tar.gz"
      out_file="${snap_dir}/media.tar.gz"
      # Prefer docker run -v volume
      if remote_docker "volume inspect ${MEDIA_VOLUME_NAME} >/dev/null 2>&1"; then
        # Stream tar.gz from remote to local file
        if [[ "${DRY_RUN:-0}" = "1" ]]; then
          echo "[DRY_RUN] ssh ${SSH_USER}@${SSH_HOST} $(remote_docker_cmd) run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -c \"cd /data && tar -cz .\" > ${out_file}"
        else
          ssh_exec "$(remote_docker_cmd) run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -c \"cd /data && tar -cz .\"" > "${out_file}"
        fi
      else
        # Fallback: tar from inside web container mount
        warn "Volume ${MEDIA_VOLUME_NAME} not found, falling back to web container mount at ${MEDIA_MOUNT_PATH_IN_WEB}"
        if [[ "${DRY_RUN:-0}" = "1" ]]; then
          echo "[DRY_RUN] ssh ${SSH_USER}@${SSH_HOST} ${compose} exec -T web tar -cz -C ${MEDIA_MOUNT_PATH_IN_WEB} . > ${out_file}"
        else
          ssh_exec "${compose} exec -T web tar -cz -C ${MEDIA_MOUNT_PATH_IN_WEB} ." > "${out_file}"
        fi
      fi
    fi

    # 5) Manifest
    manifest="${snap_dir}/manifest.json"
    write_manifest "${manifest}" \
      TS="${ts}" \
      SSH_HOST="${SSH_HOST}" \
      COMPOSE_FILE="${COMPOSE_FILE}" \
      COMPOSE_CMD="${compose}" \
      PG_SERVICE="${PG_SERVICE}" \
      MEDIA_MODE="${mode}" \
      MEDIA_VOLUME_NAME="${MEDIA_VOLUME_NAME}" \
      MEDIA_BIND_HOST_PATH="${MEDIA_BIND_HOST_PATH}" \
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

    # 7) Quick validation of db.dump
    if command -v pg_restore >/dev/null 2>&1; then
      pg_restore -l "${snap_dir}/db.dump" >/dev/null
    else
      warn "pg_restore not found on host; skipping quick validation"
    fi

    # 8) Update latest symlink
    update_latest_symlink "${snap_dir}"

    # 9) Prune local snapshots
    prune_local_snapshots

    # 10) Size summary
    log "Artifacts sizes: db.dump=$(file_size "${snap_dir}/db.dump"), schema.sql=$(file_size "${snap_dir}/schema.sql"), roles.sql=$(file_size "${snap_dir}/roles.sql"), media=$(file_size "${snap_dir}/media.tar.gz")"

    # Optional local verify restore
    if [[ "${VERIFY_RESTORE_DEFAULT:-no}" == "yes" ]]; then
      log "Running local verify restore for snapshot ${ts}"
      if "${PROJECT_ROOT}/scripts/verify_restore_local.sh" "${ts}"; then
        echo "OK" > "${snap_dir}/VERIFY_STATUS.txt"
      else
        echo "FAIL" > "${snap_dir}/VERIFY_STATUS.txt"
        warn "Local verify restore failed for ${ts}"
      fi
    fi

    # Future cloud hook (no-op placeholder)
    # cloud_post_snapshot_hook() { :; }
    # cloud_post_snapshot_hook "${snap_dir}"

    log "Backup completed: ${snap_dir}"
  '
}

main "$@"
