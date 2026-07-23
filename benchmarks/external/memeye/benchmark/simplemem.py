"""
SimpleMem / Omni-SimpleMem adapter for MemoryBench.

Wraps `omni_memory.OmniMemoryOrchestrator` (vendored under
`benchmark/simplemem/upstream/OmniSimpleMem`) so it can be selected as a
HistoryMethod via `--method simplemem`.

Design choices:
- **Caption-based ingestion** (mirrors the upstream Mem-Gallery adapter at
  `OmniSimpleMem/benchmarks/memgallery/adapter.py`): we feed each round into
  `orchestrator.add_text()` with the dialogue text + per-image caption lines,
  and tag the MAU with `session_id:` / `image_id:` / `timestamp:`. Raw images
  are not passed to `add_image()` because the upstream image branch would
  re-caption them with `caption_model`, double-counting work and adding cost.
  This matches the `caption_preprocessed: true` convention used by A-MEM.
- **Answer flow**: retrieval uses `orchestrator.retrieve_answer_context()` (hybrid
  search + KG + vision_on_demand).  Answer generation uses MemEye's
  `sys_prompt_mcq.txt` / `sys_prompt_open.txt` (same as non-agentic baselines),
  not the upstream LoCoMo JSON prompt inside `orchestrator.answer()`.
- **Visual encoder disabled**: `entropy_trigger.visual_encoder = "none"` so we
  don't pull `openvision-vit-large-patch14-224` (~1.6 GB) for a caption-only
  run. The upstream LoCoMo benchmark uses the same setting.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None  # type: ignore[misc, assignment]

from .common import REPO_ROOT, write_json
from .dataset import MemoryBenchmarkDataset
from .methods import HistoryMethod
from .runner import load_sys_prompt


_SIMPLEMEM_ROOT = (
    Path(__file__).resolve().parent / "simplemem" / "upstream" / "OmniSimpleMem"
).resolve()
if str(_SIMPLEMEM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SIMPLEMEM_ROOT))


def _load_simplemem_classes() -> Tuple[Any, Any]:
    try:
        from omni_memory import OmniMemoryConfig, OmniMemoryOrchestrator  # type: ignore
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Omni-SimpleMem dependencies are not fully installed. Missing module: "
            f"{exc.name}. Verify the upstream clone exists at "
            f"{_SIMPLEMEM_ROOT} and that benchmark/simplemem/upstream/OmniSimpleMem/"
            "omni_memory/core/config.py is present (it is a stopgap reverse-engineered "
            "from tests/test_config.py because upstream gitignored their copy)."
        ) from exc
    return OmniMemoryConfig, OmniMemoryOrchestrator


def _resolve_api_key(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> Optional[str]:
    raw = str(method_config.get("llm_api_key", "")).strip()
    if raw:
        return raw
    raw = str(model_config.get("api_key", "")).strip()
    if raw:
        return raw
    method_env = str(method_config.get("llm_api_key_env", "")).strip()
    model_env = str(model_config.get("api_key_env", "")).strip()
    env_name = method_env or model_env or "OPENAI_API_KEY"
    return os.getenv(env_name)


def _api_key_env_name(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    method_env = str(method_config.get("llm_api_key_env", "")).strip()
    model_env = str(model_config.get("api_key_env", "")).strip()
    return method_env or model_env or "OPENAI_API_KEY"


def _resolve_base_url(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> Optional[str]:
    raw = str(method_config.get("base_url", "")).strip()
    if raw:
        return raw
    raw = str(model_config.get("base_url", "")).strip()
    return raw or None


def _resolve_model_name(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    explicit = str(method_config.get("llm_model", "")).strip()
    if explicit:
        return explicit
    return (
        str(model_config.get("model", "")).strip()
        or str(model_config.get("name", "")).strip()
        or "gpt-4o-mini"
    )


def _dialogue_text(round_payload: Dict[str, Any], speaker_a: str, speaker_b: str) -> str:
    parts: List[str] = []
    user_text = str(round_payload.get("user", "")).strip()
    assistant_text = str(round_payload.get("assistant", "")).strip()
    if user_text:
        parts.append(f"{speaker_a}: {user_text}")
    if assistant_text:
        parts.append(f"{speaker_b}: {assistant_text}")
    return "\n".join(parts).strip()


def _round_image_blocks(raw_dialogue: Dict[str, Any]) -> List[Tuple[str, str]]:
    input_images = raw_dialogue.get("input_image", []) or []
    captions = raw_dialogue.get("image_caption", []) or []
    image_ids = raw_dialogue.get("image_id", []) or []
    blocks: List[Tuple[str, str]] = []
    for idx, _ in enumerate(input_images):
        image_id = str(image_ids[idx]).strip() if idx < len(image_ids) else ""
        caption = str(captions[idx]).strip() if idx < len(captions) else ""
        blocks.append((image_id, caption))
    return blocks


def _build_round_text(
    round_payload: Dict[str, Any],
    speaker_a: str,
    speaker_b: str,
) -> str:
    """Render one round into a single text blob with caption lines per image."""
    raw_dialogue = round_payload.get("raw", {}) or {}
    text = _dialogue_text(round_payload, speaker_a, speaker_b)
    lines: List[str] = [text] if text else []
    for image_id, caption in _round_image_blocks(raw_dialogue):
        lines.extend(
            [
                "image:",
                f"image_id: {image_id}",
                f"image_caption: {caption}",
            ]
        )
    return "\n".join(lines).strip()


def _build_round_tags(
    round_id: str,
    session_id: str,
    timestamp: Optional[str],
    raw_dialogue: Dict[str, Any],
) -> List[str]:
    tags: List[str] = []
    if session_id:
        tags.append(f"session_id:{session_id}")
    if round_id:
        tags.append(f"round_id:{round_id}")
    if timestamp:
        tags.append(f"timestamp:{timestamp}")
    for image_id, _ in _round_image_blocks(raw_dialogue):
        if image_id:
            tags.append(f"image_id:{image_id}")
    return tags


def _question_with_image_caption(qa: Dict[str, Any], question: str) -> str:
    """Append the question's own image caption (if any) to the query string."""
    query = question.strip()
    question_image = str(qa.get("question_image", "")).strip()
    question_caption = qa.get("image_caption")
    if not question_image or not question_caption:
        return query
    if isinstance(question_caption, list):
        caption_text = " ".join(
            str(item).strip() for item in question_caption if str(item).strip()
        )
    else:
        caption_text = str(question_caption).strip()
    if not caption_text:
        return query
    return f"{query}\nquestion's image:\nimage_caption: {caption_text}"


