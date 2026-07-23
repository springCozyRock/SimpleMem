"""Omni-Memory configuration dataclasses (vendored stopgap for upstream)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


def _filter_kwargs(cls: Type[T], data: Dict[str, Any]) -> Dict[str, Any]:
    valid = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in valid}


@dataclass
class EmbeddingConfig:
    model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    batch_size: int = 32
    visual_embedding_model: str = "UCSC-VLAA/openvision-vit-large-patch14-224"
    visual_embedding_dim: int = 768
    api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    # Shared embedding HTTP service (OpenAI-compatible /v1/embeddings).
    # When set, text embeddings are fetched remotely and no local BGE is loaded.
    server_url: Optional[str] = None
    server_timeout_s: float = 120.0


@dataclass
class RetrievalConfig:
    default_top_k: int = 10
    enable_hybrid_search: bool = True
    enable_graph_traversal: bool = True
    enable_multi_query_retrieval: bool = False
    auto_expand_threshold: float = 0.85
    evidence_token_budget: int = 6000
    max_expanded_items: int = 5
    evidence_token_budget: int = 6000
    # Pyramid retrieval: preview returns summary only; full_text loads on DETAILS expand.
    include_details_in_preview: bool = True


@dataclass
class StorageConfig:
    base_dir: str = "./omni_memory_data"
    cold_storage_dir: str = "./omni_memory_data/cold_storage"
    index_dir: str = "./omni_memory_data/index"
    use_s3: bool = False
    s3_bucket: str = ""
    organize_by_date: bool = True
    organize_by_modality: bool = True


@dataclass
class LLMConfig:
    summary_model: str = "gpt-4o-mini"
    query_model: str = "gpt-4o-mini"
    caption_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    temperature: float = 0.0
    max_tokens: int = 1000
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None


@dataclass
class EventConfig:
    auto_create_events: bool = True
    event_time_window_seconds: float = 300.0
    summarize_on_close: bool = True
    max_maus_for_summary: int = 20


@dataclass
class EntropyTriggerConfig:
    visual_similarity_threshold_high: float = 0.9
    visual_similarity_threshold_low: float = 0.7
    enable_visual_trigger: bool = True
    enable_audio_trigger: bool = True
    visual_encoder: str = "clip"
    visual_model_name: str = "UCSC-VLAA/openvision-vit-large-patch14-224"
    audio_energy_threshold: float = 0.01
    audio_vad_threshold: float = 0.5
    audio_min_speech_duration_ms: int = 500


@dataclass
class RouterConfig:
    router_mode: str = "off"
    benchmark_safe: bool = False
    gini_threshold: float = 0.65
    top1_threshold: float = 0.75
    gap_threshold: float = 0.15
    episodic_margin: float = 0.1
    close_margin: float = 0.05
    shadow_mode: bool = True


@dataclass
class OmniMemoryConfig:
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    event: EventConfig = field(default_factory=EventConfig)
    entropy_trigger: EntropyTriggerConfig = field(default_factory=EntropyTriggerConfig)
    router: RouterConfig = field(default_factory=RouterConfig)
    debug_mode: bool = False
    log_level: str = "INFO"
    enable_self_evolution: bool = False
    evolution: Optional[Any] = None

    def __post_init__(self) -> None:
        if not self.llm.api_key:
            self.llm.api_key = os.getenv("OPENAI_API_KEY")
        if not self.llm.api_base_url:
            self.llm.api_base_url = os.getenv("OPENAI_API_BASE")
        if not self.embedding.server_url:
            env_url = (os.getenv("OMNI_EMBEDDING_SERVER_URL") or "").strip()
            if env_url:
                self.embedding.server_url = env_url.rstrip("/")

    @classmethod
    def create_default(cls) -> "OmniMemoryConfig":
        return cls()

    def set_unified_model(self, model_name: str) -> "OmniMemoryConfig":
        self.llm.summary_model = model_name
        self.llm.query_model = model_name
        self.llm.caption_model = model_name
        return self

    def enable_evolution(self) -> "OmniMemoryConfig":
        from omni_memory.evolution.evolution_config import EvolutionConfig

        self.enable_self_evolution = True
        if self.evolution is None:
            self.evolution = EvolutionConfig()
        return self

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "embedding": asdict(self.embedding),
            "retrieval": asdict(self.retrieval),
            "storage": asdict(self.storage),
            "llm": asdict(self.llm),
            "event": asdict(self.event),
            "entropy_trigger": asdict(self.entropy_trigger),
            "router": asdict(self.router),
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "enable_self_evolution": self.enable_self_evolution,
        }
        if self.evolution is not None and hasattr(self.evolution, "to_dict"):
            payload["evolution"] = self.evolution.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OmniMemoryConfig":
        return cls(
            embedding=EmbeddingConfig(**_filter_kwargs(EmbeddingConfig, data.get("embedding", {}))),
            retrieval=RetrievalConfig(**_filter_kwargs(RetrievalConfig, data.get("retrieval", {}))),
            storage=StorageConfig(**_filter_kwargs(StorageConfig, data.get("storage", {}))),
            llm=LLMConfig(**_filter_kwargs(LLMConfig, data.get("llm", {}))),
            event=EventConfig(**_filter_kwargs(EventConfig, data.get("event", {}))),
            entropy_trigger=EntropyTriggerConfig(
                **_filter_kwargs(EntropyTriggerConfig, data.get("entropy_trigger", {}))
            ),
            router=RouterConfig(**_filter_kwargs(RouterConfig, data.get("router", {}))),
            debug_mode=bool(data.get("debug_mode", False)),
            log_level=str(data.get("log_level", "INFO")),
            enable_self_evolution=bool(data.get("enable_self_evolution", False)),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "OmniMemoryConfig":
        return cls.from_dict(json.loads(json_str))

    def save_to_file(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_file(cls, filepath: str) -> "OmniMemoryConfig":
        return cls.from_json(Path(filepath).read_text(encoding="utf-8"))

    def ensure_directories(self) -> None:
        for raw in (
            self.storage.base_dir,
            self.storage.cold_storage_dir,
            self.storage.index_dir,
        ):
            Path(raw).mkdir(parents=True, exist_ok=True)
