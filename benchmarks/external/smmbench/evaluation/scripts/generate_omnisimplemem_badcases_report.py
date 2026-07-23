#!/usr/bin/env python3
"""Generate SMMBench OmniSimpleMem bad-case report (sampled per task)."""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SMMBENCH_ROOT = SCRIPT_DIR.parent.parent
RUNS_ROOT = SMMBENCH_ROOT / "runs"
OUT_DIR = SMMBENCH_ROOT / "analysis" / "omnisimplemem_badcases"
SAMPLES_ROOT = SMMBENCH_ROOT / "data" / "Samples"
IMAGES_ROOT = SMMBENCH_ROOT / "data" / "Images"
# Relative from analysis/omnisimplemem_badcases/ → data/Images/
IMAGE_MD_REL = Path("../../data/Images")

MODEL_SUBSTR = "omnisimplemem"
SAMPLE_PER_TASK = 20
# Retrieval section: show every hit with full summary (no top-k cap, no ellipsis).
RETRIEVAL_SHOW: Optional[int] = None
SUMMARY_TRUNC = 180
SEED = 42
SINCE_CUTOFF: Optional[datetime] = None

# Cache: cluster_name -> {qa_id -> qa_sample}
_QA_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}

TASK_ORDER = [
    "Single_Hop_QA",
    "Multi_Hop_QA",
    "Conflict_Resolution_QA",
    "Preference_QA",
    "Function_Call",
    "Other",
]

TAG_RULES: List[Tuple[str, str]] = [
    ("R1_retrieval_deny", r"(don't have any relevant|do not have any relevant|no relevant memor|no memories to answer|cannot find)"),
    ("T1_temporal", r"\b(before|after|first|last|earlier|later|when|order|sequence|timeline|prior)\b"),
    ("C1_counting", r"\b(how many|count|number of|total|how much)\b"),
    ("V1_visual_detail", r"\b(fig\.|image|picture|color|look like|appearance|photo)\b"),
    ("L2_comparison", r"\b(both|compare|difference|same|versus|vs\.|which one|least likely|most likely)\b"),
    ("L3_multi_hop", r"\b(also|and also|who also|which .+ also)\b"),
    ("P1_preference", r"\b(most likely|least likely|prefer|preference)\b"),
    ("F1_function_call", r"\b(function|tool|api|call)\b"),
]


def truncate(text: str, limit: Optional[int] = SUMMARY_TRUNC) -> str:
    text = " ".join(str(text or "").split())
    if limit is None or limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def item_tags(item: Dict[str, Any]) -> List[str]:
    tags = list(item.get("tags") or [])
    meta_tags = (item.get("metadata") or {}).get("tags") or []
    return tags + [t for t in meta_tags if t not in tags]


def rel_image_path(pointer: str) -> str:
    """Short path for display (avoid dumping full cold_storage absolute paths)."""
    if not pointer:
        return ""
    p = Path(str(pointer))
    parts = p.parts
    for anchor in ("cold_storage", "inputs", "smmbench"):
        if anchor in parts:
            idx = parts.index(anchor)
            return str(Path(*parts[idx + 1 :]))
    if len(parts) >= 3:
        return "/".join(parts[-3:])
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return p.name


def image_caption_from_item(item: Dict[str, Any]) -> str:
    for tag in item_tags(item):
        if str(tag).startswith("caption:"):
            return str(tag)[len("caption:") :].strip()
    return ""


def image_names_from_item(item: Dict[str, Any]) -> List[str]:
    """Image filenames for a retrieval MAU (image_id tag, pointers, region_pointers)."""
    names: List[str] = []
    for tag in item_tags(item):
        if str(tag).startswith("image_id:"):
            name = str(tag)[len("image_id:") :].strip()
            if name and name not in names:
                names.append(name)
    raw = item.get("raw_content") or {}
    pointer_values: List[str] = []
    if raw.get("pointer"):
        pointer_values.append(str(raw["pointer"]))
    if isinstance(raw.get("pointers"), list):
        pointer_values.extend(str(p) for p in raw["pointers"])
    for images in raw.get("images") or []:
        if isinstance(images, dict) and images.get("pointer"):
            pointer_values.append(str(images["pointer"]))
    for pointer in pointer_values:
        name = Path(pointer).name
        if name and name not in names:
            names.append(name)
    meta = item.get("metadata") or {}
    for pointer in meta.get("region_pointers") or []:
        name = Path(str(pointer)).name
        if name and name not in names:
            names.append(name)
    return names


