"""
SeCom adapter for MemEye (text-only).

SeCom builds a segment-level memory bank (optional LLMLingua compression) and
retrieves with BM25 / dense embeddings. Images are replaced by precomputed
dense captions (`image_caption`), matching other text-only MemEye methods.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from .common import REPO_ROOT, SCRIPT_DIR, write_json
from .dataset import MemoryBenchmarkDataset, build_caption_text, validate_text_only_captions
from .methods import HistoryMethod
from .runner import load_sys_prompt


def _default_secom_roots() -> List[Path]:
    roots: List[Path] = []
    env = str(os.getenv("SECOM_ROOT", "")).strip()
    if env:
        roots.append(Path(env).expanduser().resolve())
    # Sibling of SimpleMem under repos/
    roots.append((SCRIPT_DIR.parent.parent.parent.parent / "SeCom").resolve())
    # Optional vendored copy under MemEye
    roots.append((Path(__file__).resolve().parent / "secom" / "upstream").resolve())
    return roots


def _resolve_secom_root(method_config: Dict[str, Any]) -> Path:
    raw = str(method_config.get("secom_root", "")).strip()
    candidates: List[Path] = []
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (SCRIPT_DIR / path).resolve()
        candidates.append(path)
    candidates.extend(_default_secom_roots())

    for root in candidates:
        if (root / "secom" / "__init__.py").exists():
            return root
    raise ModuleNotFoundError(
        "Could not locate the SeCom package. Set SECOM_ROOT or method config "
        "`secom_root` to the SeCom repo root (the directory that contains the "
        f"`secom/` package). Tried: {', '.join(str(p) for p in candidates)}"
    )


def _ensure_secom_on_path(secom_root: Path) -> None:
    root = str(secom_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_secom_class(secom_root: Path) -> Any:
    _ensure_secom_on_path(secom_root)
    try:
        from secom import SeCom  # type: ignore
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "SeCom dependencies are not fully installed. Missing module: "
            f"{exc.name}. Install SeCom (`pip install -e {secom_root}`) and its "
            "requirements (langchain_core, langchain_community, omegaconf, "
            "tiktoken, rank_bm25 / sentence-transformers as needed)."
        ) from exc
    return SeCom


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
    return os.getenv(env_name) or None


def _resolve_base_url(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    raw = str(method_config.get("llm_base_url", "")).strip()
    if raw:
        return raw
    raw = str(model_config.get("base_url", "")).strip()
    return raw or "https://api.openai.com/v1"


def _resolve_timeout(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> int:
    try:
        return int(method_config.get("llm_timeout", model_config.get("timeout", 90)) or 90)
    except Exception:
        return 90


def _resolve_segment_model(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    explicit = str(method_config.get("segment_model", "")).strip()
    if explicit:
        return explicit
    explicit = str(method_config.get("llm_model", "")).strip()
    if explicit:
        return explicit
    return str(model_config.get("model", "")).strip() or "gpt-4o-mini"


def _resolve_answer_model(method_config: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    explicit = str(method_config.get("answer_model", "")).strip()
    if explicit:
        return explicit
    return str(model_config.get("model", "")).strip() or "gpt-4.1-nano"


def _resolve_secom_config_path(method_config: Dict[str, Any], secom_root: Path) -> Path:
    raw = str(method_config.get("secom_config", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            cand = (secom_root / path).resolve()
            if cand.exists():
                return cand
            return (SCRIPT_DIR / path).resolve()
        return path.resolve()
    return (secom_root / "secom" / "configs" / "halumem_bm25.yaml").resolve()


def _unit_to_text(unit: Any) -> str:
    if isinstance(unit, list):
        return "\n".join(str(x) for x in unit)
    return str(unit)


def _is_mcq(qa: Dict[str, Any]) -> bool:
    options = qa.get("options")
    return bool(options and isinstance(options, (dict, list)))


def _question_caption_text(qa: Dict[str, Any]) -> str:
    raw = qa.get("question_image_caption")
    if raw is None:
        raw = qa.get("image_caption")
    if isinstance(raw, list):
        return " ".join(str(item).strip() for item in raw if str(item).strip())
    return str(raw or "").strip()


def _question_with_image_caption(qa: Dict[str, Any], question: str) -> str:
    query = question.strip()
    has_question_image = bool(qa.get("question_image") or qa.get("question_images"))
    caption_text = _question_caption_text(qa)
    if not has_question_image or not caption_text:
        return query
    return f"{query}\nquestion's image:\nimage_caption: {caption_text}"


def build_secom_exchange_text(
    round_payload: Dict[str, Any],
    *,
    turn_idx: int,
    timestamp: str = "",
) -> str:
    """Format one MemEye round as a SeCom [human]/[bot] exchange with captions."""
    user_text = str(round_payload.get("user", "")).strip()
    assistant_text = str(round_payload.get("assistant", "")).strip()
    caption_text = build_caption_text(round_payload)

    human_parts: List[str] = []
    if user_text:
        human_parts.append(user_text)
    if caption_text:
        human_parts.append(caption_text)
    human_block = "\n".join(human_parts).strip()

    if timestamp:
        header = f"<Turn {turn_idx}> [{timestamp}]:"
    else:
        header = f"<Turn {turn_idx}>:"

    parts = [f"{header} [human]: {human_block}"]
    if assistant_text:
        parts.append(f"[bot]: {assistant_text}")
    return "\n".join(parts).strip()


class SeComAgent:
    def __init__(self, method_config: Dict[str, Any], model_config: Dict[str, Any]) -> None:
        self.method_config = method_config
        self.model_config = model_config
        self.secom_root = _resolve_secom_root(method_config)
        secom_cls = _load_secom_class(self.secom_root)
        self.config_path = _resolve_secom_config_path(method_config, self.secom_root)
        if not self.config_path.exists():
            raise FileNotFoundError(f"SeCom config not found: {self.config_path}")

        self.granularity = str(method_config.get("granularity", "segment")).strip() or "segment"
        self.compress_rate = float(method_config.get("compress_rate", 1.0))
        self.retrieve_k = max(1, int(method_config.get("retrieve_k", 3)))
        self.temperature = float(method_config.get("temperature", 0.0))

        api_key = _resolve_api_key(method_config, model_config)
        base_url = _resolve_base_url(method_config, model_config)
        # SeCom's OpenAILLM reads OPENAI_* from the environment.
        if api_key and not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = api_key
        if base_url:
            os.environ.setdefault("OPENAI_BASE_URL", base_url)
            os.environ.setdefault("OPENAI_API_BASE", base_url)

        self.secom = secom_cls(granularity=self.granularity, config_path=str(self.config_path))
        segment_model = _resolve_segment_model(method_config, model_config)
        if self.secom.segmentor is not None:
            self.secom.segment_model = segment_model
            self.secom.segmentor.model_name = segment_model

        self.answer_model = _resolve_answer_model(method_config, model_config)
        self.answer_provider = str(model_config.get("provider", "")).strip().lower() or "openai_api"
        self.answer_timeout = _resolve_timeout(method_config, model_config)
        self.answer_client: Optional[OpenAI] = None
        if self.answer_provider in ("openai_api", "gemini_api"):
            if not api_key:
                raise ValueError("API key not found for SeCom answer model.")
            self.answer_client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.answer_timeout)
        self._answer_retryable_errors = (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )
        self._retriever_ready = False

    def clear(self) -> None:
        self.secom.clear()
        self._retriever_ready = False

    def build_memory(self, conversation_history: List[List[str]]) -> int:
        self.clear()
        if not conversation_history:
            return 0
        self.secom.build_memory(conversation_history, compress_rate=self.compress_rate)
        if not self.secom.memory_bank:
            return 0
        self.secom.init_retriever(self.retrieve_k, **self.secom.config.retriever)
        self._retriever_ready = True
        return len(self.secom.memory_bank)

    def _ensure_retriever(self) -> None:
        if not self.secom.memory_bank:
            raise ValueError("SeCom memory bank is empty; ingest dialogue first.")
        if not self._retriever_ready:
            self.secom.init_retriever(self.retrieve_k, **self.secom.config.retriever)
            self._retriever_ready = True
        else:
            self.secom.update_retriever(self.retrieve_k)

    def retrieve(self, query: str) -> Tuple[str, List[str]]:
        self._ensure_retriever()
        memories: List[str] = []
        r_docs = self.secom.retriever.invoke(query)
        for doc in r_docs:
            content = doc.metadata.get("content", doc.page_content)
            memories.append(_unit_to_text(content))
        context = "\n\n".join(
            f"[Retrieved Memory {idx}]\n{text}"
            for idx, text in enumerate(memories, start=1)
            if text.strip()
        )
        return context, memories

    def _create_answer_with_retry(self, **kwargs: Any) -> Any:
        if self.answer_client is None:
            raise ValueError("OpenAI answer client is not initialized.")
        max_retries = 4
        for attempt in range(max_retries):
            try:
                return self.answer_client.chat.completions.create(**kwargs)
            except self._answer_retryable_errors:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1.5 * (2 ** attempt))

    def answer_question(self, question: str, context: str, *, prompt_mode: str) -> Tuple[str, str]:
        system_prompt = load_sys_prompt(prompt_mode, self.method_config)
        intro = "Answer based on the retrieved memories below."
        if prompt_mode == "open":
            intro += " Be concise and factual."
        blocks: List[str] = []
        if context.strip():
            blocks.append(
                "Use the following retrieved memories as conversation context.\n\n"
                + context.strip()
            )
        else:
            blocks.append("No relevant memories were retrieved.")
        blocks.append(f"{intro}\n\nQuestion: {question}")
        user_prompt = "\n\n".join(blocks)

        if self.answer_client is None:
            raise ValueError(
                f"Unsupported answer model provider for SeCom benchmark QA: {self.answer_provider}. "
                "Use an OpenAI/Gemini API model config for final answer generation."
            )

        max_tokens = int(
            self.model_config.get("max_new_tokens") or self.method_config.get("max_tokens", 128)
        )
        create_kwargs: Dict[str, Any] = {
            "model": self.answer_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }
        if any(self.answer_model.startswith(prefix) for prefix in ("gpt-5", "o3", "o4")):
            create_kwargs["max_completion_tokens"] = max_tokens
        else:
            create_kwargs["max_tokens"] = max_tokens

        response = self._create_answer_with_retry(**create_kwargs)
        return str(response.choices[0].message.content or "").strip(), user_prompt


class SeComMethod(HistoryMethod):
    name = "secom"
    fixed_modality = "text_only"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self.config.setdefault("modality", "text_only")
        self.config.setdefault("caption_preprocessed", True)
        self._dataset_key: Optional[int] = None
        self._agent: Optional[SeComAgent] = None
        self._debug_rows: List[Dict[str, Any]] = []

    def _debug_dir(self, dataset: MemoryBenchmarkDataset) -> Path:
        task_name = str(dataset.data.get("task_name", "")).strip() or dataset.dialog_json_path.stem
        safe_task = task_name.lower().replace(" ", "_").replace("/", "_")
        return (REPO_ROOT / "output" / safe_task / "secom").resolve()

    def _flush_debug(self, dataset: MemoryBenchmarkDataset) -> None:
        if not self._debug_rows:
            return
        payload = {
            "dataset_path": str(dataset.dialog_json_path),
            "rows": self._debug_rows,
        }
        write_json(self._debug_dir(dataset) / "debug_trace.json", payload)

    def _build_conversation_history(
        self, dataset: MemoryBenchmarkDataset
    ) -> Tuple[List[List[str]], List[Dict[str, Any]]]:
        conversation_history: List[List[str]] = []
        stored_rows: List[Dict[str, Any]] = []
        global_turn = 0

        for session_id in dataset.session_order():
            session = dataset.get_session(session_id)
            timestamp = str(session.get("date", "")).strip()
            exchanges: List[str] = []
            for dialogue in session.get("dialogues", []):
                round_id = str(dialogue.get("round", "")).strip()
                if not round_id or round_id not in dataset.rounds:
                    continue
                round_payload = dataset.rounds[round_id]
                exchange = build_secom_exchange_text(
                    round_payload,
                    turn_idx=global_turn,
                    timestamp=timestamp,
                )
                global_turn += 1
                if not exchange:
                    continue
                exchanges.append(exchange)
                stored_rows.append(
                    {
                        "type": "stored_exchange",
                        "round_id": round_id,
                        "session_id": round_payload.get("session_id", session_id),
                        "timestamp": timestamp,
                        "text": exchange,
                    }
                )
            if exchanges:
                conversation_history.append(exchanges)
        return conversation_history, stored_rows

    def _ensure_initialized(self, dataset: MemoryBenchmarkDataset) -> None:
        dataset_id = id(dataset)
        if self._agent is not None and self._dataset_key == dataset_id:
            return

        self.runtime_info.update(validate_text_only_captions(dataset.rounds))
        self._debug_rows = []
        model_config = dict(self.config.get("_model_cfg", {}))
        self._agent = SeComAgent(self.config, model_config)

        conversation_history, stored_rows = self._build_conversation_history(dataset)
        self._debug_rows.extend(stored_rows)
        print(
            f"[SeCom] Building memory bank from {len(conversation_history)} sessions / "
            f"{sum(len(s) for s in conversation_history)} exchanges "
            f"(granularity={self._agent.granularity}, compress_rate={self._agent.compress_rate})..."
        )
        num_units = self._agent.build_memory(conversation_history)
        print(f"[SeCom] Memory ready: {num_units} units.")

        for idx, doc in enumerate(self._agent.secom.memory_bank):
            self._debug_rows.append(
                {
                    "type": "memory_unit",
                    "idx": idx,
                    "page_content": doc.page_content,
                    "content": _unit_to_text(doc.metadata.get("content", doc.page_content)),
                }
            )

        self._dataset_key = dataset_id
        self.runtime_info["num_exchanges"] = len(stored_rows)
        self.runtime_info["num_memory_units"] = num_units
        self.runtime_info["secom_root"] = str(self._agent.secom_root)
        self.runtime_info["secom_config"] = str(self._agent.config_path)
        self.runtime_info["granularity"] = self._agent.granularity
        self.runtime_info["compress_rate"] = self._agent.compress_rate
        self.runtime_info["retrieve_k"] = self._agent.retrieve_k
        self.runtime_info["debug_dir"] = str(self._debug_dir(dataset))
        self._flush_debug(dataset)

    def answer(
        self,
        dataset: MemoryBenchmarkDataset,
        qa: Dict[str, Any],
        question: str,
        answer_tag: str = "",
    ) -> str:
        self._ensure_initialized(dataset)
        assert self._agent is not None

        query = _question_with_image_caption(qa, question)
        prompt_mode = "mcq" if _is_mcq(qa) else "open"
        if not answer_tag.strip():
            answer_tag = prompt_mode

        context, memories = self._agent.retrieve(query)
        answer, answer_prompt = self._agent.answer_question(
            question, context, prompt_mode=prompt_mode
        )
        self._debug_rows.append(
            {
                "type": "qa",
                "question_id": qa.get("question_id", ""),
                "answer_tag": answer_tag,
                "prompt_mode": prompt_mode,
                "question": question,
                "recall_query": query,
                "retrieved_memories": memories,
                "answer_prompt": answer_prompt,
                "prediction": answer,
            }
        )
        self._flush_debug(dataset)
        return answer

    def build_history(self, dataset: MemoryBenchmarkDataset, qa: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
