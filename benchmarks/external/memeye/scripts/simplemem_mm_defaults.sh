# SimpleMem-MM × MemEye 默认配置（GPT-5.4-mini 中转 API + local MiniLM）。
# 被 run_memeye_task_full.sh / simplemem_mm_memeye.sh 引用。
#
# 运行前:
#   source /mnt/data/bts/repos/SimpleMem/.venv/bin/activate
#   cp scripts/llm_env.local.example scripts/llm_env.local  # 首次
#   # 或 export MEMEYE_LLM_API_KEY=sk-...
#
# 切回 Qwen3-VL-8B:
#   export MODEL_CONFIG=config/models/qwen3_vl_8b_dashscope.yaml
#   export METHOD_CONFIG=config/methods/simplemem_multimodal_dashscope.yaml
#   export DASHSCOPE_API_KEY=sk-...
#
# MiniLM 下载策略（自动）:
#   - 本地已有 ~/.cache/huggingface/.../all-MiniLM-L6-v2 → 离线加载，不访问 huggingface.co
#   - 本地无缓存 → 走国内镜像 hf-mirror.com 拉取
#
# GPU: 默认用物理卡 4（LLM 走 API，本地只有 MiniLM embedding 会用 GPU）
#   export CUDA_VISIBLE_DEVICES=4
# 若 8 路并行仍 OOM，可让 MiniLM 走 CPU（推荐，embedding 很轻）:
#   export SIMPLEMEM_EMBEDDING_DEVICE=cpu

_MEMEYE_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_MEMEYE_SCRIPTS_DIR/llm_env.local" ]]; then
  # shellcheck source=/dev/null
  source "$_MEMEYE_SCRIPTS_DIR/llm_env.local"
fi
unset _MEMEYE_SCRIPTS_DIR

export MODEL_CONFIG="${MODEL_CONFIG:-config/models/gpt_5_4_mini_proxy.yaml}"
export METHOD_CONFIG="${METHOD_CONFIG:-config/methods/simplemem_multimodal_gpt54mini.yaml}"

# 物理 GPU 4 → 进程内可见为 cuda:0
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-4}"

_MINILM_HF_CACHE="${HOME}/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
if [[ -d "$_MINILM_HF_CACHE" ]]; then
  # 之前从镜像/有网环境下载的缓存，直接离线用，避免 retry huggingface.co
  export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
  export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
else
  # 无本地缓存时，用国内镜像（与之前常见做法一致）
  export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
  export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-0}"
  export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-0}"
fi
unset _MINILM_HF_CACHE

# 供 tmux launch 拼进子 shell 的环境变量片段
simplemem_mm_hf_env_exports() {
  local parts=()
  parts+=("CUDA_VISIBLE_DEVICES='${CUDA_VISIBLE_DEVICES}'")
  if [[ -n "${SIMPLEMEM_EMBEDDING_DEVICE:-}" ]]; then
    parts+=("SIMPLEMEM_EMBEDDING_DEVICE='${SIMPLEMEM_EMBEDDING_DEVICE}'")
  fi
  parts+=("HF_HUB_OFFLINE='${HF_HUB_OFFLINE:-0}'")
  parts+=("TRANSFORMERS_OFFLINE='${TRANSFORMERS_OFFLINE:-0}'")
  if [[ -n "${HF_ENDPOINT:-}" ]]; then
    parts+=("HF_ENDPOINT='${HF_ENDPOINT}'")
  fi
  local IFS=' '
  echo "${parts[*]}"
}
