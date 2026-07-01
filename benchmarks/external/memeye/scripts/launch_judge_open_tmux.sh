#!/usr/bin/env bash
# Launch Open LLM-as-a-Judge in a detached tmux session (checkpoint resume).
#
#   ./scripts/launch_judge_open_tmux.sh
#   ./scripts/launch_judge_open_tmux.sh --force   # kill existing session and relaunch
#
# Attach:  tmux attach -t memeye_judge_open
# Detach:  Ctrl-b d
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
SESSION="${JUDGE_SESSION:-memeye_judge_open}"
LOG_DIR="$ROOT/runs/logs"
LOG_FILE="${JUDGE_LOG_FILE:-$LOG_DIR/llm_judge_open.log}"
JUDGE_SCRIPT="$ROOT/scripts/score_open_llm_judge.sh"

# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"

if [[ -f "$ROOT/scripts/.env.judge.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/.env.judge.local"
elif [[ -f "$ROOT/scripts/judge_env.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/judge_env.local"
fi

API_KEY="${MEMEYE_JUDGE_API_KEY:-${OPENAI_API_KEY:-}}"
if [[ -z "$API_KEY" ]]; then
  echo "ERROR: set MEMEYE_JUDGE_API_KEY in scripts/judge_env.local (or export OPENAI_API_KEY)." >&2
  exit 1
fi

_shell_setup_snippet() {
  local setup=""
  local conda_base="${CONDA_BASE:-/mnt/data/xzr/miniconda3}"
  if [[ -n "${CONDA_ENV:-}" && -f "$conda_base/etc/profile.d/conda.sh" ]]; then
    setup="source '$conda_base/etc/profile.d/conda.sh' && conda activate '$CONDA_ENV'"
  elif [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
    setup="source '$REPO_ROOT/.venv/bin/activate'"
  fi
  if [[ -n "$setup" ]]; then
    printf '%s && ' "$setup"
  fi
}

if [[ "${1:-}" == "--force" ]]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  shift
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already exists."
  echo "  attach: tmux attach -t $SESSION"
  echo "  kill:   tmux kill-session -t $SESSION"
  echo "  relaunch: $0 --force"
  exit 1
fi

mkdir -p "$LOG_DIR"

env_prefix="$(_shell_setup_snippet)cd '$ROOT';"
# Default: no tee so tqdm progress bar works when attaching.
# Set JUDGE_LOG=1 to also append full output to LOG_FILE.
if [[ "${JUDGE_LOG:-0}" == "1" ]]; then
  run_line="${env_prefix} ${JUDGE_SCRIPT} 2>&1 | tee -a '${LOG_FILE}'"
else
  run_line="${env_prefix} ${JUDGE_SCRIPT}"
fi

tmux new-session -d -s "$SESSION" -n judge
tmux send-keys -t "$SESSION:0" "$run_line" C-m

echo "Launched Open LLM-Judge in tmux session: $SESSION"
echo "  model=${JUDGE_MODEL:-gpt-5.2} (serial)"
echo "  attach: tmux attach -t $SESSION"
echo "  detach: Ctrl-b d"
if [[ "${JUDGE_LOG:-0}" == "1" ]]; then
  echo "  log:    $LOG_FILE"
else
  echo "  log:    (disabled; set JUDGE_LOG=1 to tee to $LOG_FILE)"
fi
