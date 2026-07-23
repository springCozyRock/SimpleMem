#!/usr/bin/env python3
"""Generate Qwen3-VL-8B paired-wrong bad-case report (MCQ + Open both fail)."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
MEMEYE_ROOT = SCRIPT_DIR.parent
ROOT = MEMEYE_ROOT / "runs" / "benchmark8"
OUT_DIR = MEMEYE_ROOT / "analysis" / "qwen3_vl_8b_badcases"

MCQ_PATH = ROOT / "mcq/qwen3_vl_8b_dashscope__simplemem__multimodal/predictions.jsonl"
OPEN_PATH = ROOT / "open/qwen3_vl_8b_dashscope__simplemem__multimodal/predictions.jsonl"
MCQ_METRICS = ROOT / "mcq/qwen3_vl_8b_dashscope__simplemem__multimodal/metrics.json"
OPEN_METRICS = ROOT / "open/qwen3_vl_8b_dashscope__simplemem__multimodal/metrics.json"

MEMEYE_TASK_ORDER = [
    "brand_memory_test",
    "card_playlog_test",
    "cartoon_entertainment_companion",
    "home_renovation_interior_design",
    "multi_scene_visual_case_archive_assistant",
    "outdoor_navigation_route_memory_assistant",
    "personal_health_dashboard_assistant",
    "social_chat_memory_test",
]

TASK_MCQ_DIALOG = {
    "brand_memory_test": "Brand_Memory_Test.json",
    "card_playlog_test": "Card_Playlog_Test.json",
    "cartoon_entertainment_companion": "Cartoon_Entertainment_Companion.json",
    "home_renovation_interior_design": "Home_Renovation_Interior_Design.json",
    "multi_scene_visual_case_archive_assistant": "Multi-Scene_Visual_Case_Archive_Assistant.json",
    "outdoor_navigation_route_memory_assistant": "Outdoor_Navigation_Route_Memory_Assistant.json",
    "personal_health_dashboard_assistant": "Personal_Health_Dashboard_Assistant.json",
    "social_chat_memory_test": "Social_Chat_Memory_Test.json",
}

DIALOG_ROOT = MEMEYE_ROOT / "data" / "dialog"
IMAGE_ROOT = MEMEYE_ROOT / "data" / "image"
TEXT_TRUNC = 400
RETRIEVAL_TEXT_TRUNC = 140
RETRIEVAL_TEXT_TRUNC_LONG = 200
RETRIEVAL_KG_LINE_TRUNC = 200
RETRIEVAL_TOP_K = 0  # 0 = show all retrieved_items that entered context
CLUE_TEXT_TRUNC = 200
VLM_CAPTION_TRUNC = 240
_IMAGE_CAPTION_RE = re.compile(r"image_caption:\s*(.+?)(?:\n|$)", re.IGNORECASE)

# MemEye matrix cell order: group by Y first (Y1: X1→X4, then Y2, Y3).
CELL_ORDER = [f"X{x}_Y{y}" for y in range(1, 4) for x in range(1, 5)]
AXIS_X_ORDER = [f"X{x}" for x in range(1, 5)]
AXIS_Y_ORDER = [f"Y{y}" for y in range(1, 4)]

TAG_RULES: List[Tuple[str, str]] = [
    ("T1_temporal", r"\b(before|after|first|last|earlier|later|when|order|sequence|timeline|prior)\b"),
    ("C1_counting", r"\b(how many|count|number of|total|how much)\b"),
    ("V1_visual_detail", r"\b(color|background|pixel|shape|look like|appearance|shade|hue|eye|font)\b"),
    ("B1_brand", r"\b(brand|which brand|company|advertisement|ad\b)\b"),
    ("R1_retrieval_deny", r"(no such memory|not discuss|no memory|do not contain|not contain any|was not discussed|cannot find)"),
    ("L2_comparison", r"\b(both|compare|difference|same|versus|vs\.|which one)\b"),
    ("L3_multi_session", r"\b(across|entire conversation|all \d+|between)\b"),
]


def truncate(text: str, limit: int = TEXT_TRUNC) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def rel_image(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.relative_to(IMAGE_ROOT))
    except ValueError:
        return p.name


def load_context(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return load_json(p)


def _extract_image_caption(text: str) -> str:
    if not text:
        return ""
    match = _IMAGE_CAPTION_RE.search(text)
    return match.group(1).strip() if match else ""


def _lookup_image_caption(rel_path: str, *caption_maps: Dict[str, str]) -> str:
    name = Path(rel_path).name
    for caption_map in caption_maps:
        if rel_path in caption_map:
            return caption_map[rel_path]
        if name in caption_map:
            return caption_map[name]
    return ""


def _caption_map_from_retrieved_items(items: List[Dict[str, Any]]) -> Dict[str, str]:
    caption_map: Dict[str, str] = {}
    for item in items:
        image_path = item.get("image_path")
        if not image_path:
            continue
        rel = rel_image(str(image_path))
        caption = _extract_image_caption(item.get("full_text_preview") or "")
        if caption:
            caption_map[rel] = caption
            caption_map[Path(rel).name] = caption
    return caption_map


def _vlm_image_entries(
    ctx: Dict[str, Any],
    dialog_captions: Optional[Dict[str, str]] = None,
) -> List[Tuple[str, str]]:
    """Return (rel_image_path, caption) for each image sent to the VLM."""
    items = ctx.get("retrieved_items") or []
    items_by_rank = {
        int(item["rank"]): item for item in items if item.get("rank") is not None
    }
    item_captions = _caption_map_from_retrieved_items(items)
    dialog_captions = dialog_captions or {}

    entries: List[Tuple[str, str]] = []
    expanded = ctx.get("images_expanded") or []
    if expanded:
        for row in expanded:
            image_path = row.get("image_path", "")
            if not image_path:
                continue
            rel = rel_image(str(image_path))
            caption = ""
            rank = row.get("context_rank")
            if rank is not None:
                item = items_by_rank.get(int(rank))
                if item:
                    caption = _extract_image_caption(item.get("full_text_preview") or "")
            if not caption:
                caption = _lookup_image_caption(rel, item_captions, dialog_captions)
            entries.append((rel, caption))
        return entries

    for image_path in (ctx.get("prompt") or {}).get("user_image_paths") or []:
        rel = rel_image(str(image_path))
        caption = _lookup_image_caption(rel, item_captions, dialog_captions)
        entries.append((rel, caption))
    return entries


def _knowledge_graph_text(ctx: Dict[str, Any]) -> str:
    """KG block appended to LLM context (separate from faiss/bm25 retrieved_items)."""
    kg = str(ctx.get("knowledge_graph_text") or "").strip()
    if kg:
        return kg
    context_text = str(ctx.get("context_text") or "")
    marker = "\n\n[Knowledge Graph]\n"
    if marker in context_text:
        return context_text.split(marker, 1)[1].strip()
    return ""


def format_retrieval_block(
    context_path: str,
    label: str,
    *,
    dialog_captions: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Full retrieval trace: retrieved_items + KG text + images sent to VLM."""
    lines: List[str] = []
    ctx = load_context(context_path)
    if ctx is None:
        lines.append(f"**Retrieval ({label})**: _(context missing: `{context_path}`)_")
        lines.append("")
        return lines

    items = ctx.get("retrieved_items") or []
    retrieve_k = ctx.get("retrieve_k", "?")
    shown = items if not RETRIEVAL_TOP_K else items[:RETRIEVAL_TOP_K]
    lines.append(
        f"**Retrieval ({label}, {len(shown)}/{retrieve_k} in context)**"
    )
    if not shown:
        lines.append("- _(no retrieved items)_")
    for it in shown:
        rank = it.get("rank", "?")
        score = it.get("score")
        score_s = f" score={score:.2f}" if isinstance(score, (int, float)) else ""
        rid = it.get("round_id") or it.get("id", "")
        text = it.get("full_text_preview") or it.get("summary") or ""
        limit = RETRIEVAL_TEXT_TRUNC_LONG if it.get("image_expanded") or it.get("image_path") else RETRIEVAL_TEXT_TRUNC
        img_note = ""
        if it.get("image_path"):
            img_note = f" [img `{rel_image(it['image_path'])}`]"
        elif it.get("image_expanded"):
            img_note = " [expanded]"
        source = it.get("source", "")
        source_s = f" {source}" if source else ""
        lines.append(
            f"- #{rank}{score_s}{source_s} `{rid}`{img_note}: {truncate(text, limit)}"
        )

    kg_text = _knowledge_graph_text(ctx)
    if kg_text:
        lines.append("- **→ Knowledge Graph**:")
        for line in kg_text.splitlines():
            stripped = line.rstrip()
            if stripped:
                lines.append(f"  - {truncate(stripped, RETRIEVAL_KG_LINE_TRUNC)}")
    else:
        lines.append("- **→ Knowledge Graph**: _(empty)_")

    vlm_entries = _vlm_image_entries(ctx, dialog_captions)
    if vlm_entries:
        lines.append(f"- **→ VLM ({len(vlm_entries)})**:")
        for rel_path, caption in vlm_entries:
            line = f"  - `{rel_path}`"
            if caption:
                line += f": {truncate(caption, VLM_CAPTION_TRUNC)}"
            lines.append(line)
    else:
        lines.append("- **→ VLM**: _(no images)_")
    lines.append("")
    return lines


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class TaskDialogIndex:
    """Lazy-loaded dialog JSON + round lookup per MemEye task."""

    def __init__(self, dialog_root: Path = DIALOG_ROOT) -> None:
        self.dialog_root = dialog_root
        self._cache: Dict[str, Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = {}

    def _load(self, task: str) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        if task in self._cache:
            return self._cache[task]
        filename = TASK_MCQ_DIALOG.get(task)
        if not filename:
            self._cache[task] = ([], {})
            return self._cache[task]
        path = self.dialog_root / filename
        if not path.exists():
            self._cache[task] = ([], {})
            return self._cache[task]
        data = load_json(path)
        rounds: Dict[str, Dict[str, Any]] = {}
        for sess in data.get("multi_session_dialogues", []):
            for dlg in sess.get("dialogues", []):
                rid = dlg.get("round", "")
                if rid:
                    rounds[rid] = dlg
        qas = data.get("human-annotated QAs") or data.get("human_annotated_qas") or []
        self._cache[task] = (qas, rounds)
        return self._cache[task]

    def qa(self, task: str, idx: int) -> Optional[Dict[str, Any]]:
        qas, _ = self._load(task)
        if idx < 1 or idx > len(qas):
            return None
        return qas[idx - 1]

    def round_payload(self, task: str, round_id: str) -> Optional[Dict[str, Any]]:
        _, rounds = self._load(task)
        return rounds.get(round_id)

    def image_caption_index(self, task: str) -> Dict[str, str]:
        """Map relative image path (and basename) -> caption from dialog JSON."""
        _, rounds = self._load(task)
        caption_map: Dict[str, str] = {}
        for payload in rounds.values():
            images = payload.get("input_image") or []
            captions = payload.get("image_caption") or []
            for idx, image in enumerate(images):
                rel = str(image).strip()
                if not rel:
                    continue
                caption = str(captions[idx]).strip() if idx < len(captions) else ""
                if not caption:
                    continue
                caption_map[rel] = caption
                caption_map[Path(rel).name] = caption
        return caption_map


def canonical_mcq_options(qa: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    """Return option letter→text and GT letter (matches runner last-rotation display)."""
    options = qa.get("options")
    gt = str(qa.get("answer", "")).strip().upper()
    if isinstance(options, list) and options:
        rot = options[-1]
        option_map = {k: v for k, v in rot.items() if k != "answer"}
        return option_map, gt
    if isinstance(options, dict):
        option_map = {k: v for k, v in options.items() if k != "answer"}
        return option_map, gt
    return {}, gt


def format_mcq_options_block(option_map: Dict[str, str], gt: str, pred: str) -> List[str]:
    lines: List[str] = []
    for key in sorted(option_map.keys()):
        marker = ""
        tags: List[str] = []
        if key == gt:
            tags.append("GT")
        if key == pred.strip().upper():
            tags.append("Pred")
        if tags:
            marker = f" ← {', '.join(tags)}"
        lines.append(f"  - **{key}**: {option_map[key]}{marker}")
    return lines


def format_clue_dialogues(task: str, clue_rounds: List[str], index: TaskDialogIndex) -> List[str]:
    lines: List[str] = []
    for round_id in clue_rounds:
        payload = index.round_payload(task, round_id)
        session_hint = round_id.split(":")[0] if ":" in round_id else ""
        lines.append(f"##### `{round_id}`" + (f" (session `{session_hint}`)" if session_hint else ""))
        if not payload:
            lines.append("- _(round not found in dialog JSON)_")
            continue
        user = payload.get("user", "")
        assistant = payload.get("assistant", "")
        if user:
            lines.append(f"- **User**: {truncate(user, CLUE_TEXT_TRUNC)}")
        if assistant:
            lines.append(f"- **Assistant**: {truncate(assistant, CLUE_TEXT_TRUNC)}")
        captions = payload.get("image_caption") or []
        images = payload.get("input_image") or []
        if captions:
            for i, cap in enumerate(captions):
                img = images[i] if i < len(images) else ""
                cap_line = f"- **Caption**: {truncate(str(cap))}"
                if img:
                    cap_line += f" (`{img}`)"
                lines.append(cap_line)
        elif images:
            for img in images:
                lines.append(f"- **Image**: `{img}`")
        lines.append("")
    return lines


def enrich_paired_row(row: Dict[str, Any], index: TaskDialogIndex) -> Dict[str, Any]:
    qa = index.qa(row["task"], row["idx"])
    out = dict(row)
    clue_list = [c for c in (row.get("clue_rounds") or "").split(";") if c]
    session_list = [s for s in (row.get("source_sessions") or "").split(";") if s]

    if qa:
        option_map, gt_letter = canonical_mcq_options(qa)
        out["session_id"] = ";".join(qa.get("session_id") or [])
        out["mcq_options"] = " | ".join(f"{k}:{option_map[k]}" for k in sorted(option_map.keys()))
        out["mcq_option_map"] = option_map
        out["mcq_gt_letter"] = gt_letter
        if not clue_list:
            clue_list = list(qa.get("clue") or [])
            out["clue_rounds"] = ";".join(clue_list)
            out["num_clues"] = len(clue_list)
        if not session_list:
            session_list = list(qa.get("session_id") or [])
            out["source_sessions"] = ";".join(session_list)
    else:
        out["session_id"] = row.get("source_sessions", "")
        out["mcq_options"] = ""
        out["mcq_option_map"] = {}
        out["mcq_gt_letter"] = row.get("mcq_gt", "")

    out["clue_dialogue_md"] = format_clue_dialogues(row["task"], clue_list, index)
    return out


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def matrix_cells(point: Any) -> List[str]:
    if not isinstance(point, list) or len(point) != 2:
        return []
    xs, ys = point[0], point[1]
    if not isinstance(xs, list) or not isinstance(ys, list):
        return []
    return [f"{x}_{y}" for x in xs for y in ys]


def matrix_axes(point: Any) -> Tuple[str, str]:
    cells = matrix_cells(point)
    if not cells:
        return "", ""
    parts = cells[0].split("_", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else ("", "")


def matrix_axes_all(point: Any) -> Tuple[List[str], List[str]]:
    if not isinstance(point, list) or len(point) != 2:
        return [], []
    xs, ys = point[0], point[1]
    if not isinstance(xs, list) or not isinstance(ys, list):
        return [], []
    return list(xs), list(ys)


def count_by_category(rows: List[Dict[str, Any]]) -> Tuple[Counter, Counter, Counter, Counter]:
    """Count rows by cell / task / X / Y (MemEye matrix convention)."""
    by_cell: Counter = Counter()
    by_task: Counter = Counter()
    by_x: Counter = Counter()
    by_y: Counter = Counter()
    for row in rows:
        by_task[row.get("task_name") or row.get("task", "")] += 1
        xs, ys = matrix_axes_all(row.get("point"))
        for cell in matrix_cells(row.get("point")):
            by_cell[cell] += 1
        for x in dict.fromkeys(xs):
            by_x[x] += 1
        for y in dict.fromkeys(ys):
            by_y[y] += 1
    return by_cell, by_task, by_x, by_y


def _sort_cells(keys: List[str]) -> List[str]:
    order = {name: idx for idx, name in enumerate(CELL_ORDER)}
    return sorted(keys, key=lambda k: order.get(k, 999))


def _sort_tasks(keys: List[str]) -> List[str]:
    order = {name: idx for idx, name in enumerate(MEMEYE_TASK_ORDER)}
    return sorted(keys, key=lambda k: order.get(k, 999))


def _rate_table(
    lines: List[str],
    title: str,
    headers: Tuple[str, ...],
    keys: List[str],
    wrong: Counter,
    total: Counter,
) -> None:
    lines.append(f"### {title}")
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["------"] * len(headers)) + "|")
    for key in keys:
        if key not in total and key not in wrong:
            continue
        w = wrong.get(key, 0)
        t = total.get(key, 0)
        rate = f"{100 * w / t:.1f}%" if t else "—"
        display = f"`{key}`" if key in MEMEYE_TASK_ORDER else key
        lines.append(f"| {display} | {w} | {t} | {rate} |")
    lines.append("")


def auto_tag(mcq: Dict[str, Any], open_row: Dict[str, Any]) -> str:
    text = f"{mcq.get('question', '')} {open_row.get('question', '')} {open_row.get('pred', '')}"
    tags: List[str] = []
    for name, pattern in TAG_RULES:
        if re.search(pattern, text, re.I):
            tags.append(name)
    if not tags:
        return "U0_other"
    return "+".join(tags[:3])


def position_bias_flag(mcq: Dict[str, Any]) -> str:
    pb = mcq.get("position_bias") or {}
    if not pb:
        return ""
    top = max(pb, key=pb.get)
    if pb[top] >= 2:
        return f"bias_{top}x{pb[top]}"
    return ""


def paired_rows(mcq_rows: List[Dict[str, Any]], open_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    open_by = {(r["task_name"], r["idx"]): r for r in open_rows}
    out: List[Dict[str, Any]] = []
    mcq_paired: List[Dict[str, Any]] = []
    for m in mcq_rows:
        if (m.get("debiased_em") or 0) != 0:
            continue
        o = open_by.get((m["task_name"], m["idx"]))
        if not o or (o.get("judge") if o.get("judge") is not None else -1) != 0:
            continue
        mcq_paired.append(m)
        x, y = matrix_axes(m.get("point"))
        cells = ";".join(matrix_cells(m.get("point")))
        clues = m.get("clue_rounds") or []
        out.append(
            {
                "task": m["task_name"],
                "idx": m["idx"],
                "point": m.get("point"),
                "cell": cells,
                "x": x,
                "y": y,
                "mcq_question": m.get("question", ""),
                "open_question": o.get("question", ""),
                "mcq_gt": m.get("gt", ""),
                "mcq_pred": m.get("pred", ""),
                "mcq_choice": m.get("choice", ""),
                "mcq_debiased_em": m.get("debiased_em", 0),
                "mcq_em": m.get("em", 0),
                "open_gt": o.get("gt", ""),
                "open_pred": o.get("pred", ""),
                "open_judge": o.get("judge", ""),
                "open_judge_reasoning": o.get("judge_reasoning", ""),
                "open_bleu1": o.get("bleu_1"),
                "open_f1": o.get("f1"),
                "source_sessions": ";".join(m.get("source_sessions") or []),
                "clue_rounds": ";".join(clues),
                "num_clues": len(clues),
                "failure_tag": auto_tag(m, o),
                "position_bias": position_bias_flag(m),
                "latency_mcq_ms": m.get("latency_ms"),
                "latency_open_ms": o.get("latency_ms"),
                "mcq_context_file": m.get("context_file", ""),
                "open_context_file": o.get("context_file", ""),
                "debug_dir": (m.get("method_runtime") or {}).get("debug_dir", ""),
            }
        )
    out.sort(key=lambda r: (_sort_tasks([r["task"]])[0], _cell_sort_key(r.get("cell", "")), r["idx"]))
    return out, mcq_paired


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "0/0"


def _cell_sort_key(cell: str) -> int:
    primary = (cell or "").split(";")[0].strip()
    order = {name: idx for idx, name in enumerate(CELL_ORDER)}
    return order.get(primary, 999)


def group_paired_by_task(paired: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in paired:
        grouped[row["task"]].append(row)
    for task in grouped:
        grouped[task].sort(key=lambda r: (_cell_sort_key(r.get("cell", "")), r["idx"]))
    return grouped


def format_case_card(
    r: Dict[str, Any],
    case_no: int,
    dialog_index: TaskDialogIndex,
) -> List[str]:
    lines: List[str] = []
    lines.append(f"#### {case_no}. `{r['task']}` #{r['idx']}")
    lines.append("")
    lines.append(
        f"- **Tag**: `{r['failure_tag']}`"
        + (f" | **Position bias**: `{r['position_bias']}`" if r["position_bias"] else "")
    )
    lines.append(f"- **session_id**: `{r.get('session_id', r.get('source_sessions', ''))}`")
    lines.append(f"- **source_sessions**: `{r.get('source_sessions', '')}`")
    lines.append(f"- **clue_rounds** ({r['num_clues']}): `{r['clue_rounds']}`")
    lines.append("")
    lines.append("**MCQ**")
    lines.append(f"- Q: {r['mcq_question']}")
    option_map = r.get("mcq_option_map") or {}
    if option_map:
        lines.append("- Options (canonical rotation):")
        lines.extend(format_mcq_options_block(option_map, r.get("mcq_gt_letter", r["mcq_gt"]), r["mcq_pred"]))
    lines.append(f"- GT: `{r['mcq_gt']}` | Pred: `{r['mcq_pred']}` | debiased_em: `{r['mcq_debiased_em']}`")
    lines.append("")
    dialog_captions = dialog_index.image_caption_index(r["task"])
    lines.extend(
        format_retrieval_block(
            r.get("mcq_context_file", ""),
            "MCQ",
            dialog_captions=dialog_captions,
        )
    )
    lines.append("**Open**")
    lines.append(f"- Q: {r['open_question']}")
    lines.append(f"- GT: {r['open_gt']}")
    lines.append(f"- Pred: {r['open_pred']}")
    if r.get("open_judge_reasoning"):
        lines.append(f"- Judge reasoning: {truncate(r['open_judge_reasoning'], 240)}")
    lines.append("")
    lines.extend(
        format_retrieval_block(
            r.get("open_context_file", ""),
            "Open",
            dialog_captions=dialog_captions,
        )
    )
    if r.get("clue_dialogue_md"):
        lines.append("**Clue rounds (abbrev.)**")
        lines.append("")
        lines.extend(r["clue_dialogue_md"])
    if r.get("debug_dir"):
        lines.append(f"- Debug: `{r['debug_dir']}`")
        lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def build_summary_md(
    paired: List[Dict[str, Any]],
    mcq_paired_rows: List[Dict[str, Any]],
    all_mcq_rows: List[Dict[str, Any]],
    mcq_metrics: Dict[str, Any],
    open_metrics: Dict[str, Any],
    dialog_index: TaskDialogIndex,
) -> str:
    lines: List[str] = []
    lines.append("# Qwen3-VL-8B Bad Cases Report — Paired Wrong (MCQ + Open)")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("- Model: `qwen3-vl-8b-instruct` (`qwen3_vl_8b_dashscope`)")
    lines.append("- Method: `simplemem__multimodal` (caption ingest + vision_on_demand, K=20, max_expanded_images=5)")
    lines.append("- Run batch: `20260701` (vision_on_demand fix, images expanded in QA)")
    lines.append("- Definition: **MCQ `debiased_em=0` AND Open `judge=0`** on mirrored question pair")
    lines.append("- **Rate** = paired wrong / total questions in that category (371 overall)")
    lines.append("")
    lines.append("## 1. Overall")
    lines.append("")
    mcq_em = mcq_metrics.get("summary", {}).get("overall", {}).get("em", 0)
    open_judge = open_metrics.get("summary", {}).get("overall", {}).get("judge", 0)
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| MCQ EM (debiased aggregate) | {mcq_em * 100:.2f}% |")
    lines.append(f"| Open LLM-Judge | {open_judge * 100:.2f}% |")
    lines.append(f"| **Paired wrong (this report)** | **{len(paired)} / 371 ({100 * len(paired) / 371:.2f}%)** |")
    lines.append("")
    lines.append("## 2. Breakdown")
    lines.append("")

    total_cell, total_task, total_x, total_y = count_by_category(all_mcq_rows)
    wrong_cell, wrong_task, wrong_x, wrong_y = count_by_category(mcq_paired_rows)

    _rate_table(
        lines,
        "By MemEye cell (sorted by Y: X1_Y1 → X4_Y1 → … → X4_Y3)",
        ("Cell", "Paired wrong", "Total", "Rate"),
        _sort_cells(list(set(total_cell.keys()) | set(wrong_cell.keys()))),
        wrong_cell,
        total_cell,
    )
    _rate_table(
        lines,
        "By task (MemEye 8-scenario order)",
        ("Task", "Paired wrong", "Total", "Rate"),
        _sort_tasks(list(set(total_task.keys()) | set(wrong_task.keys()))),
        wrong_task,
        total_task,
    )
    _rate_table(
        lines,
        "By X axis (sorted X1 → X4)",
        ("X", "Paired wrong", "Total", "Rate"),
        AXIS_X_ORDER,
        wrong_x,
        total_x,
    )
    _rate_table(
        lines,
        "By Y axis (sorted Y1 → Y3)",
        ("Y", "Paired wrong", "Total", "Rate"),
        AXIS_Y_ORDER,
        wrong_y,
        total_y,
    )

    by_tag = Counter(r["failure_tag"] for r in paired)
    lines.append("### By auto failure tag (heuristic, review manually)")
    lines.append("")
    lines.append("| Tag | Count |")
    lines.append("|------|-------|")
    for tag, n in by_tag.most_common(15):
        lines.append(f"| `{tag}` | {n} |")
    lines.append("")
    # clue stats
    clue_bins: Dict[int, List[int]] = defaultdict(lambda: [0, 0])
    for r in paired:
        clue_bins[r["num_clues"]][0] += 1
    lines.append("### Clue count distribution (paired wrong)")
    lines.append("")
    lines.append("| #clue_rounds | Count |")
    lines.append("|--------------|-------|")
    for n in sorted(clue_bins):
        lines.append(f"| {n} | {clue_bins[n][0]} |")
    lines.append("")
    lines.append("## 3. How to use")
    lines.append("")
    lines.append("- Full machine-readable list: `badcases_paired_wrong.csv`")
    lines.append("- Case cards below are grouped **by task (scenario)**, then **by MemEye cell** (Y-first: X1_Y1 → X4_Y3)")
    lines.append("- Within each cell: sorted by question idx")
    lines.append("- Each card lists **all retrieved_items** in context (typically 10–20), **Knowledge Graph** text, plus **VLM images with captions** from `contexts/*.json` / dialog JSON")
    lines.append("")
    lines.append(f"## 4. All {len(paired)} paired-wrong case cards (by task → cell)")
    lines.append("")

    by_task = group_paired_by_task(paired)
    case_no = 0
    for task in MEMEYE_TASK_ORDER:
        task_rows = by_task.get(task, [])
        if not task_rows:
            continue
        total_in_task = total_task.get(task, 0)
        rate = f"{100 * len(task_rows) / total_in_task:.1f}%" if total_in_task else "—"
        lines.append(f"## `{task}` — {len(task_rows)} paired wrong / {total_in_task} total ({rate})")
        lines.append("")

        by_cell_in_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in task_rows:
            primary = (row.get("cell") or "unknown").split(";")[0].strip() or "unknown"
            by_cell_in_task[primary].append(row)

        for cell in CELL_ORDER + sorted(set(by_cell_in_task.keys()) - set(CELL_ORDER)):
            rows = by_cell_in_task.get(cell, [])
            if not rows:
                continue
            lines.append(f"### `{cell}` — {len(rows)} in this task")
            lines.append("")
            for row in rows:
                case_no += 1
                lines.extend(format_case_card(row, case_no, dialog_index))

    return "\n".join(lines)


def main() -> None:
    mcq_rows = load_jsonl(MCQ_PATH)
    open_rows = load_jsonl(OPEN_PATH)
    mcq_metrics = json.loads(MCQ_METRICS.read_text(encoding="utf-8"))
    open_metrics = json.loads(OPEN_METRICS.read_text(encoding="utf-8"))

    paired, mcq_paired_rows = paired_rows(mcq_rows, open_rows)

    dialog_index = TaskDialogIndex()
    paired = [enrich_paired_row(r, dialog_index) for r in paired]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    for r in paired:
        csv_row = {k: v for k, v in r.items() if k not in ("point", "mcq_option_map", "clue_dialogue_md")}
        if r.get("clue_dialogue_md"):
            csv_row["clue_dialogues"] = "\n".join(
                line for line in r["clue_dialogue_md"] if line and not line.startswith("#")
            )
        csv_rows.append(csv_row)
    fields = [k for k in (csv_rows[0].keys() if csv_rows else [])]
    csv_path = OUT_DIR / "badcases_paired_wrong.csv"
    write_csv(csv_path, csv_rows, fields)

    report = build_summary_md(
        paired, mcq_paired_rows, mcq_rows, mcq_metrics, open_metrics, dialog_index
    )
    report_path = OUT_DIR / f"REPORT_paired_wrong_{len(paired)}_by_task.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"[OK] Wrote {len(paired)} rows -> {csv_path}")
    print(f"[OK] Report -> {report_path}")


if __name__ == "__main__":
    main()
