"""
API usage tracking for Omni-Memory.

Tracks chat/VLM and text-embedding calls (including local BGE-M3 counted as API tokens).
Phases: memory_construction | retrieval.
"""

from __future__ import annotations

import copy
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

PHASE_MEMORY_CONSTRUCTION = "memory_construction"
PHASE_RETRIEVAL = "retrieval"

KIND_CHAT = "chat"
KIND_TEXT_EMBEDDING = "text_embedding"

_EMPTY_COUNTER = {
    "api_calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "latency_ms": 0.0,
}


def _empty_bucket() -> Dict[str, Any]:
    return {
        "api_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "latency_ms": 0.0,
        "by_kind": {
            KIND_CHAT: dict(_EMPTY_COUNTER),
            KIND_TEXT_EMBEDDING: dict(_EMPTY_COUNTER),
        },
    }


def _add_into(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for key in ("api_calls", "prompt_tokens", "completion_tokens", "total_tokens"):
        dst[key] = int(dst.get(key, 0)) + int(src.get(key, 0))
    dst["latency_ms"] = float(dst.get("latency_ms", 0.0)) + float(src.get("latency_ms", 0.0))
    dst_kinds = dst.setdefault(
        "by_kind",
        {
            KIND_CHAT: dict(_EMPTY_COUNTER),
            KIND_TEXT_EMBEDDING: dict(_EMPTY_COUNTER),
        },
    )
    for kind, vals in (src.get("by_kind") or {}).items():
        bucket = dst_kinds.setdefault(kind, dict(_EMPTY_COUNTER))
        for key in ("api_calls", "prompt_tokens", "completion_tokens", "total_tokens"):
            bucket[key] = int(bucket.get(key, 0)) + int(vals.get(key, 0))
        bucket["latency_ms"] = float(bucket.get("latency_ms", 0.0)) + float(
            vals.get("latency_ms", 0.0)
        )


def _sub_bucket(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Return a - b for usage buckets (non-negative)."""
    out = _empty_bucket()
    for key in ("api_calls", "prompt_tokens", "completion_tokens", "total_tokens"):
        out[key] = max(0, int(a.get(key, 0)) - int(b.get(key, 0)))
    out["latency_ms"] = max(0.0, float(a.get("latency_ms", 0.0)) - float(b.get("latency_ms", 0.0)))
    for kind in (KIND_CHAT, KIND_TEXT_EMBEDDING):
        ak = (a.get("by_kind") or {}).get(kind, _EMPTY_COUNTER)
        bk = (b.get("by_kind") or {}).get(kind, _EMPTY_COUNTER)
        out["by_kind"][kind] = {
            "api_calls": max(0, int(ak.get("api_calls", 0)) - int(bk.get("api_calls", 0))),
            "prompt_tokens": max(
                0, int(ak.get("prompt_tokens", 0)) - int(bk.get("prompt_tokens", 0))
            ),
            "completion_tokens": max(
                0, int(ak.get("completion_tokens", 0)) - int(bk.get("completion_tokens", 0))
            ),
            "total_tokens": max(
                0, int(ak.get("total_tokens", 0)) - int(bk.get("total_tokens", 0))
            ),
            "latency_ms": max(
                0.0, float(ak.get("latency_ms", 0.0)) - float(bk.get("latency_ms", 0.0))
            ),
        }
    return out


def _split_scalar_bucket(bucket: Dict[str, Any], parts: int) -> list[Dict[str, Any]]:
    """Split numeric fields only (no nested by_kind)."""
    n = max(1, int(parts))
    if n == 1:
        return [
            {
                "api_calls": int(bucket.get("api_calls", 0)),
                "prompt_tokens": int(bucket.get("prompt_tokens", 0)),
                "completion_tokens": int(bucket.get("completion_tokens", 0)),
                "total_tokens": int(bucket.get("total_tokens", 0)),
                "latency_ms": float(bucket.get("latency_ms", 0.0)),
            }
        ]

    slices = [
        {
            "api_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0.0,
        }
        for _ in range(n)
    ]
    for key in ("api_calls", "prompt_tokens", "completion_tokens", "total_tokens"):
        total = int(bucket.get(key, 0))
        base, rem = divmod(total, n)
        for i in range(n):
            slices[i][key] = base + (1 if i < rem else 0)
    total_latency = float(bucket.get("latency_ms", 0.0))
    if total_latency:
        per = total_latency / n
        for i in range(n):
            slices[i]["latency_ms"] = per if i < n - 1 else total_latency - per * (n - 1)
    return slices


def split_usage_bucket(bucket: Dict[str, Any], parts: int) -> list[Dict[str, Any]]:
    """Split a usage bucket into ``parts`` slices that sum back to the original."""
    n = max(1, int(parts))
    scalar_slices = _split_scalar_bucket(bucket, n)
    if n == 1:
        return [copy.deepcopy(bucket)]

    slices = [_empty_bucket() for _ in range(n)]
    for i, scalar in enumerate(scalar_slices):
        for key, value in scalar.items():
            slices[i][key] = value
    for kind in (KIND_CHAT, KIND_TEXT_EMBEDDING):
        kind_bucket = (bucket.get("by_kind") or {}).get(kind, _EMPTY_COUNTER)
        kind_slices = _split_scalar_bucket(kind_bucket, n)
        for i in range(n):
            slices[i]["by_kind"][kind] = {
                **dict(_EMPTY_COUNTER),
                **kind_slices[i],
            }
    return slices


class UsageTracker:
    """Thread-safe cumulative usage tracker with phase tagging."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._phase_local = threading.local()
        self._totals = _empty_bucket()
        self._by_phase: Dict[str, Dict[str, Any]] = {
            PHASE_MEMORY_CONSTRUCTION: _empty_bucket(),
            PHASE_RETRIEVAL: _empty_bucket(),
        }
        self._by_session: Dict[str, Dict[str, Any]] = {}

    def _current_session(self) -> Optional[str]:
        return getattr(self._phase_local, "session_id", None)

    def _current_phase(self) -> Optional[str]:
        return getattr(self._phase_local, "phase", None)

    @contextmanager
    def session(self, session_id: str):
        prev = self._current_session()
        self._phase_local.session_id = session_id
        try:
            yield
        finally:
            self._phase_local.session_id = prev

    @contextmanager
    def phase(self, name: str):
        prev = self._current_phase()
        self._phase_local.phase = name
        try:
            yield
        finally:
            self._phase_local.phase = prev

    def reset(self) -> None:
        with self._lock:
            self._totals = _empty_bucket()
            self._by_phase = {
                PHASE_MEMORY_CONSTRUCTION: _empty_bucket(),
                PHASE_RETRIEVAL: _empty_bucket(),
            }
            self._by_session = {}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "totals": copy.deepcopy(self._totals),
                "by_phase": copy.deepcopy(self._by_phase),
                "by_session": copy.deepcopy(self._by_session),
            }

    def delta(self, before: Dict[str, Any]) -> Dict[str, Any]:
        after = self.snapshot()
        return {
            "totals": _sub_bucket(after["totals"], before.get("totals") or _empty_bucket()),
            "by_phase": {
                phase: _sub_bucket(
                    after["by_phase"].get(phase, _empty_bucket()),
                    (before.get("by_phase") or {}).get(phase, _empty_bucket()),
                )
                for phase in (PHASE_MEMORY_CONSTRUCTION, PHASE_RETRIEVAL)
            },
        }

    def _record(
        self,
        kind: str,
        *,
        api_calls: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        phase: Optional[str] = None,
    ) -> None:
        entry = {
            "api_calls": int(api_calls),
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "latency_ms": float(latency_ms),
            "by_kind": {
                kind: {
                    "api_calls": int(api_calls),
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(total_tokens),
                    "latency_ms": float(latency_ms),
                }
            },
        }
        phase_name = phase if phase is not None else self._current_phase()
        session_name = self._current_session()
        with self._lock:
            _add_into(self._totals, entry)
            if phase_name:
                bucket = self._by_phase.setdefault(phase_name, _empty_bucket())
                _add_into(bucket, entry)
            if (
                session_name
                and phase_name == PHASE_MEMORY_CONSTRUCTION
            ):
                session_bucket = self._by_session.setdefault(session_name, _empty_bucket())
                _add_into(session_bucket, entry)

    def record_chat(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: Optional[int] = None,
        latency_ms: float = 0.0,
        api_calls: int = 1,
        phase: Optional[str] = None,
    ) -> None:
        total = (
            int(total_tokens)
            if total_tokens is not None
            else int(prompt_tokens) + int(completion_tokens)
        )
        self._record(
            KIND_CHAT,
            api_calls=api_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            phase=phase,
        )

    def record_embedding(
        self,
        *,
        prompt_tokens: int = 0,
        latency_ms: float = 0.0,
        api_calls: int = 1,
        phase: Optional[str] = None,
    ) -> None:
        prompt = int(prompt_tokens)
        self._record(
            KIND_TEXT_EMBEDDING,
            api_calls=api_calls,
            prompt_tokens=prompt,
            completion_tokens=0,
            total_tokens=prompt,
            latency_ms=latency_ms,
            phase=phase,
        )


_TRACKER: Optional[UsageTracker] = None
_TRACKER_LOCK = threading.Lock()


def get_usage_tracker() -> UsageTracker:
    global _TRACKER
    if _TRACKER is None:
        with _TRACKER_LOCK:
            if _TRACKER is None:
                _TRACKER = UsageTracker()
    return _TRACKER


def reset_usage_tracker() -> UsageTracker:
    """Replace the process singleton (useful for tests / new clusters)."""
    global _TRACKER
    with _TRACKER_LOCK:
        _TRACKER = UsageTracker()
        return _TRACKER


def _extract_chat_usage(response: Any) -> Dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or 0) or (prompt + completion)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def _extract_embedding_usage(response: Any, fallback_tokens: int = 0) -> int:
    usage = getattr(response, "usage", None)
    if usage is not None:
        total = int(getattr(usage, "total_tokens", 0) or 0)
        if total:
            return total
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        if prompt:
            return prompt
    return int(fallback_tokens)


