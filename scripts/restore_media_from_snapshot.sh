#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="restore-media"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

SNAP_ID="${1:-}"
CONFIRM="${2:-}"

[[ -n "${SNAP_ID}" ]] || die "Usage: $0 <snapshot_id|latest> [--yes]"
[[ "${CONFIRM:-}" == "--yes" ]] || die "Refusing to proceed without --yes"

with_lock "restore-media" bash -c '
  check_host_deps
  mode=$(resolve_media_mode)
  if [[ "${SNAP_ID}" == "latest" ]]; then snap_dir="${BACKUP_ROOT}/latest"; else snap_dir="${BACKUP_ROOT}/${SNAP_ID}"; fi
  if [[ "${mode}" == "rsync" ]]; then
    [[ -d "${snap_dir}/media" ]] || die "media/ directory not found in snapshot"
    log "Rsync restoring media to VPS path ${MEDIA_BIND_HOST_PATH}"
    local rsync_opts=("-aH" "--delete" "--numeric-ids" "--info=stats2,progress2")
    if [[ "${DRY_RUN:-0}" = "1" ]]; then rsync_opts+=("--dry-run"); fi
    run_rsync ${SSH_OPTS:-} "${rsync_opts[@]}" "${snap_dir}/media/" "${SSH_USER}@${SSH_HOST}:${MEDIA_BIND_HOST_PATH%/}/"
  else
    local tarfile="${snap_dir}/media.tar.gz"
    [[ -f "${tarfile}" ]] || die "media.tar.gz not found in snapshot"
    log "Streaming media.tar.gz into docker volume ${MEDIA_VOLUME_NAME} on VPS"
    if [[ "${DRY_RUN:-0}" = "1" ]]; then
      echo "[DRY_RUN] cat ${tarfile} | ssh ${SSH_USER}@${SSH_HOST} $(remote_docker_cmd) run --rm -i -v ${MEDIA_VOLUME_NAME}:/data alpine tar -xz -C /data"
    else
      cat "${tarfile}" | ssh ${SSH_OPTS:-} "${SSH_USER}@${SSH_HOST}" "$(remote_docker_cmd) run --rm -i -v ${MEDIA_VOLUME_NAME}:/data alpine tar -xz -C /data"
    fi
  fi
  log "Media restore completed for ${SNAP_ID}"
'
