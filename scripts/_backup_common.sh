#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Common helpers for backup scripts (Mac host driving a remote Ubuntu VPS)

# Resolve repo root based on this script's location (assumes scripts/ under project root)
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${_SCRIPT_DIR}/.." && pwd)"

# Load env
_ENV_FILE_DEFAULT="${PROJECT_ROOT}/.backup.env"
if [[ -n "${BACKUP_ENV:-}" ]]; then
  ENV_FILE="${BACKUP_ENV}"
else
  ENV_FILE="${_ENV_FILE_DEFAULT}"
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}. Copy .backup.env.example to .backup.env and configure." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${ENV_FILE}"

# Bootstrap directories
BACKUP_ROOT="${BACKUP_ROOT:?BACKUP_ROOT must be set to an absolute path}"
[[ "${BACKUP_ROOT}" = /* ]] || { echo "BACKUP_ROOT must be an absolute path: ${BACKUP_ROOT}" >&2; exit 1; }
mkdir -p "${BACKUP_ROOT}/logs" "${BACKUP_ROOT}/.locks"

# Timestamp (UTC)
ts_utc() { date -u +%Y%m%dT%H%M%SZ; }

# Logging to stdout and file
_log_file_for() { local name="$1"; local dts; dts=$(date +%Y%m%d); echo "${BACKUP_ROOT}/logs/${name}-${dts}.log"; }
log() { local msg="$*"; echo "[INFO] ${msg}" | tee -a "$(_log_file_for "${SCRIPT_BASENAME:-backup}")"; }
warn() { local msg="$*"; echo "[WARN] ${msg}" | tee -a "$(_log_file_for "${SCRIPT_BASENAME:-backup}")" >&2; }
die() { local msg="$*"; echo "[ERROR] ${msg}" | tee -a "$(_log_file_for "${SCRIPT_BASENAME:-backup}")" >&2; exit 1; }

trap 'die "failed at line $LINENO"' ERR

# Concurrency lock helper (flock)
with_lock() { local lock_name="$1"; shift; local lock_file="${BACKUP_ROOT}/.locks/${lock_name}.lock"; mkdir -p "$(dirname "${lock_file}")"; if command -v flock >/dev/null 2>&1; then flock -w 1 "${lock_file}" "$@"; else warn "flock not found; proceeding without lock for ${lock_name}"; "$@"; fi }

# DRY RUN guard wrappers
run_cmd() { if [[ "${DRY_RUN:-0}" = "1" ]]; then echo "[DRY_RUN] $*"; else eval "$*"; fi }
run_rsync() { if [[ "${DRY_RUN:-0}" = "1" ]]; then rsync --version >/dev/null 2>&1 || true; echo "[DRY_RUN] rsync $*"; else rsync "$@"; fi }
run_rm_rf() { if [[ "${DRY_RUN:-0}" = "1" ]]; then echo "[DRY_RUN] rm -rf $*"; else rm -rf "$@"; fi }

# Cross-platform sha256 (mac uses shasum -a 256)
sha256_file() { local f="$1"; if command -v shasum >/dev/null 2>&1; then shasum -a 256 "${f}" | awk '{print $1}'; elif command -v sha256sum >/dev/null 2>&1; then sha256sum "${f}" | awk '{print $1}'; else die "Neither shasum nor sha256sum found"; fi }

# Required tools checks (host/mac)
require_host_tool() { local bin="$1"; command -v "${bin}" >/dev/null 2>&1 || die "Missing required tool on host: ${bin}"; }
check_host_deps() { require_host_tool ssh; require_host_tool rsync; require_host_tool tar; require_host_tool docker; require_host_tool sed; require_host_tool awk; require_host_tool head; require_host_tool tail; require_host_tool date; command -v pg_restore >/dev/null 2>&1 || warn "pg_restore not found; verify script may fail"; command -v flock >/dev/null 2>&1 || warn "flock not found; locking disabled"; }

# Remote execution helpers
ssh_base() { echo ssh ${SSH_OPTS:-} "${SSH_USER:?}@${SSH_HOST:?}"; }
ssh_exec() { local cmd="$*"; local s; s=$(ssh_base); ${s} "${cmd}"; }
ssh_copy_to_remote() { local src="$1"; local dst="$2"; scp ${SSH_OPTS:-} "${src}" "${SSH_USER}@${SSH_HOST}:${dst}"; }

# Detect compose command on VPS
remote_compose_cmd() { local base="cd ${REMOTE_PROJECT_DIR:?} && "; local cmd=""; if ssh_exec "docker compose version >/dev/null 2>&1"; then cmd="docker compose -f ${COMPOSE_FILE}"; elif ssh_exec "docker-compose version >/dev/null 2>&1"; then cmd="docker-compose -f ${COMPOSE_FILE}"; else die "Neither 'docker compose' nor 'docker-compose' found on remote"; fi; echo "${base}${cmd}"; }

# Git commit on remote (best effort)
remote_git_rev() { ssh_exec "git -C ${REMOTE_PROJECT_DIR} rev-parse --short HEAD" 2>/dev/null || true }

# Media mode resolver
resolve_media_mode() { if [[ -n "${MEDIA_BIND_HOST_PATH:-}" ]]; then echo rsync; else echo volume-tar; fi }

# Atomic latest symlink update
update_latest_symlink() { local new_dir="$1"; local latest_link="${BACKUP_ROOT}/latest"; local tmp_link="${latest_link}.tmp"; ln -sfn "${new_dir}" "${tmp_link}"; mv -Tf "${tmp_link}" "${latest_link}" 2>/dev/null || { rm -f "${latest_link}"; ln -s "${new_dir}" "${latest_link}"; } }

# Prune local snapshots to KEEP_LOCAL
prune_local_snapshots() { local keep="${KEEP_LOCAL:-5}"; local dir="${BACKUP_ROOT}"; local snaps; IFS=$'\n' read -r -d '' -a snaps < <(find "${dir}" -maxdepth 1 -type d -name '20*' -print 2>/dev/null | sed "s#^${dir}/##" | sort -r && printf '\0'); local count=${#snaps[@]}; if (( count <= keep )); then return 0; fi; for ((i=keep;i<count;i++)); do local to_del="${dir}/${snaps[$i]}"; log "Pruning old snapshot ${to_del}"; run_rm_rf "${to_del}"; done }

# Manifest writer without jq
write_manifest() { local outfile="$1"; shift; local kv_pairs=("$@"); local json="{"; local first=1; for pair in "${kv_pairs[@]}"; do local key="${pair%%=*}"; local val="${pair#*=}"; val=${val//"/\"}; if [[ ${first} -eq 0 ]]; then json+=" ,"; fi; json+=" \"${key}\": \"${val}\""; first=0; done; json+=" }"; printf '%s\n' "${json}" > "${outfile}" }

# File size pretty
file_size() { local f="$1"; if [[ -f "${f}" ]]; then du -h "${f}" | awk '{print $1}'; else echo "-"; fi }

# Compose exec/ps helpers
remote_compose_exec() { local service="$1"; shift; local cmd; cmd=$(remote_compose_cmd); ssh_exec "${cmd} exec -T ${service} $*" }

# Random sampler count numbers [1..N]
rand_n() { local n="$1"; if command -v shuf >/dev/null 2>&1; then shuf -i 1-"${n}" -n 1; elif command -v jot >/dev/null 2>&1; then jot -r 1 1 "${n}"; else awk -v n="${n}" 'BEGIN{srand(); printf "%d\n", int(1+rand()*n)}'; fi }

# Sample at most K lines from stdin (reservoir sampling fallback if shuf missing)
sample_lines() { local k="$1"; if command -v shuf >/dev/null 2>&1; then shuf -n "${k}"; else awk -v k="${k}" 'BEGIN{srand(); n=0} {n++; if (n<=k) a[n]=$0; else {i=int(rand()*n)+1; if (i<=k) a[i]=$0}} END{for (i=1;i<=k;i++) if (i in a) print a[i]}' ; fi }

# Resolve Postgres DB/user from remote container env if not provided in .backup.env
remote_pg_db() { local compose; compose=$(remote_compose_cmd); local val; val=$(ssh_exec "${compose} exec -T ${PG_SERVICE} sh -lc 'printenv POSTGRES_DB || printenv PGDATABASE'" 2>/dev/null || true); echo -n "${val}"; }
remote_pg_user() { local compose; compose=$(remote_compose_cmd); local val; val=$(ssh_exec "${compose} exec -T ${PG_SERVICE} sh -lc 'printenv POSTGRES_USER || printenv PGUSER'" 2>/dev/null || true); echo -n "${val}"; }
resolve_pg_db() { local val="${PG_DB:-}"; if [[ -z "${val}" || "${val}" == "your_db_name" ]]; then val="$(remote_pg_db)"; fi; echo -n "${val}"; }
resolve_pg_user() { local val="${PG_USER:-}"; if [[ -z "${val}" || "${val}" == "your_db_user" ]]; then val="$(remote_pg_user)"; fi; echo -n "${val}"; }

# End of common library
