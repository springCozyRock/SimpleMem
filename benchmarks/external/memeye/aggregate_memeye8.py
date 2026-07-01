#!/usr/bin/env python3
"""Aggregate MemEye 8-scenario benchmark runs (auto or manual)."""

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark.aggregate8 import aggregate_latest_runs, identity_from_configs
from benchmark.memeye_tasks import MEMEYE_TASKS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate MemEye 8-scenario runs into runs/benchmark8/<mode>/<model>__<method>/metrics.json",
    )
    parser.add_argument(
        "--runs-root",
        type=str,
        default="runs",
        help="Root directory containing per-task run folders (default: runs).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="",
        choices=["", "mcq", "open"],
        help="Filter runs by evaluation mode.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="",
        help="Filter runs by model config name (e.g. qwen3_7_plus_dashscope).",
    )
    parser.add_argument(
        "--method-name",
        type=str,
        default="",
        help="Filter runs by effective method name (e.g. simplemem__multimodal).",
    )
    parser.add_argument(
        "--model-config",
        type=str,
        default="",
        help="Infer --model-name from a model yaml (with --method-config).",
    )
    parser.add_argument(
        "--method-config",
        type=str,
        default="",
        help="Infer --method-name from a method yaml (with --model-config).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_name = args.model_name
    method_name = args.method_name

    if args.model_config and args.method_config:
        inferred_model, inferred_method = identity_from_configs(
            args.model_config,
            args.method_config,
            args.mode,
        )
        model_name = model_name or inferred_model
        method_name = method_name or inferred_method

    root = Path(args.runs_root)
    if not root.is_absolute():
        root = (Path(__file__).resolve().parent / root).resolve()

    out_dir = aggregate_latest_runs(
        root,
        mode=args.mode,
        model_name=model_name,
        method_name=method_name,
    )
    print(f"[DONE] Wrote 8-scenario summary under {out_dir}")
    print(f"       Tasks: {', '.join(MEMEYE_TASKS)}")


if __name__ == "__main__":
    main()
