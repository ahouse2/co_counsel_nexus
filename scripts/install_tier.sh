#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") <community|pro|enterprise> [--dry-run]

Bundles compose services, tier-specific environment defaults, and
installer automation for the selected deployment tier.
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

tier="$1"
dry_run="0"
if [[ $# -gt 1 ]]; then
  if [[ "$2" == "--dry-run" ]]; then
    dry_run="1"
  else
    echo "Unrecognised option: $2" >&2
    usage
    exit 1
  fi
fi

case "$tier" in
  community|pro|enterprise)
    ;;
  *)
    echo "Unsupported tier: $tier" >&2
    usage
    exit 1
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/infra/docker-compose.yml"
profile_file="$repo_root/infra/profiles/${tier}.env"

if [[ ! -f "$compose_file" ]]; then
  echo "Compose file not found: $compose_file" >&2
  exit 1
fi

if [[ ! -f "$profile_file" ]]; then
  echo "Tier profile missing: $profile_file" >&2
  exit 1
fi

storage_root="$repo_root/storage"
billing_dir="$storage_root/billing"
if [[ "$dry_run" == "0" ]]; then
  mkdir -p "$billing_dir"
  cp "$profile_file" "$repo_root/.env"
fi

echo "Selected tier: $tier"
echo "Using compose file: $compose_file"
echo "Applying environment defaults from: $profile_file"

compose_cmd=(docker compose --env-file "$profile_file" --profile "$tier" -f "$compose_file" up -d)

if [[ "$dry_run" == "1" ]]; then
  printf 'DRY RUN: '
  printf '%q ' "${compose_cmd[@]}"
  printf '\n'
  exit 0
fi

"${compose_cmd[@]}"

echo "Deployment for tier '$tier' initialised."
