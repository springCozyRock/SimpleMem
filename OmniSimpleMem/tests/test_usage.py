"""Tests for omni_memory.utils.usage UsageTracker."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omni_memory.utils.usage import (
    PHASE_MEMORY_CONSTRUCTION,
    PHASE_RETRIEVAL,
    UsageTracker,
    _empty_bucket,
)


class TestUsageTrackerBySession:
    def test_by_session_only_in_memory_construction_phase(self):
        tracker = UsageTracker()
        with tracker.phase(PHASE_RETRIEVAL):
            with tracker.session("sess_a"):
                tracker.record_chat(prompt_tokens=10, completion_tokens=5)
        snap = tracker.snapshot()
        assert snap["by_session"] == {}

    def test_by_session_accumulates_per_session(self):
        tracker = UsageTracker()
        with tracker.phase(PHASE_MEMORY_CONSTRUCTION):
            with tracker.session("sess_a"):
                tracker.record_chat(prompt_tokens=100, completion_tokens=20)
                tracker.record_embedding(prompt_tokens=50)
            with tracker.session("sess_b"):
                tracker.record_chat(prompt_tokens=30, completion_tokens=10)

        snap = tracker.snapshot()
        by_session = snap["by_session"]
        assert set(by_session) == {"sess_a", "sess_b"}

        a = by_session["sess_a"]
        assert a["prompt_tokens"] == 150
        assert a["completion_tokens"] == 20
        assert a["total_tokens"] == 170
        assert a["api_calls"] == 2
        assert a["by_kind"]["chat"]["prompt_tokens"] == 100
        assert a["by_kind"]["text_embedding"]["prompt_tokens"] == 50

        b = by_session["sess_b"]
        assert b["prompt_tokens"] == 30
        assert b["completion_tokens"] == 10
        assert b["total_tokens"] == 40
        assert b["api_calls"] == 1

    def test_by_session_matches_hand_sum(self):
        tracker = UsageTracker()
        with tracker.phase(PHASE_MEMORY_CONSTRUCTION):
            sessions = [("s1", 10, 2), ("s2", 20, 4), ("s1", 5, 1)]
            for sid, prompt, completion in sessions:
                with tracker.session(sid):
                    tracker.record_chat(prompt_tokens=prompt, completion_tokens=completion)

        snap = tracker.snapshot()
        hand = _empty_bucket()
        for sid, prompt, completion in sessions:
            bucket = snap["by_session"][sid]
            from omni_memory.utils.usage import _add_into

            _add_into(
                hand,
                {
                    "api_calls": 1,
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "total_tokens": prompt + completion,
                    "latency_ms": 0.0,
                    "by_kind": {
                        "chat": {
                            "api_calls": 1,
                            "prompt_tokens": prompt,
                            "completion_tokens": completion,
                            "total_tokens": prompt + completion,
                            "latency_ms": 0.0,
                        }
                    },
                },
            )

        s1 = snap["by_session"]["s1"]
        assert s1["prompt_tokens"] == 15
        assert s1["completion_tokens"] == 3
        assert s1["total_tokens"] == 18

        phase_total = snap["by_phase"][PHASE_MEMORY_CONSTRUCTION]
        assert phase_total["prompt_tokens"] == sum(p for _, p, _ in sessions)
        assert phase_total["completion_tokens"] == sum(c for _, _, c in sessions)


class TestSplitUsageBucket:
    def test_split_preserves_total(self):
        from omni_memory.utils.usage import split_usage_bucket

        bucket = {
            "api_calls": 3,
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "total_tokens": 140,
            "latency_ms": 30.0,
            "by_kind": {
                "chat": {
                    "api_calls": 2,
                    "prompt_tokens": 80,
                    "completion_tokens": 40,
                    "total_tokens": 120,
                    "latency_ms": 20.0,
                },
                "text_embedding": {
                    "api_calls": 1,
                    "prompt_tokens": 20,
                    "completion_tokens": 0,
                    "total_tokens": 20,
                    "latency_ms": 10.0,
                },
            },
        }
        parts = split_usage_bucket(bucket, 3)
        assert len(parts) == 3
        assert sum(p["prompt_tokens"] for p in parts) == 100
        assert sum(p["completion_tokens"] for p in parts) == 40
        assert sum(p["total_tokens"] for p in parts) == 140
        assert sum(p["api_calls"] for p in parts) == 3

