#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="audit"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

with_lock "audit" bash -c '
  check_host_deps
  mode=$(resolve_media_mode)
  latest_dir="${BACKUP_ROOT}/latest"
  [[ -d "${latest_dir}" ]] || die "No latest snapshot present"
  n=${SAMPLE_SIZE_FOR_AUDIT:-200}
  mismatches=0

  if [[ "${mode}" == "rsync" ]]; then
    log "Audit mode: rsync bind path"
    list_file=$(mktemp)
    find "${latest_dir}/media" -type f | sample_lines "${n}" > "${list_file}"
    while IFS= read -r f; do
      rel="${f#${latest_dir}/media/}"
      local_hash=$(sha256_file "${f}")
      remote_path="${MEDIA_BIND_HOST_PATH%/}/${rel}"
      remote_hash
      remote_hash=$(ssh_exec "sha256sum \"${remote_path}\" | awk '{print $1}'" 2>/dev/null || true)
      if [[ -z "${remote_hash}" ]]; then
        warn "Missing on VPS: ${remote_path}"
        mismatches=$((mismatches+1))
      elif [[ "${local_hash}" != "${remote_hash}" ]]; then
        warn "Hash mismatch: ${rel}"
        mismatches=$((mismatches+1))
      fi
    done < "${list_file}"
    rm -f "${list_file}"
  else
    log "Audit mode: volume-tar comparing against media.tar.gz"
    tarfile="${latest_dir}/media.tar.gz"
    [[ -f "${tarfile}" ]] || die "media.tar.gz not found in latest snapshot"
    # Get sample of files from remote volume
    sample
    if ssh_exec "docker volume inspect ${MEDIA_VOLUME_NAME} >/dev/null 2>&1"; then
      sample=$(ssh_exec "docker run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -lc 'cd /data && find . -type f | sed s#^./## | shuf -n ${n}'")
    else
      sample=$(ssh_exec "$(remote_compose_cmd) exec -T web sh -lc 'cd ${MEDIA_MOUNT_PATH_IN_WEB} && find . -type f | sed s#^./## | shuf -n ${n}'")
    fi
    while IFS= read -r rel; do
      [[ -z "${rel}" ]] && continue
      local remote_hash
      # Remote hash
      if ssh_exec "docker volume inspect ${MEDIA_VOLUME_NAME} >/dev/null 2>&1"; then
        remote_hash=$(ssh_exec "docker run --rm -v ${MEDIA_VOLUME_NAME}:/data alpine sh -lc 'cd /data && sha256sum \"${rel}\" | awk \"{print \\\$1}\"'" 2>/dev/null || true)
      else
        remote_hash=$(ssh_exec "$(remote_compose_cmd) exec -T web sh -lc 'cd ${MEDIA_MOUNT_PATH_IN_WEB} && sha256sum \"${rel}\" | awk \"{print \\\$1}\"'" 2>/dev/null || true)
      fi
      # Local hash by extracting a single file stream
      local local_hash
      if command -v gtar >/dev/null 2>&1; then
        local_hash=$(gtar -xzOf "${tarfile}" "${rel}" 2>/dev/null | shasum -a 256 | awk '{print $1}')
      else
        local_hash=$(tar -xzOf "${tarfile}" "${rel}" 2>/dev/null | shasum -a 256 | awk '{print $1}')
      fi
      if [[ -z "${remote_hash}" || -z "${local_hash}" ]]; then
        warn "Could not hash: ${rel}"
        mismatches=$((mismatches+1))
      elif [[ "${remote_hash}" != "${local_hash}" ]]; then
        warn "Hash mismatch: ${rel}"
        mismatches=$((mismatches+1))
      fi
    done <<< "${sample}"
  fi

  if (( mismatches > 0 )); then
    warn "Audit found ${mismatches} mismatches"
    exit 2
  fi
  log "Audit passed with 0 mismatches"
'