def format_image_label(item: Dict[str, Any]) -> str:
    """Human-readable image marker with filename(s) when available."""
    names = image_names_from_item(item)
    name_s = ", ".join(f"`{n}`" for n in names)
    if is_vlm_image(item):
        return f" **[→VLM {name_s}]**" if name_s else " **[→VLM]**"
    if is_image_eligible(item):
        return f" **[img {name_s}, not expanded]**" if name_s else " **[img, not expanded]**"
    if names:
        return f" **[img {name_s}]**"
    return ""


def is_vlm_image(item: Dict[str, Any]) -> bool:
    """True when raw image was loaded into the multimodal prompt."""
    raw = item.get("raw_content") or {}
    return raw.get("type") == "image" and bool(raw.get("base64"))


def is_image_eligible(item: Dict[str, Any]) -> bool:
    """Caption-only image MAU in retrieval but not expanded to VLM."""
    if is_vlm_image(item):
        return False
    return "vision_on_demand" in item_tags(item) and bool(item.get("has_raw_data"))


def vlm_entries_from_items(items: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """Return (mau_id, rel_image_path, caption) for each VLM-expanded retrieval item."""
    entries: List[Tuple[str, str, str]] = []
    for it in items:
        if not is_vlm_image(it):
            continue
        pointer = str((it.get("raw_content") or {}).get("pointer") or "")
        entries.append(
            (
                str(it.get("id") or ""),
                rel_image_path(pointer),
                image_caption_from_item(it),
            )
        )
    return entries


def letter_from_index(idx: Any) -> str:
    try:
        i = int(idx)
    except (TypeError, ValueError):
        return "?"
    if 0 <= i < 26:
        return chr(ord("A") + i)
    return "?"


def load_qa_index(cluster: str) -> Dict[str, Dict[str, Any]]:
    """Load QA_sample.json for a cluster, keyed by id."""
    if cluster in _QA_CACHE:
        return _QA_CACHE[cluster]
    path = SAMPLES_ROOT / cluster / "QA_sample.json"
    index: Dict[str, Dict[str, Any]] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    index[str(item["id"])] = item
    _QA_CACHE[cluster] = index
    return index


def _assignment_ref_map(assignment_items: Any) -> Dict[str, str]:
    """Map image filename → Fig./Doc. reference_name from evidence_assignment."""
    out: Dict[str, str] = {}
    if not isinstance(assignment_items, list):
        return out
    # assignment often lacks filename; pair by order with evidence list elsewhere
    for item in assignment_items:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("reference_name") or "").strip()
        name = str(item.get("image_path") or item.get("image_name") or "").strip()
        if name and ref:
            out[Path(name).name] = ref
    return out


