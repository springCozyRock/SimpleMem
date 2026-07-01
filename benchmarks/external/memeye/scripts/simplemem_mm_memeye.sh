#!/usr/bin/env bash
# SimpleMem-MM on MemEye — 长期跑全量 benchmark 的统一入口。
#
# 前置（建议写进 ~/.bashrc 或长期 tmux 启动脚本）:
#   source /mnt/data/bts/repos/SimpleMem/.venv/bin/activate
#   cp scripts/llm_env.local.example scripts/llm_env.local  # GPT backbone
#   # 或 export MEMEYE_LLM_API_KEY=sk-...
#
# 用法:
#   ./scripts/simplemem_mm_memeye.sh run <task>     # 单场景 MCQ + Open
#   ./scripts/simplemem_mm_memeye.sh run-all        # 8 场景串行
#   ./scripts/simplemem_mm_memeye.sh launch         # 8 场景 tmux 并行
#   ./scripts/simplemem_mm_memeye.sh clean          # 清空 runs/simplemem 缓存后重跑
#   ./scripts/simplemem_mm_memeye.sh judge-open      # Open LLM-Judge（前台）
#   ./scripts/simplemem_mm_memeye.sh judge-tmux      # Open LLM-Judge（tmux 后台）
#   ./scripts/simplemem_mm_memeye.sh aggregate mcq  # 仅聚合 MCQ
#   ./scripts/simplemem_mm_memeye.sh aggregate open # 仅聚合 Open
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"
# shellcheck source=memeye_task_defs.sh
source "$ROOT/scripts/memeye_task_defs.sh"
# shellcheck source=simplemem_mm_defaults.sh
source "$ROOT/scripts/simplemem_mm_defaults.sh"

RUN_ONE="$ROOT/scripts/run_memeye_task_full.sh"
AGG="$ROOT/scripts/aggregate_memeye8.sh"

_usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args]

Commands:
  run <task>    Run one MemEye scenario (MCQ then Open)
  run-all       Run all 8 scenarios sequentially
  launch        Launch all 8 scenarios in tmux (session: memeye_simplemem_mm)
  aggregate     Aggregate latest MCQ + Open runs
  aggregate mcq Aggregate MCQ only
  aggregate open Aggregate Open only
  judge-open      Score Open predictions with LLM-as-a-Judge (gpt-5.2)
  judge-tmux      Launch judge-open in tmux (session: memeye_judge_open)
  clean         Delete cached memory under runs/simplemem/

Config (override via env):
  MODEL_CONFIG=$MODEL_CONFIG
  METHOD_CONFIG=$METHOD_CONFIG
  MEMEYE_LLM_API_KEY (or env from model yaml) must be set

Tasks: ${MEMEYE_TASKS[*]}
EOF
}

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

_resolve_api_key_env() {
  local python="${PYTHON:-}"
  if [[ -z "$python" && -x "$REPO_ROOT/.venv/bin/python" ]]; then
    python="$REPO_ROOT/.venv/bin/python"
  fi
  python="${python:-python}"
  "$python" -c "
import yaml
from pathlib import Path

model = yaml.safe_load(Path('$MODEL_CONFIG').read_text())
method = yaml.safe_load(Path('$METHOD_CONFIG').read_text())
print(
    (method.get('llm_api_key_env') or '').strip()
    or (model.get('api_key_env') or '').strip()
    or 'DASHSCOPE_API_KEY'
)
"
}

