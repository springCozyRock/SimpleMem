#!/usr/bin/env bash
# Run one MemEye scenario: MCQ then Open (same ingested memory), no LLM judge.
set -euo pipefail

TASK="${1:?usage: $0 <task_name>}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"
# shellcheck source=memeye_task_defs.sh
source "$ROOT/scripts/memeye_task_defs.sh"

if ! memeye_mcq_dialog "$TASK" >/dev/null; then
  echo "ERROR: unknown scenario '$TASK'" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
# shellcheck source=simplemem_mm_defaults.sh
source "$ROOT/scripts/simplemem_mm_defaults.sh"
TASK_CONFIG="${TASK_CONFIG:-config/tasks/${TASK}.yaml}"

MCQ_DIALOG="data/dialog/$(memeye_mcq_dialog "$TASK")"
OPEN_DIALOG="data/dialog/$(memeye_open_dialog "$TASK")"

LOG_DIR="$ROOT/runs/logs"
mkdir -p "$LOG_DIR"

activate_memeye_python_env
cd "$ROOT"

PYTHON="${PYTHON:-python}"
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
fi
if ! "$PYTHON" -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
  echo "ERROR: MemEye requires Python 3.10+; got $($PYTHON --version 2>&1)" >&2
  echo "Hint: source $REPO_ROOT/.venv/bin/activate" >&2
  exit 1
fi

# Preflight: resolve required API key env from model + method yaml
API_KEY_ENV="$("$PYTHON" -c "
import yaml
from pathlib import Path

model = yaml.safe_load(Path('$MODEL_CONFIG').read_text())
method = yaml.safe_load(Path('$METHOD_CONFIG').read_text())
print(
    (method.get('llm_api_key_env') or '').strip()
    or (model.get('api_key_env') or '').strip()
    or 'OPENAI_API_KEY'
)
")"
if [[ -z "${!API_KEY_ENV:-}" ]]; then
  echo "ERROR: $API_KEY_ENV is not set (required by $MODEL_CONFIG)" >&2
  echo "Example: export $API_KEY_ENV=sk-..." >&2
  exit 1
fi
echo "Using model=$MODEL_CONFIG api_key_env=$API_KEY_ENV (set)"

echo "========== [$TASK] MCQ started $(date -Is) =========="
"$PYTHON" run_benchmark.py \
  --task-config "$TASK_CONFIG" \
  --model-config "$MODEL_CONFIG" \
  --method-config "$METHOD_CONFIG" \
  --mode mcq \
  --dialog-json "$MCQ_DIALOG" \
  2>&1 | tee -a "$LOG_DIR/${TASK}.log"

echo "========== [$TASK] OPEN started $(date -Is) =========="
"$PYTHON" run_benchmark.py \
  --task-config "$TASK_CONFIG" \
  --model-config "$MODEL_CONFIG" \
  --method-config "$METHOD_CONFIG" \
  --mode open \
  --dialog-json "$OPEN_DIALOG" \
  2>&1 | tee -a "$LOG_DIR/${TASK}_open.log"

echo "========== [$TASK] DONE $(date -Is) =========="