def gold_evidence_images(cluster: str, qa_id: Optional[str]) -> Dict[str, List[Dict[str, str]]]:
    """
    Return gold / conflicting evidence images for a QA.
    Each entry: {name, ref, kind} where kind in {gold, mis}.
    Includes:
      - evidence.image_evidence / mis_image_evidence
      - images embedded inside evidence.json_evidence blocks
    """
    empty: Dict[str, List[Dict[str, str]]] = {"gold": [], "mis": []}
    if not qa_id:
        return empty
    qa = load_qa_index(cluster).get(str(qa_id))
    if not qa:
        return empty
    evidence = qa.get("evidence") or {}
    assignment = qa.get("evidence_assignment") or {}

    def collect(filenames: Any, assigns: Any, kind: str) -> List[Dict[str, str]]:
        names = [Path(str(n)).name for n in (filenames or []) if n]
        refs_by_name = _assignment_ref_map(assigns)
        ordered_refs: List[str] = []
        if isinstance(assigns, list):
            for a in assigns:
                if isinstance(a, dict):
                    ordered_refs.append(str(a.get("reference_name") or "").strip())
        rows: List[Dict[str, str]] = []
        seen: set[str] = set()
        for i, name in enumerate(names):
            if name in seen or not (IMAGES_ROOT / name).is_file():
                continue
            seen.add(name)
            ref = refs_by_name.get(name) or (ordered_refs[i] if i < len(ordered_refs) else "")
            rows.append({"name": name, "ref": ref, "kind": kind})
        return rows

    def images_from_json_evidence(blocks: Any, kind: str) -> List[Dict[str, str]]:
        """Pull image_path from nested json_evidence document blocks."""
        rows: List[Dict[str, str]] = []
        seen: set[str] = set()

        def walk(node: Any) -> None:
            if isinstance(node, list):
                for x in node:
                    walk(x)
                return
            if not isinstance(node, dict):
                return
            if node.get("type") == "image":
                inner = node.get("content") or {}
                if isinstance(inner, dict):
                    name = Path(
                        str(inner.get("image_path") or inner.get("image_url") or "")
                    ).name
                    if name and name not in seen and (IMAGES_ROOT / name).is_file():
                        seen.add(name)
                        rows.append({"name": name, "ref": "", "kind": kind})
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)

        walk(blocks)
        return rows

    gold = collect(
        evidence.get("image_evidence"),
        assignment.get("image_evidence_assignment"),
        "gold",
    )
    # Doc-style evidence often stores figures inside json_evidence, not image_evidence
    existing = {e["name"] for e in gold}
    for entry in images_from_json_evidence(evidence.get("json_evidence"), "gold"):
        if entry["name"] not in existing:
            gold.append(entry)
            existing.add(entry["name"])

    mis = collect(
        evidence.get("mis_image_evidence"),
        assignment.get("mis_image_evidence_assignment"),
        "mis",
    )
    return {"gold": gold, "mis": mis}


def format_evidence_images(evidence_images: Dict[str, List[Dict[str, str]]]) -> List[str]:
    """Markdown embeds for gold (+ conflicting) evidence images under each MCQ."""
    gold = evidence_images.get("gold") or []
    mis = evidence_images.get("mis") or []
    if not gold and not mis:
        return ["- **Evidence images**: _(none / text-only)_", ""]

    lines: List[str] = ["- **Evidence images**:"]
    for entry in gold:
        name = entry["name"]
        ref = entry.get("ref") or ""
        label = f"{ref} — `{name}`" if ref else f"`{name}`"
        rel = (IMAGE_MD_REL / name).as_posix()
        lines.append(f"  - {label}")
        lines.append(f"    ![{name}]({rel})")
    for entry in mis:
        name = entry["name"]
        ref = entry.get("ref") or ""
        label = f"(conflicting) {ref} — `{name}`" if ref else f"(conflicting) `{name}`"
        rel = (IMAGE_MD_REL / name).as_posix()
        lines.append(f"  - {label}")
        lines.append(f"    ![{name}]({rel})")
    lines.append("")
    return lines


def parse_pred_letter(raw: str, options: List[str]) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    m = re.search(r"\(([A-Da-d])\)", text)
    if m:
        return m.group(1).upper()
    m = re.match(r"^([A-Da-d])\b", text)
    if m:
        return m.group(1).upper()
    # exact option text match
    for i, opt in enumerate(options or []):
        if text == str(opt).strip() or text.lower() == str(opt).strip().lower():
            return letter_from_index(i)
    return ""


def is_deny(raw: str) -> bool:
    return bool(
        re.search(
            r"(don't have any relevant|do not have any relevant|no relevant memor|no memories to answer)",
            raw or "",
            re.I,
        )
    )