_preflight() {
  activate_memeye_python_env
  cd "$ROOT"
  API_KEY_ENV="$(_resolve_api_key_env)"
  if [[ -z "${!API_KEY_ENV:-}" ]]; then
    echo "ERROR: $API_KEY_ENV is not set (required by $MODEL_CONFIG)" >&2
    exit 1
  fi
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "python env: venv ($VIRTUAL_ENV)"
  elif [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    echo "python env: conda ($CONDA_DEFAULT_ENV)"
  elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "python env: $REPO_ROOT/.venv/bin/python (auto)"
  else
    echo "WARN: no venv/conda detected; using PATH python" >&2
  fi
  echo "model=$MODEL_CONFIG method=$METHOD_CONFIG api_key_env=$API_KEY_ENV (set)"
  if [[ "${HF_HUB_OFFLINE:-0}" == "1" ]]; then
    echo "minilm: offline (local HF cache)"
  elif [[ -n "${HF_ENDPOINT:-}" ]]; then
    echo "minilm: download via $HF_ENDPOINT"
  fi
  echo "gpu: CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
  if [[ -n "${SIMPLEMEM_EMBEDDING_DEVICE:-}" ]]; then
    echo "minilm device: ${SIMPLEMEM_EMBEDDING_DEVICE}"
  fi
}

_cmd_run() {
  local task="${1:?task name required}"
  _preflight
  exec "$RUN_ONE" "$task"
}

_cmd_run_all() {
  _preflight
  for task in "${MEMEYE_TASKS[@]}"; do
    "$RUN_ONE" "$task"
  done
}

_cmd_launch() {
  _preflight
  local session="${SESSION:-memeye_simplemem_mm}"
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "tmux session '$session' already exists. Attach: tmux attach -t $session"
    exit 1
  fi

  # tmux 子 shell 默认不继承父 shell 的自定义环境变量，必须显式传入 API key。
  local api_key_value="${!API_KEY_ENV}"
  local env_prefix
  env_prefix="$(_shell_setup_snippet)cd '$ROOT' && export MODEL_CONFIG='$MODEL_CONFIG' METHOD_CONFIG='$METHOD_CONFIG' $(simplemem_mm_hf_env_exports) ${API_KEY_ENV}='${api_key_value}';"

  tmux new-session -d -s "$session" -n "${MEMEYE_TASKS[0]}"
  tmux set-environment -t "$session" "${API_KEY_ENV}" "${api_key_value}"
  tmux set-environment -t "$session" CUDA_VISIBLE_DEVICES "${CUDA_VISIBLE_DEVICES}"
  if [[ -n "${SIMPLEMEM_EMBEDDING_DEVICE:-}" ]]; then
    tmux set-environment -t "$session" SIMPLEMEM_EMBEDDING_DEVICE "${SIMPLEMEM_EMBEDDING_DEVICE}"
  fi
  tmux send-keys -t "$session:0" "$env_prefix $RUN_ONE ${MEMEYE_TASKS[0]}" C-m

  local i task
  for ((i = 1; i < ${#MEMEYE_TASKS[@]}; i++)); do
    task="${MEMEYE_TASKS[$i]}"
    tmux new-window -t "$session" -n "$task"
    tmux send-keys -t "$session:$i" "$env_prefix $RUN_ONE $task" C-m
  done

  echo "Launched tmux session: $session"
  echo "Attach: tmux attach -t $session"
}

_cmd_clean() {
  local mem_root="$ROOT/runs/simplemem"
  if [[ ! -d "$mem_root" ]]; then
    echo "No memory cache at $mem_root"
    return 0
  fi
  echo "Removing $mem_root ..."
  rm -rf "$mem_root"
  echo "Done. Next run will re-ingest from scratch."
}

_cmd_aggregate() {
  _preflight
  local modes=()
  case "${1:-both}" in
    mcq) modes=(mcq) ;;
    open) modes=(open) ;;
    both|"") modes=(mcq open) ;;
    *)
      echo "ERROR: aggregate mode must be mcq, open, or both" >&2
      exit 1
      ;;
  esac

  for mode in "${modes[@]}"; do
    "$AGG" \
      --mode "$mode" \
      --model-config "$MODEL_CONFIG" \
      --method-config "$METHOD_CONFIG"
  done
}

_cmd_judge_open() {
  activate_memeye_python_env
  cd "$ROOT"
  exec "$ROOT/scripts/score_open_llm_judge.sh" "$@"
}

_cmd_judge_tmux() {
  exec "$ROOT/scripts/launch_judge_open_tmux.sh" "$@"
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    run) _cmd_run "$@" ;;
    run-all) _cmd_run_all "$@" ;;
    launch) _cmd_launch "$@" ;;
    clean) _cmd_clean "$@" ;;
    aggregate) _cmd_aggregate "$@" ;;
    judge-open) _cmd_judge_open "$@" ;;
    judge-tmux) _cmd_judge_tmux "$@" ;;
    -h|--help|help|"") _usage ;;
    *)
      echo "ERROR: unknown command: $cmd" >&2
      _usage
      exit 1
      ;;
  esac
}

main "$@"
