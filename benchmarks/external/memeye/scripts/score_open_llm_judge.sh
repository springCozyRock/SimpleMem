#!/usr/bin/env bash
# Post-hoc LLM-as-a-Judge for locked Open predictions (gpt-5.2 by default).
#
# Setup (do NOT commit secrets):
#   cp scripts/judge_env.local.example scripts/judge_env.local
#   # edit judge_env.local
#
# Or export manually:
#   export MEMEYE_JUDGE_API_KEY=sk-...
#   export MEMEYE_JUDGE_BASE_URL=http://host:port/v1
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"

if [[ -f "$ROOT/scripts/.env.judge.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/.env.judge.local"
elif [[ -f "$ROOT/scripts/judge_env.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/judge_env.local"
fi

export JUDGE_MODEL="${JUDGE_MODEL:-gpt-5.2}"
export JUDGE_ROOT="${JUDGE_ROOT:-$ROOT/runs/benchmark8/open/qwen3_vl_8b_dashscope__simplemem__multimodal}"
export JUDGE_MAX_RETRIES="${JUDGE_MAX_RETRIES:-5}"
export JUDGE_TIMEOUT="${JUDGE_TIMEOUT:-120}"
export JUDGE_SLEEP="${JUDGE_SLEEP:-1.5}"

API_KEY="${MEMEYE_JUDGE_API_KEY:-${OPENAI_API_KEY:-}}"
BASE_URL="${MEMEYE_JUDGE_BASE_URL:-${JUDGE_BASE_URL:-}}"

if [[ -z "$API_KEY" ]]; then
  echo "ERROR: set MEMEYE_JUDGE_API_KEY (or OPENAI_API_KEY) for judge scoring." >&2
  exit 1
fi

activate_memeye_python_env
cd "$ROOT"

PYTHON="${PYTHON:-python}"
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
fi

ARGS=(
  score_locked_llm_judge.py
  --root "$JUDGE_ROOT"
  --judge-model "$JUDGE_MODEL"
  --judge-api-key "$API_KEY"
  --judge-max-retries "$JUDGE_MAX_RETRIES"
  --judge-timeout "$JUDGE_TIMEOUT"
  --judge-sleep "$JUDGE_SLEEP"
)
if [[ -n "$BASE_URL" ]]; then
  ARGS+=(--judge-base-url "$BASE_URL")
fi
if [[ "${1:-}" == "--force" ]]; then
  ARGS+=(--force)
fi

echo "Judge model=$JUDGE_MODEL (serial) root=$JUDGE_ROOT"
if [[ -n "$BASE_URL" ]]; then
  echo "Judge base_url=$BASE_URL"
fi

exec "$PYTHON" "${ARGS[@]}"