def failure_tag(question: str, raw: str, category: str) -> str:
    tags: List[str] = []
    blob = f"{question}\n{raw}"
    for name, pat in TAG_RULES:
        if re.search(pat, blob, re.I):
            tags.append(name)
    if category == "Function_Call" and "F1_function_call" not in tags:
        tags.append("F1_function_call")
    if category == "Preference_QA" and "P1_preference" not in tags:
        tags.append("P1_preference")
    if not tags:
        return "U0_other"
    # keep deny first if present
    if "R1_retrieval_deny" in tags:
        tags = ["R1_retrieval_deny"] + [t for t in tags if t != "R1_retrieval_deny"]
    return "+".join(tags[:3])


def find_result_files() -> List[Path]:
    files = sorted(RUNS_ROOT.glob(f"cluster_*/time_sequential_memory__{MODEL_SUBSTR}__*round0.json"))
    out: List[Path] = []
    for p in files:
        if "_readable" in p.name:
            continue
        if SINCE_CUTOFF is not None:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime < SINCE_CUTOFF:
                continue
        out.append(p)
    return out


def load_cluster_items(round0: Path) -> Tuple[str, List[Dict[str, Any]], Optional[Path]]:
    cluster = round0.parent.name
    data = json.loads(round0.read_text())
    items = data.get("cluster") if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = []
    readable = round0.with_name(round0.name.replace(".json", "_readable.json"))
    if not readable.exists():
        # alternate naming
        candidates = list(round0.parent.glob("*round0_readable.json"))
        readable = candidates[0] if candidates else None
    return cluster, items, readable


def index_readable(readable: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if readable is None or not readable.exists():
        return {}
    data = json.loads(readable.read_text())
    items = data.get("cluster") if isinstance(data, dict) else data
    out: Dict[str, Dict[str, Any]] = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        qid = it.get("id")
        if qid:
            out[qid] = it
    return out


def enrich_case(base: Dict[str, Any], readable_item: Optional[Dict[str, Any]], cluster: str) -> Dict[str, Any]:
    mcq = base.get("multi_choice_QA") or {}
    options = list(mcq.get("multi_choice_QA_options") or [])
    gt_idx = mcq.get("multi_choice_QA_answer")
    gt = letter_from_index(gt_idx) if options else str(base.get("answer") or "")
    raw = base.get("raw_response") or ""
    pred = parse_pred_letter(raw, options)
    msgs_raw = (readable_item or {}).get("messages")
    msgs = msgs_raw if isinstance(msgs_raw, dict) else {}
    rr_raw = msgs.get("retrieval_result")
    rr = rr_raw if isinstance(rr_raw, dict) else {}
    items_raw = rr.get("items")
    items = items_raw if isinstance(items_raw, list) else []
    vlm_entries = vlm_entries_from_items(items)
    evidence_images = gold_evidence_images(cluster, base.get("id"))
    return {
        "cluster": cluster,
        "id": base.get("id"),
        "category": base.get("category") or "Other",
        "question": base.get("question") or "",
        "answer": base.get("answer"),
        "gt_letter": gt,
        "pred_letter": pred or ("DENY" if is_deny(raw) else ""),
        "options": options,
        "raw_response": raw,
        "deny": is_deny(raw),
        "failure_tag": failure_tag(base.get("question") or "", raw, base.get("category") or ""),
        "n_retrieval": len(items),
        "n_vlm_images": len(vlm_entries),
        "n_image_eligible": sum(1 for it in items if is_image_eligible(it)),
        "total_candidates": rr.get("total_candidates"),
        "retrieval_items": items,
        "vlm_entries": vlm_entries,
        "evidence_images": evidence_images,
        "latency_ms": msgs.get("latency_ms"),
        "query_image_used": msgs.get("query_image_used"),
        "stored_text_items": msgs.get("stored_text_items"),
        "stored_image_items": msgs.get("stored_image_items"),
    }


def collect_all() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Counter, Counter]:
    """Returns (all_rows_for_stats, wrong_rows, total_by_cat, wrong_by_cat)."""
    totals: Counter = Counter()
    wrongs: Counter = Counter()
    wrong_rows: List[Dict[str, Any]] = []
    all_n = 0
    correct_n = 0

    for round0 in find_result_files():
        cluster, items, readable = load_cluster_items(round0)
        rmap = index_readable(readable)
        for it in items:
            cat = it.get("category") or "Other"
            totals[cat] += 1
            all_n += 1
            ok = it.get("single_qa_result") is True
            if ok:
                correct_n += 1
                continue
            wrongs[cat] += 1
            wrong_rows.append(enrich_case(it, rmap.get(it.get("id")), cluster))

    return (
        [{"_all_n": all_n, "_correct_n": correct_n}],
        wrong_rows,
        totals,
        wrongs,
    )