def _is_mcq(qa: Dict[str, Any]) -> bool:
    options = qa.get("options")
    return bool(options and isinstance(options, (dict, list)))


def _retrieval_image_parts(user_content: Any) -> List[Dict[str, Any]]:
    if not isinstance(user_content, list):
        return []
    return [part for part in user_content if part.get("type") == "image_url"]


def _tag_value(tags: Any, prefix: str) -> str:
    for tag in tags or []:
        text = str(tag)
        if text.startswith(prefix):
            return text[len(prefix) :]
    return ""


def _resolve_image_path(raw_pointer: str, dataset: MemoryBenchmarkDataset) -> str:
    path = Path(raw_pointer)
    if path.is_file():
        return str(path.resolve())
    from .dataset import resolve_image_path

    resolved = resolve_image_path(
        raw_pointer, dataset.dialog_json_path, dataset.image_root
    )
    return resolved


def _full_text_from_details(details: Any) -> str:
    if not isinstance(details, dict):
        return ""
    for key in ("full_text", "text", "transcript"):
        value = details.get(key)
        if value:
            return str(value)
    return ""


def _infer_retrieval_source(item: Dict[str, Any]) -> str:
    """Heuristic: BM25 appends omit ``details``; FAISS preview includes it when present."""
    if item.get("details"):
        return "faiss"
    if item.get("score", 0) < 0.1:
        return "bm25"
    return "faiss"


