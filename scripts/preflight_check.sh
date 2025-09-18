#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="preflight"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

with_lock "preflight" bash -c '
  log "Starting preflight checks on host and remote"
  check_host_deps

  # Remote connectivity
  log "Checking SSH connectivity to ${SSH_USER}@${SSH_HOST}"
  if ! ssh_exec "echo ok" >/dev/null 2>&1; then
    die "SSH to ${SSH_USER}@${SSH_HOST} failed. Ensure keys and ${SSH_OPTS} are correct."
  fi

  # Check docker on remote
  log "Checking docker on remote"
  ssh_exec "docker version --format '{{.Server.Version}}'" >/dev/null 2>&1 || die "Docker not available on remote"

  # Compose detection
  cmd=$(remote_compose_cmd) || die "Failed to detect compose on remote"
  log "Remote compose command: ${cmd}"

  # Compose file presence
  ssh_exec "test -f ${REMOTE_PROJECT_DIR}/${COMPOSE_FILE}" || die "Compose file not found at ${REMOTE_PROJECT_DIR}/${COMPOSE_FILE}"

  # Postgres service reachable via compose ps (best effort)
  ssh_exec "${cmd} ps ${PG_SERVICE} >/dev/null 2>&1 || true"

  # Media mode validation
  mode=$(resolve_media_mode)
  if [[ "${mode}" == "rsync" ]]; then
    log "Media mode: rsync (bind path)"
    ssh_exec "test -d ${MEDIA_BIND_HOST_PATH}" || die "MEDIA_BIND_HOST_PATH does not exist on VPS: ${MEDIA_BIND_HOST_PATH}"
  else
    log "Media mode: volume-tar (docker volume ${MEDIA_VOLUME_NAME})"
    ssh_exec "docker volume inspect ${MEDIA_VOLUME_NAME} >/dev/null" || warn "Media volume ${MEDIA_VOLUME_NAME} not found yet; will be created by compose on first run"
  fi

  # Backups dir
  log "Ensuring backup directories exist at ${BACKUP_ROOT}"
  mkdir -p "${BACKUP_ROOT}/logs" "${BACKUP_ROOT}/.locks"

  log "Preflight checks passed"
'
