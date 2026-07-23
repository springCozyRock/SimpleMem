#!/usr/bin/env bash
# Compact smoke: truncated cluster_1 sample + OmniSimpleMem harness.
# Rebuilds smoke_samples, then runs evaluation_omnisimplemem.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(dirname "${SCRIPT_DIR}")"
SMMBENCH_ROOT="$(cd "${EVAL_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SMMBENCH_ROOT}/../../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/env.smmbench.local"
PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then PY="$(command -v python3)"; fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${ENV_FILE}"

export MODEL="${MODEL:-gpt-5.4-mini}"
export OPENAI_API_KEY="${MODEL_API_KEY}"
export OPENAI_API_BASE="${MODEL_API_BASE_URL}"
export DATASET_PARENT_DIR="${SMMBENCH_ROOT}/runs/smoke_samples"
export SAVE_ROOT_PATH="${SMMBENCH_ROOT}/runs/smoke_out"
export START_CLUSTER_INDEX=1
export END_CLUSTER_INDEX=1
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

"${PY}" - <<PY
import json, shutil
from pathlib import Path
src = Path(${SMMBENCH_ROOT@Q}) / "data/Samples/cluster_1"
dst = Path(${DATASET_PARENT_DIR@Q}) / "cluster_1"
if dst.exists():
    shutil.rmtree(dst)
dst.mkdir(parents=True)
ranked = []
for p in src.glob("*.json"):
    if p.name == "QA_sample.json":
        continue
    data = json.loads(p.read_text())
    conv = data.get("conversation") or []
    imgs = [i for i, t in enumerate(conv) if t.get("content_type") == "image"]
    ranked.append((len(imgs), p, data, conv, imgs))
ranked.sort(reverse=True)
img_total = 0
for n_imgs, p, data, conv, imgs in ranked:
    if n_imgs == 0 and img_total >= 8:
        continue
    if imgs:
        start = max(0, imgs[0] - 5)
        end = min(len(conv), imgs[min(4, len(imgs) - 1)] + 10)
        slice_turns = conv[start:end][:60]
    else:
        slice_turns = conv[:20]
    out = dict(data)
    out["conversation"] = slice_turns
    (dst / p.name).write_text(json.dumps(out, ensure_ascii=False))
    img_total += sum(1 for t in slice_turns if t.get("content_type") == "image")
    if img_total >= 10:
        break
qa = json.loads((src / "QA_sample.json").read_text())
picked = [q for q in qa if q.get("category") != "Function_Call"][:3]
(dst / "QA_sample.json").write_text(json.dumps(picked, ensure_ascii=False, indent=2))
print(f"[smoke] rebuilt {dst} images~={img_total} qa={len(picked)}")
PY

mkdir -p "${SAVE_ROOT_PATH}"
echo "[smoke] MODEL=${MODEL} DATASET=${DATASET_PARENT_DIR} OUT=${SAVE_ROOT_PATH}"
bash "${EVAL_DIR}/evaluation_scripts/evaluation_omnisimplemem.sh"