def sample_per_task(wrong_rows: List[Dict[str, Any]], k: int = SAMPLE_PER_TASK) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(SEED)
    by_cat: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in wrong_rows:
        by_cat[row["category"]].append(row)

    sampled: Dict[str, List[Dict[str, Any]]] = {}
    for cat in TASK_ORDER:
        rows = by_cat.get(cat, [])
        if not rows:
            continue
        # diversify: shuffle within cluster-stratified buckets
        by_cluster: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_cluster[r["cluster"]].append(r)
        pool: List[Dict[str, Any]] = []
        clusters = list(by_cluster.keys())
        rng.shuffle(clusters)
        # round-robin pick to cover more clusters
        pointers = {c: 0 for c in clusters}
        for c in clusters:
            rng.shuffle(by_cluster[c])
        while len(pool) < min(k, len(rows)):
            progressed = False
            for c in clusters:
                i = pointers[c]
                if i < len(by_cluster[c]):
                    pool.append(by_cluster[c][i])
                    pointers[c] = i + 1
                    progressed = True
                    if len(pool) >= min(k, len(rows)):
                        break
            if not progressed:
                break
        # prefer mix of deny / non-deny if possible
        deny = [r for r in pool if r["deny"]]
        nondeny = [r for r in pool if not r["deny"]]
        if deny and nondeny and len(pool) >= k:
            half = k // 2
            mix = deny[:half] + nondeny[: k - half]
            # fill if short
            used = {id(r) for r in mix}
            for r in pool:
                if len(mix) >= k:
                    break
                if id(r) not in used:
                    mix.append(r)
            pool = mix[:k]
        else:
            pool = pool[:k]
        sampled[cat] = pool
    # leftover categories
    for cat, rows in by_cat.items():
        if cat not in sampled and rows:
            sampled[cat] = rows[:k]
    return sampled


def format_options(options: List[str], gt: str, pred: str) -> List[str]:
    lines = []
    for i, opt in enumerate(options):
        letter = letter_from_index(i)
        marks = []
        if letter == gt:
            marks.append("GT")
        if letter == pred:
            marks.append("Pred")
        suffix = f" ← {'+'.join(marks)}" if marks else ""
        lines.append(f"  - **{letter}**: {truncate(opt, 160)}{suffix}")
    return lines