def wrap_openai_client(client: Any) -> Any:
    """
    Wrap an OpenAI client so chat.completions.create and embeddings.create
    record usage into the process UsageTracker.
    """
    if getattr(client, "_omni_usage_wrapped", False):
        return client

    tracker = get_usage_tracker()

    # --- chat.completions.create ---
    chat_completions = client.chat.completions
    original_chat_create = chat_completions.create

    def tracked_chat_create(*args, **kwargs):
        t0 = time.perf_counter()
        response = original_chat_create(*args, **kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        usage = _extract_chat_usage(response)
        tracker.record_chat(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            latency_ms=latency_ms,
            api_calls=1,
        )
        return response

    chat_completions.create = tracked_chat_create  # type: ignore[method-assign]

    client._omni_usage_wrapped = True
    return client


def count_text_embedding_tokens(tokenizer: Any, texts: list, max_seq_length: Optional[int] = None) -> int:
    """Count tokens for texts that will be embedded (after char truncate elsewhere)."""
    if not texts:
        return 0
    total = 0
    max_len = max_seq_length
    for text in texts:
        kwargs: Dict[str, Any] = {
            "add_special_tokens": True,
            "truncation": True,
        }
        if max_len is not None and max_len > 0:
            kwargs["max_length"] = int(max_len)
        encoded = tokenizer(text, **kwargs)
        ids = encoded["input_ids"] if hasattr(encoded, "__getitem__") else None
        if ids is None:
            continue
        # BatchEncoding may wrap a single sequence or a batch
        if ids and isinstance(ids[0], (list, tuple)):
            total += sum(len(x) for x in ids)
        else:
            total += len(ids)
    return total
