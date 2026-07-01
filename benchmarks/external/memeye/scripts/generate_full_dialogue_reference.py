#!/usr/bin/env python3
"""Generate MemEye 8-scenario full dialogue reference with inline images and clue tags."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
MEMEYE_ROOT = SCRIPT_DIR.parent
DIALOG_ROOT = MEMEYE_ROOT / "data" / "dialog"
IMAGE_ROOT = MEMEYE_ROOT / "data" / "image"
OUT_DIR = MEMEYE_ROOT / "analysis" / "full_dialogue_reference"

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

TASK_TITLES = {
    "brand_memory_test": "Brand Memory Test",
    "card_playlog_test": "Card Playlog Test",
    "cartoon_entertainment_companion": "Cartoon Entertainment Companion",
    "home_renovation_interior_design": "Home Renovation Interior Design",
    "multi_scene_visual_case_archive_assistant": "Multi-Scene Visual Case Archive Assistant",
    "outdoor_navigation_route_memory_assistant": "Outdoor Navigation Route Memory Assistant",
    "personal_health_dashboard_assistant": "Personal Health Dashboard Assistant",
    "social_chat_memory_test": "Social Chat Memory Test",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_image_path(raw: str) -> Optional[Path]:
    cleaned = raw.replace("file://", "").strip()
    if not cleaned:
        return None
    candidates = [
        IMAGE_ROOT / cleaned,
        IMAGE_ROOT / Path(cleaned).name,
        MEMEYE_ROOT / "data" / cleaned,
    ]
    for prefix in ("image/", "../image/", "./image/", "data/image/"):
        if cleaned.startswith(prefix):
            candidates.append(IMAGE_ROOT / cleaned[len(prefix) :])
    seen: Set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate.resolve()
    return None


def rel_image_md(out_file: Path, image_path: Path) -> str:
    rel = Path(os_relpath(image_path, out_file.parent))
    return str(rel).replace("\\", "/")


def os_relpath(target: Path, start: Path) -> str:
    try:
        return str(target.relative_to(start))
    except ValueError:
        import os

        return os.path.relpath(target, start)


def matrix_label(point: Any) -> str:
    if not isinstance(point, list) or len(point) != 2:
        return ""
    xs, ys = point[0], point[1]
    if not isinstance(xs, list) or not isinstance(ys, list):
        return ""
    cells = [f"{x}_{y}" for x in xs for y in ys]
    return ", ".join(cells)


def build_clue_index(qas: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    clue_to_qs: Dict[str, List[int]] = defaultdict(list)
    for i, qa in enumerate(qas, start=1):
        for clue in qa.get("clue") or []:
            clue_to_qs[str(clue)].append(i)
    return dict(clue_to_qs)


def format_round_block(
    dlg: Dict[str, Any],
    clue_to_qs: Dict[str, List[int]],
    out_file: Path,
) -> List[str]:
    round_id = dlg.get("round", "")
    lines: List[str] = []
    clue_qs = clue_to_qs.get(round_id, [])
    clue_tag = ""
    if clue_qs:
        clue_tag = f" — **CLUE for Q#{', Q#'.join(str(q) for q in sorted(clue_qs))}**"
    lines.append(f"##### `{round_id}`{clue_tag}")
    lines.append("")
    user = dlg.get("user", "")
    assistant = dlg.get("assistant", "")
    if user:
        lines.append(f"**User**: {user}")
        lines.append("")
    if assistant:
        lines.append(f"**Assistant**: {assistant}")
        lines.append("")

    images = dlg.get("input_image") or []
    captions = dlg.get("image_caption") or []
    image_ids = dlg.get("image_id") or []

    for i, raw_img in enumerate(images):
        img_path = resolve_image_path(str(raw_img))
        cap = captions[i] if i < len(captions) else ""
        img_id = image_ids[i] if i < len(image_ids) else ""
        if cap:
            lines.append(f"**Caption**: {cap}")
        if img_id:
            lines.append(f"**image_id**: `{img_id}`")
        if img_path:
            md_src = rel_image_md(out_file, img_path)
            alt = cap or img_path.name
            lines.append(f"![{alt}]({md_src})")
        else:
            lines.append(f"_(image not found: `{raw_img}`)_")
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def format_qa_section(qas: List[Dict[str, Any]]) -> List[str]:
    lines = ["## Questions (clue index)", ""]
    for i, qa in enumerate(qas, start=1):
        point = matrix_label(qa.get("point"))
        clues = qa.get("clue") or []
        sessions = qa.get("session_id") or []
        lines.append(f"### Q{i}" + (f" (`{point}`)" if point else ""))
        lines.append("")
        if sessions:
            lines.append(f"- **sessions**: {', '.join(f'`{s}`' for s in sessions)}")
        if clues:
            lines.append(
                "- **clues**: "
                + ", ".join(f"`{c}`" for c in clues)
            )
        lines.append(f"- **question**: {qa.get('question', '')}")
        answer = qa.get("answer", "")
        if answer:
            lines.append(f"- **answer**: {answer}")
        options = qa.get("options")
        if isinstance(options, list) and options:
            rot = options[-1]
            opt_lines = []
            for key in sorted(rot.keys()):
                if key == "answer":
                    continue
                marker = " ← GT" if key == str(answer).strip().upper() else ""
                opt_lines.append(f"  - **{key}**: {rot[key]}{marker}")
            if opt_lines:
                lines.append("- **options** (canonical rotation):")
                lines.extend(opt_lines)
        elif isinstance(options, dict):
            opt_lines = []
            for key in sorted(options.keys()):
                if key == "answer":
                    continue
                marker = " ← GT" if key == str(answer).strip().upper() else ""
                opt_lines.append(f"  - **{key}**: {options[key]}{marker}")
            if opt_lines:
                lines.append("- **options**:")
                lines.extend(opt_lines)
        lines.append("")
    return lines


def render_task(task: str) -> Tuple[Path, Dict[str, int]]:
    dialog_path = DIALOG_ROOT / TASK_MCQ_DIALOG[task]
    data = load_json(dialog_path)
    out_file = OUT_DIR / f"{task}.md"
    qas = data.get("human-annotated QAs") or data.get("human_annotated_qas") or []
    clue_to_qs = build_clue_index(qas)
    profile = data.get("character_profile") or {}

    stats = {
        "sessions": 0,
        "rounds": 0,
        "images": 0,
        "missing_images": 0,
        "clue_rounds": len(clue_to_qs),
        "questions": len(qas),
    }

    lines: List[str] = [
        f"# {TASK_TITLES.get(task, task)}",
        "",
        f"- task: `{task}`",
        f"- dialog: `{dialog_path.name}`",
        f"- generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if profile.get("name"):
        lines.append(f"**Character**: {profile['name']}")
        if profile.get("persona_summary"):
            lines.append("")
            lines.append(profile["persona_summary"])
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Full dialogues")
    lines.append("")

    for sess in data.get("multi_session_dialogues", []):
        stats["sessions"] += 1
        sid = sess.get("session_id", "")
        date = sess.get("date", "")
        date_part = f" — {date}" if date else ""
        lines.append(f"### Session `{sid}`{date_part}")
        lines.append("")
        for dlg in sess.get("dialogues", []):
            stats["rounds"] += 1
            imgs = dlg.get("input_image") or []
            stats["images"] += len(imgs)
            for raw in imgs:
                if resolve_image_path(str(raw)) is None:
                    stats["missing_images"] += 1
            lines.extend(format_round_block(dlg, clue_to_qs, out_file))

    lines.extend(format_qa_section(qas))
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file, stats


def render_index(all_stats: Dict[str, Dict[str, int]]) -> Path:
    index = OUT_DIR / "INDEX.md"
    lines = [
        "# MemEye 8-Scenario Full Dialogue Reference",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Each file contains:",
        "- All multi-session dialogues in chronological order",
        "- Inline images (relative paths — open in Cursor/VS Code preview)",
        "- `CLUE for Q#...` tags on rounds referenced by benchmark questions",
        "- A question index at the bottom with clue round IDs",
        "",
        "| Task | Sessions | Rounds | Images | Clue rounds | Questions | File |",
        "|------|----------|--------|--------|-------------|-----------|------|",
    ]
    totals = defaultdict(int)
    for task in MEMEYE_TASK_ORDER:
        s = all_stats[task]
        for k, v in s.items():
            totals[k] += v
        lines.append(
            f"| {TASK_TITLES.get(task, task)} | {s['sessions']} | {s['rounds']} | "
            f"{s['images']} | {s['clue_rounds']} | {s['questions']} | "
            f"[{task}.md](./{task}.md) |"
        )
    lines.append(
        f"| **Total** | **{totals['sessions']}** | **{totals['rounds']}** | "
        f"**{totals['images']}** | **{totals['clue_rounds']}** | "
        f"**{totals['questions']}** | |"
    )
    if totals["missing_images"]:
        lines.append("")
        lines.append(
            f"> Warning: {totals['missing_images']} image path(s) could not be resolved."
        )
    index.write_text("\n".join(lines), encoding="utf-8")
    return index


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_stats: Dict[str, Dict[str, int]] = {}
    for task in MEMEYE_TASK_ORDER:
        _, stats = render_task(task)
        all_stats[task] = stats
        print(
            f"Wrote {task}: rounds={stats['rounds']} images={stats['images']} "
            f"clue_rounds={stats['clue_rounds']} missing_images={stats['missing_images']}"
        )
    index = render_index(all_stats)
    print(f"Index: {index}")


if __name__ == "__main__":
    main()