def format_retrieval(
    items: List[Dict[str, Any]],
    show: Optional[int] = RETRIEVAL_SHOW,
    *,
    total_candidates: Optional[int] = None,
    vlm_entries: Optional[List[Tuple[str, str, str]]] = None,
) -> List[str]:
    vlm_entries = vlm_entries if vlm_entries is not None else vlm_entries_from_items(items)
    n_vlm = len(vlm_entries)
    if not items:
        lines = ["**Retrieval**"]
        if total_candidates is not None:
            lines[0] += (
                f" _(items=0, total_candidates={total_candidates}; "
                "likely filtered or empty search)_"
            )
        else:
            lines[0] += " _(no retrieval items recorded)_"
        lines.extend(["- **→ VLM**: _(no images)_", ""])
        return lines

    shown = items if show is None else items[:show]
    n_eligible = sum(1 for it in items if is_image_eligible(it))
    lines = [f"**Retrieval ({len(shown)}/{len(items)} items, VLM images {n_vlm})**"]
    for i, it in enumerate(shown, 1):
        score = it.get("score")
        score_s = f"score={score:.2f} " if isinstance(score, (int, float)) else ""
        modality = it.get("modality_type") or "?"
        summary = truncate(it.get("summary") or "", limit=None)
        mau = it.get("id") or ""
        img_note = format_image_label(it)
        lines.append(f"- #{i} {score_s}`{mau}` [{modality}]{img_note}: {summary}")
    if show is not None and len(items) > show:
        hidden_vlm = sum(1 for it in items[show:] if is_vlm_image(it))
        extra = f", incl. {hidden_vlm} VLM" if hidden_vlm else ""
        lines.append(f"- … (+{len(items) - show} more{extra})")
    if n_eligible:
        lines.append(
            f"- _(+{n_eligible} retrieval item(s) have raw image but were not expanded to VLM)_"
        )
    if vlm_entries:
        lines.append(f"- **→ VLM ({len(vlm_entries)})**:")
        for mau_id, rel_path, caption in vlm_entries:
            image_name = Path(rel_path).name if rel_path else ""
            line = f"  - `{image_name or rel_path}`"
            if rel_path and image_name and rel_path != image_name:
                line += f" ({rel_path})"
            if mau_id:
                line += f" — `{mau_id}`"
            if caption:
                line += f": {truncate(caption, limit=None)}"
            lines.append(line)
    else:
        lines.append("- **→ VLM**: _(no images)_")
    lines.append("")
    return lines


def format_case_card(row: Dict[str, Any], idx: int) -> List[str]:
    lines: List[str] = []
    title_hint = "DENY" if row["deny"] else (row["pred_letter"] or "wrong")
    lines.append(f"#### {idx}. `{row['cluster']}` / `{row['id']}` — {title_hint}")
    lines.append("")
    lines.append(f"- **Tag**: `{row['failure_tag']}`")
    lines.append(f"- **Retrieval items**: {row['n_retrieval']}")
    lines.append(f"- **VLM images expanded**: {row.get('n_vlm_images', 0)}")
    if row.get("total_candidates") is not None:
        lines.append(f"- **total_candidates** (pre-filter): `{row['total_candidates']}`")
    if row.get("query_image_used") is not None:
        lines.append(f"- **query_image_used**: `{row['query_image_used']}`")
    if row.get("latency_ms") is not None:
        try:
            lines.append(f"- **latency_ms**: `{float(row['latency_ms']):.0f}`")
        except (TypeError, ValueError):
            pass
    lines.append("")
    lines.append("**MCQ**")
    lines.append(f"- Q: {row['question']}")
    if row["options"]:
        lines.append("- Options:")
        lines.extend(format_options(row["options"], row["gt_letter"], row["pred_letter"]))
    lines.append(
        f"- GT: `{row['gt_letter'] or row.get('answer')}` | Pred: `{row['pred_letter'] or '—'}`"
    )
    lines.append(f"- Raw: {truncate(row['raw_response'], 280)}")
    lines.extend(format_evidence_images(row.get("evidence_images") or {}))
    lines.extend(
        format_retrieval(
            row.get("retrieval_items") or [],
            total_candidates=row.get("total_candidates"),
            vlm_entries=row.get("vlm_entries") or [],
        )
    )
    lines.append("---")
    lines.append("")
    return lines


