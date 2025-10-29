#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${ROOT_DIR}"

PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_PATH="${ROOT_DIR}/.venv"
USE_VENV=${USE_VENV:-true}

if [[ -n "${CI:-}" ]]; then
  USE_VENV=false
fi

if [[ "${USE_VENV}" == "true" ]]; then
  if [[ ! -d "${VENV_PATH}" ]]; then
    "${PYTHON_BIN}" -m venv "${VENV_PATH}"
  fi
  # shellcheck source=/dev/null
  source "${VENV_PATH}/bin/activate"
fi

if command -v uv >/dev/null 2>&1; then
  uv pip sync backend/uv.lock
  uv pip install --upgrade ruff mypy pytest
else
  "${PYTHON_BIN}" -m pip install --upgrade pip
  "${PYTHON_BIN}" -m pip install -r backend/requirements.txt
  "${PYTHON_BIN}" -m pip install ruff mypy pytest
fi

echo "Backend environment ready."
if [[ "${USE_VENV}" == "true" ]]; then
  echo "Activate via: source ${VENV_PATH}/bin/activate"
fi
