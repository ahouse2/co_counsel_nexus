#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--retention-days DAYS] [--backup-dir DIR]

Creates a compressed backup of storage directories (documents, graphs, telemetry)
and prunes archives older than the configured retention window. Complements the
`storage-backup` Docker service for on-demand recovery drills.
USAGE
}

RETENTION_DAYS=7
BACKUP_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STORAGE_ROOT="${ROOT_DIR}/var/storage"
DEFAULT_BACKUP_DIR="${ROOT_DIR}/var/backups"
BACKUP_DIR=${BACKUP_DIR:-${DEFAULT_BACKUP_DIR}}

mkdir -p "${BACKUP_DIR}" "${STORAGE_ROOT}/documents" "${STORAGE_ROOT}/graphs" "${STORAGE_ROOT}/telemetry"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
if command -v zstd >/dev/null 2>&1; then
  ARCHIVE_PATH="${BACKUP_DIR}/full-stack_${TIMESTAMP}.tar.zst"
  TAR_CMD=("${TAR_BIN:-tar}" --sort=name --use-compress-program="zstd -T0" -cf "${ARCHIVE_PATH}")
  PRUNE_PATTERN='full-stack_*.tar.zst'
else
  echo "zstd not found; falling back to gzip compression" >&2
  ARCHIVE_PATH="${BACKUP_DIR}/full-stack_${TIMESTAMP}.tar.gz"
  TAR_CMD=("${TAR_BIN:-tar}" --sort=name -czf "${ARCHIVE_PATH}")
  PRUNE_PATTERN='full-stack_*.tar.gz'
fi

echo "Creating archive ${ARCHIVE_PATH}"
"${TAR_CMD[@]}" -C "${STORAGE_ROOT}" documents graphs telemetry

echo "Pruning backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -maxdepth 1 -name "${PRUNE_PATTERN}" -type f -mtime +"${RETENTION_DAYS}" -print -delete

echo "Backup complete: ${ARCHIVE_PATH}"
