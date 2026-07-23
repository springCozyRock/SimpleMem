#!/usr/bin/env bash
# Start shared BGE embedding server (one GPU).
#
# Example:
#   CUDA_VISIBLE_DEVICES=4 bash scripts/run_embedding_server.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMNI_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${OMNI_ROOT}/.." && pwd)"
PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then PY="$(command -v python3)"; fi

ENV_FILE="${REPO_ROOT}/benchmarks/external/smmbench/evaluation/scripts/env.smmbench.local"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

export OMNI_EMBEDDING_MODEL="${OMNI_EMBEDDING_MODEL:-/mnt/data/bts/models/BAAI__bge-m3}"
export OMNI_EMBEDDING_HOST="${OMNI_EMBEDDING_HOST:-127.0.0.1}"
export OMNI_EMBEDDING_PORT="${OMNI_EMBEDDING_PORT:-8100}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-4}"

echo "[embedding_server] model=${OMNI_EMBEDDING_MODEL}"
echo "[embedding_server] listen=${OMNI_EMBEDDING_HOST}:${OMNI_EMBEDDING_PORT} gpu=${CUDA_VISIBLE_DEVICES}"

cd "${OMNI_ROOT}"
exec "${PY}" scripts/embedding_server.py \
  --host "${OMNI_EMBEDDING_HOST}" \
  --port "${OMNI_EMBEDDING_PORT}" \
  --model "${OMNI_EMBEDDING_MODEL}"
