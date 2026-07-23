from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, List, Optional, Tuple

from tqdm import tqdm

from constant import Image_Root_Dir_Path
from utils import (
    build_function_call_messages_multimodal,
    data_url_to_image_path,
    evaluate_function_call_response,
    get_response,
    load_function_call_candidate_tools,
)

from ..base_mem_agent import BaseMemoryAgent
from ..prompt import (
    FILL_IN_THE_BLANK_OUTPUT_FORMAT,
    MEM0_USER_PROMPT_TEMPLATE,
    MULTIPLE_CHOICE_OUTPUT_FORMAT,
    OVERALL_EVALUATION_SYSTEM_PROMPT,
    QUESTION_WITH_OPTIONS_TEMPLATE,
)

DEFAULT_OMNI_SIMPLEMEM_BASELINE_ROOT = (
    Path(__file__).resolve().parents[3] / "baselines" / "SimpleMem" / "OmniSimpleMem"
)
DEFAULT_TEXT_CHUNK_MAX_TURNS = 20
DEFAULT_TEXT_CHUNK_MAX_CHARS = 6000
UNKNOWN_SESSION_ID = "unknown_session"
CLUSTER_WIDE_SESSION = "__cluster_wide__"

def _safe_text(value) -> str:
    return "" if value is None else str(value)

def _question_with_options(qa_sample: dict, eval_format: str) -> str:
    question = _safe_text(qa_sample.get("question", "")).strip()
    if eval_format != "multiple_choice":
        return question

    mc = qa_sample.get("multi_choice_QA") or {}
    options = mc.get("multi_choice_QA_options") or []
    if not options:
        return question

    labels = ["(A)", "(B)", "(C)", "(D)"]
    option_lines = [f"{labels[i]}: {opt}" for i, opt in enumerate(options[:4])]
    return QUESTION_WITH_OPTIONS_TEMPLATE.format(
        question=question,
        candidate_options="\n".join(option_lines),
    )

def _uses_visualized_bge(text_model: str, visual_model: str) -> bool:
    text_value = (text_model or "").strip().lower().replace("\\", "/")
    visual_value = (visual_model or "").strip().lower().replace("\\", "/")
    if "bge-m3" not in text_value:
        return False
    return (
        "bge-visualized" in visual_value
        or "visualized_m3" in visual_value
        or visual_value.endswith(".pth")
    )

