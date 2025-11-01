#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--profile community|pro|enterprise] [--provider gemini|openai|ollama|huggingface] [--secondary-provider PROVIDER_ID] [--model MODEL_ID] [--embedding-model MODEL_ID] [--vision-model MODEL_ID] [--with-gpu] [--skip-download] [--skip-migrations]

Orchestrates full-stack bring-up: prepares Python dependencies, ensures model caches,
starts Docker Compose services, and runs Neo4j/Qdrant migrations.
USAGE
}

PROFILE="community"
PROVIDER="gemini"
SECONDARY_PROVIDER="openai"
CHAT_MODEL=""
EMBEDDING_MODEL=""
VISION_MODEL=""
WITH_GPU=false
SKIP_DOWNLOAD=false
SKIP_MIGRATIONS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    --model)
      CHAT_MODEL="$2"
      shift 2
      ;;
    --embedding-model)
      EMBEDDING_MODEL="$2"
      shift 2
      ;;
    --vision-model)
      VISION_MODEL="$2"
      shift 2
      ;;
    --secondary-provider)
      SECONDARY_PROVIDER="$2"
      shift 2
      ;;
    --with-gpu)
      WITH_GPU=true
      shift 1
      ;;
    --skip-download)
      SKIP_DOWNLOAD=true
      shift 1
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS=true
      shift 1
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
INFRA_DIR="${ROOT_DIR}/infra"
PROFILE_FILE="${INFRA_DIR}/profiles/${PROFILE}.env"
GPU_FILE="${INFRA_DIR}/profiles/gpu.env"
RUNTIME_ENV_FILE="${INFRA_DIR}/profiles/.runtime-provider.env"

if [[ ! -f "${PROFILE_FILE}" ]]; then
  echo "Profile file ${PROFILE_FILE} not found" >&2
  exit 1
fi

if [[ "${WITH_GPU}" == "true" && ! -f "${GPU_FILE}" ]]; then
  echo "GPU overlay ${GPU_FILE} not found" >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "docker command not available" >&2; exit 1; }

set -a
# shellcheck source=/dev/null
source "${PROFILE_FILE}"
if [[ "${WITH_GPU}" == "true" ]]; then
  # shellcheck source=/dev/null
  source "${GPU_FILE}"
fi
set +a
export ROOT_DIR

# Ensure backend dependencies (qdrant-client, neo4j, etc.) are installed.
"${ROOT_DIR}/scripts/bootstrap_backend.sh"

PYTHON_BIN=${PYTHON_BIN:-python3}
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi

mkdir -p "${ROOT_DIR}/var/models/huggingface" "${ROOT_DIR}/var/models/whisper" \
  "${ROOT_DIR}/var/models/tts" "${ROOT_DIR}/var/storage/documents" \
  "${ROOT_DIR}/var/storage/graphs" "${ROOT_DIR}/var/storage/telemetry" \
  "${ROOT_DIR}/var/audio" "${ROOT_DIR}/var/backups"

# Prepare runtime provider overrides consumed by Compose/Helm
{
  echo "MODEL_PROVIDERS_PRIMARY=${PROVIDER}"
  echo "MODEL_PROVIDERS_SECONDARY=${SECONDARY_PROVIDER}"
  if [[ -n "${CHAT_MODEL}" ]]; then
    echo "DEFAULT_CHAT_MODEL=${CHAT_MODEL}"
  fi
  if [[ -n "${EMBEDDING_MODEL}" ]]; then
    echo "DEFAULT_EMBEDDING_MODEL=${EMBEDDING_MODEL}"
  fi
  if [[ -n "${VISION_MODEL}" ]]; then
    echo "DEFAULT_VISION_MODEL=${VISION_MODEL}"
  elif [[ -n "${CHAT_MODEL}" ]]; then
    echo "DEFAULT_VISION_MODEL=${CHAT_MODEL}"
  fi
} > "${RUNTIME_ENV_FILE}"

