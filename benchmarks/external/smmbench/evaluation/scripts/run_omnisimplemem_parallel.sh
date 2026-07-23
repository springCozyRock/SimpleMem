#!/usr/bin/env bash
# Run OmniSimpleMem on SMMBench with up to N concurrent clusters.
#
# Usage (in tmux):
#   CONCURRENCY=5 GPU_LIST=0,1,2,3,4 \
#     bash scripts/run_omnisimplemem_parallel.sh
#
# Optional:
#   START_CLUSTER_INDEX=1 END_CLUSTER_INDEX=61
#   SKIP_DONE=1   # skip if round0.json already exists (default 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(dirname "${SCRIPT_DIR}")"
ENV_FILE="${SCRIPT_DIR}/env.smmbench.local"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
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

CONCURRENCY="${CONCURRENCY:-5}"
SKIP_DONE="${SKIP_DONE:-1}"
GPU_LIST="${GPU_LIST:-0,1,2,3,4}"
IFS=',' read -r -a GPUS <<< "${GPU_LIST}"

# When a shared embedding server is configured, workers do not need a GPU for BGE.
USE_REMOTE_EMBED=0
if [[ -n "${OMNI_EMBEDDING_SERVER_URL:-}" ]]; then
  USE_REMOTE_EMBED=1
  echo "[parallel] embedding_server=${OMNI_EMBEDDING_SERVER_URL}"
fi

START_I="${START_CLUSTER_INDEX:--1}"
END_I="${END_CLUSTER_INDEX:--1}"

mkdir -p "${SAVE_ROOT_PATH}/logs"

mapfile -t ALL_IDX < <(
  find "${DATASET_PARENT_DIR}" -mindepth 1 -maxdepth 1 -type d -name 'cluster_*' \
    -printf '%f\n' | sed 's/^cluster_//' | sort -n
)

CLUSTERS=()
for idx in "${ALL_IDX[@]}"; do
  if [[ "${START_I}" != "-1" && "${END_I}" != "-1" ]]; then
    if (( idx < START_I || idx > END_I )); then
      continue
    fi
  fi
  CLUSTERS+=("${idx}")
done

if [[ ${#CLUSTERS[@]} -eq 0 ]]; then
  echo "No clusters to run under ${DATASET_PARENT_DIR}" >&2
  exit 1
fi

echo "[parallel] n=${#CLUSTERS[@]} concurrency=${CONCURRENCY} gpus=${GPU_LIST} remote_embed=${USE_REMOTE_EMBED}"
echo "[parallel] model=${MODEL} save=${SAVE_ROOT_PATH}"

export OPENAI_API_KEY="${MODEL_API_KEY}"
export OPENAI_API_BASE="${MODEL_API_BASE_URL}"

gpu_i=0
fail=0

for idx in "${CLUSTERS[@]}"; do
  # throttle
  while (( $(jobs -rp | wc -l) >= CONCURRENCY )); do
    if ! wait -n; then
      fail=1
    fi
  done

  out_json="${SAVE_ROOT_PATH}/cluster_${idx}/time_sequential_memory__omnisimplemem__${MODEL}__round0.json"
  if [[ "${SKIP_DONE}" == "1" && -f "${out_json}" ]]; then
    echo "[parallel] skip cluster_${idx}"
    continue
  fi

  log="${SAVE_ROOT_PATH}/logs/cluster_${idx}.log"
  if (( USE_REMOTE_EMBED )); then
    echo "[parallel] start cluster_${idx} gpu=none(remote-embed) log=${log}"
    (
      export START_CLUSTER_INDEX="${idx}"
      export END_CLUSTER_INDEX="${idx}"
      export CUDA_VISIBLE_DEVICES=""
      export OMNI_EMBEDDING_SERVER_URL
      bash "${EVAL_DIR}/evaluation_scripts/evaluation_omnisimplemem.sh"
    ) >"${log}" 2>&1 &
  else
    gpu="${GPUS[$((gpu_i % ${#GPUS[@]}))]}"
    gpu_i=$((gpu_i + 1))
    echo "[parallel] start cluster_${idx} gpu=${gpu} log=${log}"
    (
      export START_CLUSTER_INDEX="${idx}"
      export END_CLUSTER_INDEX="${idx}"
      export CUDA_VISIBLE_DEVICES="${gpu}"
      bash "${EVAL_DIR}/evaluation_scripts/evaluation_omnisimplemem.sh"
    ) >"${log}" 2>&1 &
  fi
done

# drain remaining
for pid in $(jobs -rp); do
  if ! wait "${pid}"; then
    fail=1
  fi
done

if (( fail )); then
  echo "[parallel] finished with failures; check ${SAVE_ROOT_PATH}/logs/" >&2
  exit 1
fi
echo "[parallel] all finished"