def build_report(
    totals: Counter,
    wrongs: Counter,
    all_n: int,
    correct_n: int,
    wrong_rows: List[Dict[str, Any]],
    sampled: Dict[str, List[Dict[str, Any]]],
    done_clusters: List[int],
) -> str:
    lines: List[str] = []
    lines.append("# SMMBench OmniSimpleMem Bad Cases Report (sampled)")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("- Model: `qwen3-vl-235b-a22b-instruct` (DashScope)")
    if SINCE_CUTOFF is not None:
        lines.append(
            f"- Source: QA rerun only (`round0` mtime >= {SINCE_CUTOFF.strftime('%Y-%m-%d %H:%M')}, "
            "`OMNI_SKIP_INGEST=1`, VLM expand enabled)"
        )
    lines.append("- Method: `omnisimplemem` (BGE-M3 + per-round ingest + BM25 hybrid + on-demand images)")
    lines.append(
        "- Ingest: one TEXT MAU per round (`force=False`); user+assistant paired in UA sessions; "
        "multi-image via `raw_pointer` + `region_pointers` + `vision_on_demand`; BM25 built after ingest"
    )
    lines.append(
        "- Note: runs before P2 ingest alignment or with old checkpoints are not comparable; "
        "clear `checkpoint/omnisimplemem` and re-ingest after ingest changes"
    )
    lines.append(
        f"- Coverage: **{len(done_clusters)}/61 clusters** completed "
        f"({', '.join(f'c{i}' for i in done_clusters[:8])}{'…' if len(done_clusters) > 8 else ''})"
    )
    lines.append(
        f"- Definition: `single_qa_result == false` (MCQ / Function_Call harness)"
    )
    lines.append(
        f"- Sample: up to **{SAMPLE_PER_TASK} wrong cases per task** (seed={SEED}, cluster-diversified)"
    )
    lines.append("")
    lines.append("## 1. Overall (all completed clusters)")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| Clusters done | {len(done_clusters)} / 61 |")
    lines.append(f"| Accuracy (micro) | {correct_n}/{all_n} ({100 * correct_n / all_n:.1f}%) |")
    lines.append(f"| Wrong (eligible for bad cases) | {all_n - correct_n} |")
    lines.append(f"| Sampled in this report | {sum(len(v) for v in sampled.values())} |")
    lines.append("")
    lines.append("## 2. Breakdown by task")
    lines.append("")
    lines.append("| Task | Wrong | Total | Acc | Sampled |")
    lines.append("|------|------:|------:|----:|--------:|")
    for cat in TASK_ORDER:
        t = totals.get(cat, 0)
        w = wrongs.get(cat, 0)
        if t == 0 and cat not in sampled:
            continue
        acc = f"{100 * (t - w) / t:.1f}%" if t else "—"
        lines.append(f"| `{cat}` | {w} | {t} | {acc} | {len(sampled.get(cat, []))} |")
    for cat in sorted(set(totals) - set(TASK_ORDER)):
        t = totals[cat]
        w = wrongs[cat]
        acc = f"{100 * (t - w) / t:.1f}%" if t else "—"
        lines.append(f"| `{cat}` | {w} | {t} | {acc} | {len(sampled.get(cat, []))} |")
    lines.append("")

    deny_n = sum(1 for r in wrong_rows if r["deny"])
    lines.append("### Wrong-response mode (all wrong)")
    lines.append("")
    lines.append("| Mode | Count | Share of wrong |")
    lines.append("|------|------:|---------------:|")
    lines.append(
        f"| Retrieval deny / no memory | {deny_n} | {100 * deny_n / max(1, len(wrong_rows)):.1f}% |"
    )
    lines.append(
        f"| Other wrong answer | {len(wrong_rows) - deny_n} | {100 * (len(wrong_rows) - deny_n) / max(1, len(wrong_rows)):.1f}% |"
    )
    lines.append("")

    sample_flat = [r for rows in sampled.values() for r in rows]
    by_tag = Counter(r["failure_tag"] for r in sample_flat)
    lines.append("### Auto failure tags (sampled only; heuristic)")
    lines.append("")
    lines.append("| Tag | Count |")
    lines.append("|------|------:|")
    for tag, n in by_tag.most_common(20):
        lines.append(f"| `{tag}` | {n} |")
    lines.append("")
    lines.append("## 3. How to use")
    lines.append("")
    lines.append("- Machine-readable sample: `badcases_sample.csv`")
    lines.append("- Case cards below are grouped by SMMBench task category")
    lines.append(
        "- **Evidence images** under each MCQ are gold (and conflicting) images from "
        "`QA_sample.json` (`image_evidence` + figures inside `json_evidence`), embedded via "
        "`../../data/Images/...` (hover/preview in IDE)"
    )
    lines.append("- Retrieval lists **all** hits per case (full summary, no top-k truncation)")
    lines.append("- Retrieval snippets come from `*_round0_readable.json` when available")
    lines.append("- `[→VLM \`name.png\`]` = that MAU's raw image was loaded into the VLM prompt (`raw_content.base64`)")
    lines.append("- `[img \`name.png\`, not expanded]` = image-tagged memory in context text only (`vision_on_demand` / caption MAU, no base64)")
    lines.append("- `→ VLM (N)` lists all expanded images for the question (filename + full caption when present)")
    lines.append(
        "- VLM expansion: `max_expanded_items` (default 5, upstream-aligned) and "
        "`evidence_token_budget` (default 6000), score/token greedy"
    )
    lines.append("- `total_candidates` > 0 with `items=0` usually means modality filter removed all hits (pre-fix runs)")
    lines.append("")
    lines.append("## 4. Sampled bad-case cards")
    lines.append("")

    for cat in TASK_ORDER:
        rows = sampled.get(cat) or []
        if not rows:
            continue
        t = totals.get(cat, 0)
        w = wrongs.get(cat, 0)
        acc = f"{100 * (t - w) / t:.1f}%" if t else "—"
        lines.append(f"## `{cat}` — sample {len(rows)} / wrong {w} / total {t} (acc {acc})")
        lines.append("")
        for i, row in enumerate(rows, 1):
            lines.extend(format_case_card(row, i))
    return "\n".join(lines) + "\n"


