#!/usr/bin/env bash
# Shared Python env activation for MemEye scripts.
#
# Priority:
#   1. Already in an active venv or conda env -> no-op
#   2. CONDA_ENV set -> conda activate
#   3. VENV (default .venv) -> source activate script
#
# Defaults (override via env):
#   VENV=$REPO_ROOT/.venv/bin/activate
#   CONDA_BASE=/mnt/data/xzr/miniconda3
#   CONDA_ENV=   (empty = use .venv; set e.g. simplemem to use conda)
#
# Use conda instead of .venv:
#   CONDA_ENV=simplemem ./scripts/run_memeye_task.sh ...

activate_memeye_python_env() {
  if [[ -n "${VIRTUAL_ENV:-}" || -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    return 0
  fi

  local conda_base="${CONDA_BASE:-/mnt/data/xzr/miniconda3}"
  local conda_env="${CONDA_ENV:-}"

  if [[ -n "$conda_env" && -f "$conda_base/etc/profile.d/conda.sh" ]]; then
    # shellcheck disable=SC1091
    source "$conda_base/etc/profile.d/conda.sh"
    conda activate "$conda_env"
    return 0
  fi

  local venv_path="${VENV:-${REPO_ROOT:-}/.venv/bin/activate}"
  if [[ -n "$venv_path" && -f "$venv_path" ]]; then
    # shellcheck disable=SC1090
    source "$venv_path"
  fi
}