def _serialize_retrieval_items(
    items: List[Dict[str, Any]],
    *,
    dataset: MemoryBenchmarkDataset,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        tags = list(item.get("tags") or [])
        details = item.get("details") or {}
        full_text = _full_text_from_details(details)
        raw = item.get("raw_content") or {}
        rows.append(
            {
                "rank": rank,
                "source": _infer_retrieval_source(item),
                "id": item.get("id"),
                "score": item.get("score"),
                "summary": item.get("summary"),
                "modality_type": item.get("modality_type"),
                "session_id": _tag_value(tags, "session_id:"),
                "round_id": _tag_value(tags, "round_id:"),
                "timestamp": _tag_value(tags, "timestamp:"),
                "image_id": _tag_value(tags, "image_id:"),
                "tags": tags,
                "has_raw_data": bool(item.get("has_raw_data")),
                "vision_on_demand": "vision_on_demand" in tags,
                "has_full_text_in_context": bool(full_text),
                "full_text_chars": len(full_text),
                "full_text_preview": full_text[:500] if full_text else "",
                "image_expanded": raw.get("type") == "image" and bool(raw.get("base64")),
                "image_path": (
                    _resolve_image_path(str(raw.get("pointer", "")), dataset)
                    if raw.get("pointer")
                    else ""
                ),
            }
        )
    return rows


def _images_expanded_from_items(
    items: List[Dict[str, Any]],
    *,
    dataset: MemoryBenchmarkDataset,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    expanded: List[Dict[str, Any]] = []
    not_expanded: List[Dict[str, Any]] = []
    vlm_order = 0
    for rank, item in enumerate(items, start=1):
        tags = list(item.get("tags") or [])
        raw = item.get("raw_content") or {}
        base = {
            "context_rank": rank,
            "mau_id": item.get("id"),
            "round_id": _tag_value(tags, "round_id:"),
            "image_id": _tag_value(tags, "image_id:"),
            "vision_on_demand": "vision_on_demand" in tags,
        }
        if raw.get("type") == "image" and raw.get("base64"):
            vlm_order += 1
            expanded.append(
                {
                    **base,
                    "vlm_order": vlm_order,
                    "image_path": _resolve_image_path(str(raw.get("pointer", "")), dataset),
                    "sent_to_vlm": True,
                }
            )
        elif "vision_on_demand" in tags and item.get("has_raw_data"):
            not_expanded.append({**base, "sent_to_vlm": False})
    return expanded, not_expanded


def _split_knowledge_graph_text(context_text: str) -> Tuple[str, str]:
    marker = "\n\n[Knowledge Graph]\n"
    if marker in context_text:
        main, graph = context_text.split(marker, 1)
        return main.strip(), graph.strip()
    return context_text.strip(), ""


class SimpleMemMethod(HistoryMethod):
    """Omni-SimpleMem as a MemoryBench HistoryMethod.

    Supports two modalities via the ``modality`` config key:

    - ``text_only`` (default): caption-based ingestion.  Images are replaced
      by their ``image_caption`` text.  Requires ``caption_preprocessed: true``.
    - ``multimodal``: text MAUs carry a ``raw_pointer`` to the original image
      and a ``vision_on_demand`` tag so the orchestrator loads them at answer
      time and passes them to the VLM alongside the retrieved text context.
    """

    name = "simplemem"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self._dataset_key: Optional[int] = None
        self._orchestrator: Any = None
        self._config_cls: Any = None
        self._orch_cls: Any = None
        self._speaker_a: str = "user"
        self._speaker_b: str = "assistant"
        self._debug_rows: List[Dict[str, Any]] = []
        self._top_k: int = max(1, int(self.config.get("retrieve_k", 20)))
        self._data_dir: Optional[Path] = None
        self._reuse_memory: bool = False
        self._multimodal: bool = str(self.config.get("modality", "text_only")).strip().lower() == "multimodal"
        self._ingestion_mode: str = str(self.config.get("ingestion_mode", "caption")).strip().lower() or "caption"
        self._log_answer_context: bool = bool(self.config.get("log_answer_context", True))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_caption_preprocessed(self, dataset: MemoryBenchmarkDataset) -> None:
        if self._multimodal:
            return  # multimodal mode uses raw images, not captions
        if not bool(self.config.get("caption_preprocessed", True)):
            return
        missing_rounds: List[str] = []
        for round_id, payload in dataset.rounds.items():
            raw = payload.get("raw", {}) or {}
            images = raw.get("input_image", []) or []
            if not images:
                continue
            captions = raw.get("image_caption", []) or []
            if len(captions) != len(images):
                missing_rounds.append(round_id)
        if missing_rounds:
            raise ValueError(
                "SimpleMem caption-based adaptation requires Mem-Gallery-style image captions. "
                "Run the caption preprocess first. Missing/invalid image_caption for rounds: "
                + ", ".join(missing_rounds[:10])
                + ("..." if len(missing_rounds) > 10 else "")
            )

    def _scenario_name(self, dataset: MemoryBenchmarkDataset) -> str:
        task_name = str(self.config.get("_task_name", "")).strip()
        if not task_name:
            task_name = str(dataset.data.get("task_name", "")).strip() or dataset.dialog_json_path.stem
        return task_name.lower().replace(" ", "_").replace("/", "_")

    def _memory_namespace(self) -> str:
        explicit = str(self.config.get("memory_namespace", "")).strip()
        if explicit:
            return explicit
        model_cfg = dict(self.config.get("_model_cfg", {}))
        return str(model_cfg.get("name", "")).strip()

    def _memory_dir_candidates(self, dataset: MemoryBenchmarkDataset) -> List[Path]:
        scenario = self._scenario_name(dataset)
        namespace = self._memory_namespace()
        if namespace:
            namespaced = (
                REPO_ROOT / "runs" / "simplemem" / namespace / scenario
            ).resolve()
            return [namespaced]

        canonical = (REPO_ROOT / "runs" / "simplemem" / scenario).resolve()
        candidates: List[Path] = [canonical]
        stem = dataset.dialog_json_path.stem.lower().replace(" ", "_").replace("/", "_")
        legacy = (REPO_ROOT / "runs" / "simplemem" / stem).resolve()
        if legacy not in candidates:
            candidates.append(legacy)
        if stem.endswith("_open"):
            legacy_open = (REPO_ROOT / "runs" / "simplemem" / stem[: -len("_open")]).resolve()
            if legacy_open not in candidates:
                candidates.append(legacy_open)
        return candidates

    def _has_existing_memory(self, data_dir: Path) -> bool:
        mau_store = data_dir / "index" / "mau_store"
        if not mau_store.is_dir():
            return False
        for path in mau_store.glob("*.jsonl"):
            try:
                if path.stat().st_size <= 0:
                    continue
                with path.open(encoding="utf-8") as handle:
                    if any(line.strip() for line in handle):
                        return True
            except OSError:
                continue
        return False

    def _resolve_memory_data_dir(self, dataset: MemoryBenchmarkDataset) -> Path:
        for path in self._memory_dir_candidates(dataset):
            if self._has_existing_memory(path):
                return path
        return self._memory_dir_candidates(dataset)[0]

    def _debug_dir(self, dataset: MemoryBenchmarkDataset) -> Path:
        return (REPO_ROOT / "output" / self._scenario_name(dataset) / "simplemem").resolve()

    def _contexts_dir(self) -> Optional[Path]:
        run_dir = str(self.config.get("_runtime_paths", {}).get("run_dir", "")).strip()
        if not run_dir:
            return None
        return (Path(run_dir) / "contexts").resolve()

    def _context_filename(
        self,
        qa: Dict[str, Any],
        *,
        prompt_mode: str,
        answer_tag: str,
    ) -> str:
        qid = str(qa.get("question_id", "")).strip() or "unknown"
        safe_qid = qid.replace("/", "_").replace(" ", "_")
        tag = answer_tag.strip() or prompt_mode
        safe_tag = tag.replace("/", "_").replace(" ", "_")
        return f"{safe_qid}_{safe_tag}.json"

    def _runtime_data_dir(self, dataset: MemoryBenchmarkDataset) -> Path:
        return self._resolve_memory_data_dir(dataset)

    def _flush_debug(self, dataset: MemoryBenchmarkDataset) -> None:
        if not self._debug_rows:
            return
        payload = {
            "dataset_path": str(dataset.dialog_json_path),
            "rows": self._debug_rows,
        }
        write_json(self._debug_dir(dataset) / "debug_trace.json", payload)

    def _build_orchestrator(self, dataset: MemoryBenchmarkDataset) -> None:
        OmniMemoryConfig, OmniMemoryOrchestrator = _load_simplemem_classes()
        self._config_cls = OmniMemoryConfig
        self._orch_cls = OmniMemoryOrchestrator

        model_config = dict(self.config.get("_model_cfg", {}))
        model_name = _resolve_model_name(self.config, model_config)
        api_key = _resolve_api_key(self.config, model_config)
        if not api_key:
            env_name = _api_key_env_name(self.config, model_config)
            raise ValueError(
                f"API key not found for SimpleMem. Set environment variable {env_name} "
                f"(or llm_api_key / api_key in the method/model yaml)."
            )
        base_url = _resolve_base_url(self.config, model_config)

        cfg = OmniMemoryConfig.create_default()
        cfg.set_unified_model(model_name)
        cfg.llm.api_key = api_key
        if base_url:
            cfg.llm.api_base_url = base_url
        cfg.llm.temperature = float(self.config.get("temperature", 0.0))
        cfg.llm.max_tokens = int(self.config.get("max_tokens", 1000))

        # Embedding settings (default to MemoryBench's standard)
        cfg.embedding.model_name = str(
            self.config.get("embedding_model", "all-MiniLM-L6-v2")
        )
        cfg.embedding.embedding_dim = int(self.config.get("embedding_dim", 384))

        # Caption-only mode: skip CLIP and visual MAUs entirely
        cfg.entropy_trigger.visual_encoder = "none"
        cfg.entropy_trigger.enable_visual_trigger = False

        # Retrieval depth
        cfg.retrieval.default_top_k = self._top_k
        cfg.retrieval.enable_hybrid_search = bool(
            self.config.get("enable_hybrid_search", True)
        )
        cfg.retrieval.enable_graph_traversal = bool(
            self.config.get("enable_graph_traversal", True)
        )
        cfg.retrieval.enable_multi_query_retrieval = bool(
            self.config.get("enable_multi_query_retrieval", False)
        )
        cfg.retrieval.auto_expand_threshold = float(
            self.config.get("auto_expand_threshold", 0.4)
        )
        cfg.retrieval.evidence_token_budget = int(
            self.config.get("evidence_token_budget", 6000)
        )
        # Pyramid retrieval: preview = summary only; full_text via DETAILS expand.
        cfg.retrieval.include_details_in_preview = bool(
            self.config.get("include_details_in_preview", False)
        )

        # Skip self-evolution (auto-research loop) by default for benchmark fairness
        cfg.enable_self_evolution = bool(self.config.get("enable_self_evolution", False))
        cfg.event.summarize_on_close = bool(self.config.get("summarize_on_close", False))
        cfg.embedding.api_key = api_key

        data_dir = self._runtime_data_dir(dataset)
        reuse_existing = bool(self.config.get("reuse_existing_memory", True))
        self._reuse_memory = False
        if data_dir.exists() and reuse_existing and self._has_existing_memory(data_dir):
            self._reuse_memory = True
            print(f"[SimpleMem] Reusing existing memory at {data_dir}")
        elif data_dir.exists():
            import shutil

            shutil.rmtree(data_dir, ignore_errors=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = data_dir

        self._orchestrator = OmniMemoryOrchestrator(
            config=cfg, data_dir=str(data_dir)
        )
        self._configure_knowledge_graph(cfg, data_dir)

    def _configure_knowledge_graph(self, cfg: Any, data_dir: Path) -> None:
        """Point KG retrieval at per-task storage."""
        assert self._orchestrator is not None
        from omni_memory.knowledge import GraphRetriever, KnowledgeGraph  # type: ignore

        kg_dir = data_dir / "knowledge_graph"
        if self._reuse_memory and not (kg_dir / "entities.jsonl").exists():
            print(
                f"[SimpleMem] WARNING: per-task KG missing at {kg_dir}; "
                "starting with empty graph."
            )

        kg = KnowledgeGraph(storage_path=str(kg_dir), config=cfg)
        self._orchestrator.knowledge_graph = kg
        self._orchestrator.graph_retriever = GraphRetriever(
            kg,
            entity_extractor=self._orchestrator.entity_extractor,
            config=cfg,
        )
        entity_count = len(getattr(kg, "_entities", {}) or {})
        if entity_count:
            print(f"[SimpleMem] Knowledge graph ready: {entity_count} entities")

    def _collect_ingest_rounds(self, dataset: MemoryBenchmarkDataset) -> List[Dict[str, Any]]:
        character_profile = dataset.data.get("character_profile", {}) or {}
        speaker_name = str(character_profile.get("name", "")).strip()
        self._speaker_a = f"user ({speaker_name})" if speaker_name else "user"
        self._speaker_b = "assistant"

        rounds: List[Dict[str, Any]] = []
        for session_id in dataset.session_order():
            session = dataset.get_session(session_id)
            timestamp = str(session.get("date", "")).strip() or None
            for dialogue in session.get("dialogues", []):
                round_id = str(dialogue.get("round", "")).strip()
                if not round_id or round_id not in dataset.rounds:
                    continue
                round_payload = dataset.rounds[round_id]
                text = _build_round_text(round_payload, self._speaker_a, self._speaker_b)
                if not text:
                    continue
                rounds.append(
                    {
                        "round_id": round_id,
                        "session_id": str(round_payload.get("session_id", "") or session_id),
                        "timestamp": timestamp,
                        "round_payload": round_payload,
                        "text": text,
                    }
                )
        return rounds

    def _ingest_dataset(self, dataset: MemoryBenchmarkDataset) -> None:
        assert self._orchestrator is not None
        ingest_rounds = self._collect_ingest_rounds(dataset)
        total_rounds = len(ingest_rounds)
        pbar = (
            tqdm(
                ingest_rounds,
                total=total_rounds,
                desc="Ingest",
                unit="round",
                dynamic_ncols=True,
            )
            if tqdm is not None
            else ingest_rounds
        )
        stored_n = 0
        rejected_n = 0
        error_n = 0

        for item in pbar:
            round_id = str(item["round_id"])
            round_payload = item["round_payload"]
            timestamp = item.get("timestamp")
            text = str(item["text"])
            raw_dialogue = round_payload.get("raw", {}) or {}
            tags = _build_round_tags(
                round_id=round_id,
                session_id=str(item["session_id"]),
                timestamp=timestamp,
                raw_dialogue=raw_dialogue,
            )
            try:
                result = self._orchestrator.add_text(
                    text,
                    tags=tags or None,
                    force=False,
                )
            except Exception as exc:
                error_n += 1
                self._debug_rows.append(
                    {
                        "type": "ingest_error",
                        "round_id": round_id,
                        "error": str(exc),
                    }
                )
                if tqdm is not None and hasattr(pbar, "set_postfix"):
                    pbar.set_postfix(stored=stored_n, skip=rejected_n, err=error_n, refresh=False)
                continue
            stored = getattr(result, "success", False) and getattr(result, "mau", None) is not None
            vision_image_path = ""
            # Multimodal: attach raw image pointer so the orchestrator
            # can load it on-demand at answer time (vision_on_demand flow).
            if stored and self._multimodal:
                round_images = list(round_payload.get("images", []) or [])
                if round_images and round_images[0]:
                    vision_image_path = str(round_images[0])
                    result.mau.raw_pointer = vision_image_path
                    result.mau.add_tag("vision_on_demand")
                    # add_text() already persisted the MAU; persist pointer + tag too.
                    if not self._orchestrator.mau_store.update(result.mau):
                        self._debug_rows.append(
                            {
                                "type": "vision_on_demand_update_failed",
                                "round_id": round_id,
                                "mau_id": result.mau.id,
                                "image_path": vision_image_path,
                            }
                        )
            if stored:
                stored_n += 1
            else:
                rejected_n += 1
            debug_entry: Dict[str, Any] = {
                "type": "stored_memory" if stored else "ingest_rejected",
                "round_id": round_id,
                "session_id": round_payload.get("session_id", ""),
                "timestamp": timestamp or "",
                "tags": tags,
                "text": text,
                "reason": getattr(getattr(result, "trigger_result", None), "reason", "") if not stored else "",
            }
            if stored and vision_image_path:
                debug_entry["vision_on_demand"] = True
                debug_entry["raw_pointer"] = vision_image_path
                debug_entry["mau_id"] = result.mau.id
            self._debug_rows.append(debug_entry)
            if tqdm is not None and hasattr(pbar, "set_postfix"):
                pbar.set_postfix(stored=stored_n, skip=rejected_n, err=error_n, refresh=False)

    def _ensure_initialized(self, dataset: MemoryBenchmarkDataset) -> None:
        dataset_id = id(dataset)
        if self._orchestrator is not None and self._dataset_key == dataset_id:
            return

        self._ensure_caption_preprocessed(dataset)
        self._debug_rows = []
        self._build_orchestrator(dataset)
        mode_label = "multimodal" if self._multimodal else "text-only"
        model_name = _resolve_model_name(self.config, dict(self.config.get("_model_cfg", {})))
        if self._reuse_memory:
            assert self._orchestrator is not None
            ingested = self._orchestrator.mau_store.count()
            vector_count = (
                self._orchestrator.vector_store.count()
                if hasattr(self._orchestrator.vector_store, "count")
                else 0
            )
            print(
                f"[SimpleMem] Skipping ingest; reusing {ingested} memories "
                f"(mode={mode_label} model={model_name} top_k={self._top_k})"
            )
            if vector_count <= 0:
                print(
                    "[SimpleMem] WARNING: FAISS index is empty. "
                    "Delete runs/simplemem/<task> and re-ingest."
                )
        else:
            print(
                f"[SimpleMem] Ingesting dataset into Omni-SimpleMem "
                f"(mode={mode_label} model={model_name} top_k={self._top_k})..."
            )
            self._ingest_dataset(dataset)
            ingested = sum(1 for r in self._debug_rows if r.get("type") == "stored_memory")
            print(f"[SimpleMem] Memory ready: {ingested} rounds ingested.")
            self._flush_debug(dataset)
            self._orchestrator.save()
            if hasattr(self._orchestrator, "knowledge_graph"):
                self._orchestrator.knowledge_graph.save()
            vector_count = (
                self._orchestrator.vector_store.count()
                if hasattr(self._orchestrator.vector_store, "count")
                else 0
            )
        assert self._orchestrator is not None
        bm25_n = self._orchestrator.build_bm25_index()
        if bm25_n:
            print(f"[SimpleMem] BM25 index ready: {bm25_n} documents")
        else:
            print("[SimpleMem] BM25 index unavailable (empty store or rank_bm25 missing)")

        self._dataset_key = dataset_id
        self.runtime_info["num_memories"] = ingested
        self.runtime_info["reused_memory"] = self._reuse_memory
        self.runtime_info["bm25_documents"] = bm25_n
        self.runtime_info["vector_count"] = vector_count
        self.runtime_info["kg_entities"] = len(
            getattr(self._orchestrator.knowledge_graph, "_entities", {}) or {}
        )
        self.runtime_info["debug_dir"] = str(self._debug_dir(dataset))
        contexts_dir = self._contexts_dir()
        if contexts_dir is not None:
            self.runtime_info["contexts_dir"] = str(contexts_dir)
        if self._data_dir is not None:
            self.runtime_info["data_dir"] = str(self._data_dir)

    def _build_memeye_user_prompt(
        self,
        *,
        prompt_mode: str,
        context: str,
        question: str,
        retrieval_user_content: Any,
    ) -> Tuple[str, Any, str]:
        """Build system prompt, user payload, and plain user text for logging."""
        system_prompt = load_sys_prompt(prompt_mode, self.config)
        intro = "Answer based on the retrieved memories and images below."
        if prompt_mode == "open":
            intro += " Be concise and factual."
        blocks: List[str] = []
        if context.strip():
            blocks.append(
                "Use the following retrieved memories as conversation context.\n\n"
                f"{context.strip()}"
            )
        blocks.append(f"{intro}\n\nQuestion: {question}")
        user_text = "\n\n".join(blocks)
        image_parts = _retrieval_image_parts(retrieval_user_content)
        if image_parts:
            user_content: Any = [{"type": "text", "text": user_text}, *image_parts]
        else:
            user_content = user_text
        return system_prompt, user_content, user_text

    def _write_answer_context(
        self,
        *,
        dataset: MemoryBenchmarkDataset,
        qa: Dict[str, Any],
        question: str,
        recall_query: str,
        prompt_mode: str,
        answer_tag: str,
        bundle: Dict[str, Any],
        user_text: str,
        images_expanded: List[Dict[str, Any]],
        images_not_expanded: List[Dict[str, Any]],
        prediction: str,
        question_images: Optional[List[str]],
    ) -> Optional[str]:
        contexts_dir = self._contexts_dir()
        if contexts_dir is None:
            return None
        contexts_dir.mkdir(parents=True, exist_ok=True)

        retrieval = bundle.get("retrieval")
        items = list(getattr(retrieval, "items", None) or [])
        context_text = str(bundle.get("context", "") or "")
        memories_text, knowledge_graph_text = _split_knowledge_graph_text(context_text)
        serialized_items = _serialize_retrieval_items(items, dataset=dataset)
        faiss_count = sum(1 for row in serialized_items if row.get("source") == "faiss")
        bm25_count = sum(1 for row in serialized_items if row.get("source") == "bm25")

        payload: Dict[str, Any] = {
            "question_id": qa.get("question_id", ""),
            "idx": qa.get("_benchmark_idx"),
            "mode": prompt_mode,
            "answer_tag": answer_tag or prompt_mode,
            "question": question,
            "recall_query": recall_query,
            "question_images": list(question_images or []),
            "retrieve_k": self._top_k,
            "retrieval_summary": {
                "total_items": len(serialized_items),
                "faiss_items": faiss_count,
                "bm25_appended": bm25_count,
                "images_expanded_count": len(images_expanded),
                "images_not_expanded_count": len(images_not_expanded),
            },
            "retrieved_items": serialized_items,
            "context_text": context_text,
            "memories_text": memories_text,
            "knowledge_graph_text": knowledge_graph_text,
            "images_expanded": images_expanded,
            "images_not_expanded": images_not_expanded,
            "prompt": {
                "user_text": user_text,
                "num_vlm_images": len(images_expanded),
                "user_image_paths": [row["image_path"] for row in images_expanded],
            },
            "prediction": prediction,
        }
        out_path = contexts_dir / self._context_filename(
            qa, prompt_mode=prompt_mode, answer_tag=answer_tag
        )
        write_json(out_path, payload)
        return str(out_path)

    def _answer_with_memeye_prompt(
        self,
        *,
        prompt_mode: str,
        context: str,
        question: str,
        retrieval_user_content: Any,
    ) -> Tuple[str, str]:
        """Generate an answer with MemEye system prompts after SimpleMem retrieval."""
        assert self._orchestrator is not None
        system_prompt, user_content, user_text = self._build_memeye_user_prompt(
            prompt_mode=prompt_mode,
            context=context,
            question=question,
            retrieval_user_content=retrieval_user_content,
        )
        model_config = dict(self.config.get("_model_cfg", {}))
        model_name = _resolve_model_name(self.config, model_config)
        max_tokens = int(
            model_config.get("max_new_tokens")
            or self.config.get("max_tokens", 128)
        )

        client = self._orchestrator._get_llm_client()
        create_kwargs: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": float(self.config.get("temperature", 0.0)),
        }
        if any(model_name.startswith(p) for p in ("gpt-5", "o3", "o4")):
            create_kwargs["max_completion_tokens"] = max_tokens
        else:
            create_kwargs["max_tokens"] = max_tokens
        response = client.chat.completions.create(**create_kwargs)
        return str(response.choices[0].message.content or "").strip(), user_text

    # ------------------------------------------------------------------
    # HistoryMethod overrides
    # ------------------------------------------------------------------

    def answer(
        self,
        dataset: MemoryBenchmarkDataset,
        qa: Dict[str, Any],
        question: str,
        question_images: Optional[List[str]] = None,
        answer_tag: str = "",
    ) -> str:
        self._ensure_initialized(dataset)
        assert self._orchestrator is not None

        query = _question_with_image_caption(qa, question)
        prompt_mode = "mcq" if _is_mcq(qa) else "open"
        if not answer_tag.strip():
            answer_tag = prompt_mode
        context_file: Optional[str] = None
        try:
            bundle = self._orchestrator.retrieve_answer_context(
                query,
                top_k=self._top_k,
                question_images=question_images or None,
            )
            retrieval = bundle.get("retrieval")
            items = list(getattr(retrieval, "items", None) or [])
            images_expanded, images_not_expanded = _images_expanded_from_items(
                items, dataset=dataset
            )
            answer_text, user_text = self._answer_with_memeye_prompt(
                prompt_mode=prompt_mode,
                context=str(bundle.get("context", "") or ""),
                question=question,
                retrieval_user_content=bundle.get("user_content"),
            )
            if self._log_answer_context:
                context_file = self._write_answer_context(
                    dataset=dataset,
                    qa=qa,
                    question=question,
                    recall_query=query,
                    prompt_mode=prompt_mode,
                    answer_tag=answer_tag,
                    bundle=bundle,
                    user_text=user_text,
                    images_expanded=images_expanded,
                    images_not_expanded=images_not_expanded,
                    prediction=answer_text,
                    question_images=question_images,
                )
                if context_file:
                    self.runtime_info["last_context_file"] = context_file
        except Exception as exc:
            self._debug_rows.append(
                {
                    "type": "answer_error",
                    "question_id": qa.get("question_id", ""),
                    "question": question,
                    "recall_query": query,
                    "question_images": list(question_images or []),
                    "answer_tag": answer_tag,
                    "error": str(exc),
                }
            )
            self._flush_debug(dataset)
            raise

        self._debug_rows.append(
            {
                "type": "qa",
                "question_id": qa.get("question_id", ""),
                "question": question,
                "recall_query": query,
                "question_images": list(question_images or []),
                "prompt_mode": prompt_mode,
                "answer_tag": answer_tag,
                "num_sources": len(items),
                "num_images_expanded": len(images_expanded),
                "context_file": context_file or "",
                "prediction": answer_text,
            }
        )
        self._flush_debug(dataset)
        return answer_text

    def build_history(
        self, dataset: MemoryBenchmarkDataset, qa: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        return []

    def __del__(self) -> None:
        try:
            if self._orchestrator is not None:
                self._orchestrator.close()
        except Exception:
            pass