def write_csv(path: Path, sampled: Dict[str, List[Dict[str, Any]]]) -> None:
    fields = [
        "category",
        "cluster",
        "id",
        "gt_letter",
        "pred_letter",
        "deny",
        "failure_tag",
        "n_retrieval",
        "n_vlm_images",
        "question",
        "raw_response",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for cat in TASK_ORDER:
            for row in sampled.get(cat, []):
                w.writerow({k: row.get(k) for k in fields})


def main() -> None:
    global SINCE_CUTOFF
    parser = argparse.ArgumentParser(description="Generate OmniSimpleMem bad-case report")
    parser.add_argument(
        "--since",
        metavar="DATETIME",
        help="Only include round0 files modified at or after this time (e.g. '2026-07-22 11:00')",
    )
    parser.add_argument(
        "--sample-per-task",
        type=int,
        default=SAMPLE_PER_TASK,
        help=f"Max wrong cases per task (default {SAMPLE_PER_TASK})",
    )
    args = parser.parse_args()
    if args.since:
        SINCE_CUTOFF = datetime.strptime(args.since, "%Y-%m-%d %H:%M")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta, wrong_rows, totals, wrongs = collect_all()
    all_n = meta[0]["_all_n"]
    correct_n = meta[0]["_correct_n"]
    done_clusters = sorted(
        int(p.parent.name.split("_")[1])
        for p in find_result_files()
    )
    sampled = sample_per_task(wrong_rows, args.sample_per_task)
    report = build_report(totals, wrongs, all_n, correct_n, wrong_rows, sampled, done_clusters)
    md_path = OUT_DIR / "REPORT_badcases_sampled.md"
    csv_path = OUT_DIR / "badcases_sample.csv"
    md_path.write_text(report, encoding="utf-8")
    write_csv(csv_path, sampled)
    print(f"wrote {md_path}")
    print(f"wrote {csv_path}")
    print(
        f"clusters={len(done_clusters)} acc={correct_n}/{all_n} "
        f"sampled={sum(len(v) for v in sampled.values())}"
    )
    for cat in TASK_ORDER:
        if cat in sampled:
            print(f"  {cat}: {len(sampled[cat])}")


if __name__ == "__main__":
    main()
