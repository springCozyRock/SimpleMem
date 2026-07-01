#!/usr/bin/env bash
# Manual recovery: aggregate latest 8-scenario runs into runs/benchmark8/.
#
# Usage:
#   ./scripts/aggregate_memeye8.sh --mode mcq
#   ./scripts/aggregate_memeye8.sh --mode mcq --model-name qwen3_7_plus_dashscope --method-name simplemem__multimodal
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../../.." && pwd)"
# shellcheck source=activate_python_env.sh
source "$ROOT/scripts/activate_python_env.sh"

activate_memeye_python_env
cd "$ROOT"
exec python aggregate_memeye8.py "$@"
