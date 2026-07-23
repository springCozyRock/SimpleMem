#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(dirname "${SCRIPT_DIR}")"
ENV_FILE="${SCRIPT_DIR}/env.smmbench.local"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  echo "Copy env.smmbench.example to env.smmbench.local and fill MODEL_API_KEY / MODEL_API_BASE_URL." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

: "${DATASET_PARENT_DIR:?}"
: "${IMAGE_ROOT_DIR:?}"
: "${OMNISIMPLEMEM_BASELINE_ROOT:?}"
: "${SAVE_ROOT_PATH:?}"
: "${MODEL_API_KEY:?}"
: "${MODEL_API_BASE_URL:?}"

mkdir -p "${SAVE_ROOT_PATH}"

echo "[smmbench] DATASET_PARENT_DIR=${DATASET_PARENT_DIR}"
echo "[smmbench] IMAGE_ROOT_DIR=${IMAGE_ROOT_DIR}"
echo "[smmbench] OMNISIMPLEMEM_BASELINE_ROOT=${OMNISIMPLEMEM_BASELINE_ROOT}"
echo "[smmbench] MODEL=${MODEL}"
echo "[smmbench] clusters=${START_CLUSTER_INDEX:- -1}..${END_CLUSTER_INDEX:--1}"

bash "${EVAL_DIR}/evaluation_scripts/evaluation_omnisimplemem.sh"