if [[ "${SKIP_DOWNLOAD}" == "false" ]]; then
  echo "Ensuring Hugging Face snapshot tooling present"
  "${PYTHON_BIN}" -m pip install --upgrade --quiet huggingface_hub==0.25.2 >/dev/null
  echo "Downloading speech-to-text model cache"
  "${PYTHON_BIN}" - <<'PY'
import os
from huggingface_hub import snapshot_download

cache_dir = os.path.join(os.environ["ROOT_DIR"], "var", "models", "huggingface")
model_id = os.environ.get("STT_MODEL_NAME", "openai/whisper-small")
snapshot_download(repo_id=model_id, cache_dir=cache_dir, resume_download=True)
PY
  echo "Downloading text-to-speech voice assets"
  "${PYTHON_BIN}" - <<'PY'
import os
from huggingface_hub import snapshot_download

voice = os.environ.get("TTS_VOICE", "en-us-blizzard_lessac")
repo = f"rhasspy/larynx-voice-{voice}"
cache_dir = os.path.join(os.environ["ROOT_DIR"], "var", "models", "huggingface")
try:
    snapshot_download(repo_id=repo, cache_dir=cache_dir, resume_download=True)
except Exception as exc:
    raise SystemExit(f"Failed to download TTS voice '{voice}' ({repo}): {exc}")
PY
fi

COMPOSE_ARGS=(--project-directory "${INFRA_DIR}" --env-file "${PROFILE_FILE}" --env-file "${RUNTIME_ENV_FILE}")
if [[ "${WITH_GPU}" == "true" ]]; then
  COMPOSE_ARGS+=(--env-file "${GPU_FILE}" --profile gpu)
fi
COMPOSE_ARGS+=(--profile "${PROFILE}")
SERVICES=(neo4j qdrant stt tts api storage-backup)
if [[ "${PROFILE}" == "pro" || "${PROFILE}" == "enterprise" ]]; then
  SERVICES+=(otel-collector)
fi
if [[ "${PROFILE}" == "enterprise" ]]; then
  SERVICES+=(grafana)
fi

echo "Starting Docker Compose services (${SERVICES[*]})"
docker compose "${COMPOSE_ARGS[@]}" up -d "${SERVICES[@]}"

wait_for_http() {
  local name="$1" url="$2" timeout="${3:-120}"
  local start=$(date +%s)
  until curl -sf "${url}" >/dev/null; do
    sleep 3
    local now=$(date +%s)
    if (( now - start > timeout )); then
      echo "Timed out waiting for ${name} at ${url}" >&2
      exit 1
    fi
  done
}

echo "Waiting for Neo4j and Qdrant health endpoints"
wait_for_http "neo4j" "http://localhost:7474" 180
wait_for_http "qdrant" "http://localhost:6333/healthz" 180

if [[ "${SKIP_MIGRATIONS}" == "false" ]]; then
  echo "Applying Neo4j migrations"
  for migration in "${INFRA_DIR}"/migrations/neo4j/*.cql; do
    [ -f "${migration}" ] || continue
    docker compose "${COMPOSE_ARGS[@]}" exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-securepassword}" -f "/var/lib/neo4j/migrations/$(basename "${migration}")"
  done

  echo "Applying Qdrant migrations"
  ROOT_DIR="${ROOT_DIR}" STT_MODEL_NAME="${STT_MODEL_NAME:-openai/whisper-small}" "${PYTHON_BIN}" "${INFRA_DIR}/migrations/qdrant/2025-10-28_chunk_collection.py"
fi

echo "Full-stack environment ready."
echo "- API: http://localhost:8000"
echo "- Neo4j Browser: http://localhost:7474"
echo "- Qdrant Console: http://localhost:6333"
if [[ "${PROFILE}" == "enterprise" ]]; then
  echo "- Grafana: http://localhost:3000"
fi