class OmniSimpleMemAgent(BaseMemoryAgent):

    def _eval_system_prompt(self) -> str:
        system_prompt = OVERALL_EVALUATION_SYSTEM_PROMPT
        if self.eval_format == "multiple_choice":
            system_prompt += MULTIPLE_CHOICE_OUTPUT_FORMAT
        elif self.eval_format == "fill_in_the_blank":
            system_prompt += FILL_IN_THE_BLANK_OUTPUT_FORMAT
        else:
            raise ValueError(f"Invalid evaluation format: {self.eval_format}")
        return system_prompt

    def __init__(self, client, args):
        super().__init__(args)
        self.client = client
        self.args = args
        self.eval_format = args.eval_format
        self.dataset_dir = Path(args.dataset_dir_path).resolve()

        raw_root = (getattr(args, "omnisimplemem_baseline_root", "") or "").strip()
        self.omni_baseline_root = Path(raw_root or DEFAULT_OMNI_SIMPLEMEM_BASELINE_ROOT).resolve()
        self.runtime_root = Path(
            (getattr(args, "omnisimplemem_runtime_root", "") or "").strip()
            or (Path(args.output_dir).resolve() / "checkpoint" / "omnisimplemem")
        )
        self.top_k = max(1, int(getattr(args, "omnisimplemem_top_k", 20)))
        self.embedding_model = (
            getattr(args, "omnisimplemem_embedding_model", "") or "all-MiniLM-L6-v2"
        ).strip()
        self.embedding_dim = int(getattr(args, "omnisimplemem_embedding_dim", 384))
        self.embedding_server_url = (
            getattr(args, "omnisimplemem_embedding_server_url", "") or ""
        ).strip().rstrip("/")
        self.visual_embedding_model = (
            getattr(args, "omnisimplemem_visual_embedding_model", "")
            or "UCSC-VLAA/openvision-vit-large-patch14-224"
        ).strip()
        self.visual_embedding_dim = int(getattr(args, "omnisimplemem_visual_embedding_dim", 768))

        self._orchestrator = None
        self._config_cls = None
        self._retrieval_level_cls = None
        self._expansion_request_cls = None
        self._ingested_turns = 0
        self._stored_text_items = 0
        self._stored_image_items = 0
        self._skipped_rounds = 0
        self._ingested_rounds = 0
        self._session_id = self._conversation_id()
        self._text_chunk_max_turns = max(
            1, int(getattr(args, "omnisimplemem_chunk_turns", DEFAULT_TEXT_CHUNK_MAX_TURNS))
        )
        self._text_chunk_max_chars = max(
            1, int(getattr(args, "omnisimplemem_chunk_max_chars", DEFAULT_TEXT_CHUNK_MAX_CHARS))
        )
        self._chunk_max_images = max(
            1, int(getattr(args, "omnisimplemem_chunk_max_images", 8))
        )
        self._progress_bar = None
        self._current_turn_type = "idle"
        self._usage_memory_construction: Optional[dict] = None
        self._usage_retrieval_list: list[dict] = []
        self._sessions_in_cluster: list[str] = []
        self._ingest_by_session: dict[str, dict] = {}
        self._retrieval_by_session: dict[str, dict] = {}
        self._retrieval_qa_ids_by_session: dict[str, list[str]] = {}
        self._function_call_candidate_tools = load_function_call_candidate_tools()
        self._cluster_id = self._conversation_id()

    def _usage_helpers(self):
        """Import usage helpers from OmniSimpleMem after bootstrap."""
        self._bootstrap_omni()
        from omni_memory.utils.usage import (
            PHASE_MEMORY_CONSTRUCTION,
            PHASE_RETRIEVAL,
            get_usage_tracker,
            reset_usage_tracker,
        )

        return {
            "PHASE_MEMORY_CONSTRUCTION": PHASE_MEMORY_CONSTRUCTION,
            "PHASE_RETRIEVAL": PHASE_RETRIEVAL,
            "get_usage_tracker": get_usage_tracker,
            "reset_usage_tracker": reset_usage_tracker,
        }

    def _write_usage_json(self, filename: str, payload: dict) -> Path:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        path = self.runtime_root / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _sum_usage_buckets(buckets: list[dict]) -> dict:
        from omni_memory.utils.usage import _add_into, _empty_bucket

        out = _empty_bucket()
        for b in buckets:
            if b:
                _add_into(out, b)
        return out

    @staticmethod
    def _session_id_from_turn(turn: dict) -> str:
        name = _safe_text(turn.get("conversation_name", "")).strip()
        return name or UNKNOWN_SESSION_ID

    @staticmethod
    def _empty_ingest_stats() -> dict:
        return {
            "rounds": 0,
            "turns": 0,
            "chars": 0,
            "images": 0,
            "text_items": 0,
            "image_items": 0,
            "skipped_rounds": 0,
        }

    @staticmethod
    def _qa_related_sessions(qa_sample: dict) -> list[str]:
        sessions: set[str] = set()
        assignment = qa_sample.get("evidence_assignment") or {}
        for items in assignment.values():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = _safe_text(item.get("conversation_name", "")).strip()
                if name:
                    sessions.add(name)
        return sorted(sessions)

    def _accumulate_ingest_stats(
        self,
        session_id: str,
        round_item: dict,
        *,
        round_status: str,
    ) -> None:
        stats = self._ingest_by_session.setdefault(session_id, self._empty_ingest_stats())
        stats["rounds"] += 1
        stats["turns"] += int(round_item.get("turn_count") or 0)
        stats["chars"] += int(round_item.get("char_count") or 0)
        stats["images"] += int(round_item.get("image_count") or 0)
        if round_status == "stored":
            stats["text_items"] += 1
            stats["image_items"] += int(round_item.get("image_count") or 0)
        elif round_status == "skipped":
            stats["skipped_rounds"] += 1

    def _accumulate_retrieval_by_session(self, qa_sample: dict, qa_usage: dict) -> None:
        from omni_memory.utils.usage import _add_into, _empty_bucket, split_usage_bucket

        related = self._qa_related_sessions(qa_sample)
        if not related:
            related = [CLUSTER_WIDE_SESSION]
        qa_id = _safe_text(qa_sample.get("id", "")).strip() or "unknown_qa"
        for session_id, part in zip(related, split_usage_bucket(qa_usage, len(related))):
            bucket = self._retrieval_by_session.setdefault(session_id, _empty_bucket())
            _add_into(bucket, part)
            self._retrieval_qa_ids_by_session.setdefault(session_id, []).append(qa_id)

    def _build_usage_by_session_payload(self) -> dict:
        from omni_memory.utils.usage import _add_into, _empty_bucket

        mem_by_session = (self._usage_memory_construction or {}).get("by_session") or {}
        session_ids = sorted(
            set(self._sessions_in_cluster)
            | set(self._ingest_by_session)
            | set(mem_by_session)
            | set(self._retrieval_by_session)
        )
        by_session: dict[str, dict] = {}
        for session_id in session_ids:
            memory = mem_by_session.get(session_id) or _empty_bucket()
            retrieval = self._retrieval_by_session.get(session_id) or _empty_bucket()
            total = _empty_bucket()
            _add_into(total, memory)
            _add_into(total, retrieval)
            by_session[session_id] = {
                "ingest": dict(self._ingest_by_session.get(session_id) or self._empty_ingest_stats()),
                "memory_construction": memory,
                "retrieval": retrieval,
                "retrieval_qa_ids": list(self._retrieval_qa_ids_by_session.get(session_id) or []),
                "total": total,
            }

        return {
            "cluster_id": self._cluster_id,
            "sessions_in_cluster": self._sessions_in_cluster,
            "by_session": by_session,
        }

    def _write_usage_by_session(self) -> None:
        self._write_usage_json("usage_by_session.json", self._build_usage_by_session_payload())

    def _retrieve_context(self, question: str) -> str:
        if self._orchestrator is None:
            return ""
        retrieval = self._orchestrator.query(
            question,
            top_k=self.top_k,
            auto_expand=True,
        )
        if not retrieval.items:
            return ""
        return self._orchestrator.retriever.format_for_llm(
            retrieval,
            include_instructions=False,
        )

    def _write_usage_summary(self) -> None:
        memory = self._usage_memory_construction or {}
        retrieval = self._sum_usage_buckets(self._usage_retrieval_list)
        grand = self._sum_usage_buckets([memory, retrieval])
        by_session_payload = self._build_usage_by_session_payload()
        payload = {
            "memory_construction": memory,
            "retrieval": retrieval,
            "retrieval_num_questions": len(self._usage_retrieval_list),
            "grand_total": grand,
            "by_session": by_session_payload["by_session"],
        }
        self._write_usage_json("usage_summary.json", payload)
        self._write_usage_by_session()

    def _conversation_id(self) -> str:
        return f"{self.args.save_dir_name or 'cluster'}__omnisimplemem"

    def _bootstrap_omni(self):
        root_candidate = self.omni_baseline_root
        if root_candidate.name != "OmniSimpleMem" and (root_candidate / "OmniSimpleMem").is_dir():
            root_candidate = (root_candidate / "OmniSimpleMem").resolve()

        if root_candidate.is_dir():
            root_str = str(root_candidate)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            self.omni_baseline_root = root_candidate

        try:
            from omni_memory import OmniMemoryConfig, OmniMemoryOrchestrator
            from omni_memory.retrieval.pyramid_retriever import (
                ExpansionRequest,
                RetrievalLevel,
            )
        except ImportError as exc:
            raise ImportError(
                "Failed to import Omni-SimpleMem. Install it with "
                "`cd baselines/SimpleMem/OmniSimpleMem && pip install -e .[all]`, "
                "or pass --omnisimplemem_baseline_root to a checked-out OmniSimpleMem repo. "
                f"Resolved baseline root: {self.omni_baseline_root}. Original error: {exc}"
            ) from exc

        self._config_cls = OmniMemoryConfig
        self._retrieval_level_cls = RetrievalLevel
        self._expansion_request_cls = ExpansionRequest
        return OmniMemoryOrchestrator, OmniMemoryConfig

    def _close_orchestrator(self) -> None:
        if self._orchestrator is not None:
            try:
                self._orchestrator.close()
            except Exception:
                pass
            self._orchestrator = None

    def _reset_runtime_state(self) -> None:
        self._close_orchestrator()
        shutil.rmtree(self.runtime_root, ignore_errors=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def _reuse_existing_memory(self, conversations: list) -> None:
        """Load checkpoint on disk; skip caption/embedding ingest. Rebuild BM25 only."""
        mau_dir = self.runtime_root / "index" / "mau_store"
        if not mau_dir.is_dir() or not any(mau_dir.glob("mau_*.jsonl")):
            raise RuntimeError(
                f"omnisimplemem_skip_ingest set but no MAU checkpoint under {mau_dir}. "
                "Run a full ingest first, or unset --omnisimplemem_skip_ingest."
            )

        usage = self._usage_helpers()
        tracker = usage["reset_usage_tracker"]()
        self._usage_memory_construction = None
        self._usage_retrieval_list = []
        self._sessions_in_cluster = []
        self._ingest_by_session = {}
        self._retrieval_by_session = {}
        self._retrieval_qa_ids_by_session = {}

        self._close_orchestrator()
        orchestrator_cls, _ = self._bootstrap_omni()
        config = self._build_config()
        self._orchestrator = orchestrator_cls(config=config, data_dir=str(self.runtime_root))

        mau_n = len(getattr(self._orchestrator.mau_store, "_id_index", {}) or {})
        if mau_n <= 0:
            raise RuntimeError(
                f"omnisimplemem_skip_ingest: loaded empty MAU store from {self.runtime_root}"
            )

        rounds = self._build_ingest_rounds(conversations)
        self._sessions_in_cluster = sorted(
            {round_item.get("session_id") or UNKNOWN_SESSION_ID for round_item in rounds}
        )
        self._ingested_turns = sum(int(r.get("turn_count") or 0) for r in rounds)
        self._ingested_rounds = len(rounds)
        self._skipped_rounds = 0
        self._stored_text_items = mau_n
        # One linear pass over jsonl (do NOT call mau_store.get() per id — that is O(n²)).
        vision_n = 0
        mau_dir = self.runtime_root / "index" / "mau_store"
        for mau_path in mau_dir.glob("mau_*.jsonl"):
            with mau_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tags = ((data.get("metadata") or {}).get("tags") or [])
                    if "vision_on_demand" in tags:
                        vision_n += 1
        self._stored_image_items = vision_n
        self._current_turn_type = "reuse"

        bm25_n = self._orchestrator.build_bm25_index()
        print(
            f"[OmniSimpleMem] skip_ingest: reused checkpoint mau={mau_n} "
            f"bm25={bm25_n} root={self.runtime_root}",
            flush=True,
        )
        if not bm25_n:
            print(
                "[OmniSimpleMem] BM25 index unavailable (empty store or rank_bm25 missing)",
                flush=True,
            )

        snap = tracker.snapshot()
        mem_usage = snap["by_phase"].get(
            usage["PHASE_MEMORY_CONSTRUCTION"], snap["totals"]
        )
        mem_usage = dict(mem_usage)
        mem_usage["by_session"] = snap.get("by_session") or {}
        mem_usage["skip_ingest"] = True
        mem_usage["reused_mau_count"] = mau_n
        self._usage_memory_construction = mem_usage
        self._write_usage_json(
            "usage_memory_construction.json",
            {
                "phase": usage["PHASE_MEMORY_CONSTRUCTION"],
                "sessions_in_cluster": self._sessions_in_cluster,
                "skip_ingest": True,
                "usage": self._usage_memory_construction,
            },
        )
        self._write_usage_by_session()

    def _build_config(self):
        _, config_cls = self._bootstrap_omni()
        if hasattr(config_cls, "create_default"):
            config = config_cls.create_default()
        else:
            config = config_cls()

        use_visualized_bge = _uses_visualized_bge(
            self.embedding_model,
            self.visual_embedding_model,
        )

        if hasattr(config, "embedding"):
            if hasattr(config.embedding, "model_name"):
                config.embedding.model_name = self.embedding_model
            if hasattr(config.embedding, "embedding_dim"):
                config.embedding.embedding_dim = self.embedding_dim
            if hasattr(config.embedding, "visual_embedding_model"):
                config.embedding.visual_embedding_model = self.visual_embedding_model
            if hasattr(config.embedding, "visual_embedding_dim"):
                config.embedding.visual_embedding_dim = self.visual_embedding_dim
            if hasattr(config.embedding, "server_url"):
                config.embedding.server_url = self.embedding_server_url or None
                if not config.embedding.server_url:
                    # Fall back to process env if agent arg empty.
                    import os

                    env_url = (os.environ.get("OMNI_EMBEDDING_SERVER_URL") or "").strip()
                    config.embedding.server_url = env_url.rstrip("/") or None

        if hasattr(config, "entropy_trigger"):
            if use_visualized_bge:

                if hasattr(config.entropy_trigger, "enable_visual_trigger"):
                    config.entropy_trigger.enable_visual_trigger = True
            else:
                # Caption-only mode: skip CLIP and visual MAUs (align with MemEye).
                if hasattr(config.entropy_trigger, "visual_encoder"):
                    config.entropy_trigger.visual_encoder = "none"
                if hasattr(config.entropy_trigger, "enable_visual_trigger"):
                    config.entropy_trigger.enable_visual_trigger = False

        if hasattr(config, "llm"):
            llm_model = self.args.model

            if hasattr(config.llm, "api_key"):
                config.llm.api_key = getattr(self.args, "api_key", None)
            if hasattr(config.llm, "api_base_url"):
                config.llm.api_base_url = getattr(self.args, "base_url", None)
            if hasattr(config.llm, "summary_model"):
                config.llm.summary_model = llm_model
            if hasattr(config.llm, "query_model"):
                config.llm.query_model = llm_model
            if hasattr(config.llm, "caption_model"):
                config.llm.caption_model = llm_model
            if hasattr(config.llm, "temperature"):
                config.llm.temperature = float(getattr(self.args, "temperature", 0.0))

        if hasattr(config, "retrieval"):
            if hasattr(config.retrieval, "default_top_k"):
                config.retrieval.default_top_k = self.top_k
            if hasattr(config.retrieval, "evidence_token_budget"):
                config.retrieval.evidence_token_budget = int(
                    getattr(self.args, "omnisimplemem_evidence_token_budget", 6000)
                )
            if hasattr(config.retrieval, "max_expanded_items"):
                # Align with upstream OmniSimpleMem default (5). 0 = no cap.
                config.retrieval.max_expanded_items = int(
                    getattr(self.args, "omnisimplemem_max_expanded_images", 5)
                )
            if hasattr(config.retrieval, "enable_hybrid_search"):
                config.retrieval.enable_hybrid_search = True
            if hasattr(config.retrieval, "enable_graph_traversal"):
                config.retrieval.enable_graph_traversal = True
            if hasattr(config.retrieval, "enable_multi_query_retrieval"):
                config.retrieval.enable_multi_query_retrieval = False
            if hasattr(config.retrieval, "include_details_in_preview"):
                config.retrieval.include_details_in_preview = False
            if hasattr(config.retrieval, "auto_expand_threshold"):
                config.retrieval.auto_expand_threshold = 0.4

        if hasattr(config, "enable_self_evolution"):
            config.enable_self_evolution = False
        if hasattr(config, "event") and hasattr(config.event, "summarize_on_close"):
            config.event.summarize_on_close = False

        return config

    def _materialize_image_ref(self, raw: str, prefix: str) -> str:
        if not raw or not isinstance(raw, str):
            return ""

        ref = raw.strip()
        if not ref:
            return ""

        input_dir = self.runtime_root / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)

        if ref.startswith("data:"):
            out_path = input_dir / f"{prefix}_{uuid.uuid4().hex}.png"
            data_url_to_image_path(ref, str(out_path))
            return str(out_path)

        if ref.startswith("file://"):
            ref = ref[7:]

        if ref.startswith(("http://", "https://")):
            suffix = Path(ref.split("?", 1)[0]).suffix or ".img"
            out_path = input_dir / f"{prefix}_{uuid.uuid4().hex}{suffix}"
            urllib.request.urlretrieve(ref, out_path)
            return str(out_path)

        ref_path = Path(ref)
        if ref_path.is_file():
            return str(ref_path.resolve())

        candidate = (self.dataset_dir / ref).resolve()
        if candidate.is_file():
            return str(candidate)

        rooted = Path(Image_Root_Dir_Path) / ref.lstrip("/\\")
        if rooted.is_file():
            return str(rooted.resolve())

        basename = Path(ref).name
        if basename and basename != ref:
            rooted_basename = Path(Image_Root_Dir_Path) / basename
            if rooted_basename.is_file():
                return str(rooted_basename.resolve())

        return ""

    def _make_tags(
        self,
        timestamp: str,
        sender: str,
        conversation_name: str,
        content_type: str,
    ) -> list[str]:
        tags = [f"content_type:{content_type}", f"sender:{sender or 'unknown'}"]
        if timestamp:
            tags.append(f"timestamp:{timestamp}")
        if conversation_name:
            tags.append(f"conversation:{conversation_name}")
        return tags

    def _build_round_text(self, round_item: dict) -> str:
        """MemEye-style text blob: dialogue plus image:/image_caption: lines per image."""
        lines: list[str] = []
        text = _safe_text(round_item.get("text", "")).strip()
        if text:
            lines.append(text)
        for idx, image_item in enumerate(round_item.get("image_items") or []):
            caption = _safe_text(image_item.get("caption", "")).strip()
            image_path = _safe_text(image_item.get("image_path", "")).strip()
            image_id = Path(image_path).name if image_path else f"image_{idx}"
            lines.extend(
                [
                    "image:",
                    f"image_id: {image_id}",
                    f"image_caption: {caption}",
                ]
            )
        return "\n".join(lines).strip()

    def _store_round_memeye_style(self, round_item: dict, *, session_id: str) -> str:
        """Store one round as a single TEXT MAU; all images via raw_pointer + region_pointers."""
        if self._orchestrator is None:
            raise RuntimeError("OmniSimpleMem runtime is not initialized.")

        text_blob = self._build_round_text(round_item)
        if not text_blob:
            return "skipped"

        tags = list(round_item.get("tags") or [])
        session_tag = f"session_id:{session_id}"
        if session_tag not in tags:
            tags.append(session_tag)
        image_items = list(round_item.get("image_items") or [])
        for image_item in image_items:
            image_path = _safe_text(image_item.get("image_path", "")).strip()
            if image_path:
                image_tag = f"image_id:{Path(image_path).name}"
                if image_tag not in tags:
                    tags.append(image_tag)

        try:
            result = self._orchestrator.add_text(
                text_blob,
                session_id=session_id,
                tags=tags,
                force=False,
            )
        except Exception:
            return "error"

        if not result.success or result.mau is None:
            return "skipped"

        self._stored_text_items += 1
        image_paths = [
            _safe_text(image_item.get("image_path", "")).strip()
            for image_item in image_items
            if _safe_text(image_item.get("image_path", "")).strip()
        ]
        if image_paths:
            mau = result.mau
            mau.raw_pointer = image_paths[0]
            mau.region_pointers = list(image_paths)
            mau.add_tag("vision_on_demand")
            for image_item in image_items:
                caption = _safe_text(image_item.get("caption", "")).strip()
                if caption:
                    mau.add_tag(f"caption:{caption}")
            if self._orchestrator.mau_store.update(mau):
                self._stored_image_items += len(image_paths)
        return "stored"

    @staticmethod
    def _qa_image_refs(qa_sample: dict) -> list[str]:
        """Prefer top-level images; fall back to evidence.image_evidence (SMMBench)."""
        top = qa_sample.get("images")
        if isinstance(top, list) and top:
            return [_safe_text(x).strip() for x in top if _safe_text(x).strip()]
        evidence = qa_sample.get("evidence")
        if isinstance(evidence, dict):
            imgs = evidence.get("image_evidence")
            if isinstance(imgs, list) and imgs:
                return [_safe_text(x).strip() for x in imgs if _safe_text(x).strip()]
        return []

    @staticmethod
    def _function_call_context_parts(bundle: dict[str, Any]) -> list[dict]:
        """Text memory context + any image parts from retrieve_answer_context."""
        parts: list[dict] = []
        context = str(bundle.get("context") or "").strip()
        parts.append(
            {
                "type": "text",
                "text": context if context else "(no retrieved memories)",
            }
        )
        user_content = bundle.get("user_content")
        if isinstance(user_content, list):
            for part in user_content:
                if isinstance(part, dict) and part.get("type") != "text":
                    parts.append(part)
        return parts

    def _build_answer_user_content(
        self,
        *,
        context: str,
        question: str,
        retrieval_user_content: Any,
    ) -> Any:
        user_prompt = MEM0_USER_PROMPT_TEMPLATE.format(context=context, question=question)
        if isinstance(retrieval_user_content, list):
            final_user: list[dict] = [{"type": "text", "text": user_prompt}]
            for part in retrieval_user_content:
                if part.get("type") != "text":
                    final_user.append(part)
            return final_user
        return user_prompt

    def _retrieval_sources(self, retrieval: Any) -> list[dict]:
        items = getattr(retrieval, "items", None) or []
        return [
            {
                "id": item["id"],
                "summary": item["summary"],
                "modality": item["modality_type"],
            }
            for item in items[:5]
        ]

    def _answer_with_retrieval_bundle(
        self,
        *,
        question: str,
        bundle: dict[str, Any],
    ) -> tuple[str, list[dict], dict[str, Any]]:
        retrieval = bundle["retrieval"]
        if bundle.get("empty"):
            deny = "I don't have any relevant memories to answer this question."
            return deny, [], {
                "answer": deny,
                "sources": [],
                "retrieval_result": retrieval.to_dict(),
            }

        context = str(bundle.get("context", "") or "")
        final_user = self._build_answer_user_content(
            context=context,
            question=question,
            retrieval_user_content=bundle.get("user_content"),
        )
        answer_messages = [
            {"role": "system", "content": self._eval_system_prompt()},
            {"role": "user", "content": final_user},
        ]
        raw = get_response(self.client, answer_messages, self.args)
        if isinstance(raw, tuple):
            raw = raw[0]
        raw_response = _safe_text(raw).strip()
        return raw_response, answer_messages, {
            "answer": raw_response,
            "sources": self._retrieval_sources(retrieval),
            "retrieval_result": retrieval.to_dict(),
        }

    def _answer_function_call_with_bundle(
        self,
        *,
        qa_sample: dict,
        bundle: dict[str, Any],
    ) -> tuple[str, list[dict], dict[str, Any], Any]:
        retrieval = bundle["retrieval"]
        answer_messages = build_function_call_messages_multimodal(
            qa_sample.get("question", ""),
            self._function_call_context_parts(bundle),
            self._function_call_candidate_tools,
        )
        raw = get_response(self.client, answer_messages, self.args)
        if isinstance(raw, tuple):
            raw = raw[0]
        raw_response = _safe_text(raw).strip()
        single_qa_result, parsed_function_calls = evaluate_function_call_response(
            raw_response,
            qa_sample.get("answer"),
        )
        return (
            raw_response,
            answer_messages,
            {
                "answer": raw_response,
                "sources": self._retrieval_sources(retrieval),
                "retrieval_result": retrieval.to_dict(),
            },
            (single_qa_result, parsed_function_calls),
        )

    @staticmethod
    def _merge_tags(existing: list[str], new_tags: Optional[list[str]]) -> list[str]:
        merged = list(existing)
        for tag in new_tags or []:
            if tag and tag not in merged:
                merged.append(tag)
        return merged

    def _refresh_progress(self, *, note: str = "") -> None:
        if self._progress_bar is None:
            return
        postfix = {
            "type": self._current_turn_type,
            "rounds": self._ingested_rounds,
            "text": self._stored_text_items,
            "images": self._stored_image_items,
            "skip": self._skipped_rounds,
        }
        if note:
            postfix["note"] = note
        self._progress_bar.set_postfix(postfix, refresh=True)

    def _format_text_turn(
        self,
        sender: str,
        timestamp: str,
        conversation_name: str,
        content: str,
    ) -> str:
        prefix = f"{sender} at {timestamp}".strip()
        if conversation_name:
            prefix += f" in {conversation_name}"
        return f"{prefix}: {content}".strip()

    def _format_image_text(
        self,
        sender: str,
        timestamp: str,
        conversation_name: str,
        caption: str,
        *,
        label: str = "image",
    ) -> str:
        prefix = f"{sender} shared a {label} at {timestamp}".strip()
        if conversation_name:
            prefix += f" in {conversation_name}"
        if caption:
            return f"{prefix}. Image caption: {caption}"
        return f"{prefix}."

    def _json_evidence_to_text(self, turn: dict) -> str:
        sender = _safe_text(turn.get("sender_name", "unknown")).strip() or "unknown"
        timestamp = _safe_text(turn.get("timestamp", "")).strip()
        conversation_name = _safe_text(turn.get("conversation_name", "")).strip()
        first_line = f"{sender} shared a json evidence document at {timestamp}".strip()
        if conversation_name:
            first_line += f" in {conversation_name}"

        parts: list[str] = [first_line]
        for item in turn.get("content") or []:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            inner = item.get("content") or {}
            if not isinstance(inner, dict):
                inner = {}
            if item_type == "text":
                text = _safe_text(inner.get("text", "")).strip()
                if text:
                    parts.append(text)
            elif item_type == "image":
                caption = _safe_text(item.get("caption", "")).strip()
                if caption:
                    parts.append(f"Embedded image caption: {caption}")

        caption = _safe_text(turn.get("caption", "")).strip()
        if caption:
            parts.append(f"Document caption: {caption}")
        return "\n".join(part for part in parts if part.strip())

    def _turn_to_chunk_item(self, turn: dict, turn_idx: int) -> Optional[dict]:
        sender = _safe_text(turn.get("sender_name", "unknown")).strip() or "unknown"
        timestamp = _safe_text(turn.get("timestamp", "")).strip()
        conversation_name = _safe_text(turn.get("conversation_name", "")).strip()
        content_type = _safe_text(turn.get("content_type", "text")).strip() or "text"
        base_tags = self._make_tags(timestamp, sender, conversation_name, content_type)

        text_parts: list[str] = []
        image_items: list[dict] = []

        if content_type == "text":
            content = _safe_text(turn.get("content", "")).strip()
            if content:
                text_parts.append(
                    self._format_text_turn(sender, timestamp, conversation_name, content)
                )

        elif content_type == "image":
            caption = _safe_text(turn.get("caption", "")).strip()
            image_path = self._materialize_image_ref(
                _safe_text(turn.get("image_path") or turn.get("image_url") or turn.get("content")),
                f"turn_{turn_idx}",
            )
            if caption:
                text_parts.append(
                    self._format_image_text(
                        sender,
                        timestamp,
                        conversation_name,
                        caption,
                    )
                )
            elif image_path:
                text_parts.append(
                    self._format_image_text(
                        sender,
                        timestamp,
                        conversation_name,
                        "",
                    )
                )
            if image_path:
                image_tags = list(base_tags)
                if caption:
                    image_tags.append(f"caption:{caption}")
                image_items.append(
                    {
                        "image_path": image_path,
                        "caption": caption,
                        "tags": image_tags,
                    }
                )

        elif content_type == "json_evidence":
            document_text = self._json_evidence_to_text(turn)
            if document_text:
                text_parts.append(document_text)

            for item_idx, item in enumerate(turn.get("content") or []):
                if not isinstance(item, dict) or item.get("type") != "image":
                    continue
                inner = item.get("content") or {}
                if not isinstance(inner, dict):
                    continue
                image_path = self._materialize_image_ref(
                    _safe_text(inner.get("image_url") or inner.get("image_path")),
                    f"turn_{turn_idx}_{item_idx}",
                )
                if not image_path:
                    continue
                caption = _safe_text(item.get("caption", "")).strip()
                image_tags = list(base_tags)
                if caption:
                    image_tags.append(f"caption:{caption}")
                image_items.append(
                    {
                        "image_path": image_path,
                        "caption": caption,
                        "tags": image_tags,
                    }
                )

        else:
            fallback_text = _safe_text(turn.get("content", "")).strip()
            if fallback_text:
                text_parts.append(
                    self._format_text_turn(
                        sender,
                        timestamp,
                        conversation_name,
                        fallback_text,
                    )
                )

        if not text_parts and not image_items:
            return None

        merged_tags = list(base_tags)
        for image_item in image_items:
            merged_tags = self._merge_tags(merged_tags, image_item.get("tags"))

        return {
            "turn_count": 1,
            "char_count": sum(len(part) for part in text_parts),
            "image_count": len(image_items),
            "text_parts": text_parts,
            "image_items": image_items,
            "tags": merged_tags,
            "content_type": content_type,
            "session_id": self._session_id_from_turn(turn),
        }

    @staticmethod
    def _is_assistant_turn(turn: dict) -> bool:
        return _safe_text(turn.get("sender_name", "")).strip().lower() == "assistant"

    @staticmethod
    def _is_user_assistant_session(session_id: str) -> bool:
        return session_id.startswith("user_assistant_")

    def _merge_turn_items_into_round(
        self,
        session_id: str,
        items: list[dict],
        *,
        first_turn_idx: int,
        last_turn_idx: int,
    ) -> Optional[dict]:
        if not items:
            return None

        text_parts: list[str] = []
        image_items: list[dict] = []
        tags: list[str] = []
        char_count = 0
        image_count = 0
        for item in items:
            text_parts.extend(item["text_parts"])
            image_items.extend(item["image_items"])
            tags = self._merge_tags(tags, item["tags"])
            char_count += int(item["char_count"])
            image_count += int(item["image_count"])

        round_id = (
            f"turn_{first_turn_idx}"
            if last_turn_idx == first_turn_idx
            else f"turn_{first_turn_idx}_{last_turn_idx}"
        )
        text = "\n\n".join(part for part in text_parts if part and part.strip()).strip()
        if not text and not image_items:
            return None

        return {
            "text": text,
            "image_items": list(image_items),
            "tags": self._merge_tags(tags, [f"round_id:{round_id}"]),
            "turn_count": len(items),
            "char_count": char_count,
            "image_count": image_count,
            "session_id": session_id,
            "round_id": round_id,
        }

    def _build_ingest_rounds(self, conversations: list[dict]) -> list[dict]:
        """Build ingest rounds: user+assistant pair for UA sessions, one turn otherwise."""
        rounds: list[dict] = []
        pending_by_session: dict[str, list[tuple[int, dict]]] = {}
        last_session_id: Optional[str] = None

        def flush_pending_user_only(session_id: str) -> None:
            pending = pending_by_session.pop(session_id, [])
            if not pending:
                return
            indices = [idx for idx, _ in pending]
            items = [item for _, item in pending]
            round_item = self._merge_turn_items_into_round(
                session_id,
                items,
                first_turn_idx=indices[0],
                last_turn_idx=indices[-1],
            )
            if round_item is not None:
                rounds.append(round_item)

        for turn_idx, turn in enumerate(conversations):
            session_id = self._session_id_from_turn(turn)
            if last_session_id and session_id != last_session_id:
                flush_pending_user_only(last_session_id)
            last_session_id = session_id

            item = self._turn_to_chunk_item(turn, turn_idx)
            if item is None:
                continue

            if self._is_user_assistant_session(session_id):
                if self._is_assistant_turn(turn):
                    pending = pending_by_session.pop(session_id, [])
                    pending.append((turn_idx, item))
                    indices = [idx for idx, _ in pending]
                    items = [it for _, it in pending]
                    round_item = self._merge_turn_items_into_round(
                        session_id,
                        items,
                        first_turn_idx=indices[0],
                        last_turn_idx=indices[-1],
                    )
                    if round_item is not None:
                        rounds.append(round_item)
                else:
                    pending_by_session.setdefault(session_id, []).append((turn_idx, item))
                continue

            flush_pending_user_only(session_id)
            round_item = self._merge_turn_items_into_round(
                session_id,
                [item],
                first_turn_idx=turn_idx,
                last_turn_idx=turn_idx,
            )
            if round_item is not None:
                rounds.append(round_item)

        if last_session_id:
            flush_pending_user_only(last_session_id)

        return rounds

    def build_memory(
        self,
        conversations: list,
        conversation_streams: Optional[list],
        qa_samples: list[dict],
    ) -> None:
        del conversation_streams, qa_samples

        if bool(getattr(self.args, "omnisimplemem_skip_ingest", False)):
            self._reuse_existing_memory(conversations)
            return

        usage = self._usage_helpers()
        tracker = usage["reset_usage_tracker"]()
        self._usage_memory_construction = None
        self._usage_retrieval_list = []
        self._sessions_in_cluster = []
        self._ingest_by_session = {}
        self._retrieval_by_session = {}
        self._retrieval_qa_ids_by_session = {}

        self._reset_runtime_state()
        orchestrator_cls, _ = self._bootstrap_omni()
        config = self._build_config()
        self._orchestrator = orchestrator_cls(config=config, data_dir=str(self.runtime_root))

        self._ingested_turns = 0
        self._stored_text_items = 0
        self._stored_image_items = 0
        self._skipped_rounds = 0
        self._ingested_rounds = 0
        self._current_turn_type = "startup"
        rounds = self._build_ingest_rounds(conversations)
        self._sessions_in_cluster = sorted(
            {round_item.get("session_id") or UNKNOWN_SESSION_ID for round_item in rounds}
        )
        self._progress_bar = tqdm(rounds, desc="Building OmniSimpleMem memory", mininterval=0.5)
        self._refresh_progress(note="init")
        try:
            with tracker.phase(usage["PHASE_MEMORY_CONSTRUCTION"]):
                for round_idx, round_item in enumerate(self._progress_bar, start=1):
                    self._current_turn_type = "round"
                    session_id = (
                        _safe_text(round_item.get("session_id", "")).strip()
                        or UNKNOWN_SESSION_ID
                    )
                    round_note = (
                        f"round={round_idx} session={session_id} "
                        f"turns={round_item['turn_count']} chars={round_item['char_count']} "
                        f"images={round_item['image_count']}"
                    )
                    self._refresh_progress(note=round_note)

                    with tracker.session(session_id):
                        round_status = self._store_round_memeye_style(
                            round_item,
                            session_id=session_id,
                        )
                        if round_status == "skipped":
                            self._skipped_rounds += 1

                    self._accumulate_ingest_stats(
                        session_id,
                        round_item,
                        round_status=round_status,
                    )

                    self._ingested_turns += int(round_item.get("turn_count") or 0)
                    self._ingested_rounds += 1
                    self._refresh_progress(note="stored")
        finally:
            if self._progress_bar is not None:
                self._progress_bar.close()
            self._progress_bar = None

        bm25_n = self._orchestrator.build_bm25_index()
        if bm25_n:
            print(f"[OmniSimpleMem] BM25 index ready: {bm25_n} documents", flush=True)
        else:
            print(
                "[OmniSimpleMem] BM25 index unavailable (empty store or rank_bm25 missing)",
                flush=True,
            )

        snap = tracker.snapshot()
        mem_usage = snap["by_phase"].get(
            usage["PHASE_MEMORY_CONSTRUCTION"], snap["totals"]
        )
        mem_usage = dict(mem_usage)
        mem_usage["by_session"] = snap.get("by_session") or {}
        self._usage_memory_construction = mem_usage
        self._write_usage_json(
            "usage_memory_construction.json",
            {
                "phase": usage["PHASE_MEMORY_CONSTRUCTION"],
                "sessions_in_cluster": self._sessions_in_cluster,
                "usage": self._usage_memory_construction,
            },
        )
        self._write_usage_by_session()

    def evaluate_cluster(
        self,
        qa_samples: List[dict],
        conversations: list,
        conversation_streams: Optional[list] = None,
    ) -> Tuple[List[Any], List[Any]]:
        evaluation_result, readable_message_result = super().evaluate_cluster(
            qa_samples,
            conversations,
            conversation_streams=conversation_streams,
        )
        try:
            self._write_usage_summary()
        except Exception as exc:
            print(f"[OmniSimpleMem] failed to write usage_summary.json: {exc}", flush=True)
        return evaluation_result, readable_message_result

    def evaluate_single_qa(
        self,
        qa_sample: dict,
        conversations: list,
        conversation_streams: list | None = None,
    ):
        del conversations, conversation_streams

        if self._orchestrator is None:
            raise RuntimeError("OmniSimpleMem runtime is not initialized. build_memory must run before QA.")

        usage_helpers = self._usage_helpers()
        tracker = usage_helpers["get_usage_tracker"]()
        before = tracker.snapshot()

        question = _question_with_options(qa_sample, self.eval_format)
        question_images: list[str] = []
        query_image_used = False
        for idx, ref in enumerate(self._qa_image_refs(qa_sample)):
            materialized = self._materialize_image_ref(ref, f"qa_image_{idx}")
            if materialized:
                question_images.append(materialized)
                query_image_used = True

        t0 = time.perf_counter()
        parsed_function_calls = None
        answer_messages: list[dict] = []
        result: dict = {}

        with tracker.phase(usage_helpers["PHASE_RETRIEVAL"]):
            bundle = self._orchestrator.retrieve_answer_context(
                question=question,
                top_k=self.top_k,
                include_on_demand_images=True,
                question_images=question_images or None,
            )
            if qa_sample.get("category") == "Function_Call":
                (
                    raw_response,
                    answer_messages,
                    result,
                    (single_qa_result, parsed_function_calls),
                ) = self._answer_function_call_with_bundle(
                    qa_sample=qa_sample,
                    bundle=bundle,
                )
            else:
                raw_response, answer_messages, result = self._answer_with_retrieval_bundle(
                    question=question,
                    bundle=bundle,
                )
                single_qa_result = self._evaluate_answer(raw_response, qa_sample)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        delta = tracker.delta(before)
        qa_usage = delta["by_phase"].get(
            usage_helpers["PHASE_RETRIEVAL"], delta["totals"]
        )
        self._usage_retrieval_list.append(qa_usage)
        self._accumulate_retrieval_by_session(qa_sample, qa_usage)

        ground_truth = qa_sample.get("answer")
        if (
            self.eval_format == "multiple_choice"
            and qa_sample.get("category") != "Function_Call"
        ):
            mc = qa_sample.get("multi_choice_QA") or {}
            ans_idx = mc.get("multi_choice_QA_answer")
            if isinstance(ans_idx, int) and 0 <= ans_idx < 4:
                ground_truth = ["(A)", "(B)", "(C)", "(D)"][ans_idx]

        readable_answer = {
            "id": qa_sample.get("id"),
            "category": qa_sample.get("category"),
            "question": qa_sample.get("question"),
            "answer": ground_truth,
            "multi_choice_QA": qa_sample.get("multi_choice_QA"),
            "raw_response": raw_response,
            "parsed_function_calls": parsed_function_calls,
            "single_qa_result": single_qa_result,
        }
        read_message = {
            "id": qa_sample.get("id"),
            "category": qa_sample.get("category"),
            "question": qa_sample.get("question"),
            "answer": ground_truth,
            "multi_choice_QA": qa_sample.get("multi_choice_QA"),
            "raw_response": raw_response,
            "parsed_function_calls": parsed_function_calls,
            "single_qa_result": single_qa_result,
            "messages": {
                "question": question,
                "top_k": self.top_k,
                "embedding_model": self.embedding_model,
                "embedding_dim": self.embedding_dim,
                "visual_embedding_model": self.visual_embedding_model,
                "visual_embedding_dim": self.visual_embedding_dim,
                "baseline_root": str(self.omni_baseline_root),
                "runtime_root": str(self.runtime_root),
                "cluster_id": self._cluster_id,
                "sessions_in_cluster": self._sessions_in_cluster,
                "ingested_turn_count": self._ingested_turns,
                "stored_text_items": self._stored_text_items,
                "stored_image_items": self._stored_image_items,
                "skipped_rounds": self._skipped_rounds,
                "ingested_rounds": self._ingested_rounds,
                "query_image_used": query_image_used,
                "query_image_supported_by_adapter": bool(question_images),
                "latency_ms": latency_ms,
                "usage": qa_usage,
                "answer_messages": answer_messages if qa_sample.get("category") == "Function_Call" else None,
                "sources": result.get("sources", []),
                "retrieval_result": result.get("retrieval_result"),
            },
        }
        return readable_answer, read_message
