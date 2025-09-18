#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

SCRIPT_BASENAME="prune"
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_backup_common.sh"

with_lock "prune" bash -c '
  log "Pruning local snapshots to KEEP_LOCAL=${KEEP_LOCAL}"
  prune_local_snapshots
  log "Prune completed"
'
