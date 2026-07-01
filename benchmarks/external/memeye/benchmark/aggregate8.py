"""Aggregate MemEye 8-scenario benchmark runs into a single metrics payload."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import SCRIPT_DIR, load_json, write_json, write_jsonl, write_text
from .evaluator import summarize_results
from .memeye_tasks import MEMEYE_TASKS


BENCHMARK8_ROOT = SCRIPT_DIR / "runs" / "benchmark8"
PENDING_ROOT = BENCHMARK8_ROOT / "pending"
BATCHES_ROOT = BENCHMARK8_ROOT / "batches"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _batch_key(model_name: str, method_name: str, mode: str) -> str:
    safe = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
    return f"{safe(mode)}__{safe(model_name)}__{safe(method_name)}"


def _summary_dir(mode: str, model_name: str, method_name: str) -> Path:
    return BENCHMARK8_ROOT / mode / f"{model_name}__{method_name}"


def _pending_path(model_name: str, method_name: str, mode: str) -> Path:
    return PENDING_ROOT / f"{_batch_key(model_name, method_name, mode)}.json"


def _named_batch_path(batch_id: str, mode: str) -> Path:
    return BATCHES_ROOT / f"{batch_id}__{mode}.json"


def _run_identity(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(payload.get("model_name", "")),
        str(payload.get("method_name", "")),
        str(payload.get("mode", "")),
    )


def _tag_rows(rows: List[Dict[str, Any]], task_name: str) -> List[Dict[str, Any]]:
    tagged: List[Dict[str, Any]] = []
    for row in rows:
        tagged_row = dict(row)
        tagged_row["task_name"] = task_name
        tagged.append(tagged_row)
    return tagged


def build_benchmark8_payload(
    task_runs: Dict[str, Dict[str, Any]],
    *,
    batch_id: str = "",
) -> Dict[str, Any]:
    """Merge per-task metrics payloads into one benchmark-wide summary."""
    if len(task_runs) != len(MEMEYE_TASKS):
        missing = [t for t in MEMEYE_TASKS if t not in task_runs]
        raise ValueError(f"Expected {len(MEMEYE_TASKS)} tasks, missing: {missing}")

    all_rows: List[Dict[str, Any]] = []
    per_task: Dict[str, Any] = {}
    ref_payload: Optional[Dict[str, Any]] = None

    for task_name in MEMEYE_TASKS:
        entry = task_runs[task_name]
        run_dir = Path(str(entry["run_dir"]))
        preds_path = run_dir / "predictions.jsonl"
        if not preds_path.exists():
            raise FileNotFoundError(f"Missing predictions for {task_name}: {preds_path}")

        metrics_path = run_dir / "metrics.json"
        task_metrics = load_json(metrics_path) if metrics_path.exists() else {}
        rows = _tag_rows(_load_jsonl(preds_path), task_name)
        all_rows.extend(rows)

        per_task[task_name] = {
            "run_dir": str(run_dir),
            "num_qas_run": task_metrics.get("num_qas_run", len({r["idx"] for r in rows})),
            "overall": task_metrics.get("summary", {}).get("overall", {}),
        }
        if ref_payload is None:
            ref_payload = task_metrics

    if ref_payload is None:
        raise ValueError("No reference metrics payload found")

    model_name, method_name, mode = _run_identity(ref_payload)
    summary = summarize_results(all_rows)

    return {
        "benchmark": "memeye8",
        "batch_id": batch_id,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "model_name": model_name,
        "model_path": ref_payload.get("model_path", ""),
        "method_name": method_name,
        "base_method_name": ref_payload.get("base_method_name", ""),
        "method_modality": ref_payload.get("method_modality", ""),
        "mode": mode,
        "num_tasks": len(MEMEYE_TASKS),
        "num_qas": sum(int(v.get("num_qas_run", 0)) for v in per_task.values()),
        "num_qas_run": len({(r["task_name"], r["idx"]) for r in all_rows}),
        "git_commit": ref_payload.get("git_commit", ""),
        "summary": summary,
        "per_task": per_task,
        "task_runs": {k: str(v["run_dir"]) for k, v in per_task.items()},
    }


def write_benchmark8_artifacts(payload: Dict[str, Any]) -> Path:
    """Write metrics.json (+ merged predictions) to the stable summary directory."""
    out_dir = _summary_dir(
        str(payload["mode"]),
        str(payload["model_name"]),
        str(payload["method_name"]),
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "metrics.json"
    write_json(metrics_path, payload)

    merged_rows: List[Dict[str, Any]] = []
    for task_name in MEMEYE_TASKS:
        run_dir = Path(payload["task_runs"][task_name])
        merged_rows.extend(_tag_rows(_load_jsonl(run_dir / "predictions.jsonl"), task_name))
    write_jsonl(out_dir / "predictions.jsonl", merged_rows)

    overall = payload.get("summary", {}).get("overall", {})
    mcq = payload.get("summary", {}).get("mcq_overall", {})
    em = overall.get("em", mcq.get("em"))
    judge = overall.get("judge")
    lines = [
        "# MemEye 8-Scenario Summary",
        "",
        f"- mode: `{payload.get('mode')}`",
        f"- model: `{payload.get('model_name')}`",
        f"- method: `{payload.get('method_name')}`",
        f"- questions: {payload.get('num_qas_run')} / {payload.get('num_qas')}",
        "",
    ]
    if em is not None:
        lines.append(f"- **EM**: {float(em) * 100:.2f}%")
    if judge is not None:
        lines.append(f"- **LLM judge**: {float(judge):.4f}")
    lines.append("")
    lines.append(f"Full metrics: `{metrics_path}`")
    lines.append("")
    write_text(out_dir / "README.md", "\n".join(lines))

    print(f"[INFO] MemEye 8-scenario summary: {metrics_path}")
    if em is not None:
        print(f"[INFO] Overall EM: {float(em) * 100:.2f}% ({payload.get('num_qas_run')} questions)")
    if judge is not None:
        print(f"[INFO] Overall LLM judge: {float(judge):.4f}")

    return out_dir


def _load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def _save_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, manifest)


def register_task_run(
    *,
    task_name: str,
    run_dir: Path,
    payload: Dict[str, Any],
    batch_id: str = "",
) -> Optional[Path]:
    """
    Record a finished task run. When all 8 tasks are present, aggregate automatically.

    Returns the summary directory if aggregation ran, else None.
    """
    if task_name not in MEMEYE_TASKS:
        return None

    model_name, method_name, mode = _run_identity(payload)
    run_dir = run_dir.resolve()
    entry = {
        "run_dir": str(run_dir),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
        "num_qas_run": payload.get("num_qas_run", 0),
    }

    if batch_id:
        manifest_path = _named_batch_path(batch_id, mode)
        manifest = _load_manifest(manifest_path)
        manifest.setdefault("batch_id", batch_id)
        manifest.setdefault("mode", mode)
        manifest.setdefault("model_name", model_name)
        manifest.setdefault("method_name", method_name)
        manifest.setdefault("tasks", {})
        manifest["tasks"][task_name] = entry
        manifest["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        _save_manifest(manifest_path, manifest)
        tasks = manifest["tasks"]
    else:
        manifest_path = _pending_path(model_name, method_name, mode)
        manifest = _load_manifest(manifest_path)
        manifest.setdefault("mode", mode)
        manifest.setdefault("model_name", model_name)
        manifest.setdefault("method_name", method_name)
        manifest.setdefault("tasks", {})
        manifest["tasks"][task_name] = entry
        manifest["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        _save_manifest(manifest_path, manifest)
        tasks = manifest["tasks"]
        batch_id = _batch_key(model_name, method_name, mode)

    if len(tasks) < len(MEMEYE_TASKS):
        missing = [t for t in MEMEYE_TASKS if t not in tasks]
        print(
            f"[INFO] MemEye8 progress ({mode}): {len(tasks)}/{len(MEMEYE_TASKS)} "
            f"— waiting for {', '.join(missing)}"
        )
        return None

    # Verify all registered runs share the same model/method/mode
    for name, info in tasks.items():
        mpath = Path(info["run_dir"]) / "metrics.json"
        if not mpath.exists():
            print(f"[WARN] MemEye8: missing metrics for {name}, skip aggregate")
            return None
        m = load_json(mpath)
        if _run_identity(m) != (model_name, method_name, mode):
            print(f"[WARN] MemEye8: {name} model/method/mode mismatch, skip aggregate")
            return None

    try:
        payload_out = build_benchmark8_payload(tasks, batch_id=batch_id)
        return write_benchmark8_artifacts(payload_out)
    except Exception as exc:
        print(f"[WARN] MemEye8 aggregate failed: {exc}")
        return None


def refresh_all_benchmark8_summaries() -> List[Path]:
    """Re-aggregate any complete 8-task manifests (e.g. after LLM judge scoring)."""
    updated: List[Path] = []
    manifest_paths = sorted(PENDING_ROOT.glob("*.json")) + sorted(BATCHES_ROOT.glob("*.json"))
    for manifest_path in manifest_paths:
        manifest = _load_manifest(manifest_path)
        tasks = manifest.get("tasks", {})
        if len(tasks) < len(MEMEYE_TASKS):
            continue
        if not all(t in tasks for t in MEMEYE_TASKS):
            continue
        batch_id = str(manifest.get("batch_id", manifest_path.stem))
        try:
            payload = build_benchmark8_payload(tasks, batch_id=batch_id)
            out_dir = write_benchmark8_artifacts(payload)
            updated.append(out_dir)
        except Exception as exc:
            print(f"[WARN] MemEye8 refresh failed for {manifest_path.name}: {exc}")
    return updated


def maybe_aggregate_after_run(payload: Dict[str, Any], run_dir: Path) -> Optional[Path]:
    """Hook called at the end of each benchmark run."""
    task_name = str(payload.get("task_name", ""))
    batch_id = os.environ.get("MEMEYE_BATCH_ID", "").strip()
    return register_task_run(
        task_name=task_name,
        run_dir=run_dir,
        payload=payload,
        batch_id=batch_id,
    )


def aggregate_latest_runs(
    runs_root: Path,
    *,
    mode: str = "",
    model_name: str = "",
    method_name: str = "",
) -> Path:
    """
    Force-aggregate the latest matching run per scenario (CLI / recovery path).
    """
    runs_root = runs_root.resolve()
    task_runs: Dict[str, Dict[str, Any]] = {}

    for task_name in MEMEYE_TASKS:
        task_dir = runs_root / task_name
        if not task_dir.is_dir():
            raise FileNotFoundError(f"Missing task directory: {task_dir}")

        candidates = sorted(
            (p for p in task_dir.iterdir() if p.is_dir() and (p / "predictions.jsonl").exists()),
            key=lambda p: p.name,
            reverse=True,
        )
        chosen: Optional[Path] = None
        for run_dir in candidates:
            metrics_path = run_dir / "metrics.json"
            if not metrics_path.exists():
                continue
            m = load_json(metrics_path)
            if mode and str(m.get("mode", "")) != mode:
                continue
            if model_name and str(m.get("model_name", "")) != model_name:
                continue
            if method_name and str(m.get("method_name", "")) != method_name:
                continue
            chosen = run_dir
            break

        if chosen is None:
            raise FileNotFoundError(
                f"No matching run for task={task_name} "
                f"(mode={mode or '*'}, model={model_name or '*'}, method={method_name or '*'})"
            )
        task_runs[task_name] = {"run_dir": str(chosen)}

    ref = load_json(Path(task_runs[MEMEYE_TASKS[0]]["run_dir"]) / "metrics.json")
    m_name, meth_name, m_mode = _run_identity(ref)
    batch_id = _batch_key(m_name, meth_name, m_mode)
    payload = build_benchmark8_payload(task_runs, batch_id=batch_id)
    return write_benchmark8_artifacts(payload)


def identity_from_configs(
    model_config_path: str,
    method_config_path: str,
    mode: str,
) -> Tuple[str, str]:
    from .common import load_yaml, resolve_config_path
    from .runner import _effective_method_name

    model_cfg = load_yaml(resolve_config_path(model_config_path))
    method_cfg = load_yaml(resolve_config_path(method_config_path))
    return str(model_cfg.get("name", "")), _effective_method_name(method_cfg)
