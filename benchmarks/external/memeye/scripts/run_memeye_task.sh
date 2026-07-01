#!/usr/bin/env bash
# Run one MemEye scenario (MCQ or mirrored Open on the same ingested memory).
set -euo pipefail

TASK_NAME="${1:-}"
if [[ -z "$TASK_NAME" ]]; then
  echo "Usage: $0 <scenario_name>" >&2
  exit 1
fi

if [[ "$TASK_NAME" == *_open ]]; then
  TASK_NAME="${TASK_NAME%_open}"
  MODE="${MODE:-open}"
fi

MODE="${MODE:-mcq}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"
# shellcheck source=memeye_task_defs.sh
source "$ROOT/scripts/memeye_task_defs.sh"

if ! memeye_mcq_dialog "$TASK_NAME" >/dev/null; then
  echo "ERROR: unknown scenario '$TASK_NAME'" >&2
  exit 1
fi

TASK_CONFIG="${TASK_CONFIG:-$ROOT/config/tasks/${TASK_NAME}.yaml}"
MODEL_CONFIG="${MODEL_CONFIG:-config/models/qwen3_7_plus_dashscope.yaml}"
METHOD_CONFIG="${METHOD_CONFIG:-config/methods/simplemem_omni_dashscope.yaml}"
MAX_QUESTIONS="${MAX_QUESTIONS:-0}"
QA_PARALLEL_WORKERS="${QA_PARALLEL_WORKERS:-0}"

case "$MODE" in
  mcq)
    DIALOG_JSON="data/dialog/$(memeye_mcq_dialog "$TASK_NAME")"
    RUN_MODE="mcq"
    ;;
  open)
    DIALOG_JSON="data/dialog/$(memeye_open_dialog "$TASK_NAME")"
    RUN_MODE="open"
    ;;
  *)
    echo "ERROR: MODE must be mcq or open (got: $MODE)" >&2
    exit 1
    ;;
esac

LOG_DIR="$ROOT/runs/logs"
mkdir -p "$LOG_DIR"
LOG_SUFFIX=""
[[ "$RUN_MODE" == "open" ]] && LOG_SUFFIX="_open"
LOG_FILE="$LOG_DIR/${TASK_NAME}${LOG_SUFFIX}.log"

activate_memeye_python_env
cd "$ROOT"

ARGS=(
  run_benchmark.py
  --task-config "$TASK_CONFIG"
  --model-config "$MODEL_CONFIG"
  --method-config "$METHOD_CONFIG"
  --mode "$RUN_MODE"
  --dialog-json "$DIALOG_JSON"
)
[[ "$MAX_QUESTIONS" != "0" ]] && ARGS+=(--max-questions "$MAX_QUESTIONS")
[[ "$QA_PARALLEL_WORKERS" != "0" ]] && ARGS+=(--qa-parallel-workers "$QA_PARALLEL_WORKERS")

{
  echo "=== scenario=$TASK_NAME mode=$RUN_MODE started at $(date -Is) ==="
  echo "memory_dir=$ROOT/runs/simplemem/$TASK_NAME"
  echo "dialog_json=$DIALOG_JSON"
  python "${ARGS[@]}"
  echo "=== scenario=$TASK_NAME mode=$RUN_MODE finished at $(date -Is), exit=$? ==="
} 2>&1 | tee -a "$LOG_FILE"
