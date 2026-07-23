"""Unit tests for OmniSimpleMem SMMBench ingest helpers."""

from __future__ import annotations

import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1]
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from agents.OmniSimpleMem.omni_simplemem_agent import OmniSimpleMemAgent  # noqa: E402


def _make_agent(tmp_path: Path) -> OmniSimpleMemAgent:
    args = SimpleNamespace(
        dataset_dir_path=str(tmp_path / "cluster_1"),
        output_dir=str(tmp_path / "out"),
        save_dir_name="cluster_1",
        eval_format="multiple_choice",
        omnisimplemem_baseline_root="",
        omnisimplemem_runtime_root="",
        omnisimplemem_top_k=20,
        omnisimplemem_embedding_model="all-MiniLM-L6-v2",
        omnisimplemem_embedding_dim=384,
        omnisimplemem_visual_embedding_model="UCSC-VLAA/openvision-vit-large-patch14-224",
        omnisimplemem_visual_embedding_dim=768,
        omnisimplemem_chunk_turns=100,
        omnisimplemem_chunk_max_chars=100000,
        omnisimplemem_chunk_max_images=100,
        model="test-model",
        temperature=0.0,
    )
    (tmp_path / "cluster_1").mkdir(parents=True, exist_ok=True)
    return OmniSimpleMemAgent(client=MagicMock(), args=args)


def _text_turn(content: str, conversation_name: str, *, sender: str = "user") -> dict:
    return {
        "content_type": "text",
        "content": content,
        "conversation_name": conversation_name,
        "sender_name": sender,
        "timestamp": "2024-01-01T00:00:00",
    }


class TestBuildConfig:
    def test_memeye_aligned_retrieval_defaults(self, tmp_path):
        agent = _make_agent(tmp_path)
        config = agent._build_config()
        assert config.retrieval.enable_hybrid_search is True
        assert config.retrieval.enable_graph_traversal is True
        assert config.retrieval.enable_multi_query_retrieval is False
        assert config.retrieval.include_details_in_preview is False
        assert config.retrieval.auto_expand_threshold == 0.4
        assert config.retrieval.max_expanded_items == 5
        assert config.enable_self_evolution is False
        assert config.event.summarize_on_close is False

    def test_default_top_k_is_20(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent.top_k == 20


class TestStoreRoundMemeyeStyle:
    def test_single_mau_with_multi_image_pointers(self, tmp_path):
        agent = _make_agent(tmp_path)
        mock_orch = MagicMock()
        mau = MagicMock()
        mock_orch.add_text.return_value = SimpleNamespace(success=True, mau=mau)
        mock_orch.mau_store.update.return_value = True
        agent._orchestrator = mock_orch

        round_item = {
            "text": "user: look at these figures",
            "tags": ["content_type:image"],
            "image_items": [
                {"image_path": "/tmp/a.png", "caption": "first"},
                {"image_path": "/tmp/b.png", "caption": "second"},
            ],
        }
        status = agent._store_round_memeye_style(round_item, session_id="sess_1")

        assert status == "stored"
        mock_orch.add_text.assert_called_once()
        text_arg = mock_orch.add_text.call_args[0][0]
        assert "image_caption: first" in text_arg
        assert "image_caption: second" in text_arg
        assert mau.raw_pointer == "/tmp/a.png"
        assert mau.region_pointers == ["/tmp/a.png", "/tmp/b.png"]
        mock_orch.mau_store.update.assert_called_once_with(mau)
        assert agent._stored_text_items == 1
        assert agent._stored_image_items == 2

    def test_skipped_when_add_text_rejected(self, tmp_path):
        agent = _make_agent(tmp_path)
        mock_orch = MagicMock()
        mock_orch.add_text.return_value = SimpleNamespace(success=False, mau=None)
        agent._orchestrator = mock_orch

        status = agent._store_round_memeye_style(
            {"text": "hello", "image_items": [], "tags": []},
            session_id="sess_1",
        )
        assert status == "skipped"
        assert agent._stored_text_items == 0


class TestBuildIngestRounds:
    def test_group_chat_one_turn_per_round(self, tmp_path):
        agent = _make_agent(tmp_path)
        conversations = [
            _text_turn("alpha", "group_chat_1"),
            _text_turn("beta", "group_chat_1"),
        ]
        rounds = agent._build_ingest_rounds(conversations)
        assert len(rounds) == 2
        assert rounds[0]["session_id"] == "group_chat_1"
        assert "alpha" in rounds[0]["text"]
        assert "beta" in rounds[1]["text"]

    def test_user_assistant_pairs_user_and_assistant(self, tmp_path):
        agent = _make_agent(tmp_path)
        conversations = [
            _text_turn("question", "user_assistant_1", sender="user"),
            _text_turn("answer", "user_assistant_1", sender="assistant"),
            _text_turn("solo", "group_chat_2"),
        ]
        rounds = agent._build_ingest_rounds(conversations)
        assert len(rounds) == 2
        assert rounds[0]["session_id"] == "user_assistant_1"
        assert rounds[0]["turn_count"] == 2
        assert "question" in rounds[0]["text"]
        assert "answer" in rounds[0]["text"]
        assert rounds[1]["session_id"] == "group_chat_2"


class TestBuildMemoryBm25:
    def test_builds_bm25_after_ingest(self, tmp_path, monkeypatch):
        agent = _make_agent(tmp_path)
        mock_orch = MagicMock()
        mock_orch.add_text.return_value = SimpleNamespace(success=True, mau=MagicMock())
        mock_orch.mau_store.update.return_value = True
        mock_orch.build_bm25_index.return_value = 3
        agent._orchestrator = mock_orch

        tracker = MagicMock()
        tracker.phase.return_value = nullcontext()
        tracker.session.return_value = nullcontext()
        tracker.snapshot.return_value = {"by_phase": {}, "totals": {}, "by_session": {}}

        monkeypatch.setattr(agent, "_reset_runtime_state", lambda: None)
        monkeypatch.setattr(
            agent,
            "_bootstrap_omni",
            lambda: (MagicMock(return_value=mock_orch), MagicMock()),
        )
        monkeypatch.setattr(agent, "_build_config", lambda: MagicMock())
        monkeypatch.setattr(
            agent,
            "_build_ingest_rounds",
            lambda _conversations: [
                {
                    "text": "hello",
                    "image_items": [],
                    "tags": [],
                    "turn_count": 1,
                    "char_count": 5,
                    "image_count": 0,
                    "session_id": "sess_a",
                }
            ],
        )
        monkeypatch.setattr(
            agent,
            "_store_round_memeye_style",
            lambda _round_item, session_id: "stored",
        )
        monkeypatch.setattr(
            agent,
            "_usage_helpers",
            lambda: {
                "reset_usage_tracker": lambda: tracker,
                "PHASE_MEMORY_CONSTRUCTION": "memory_construction",
            },
        )
        monkeypatch.setattr(agent, "_write_usage_json", lambda *_a, **_k: None)
        monkeypatch.setattr(agent, "_write_usage_by_session", lambda: None)

        agent.build_memory([_text_turn("hello", "sess_a")], None, [])

        mock_orch.build_bm25_index.assert_called_once()


class TestSkipIngest:
    def test_reuse_existing_memory_skips_reset_and_store(self, tmp_path, monkeypatch):
        agent = _make_agent(tmp_path)
        agent.args.omnisimplemem_skip_ingest = True
        agent.runtime_root = tmp_path / "ckpt"
        mau_dir = agent.runtime_root / "index" / "mau_store"
        mau_dir.mkdir(parents=True)
        (mau_dir / "mau_2026-07-21.jsonl").write_text(
            '{"id":"mau_1","modality_type":"text","metadata":{"tags":["vision_on_demand"]}}\n',
            encoding="utf-8",
        )

        mock_orch = MagicMock()
        mock_orch.mau_store._id_index = {"mau_1": str(mau_dir / "mau_2026-07-21.jsonl")}
        mock_mau = MagicMock()
        mock_mau.metadata.tags = ["vision_on_demand"]
        mock_orch.mau_store.get.return_value = mock_mau
        mock_orch.build_bm25_index.return_value = 1

        tracker = MagicMock()
        tracker.phase.return_value = nullcontext()
        tracker.session.return_value = nullcontext()
        tracker.snapshot.return_value = {"by_phase": {}, "totals": {}, "by_session": {}}

        reset_called = {"n": 0}
        store_called = {"n": 0}

        monkeypatch.setattr(
            agent,
            "_reset_runtime_state",
            lambda: reset_called.__setitem__("n", reset_called["n"] + 1),
        )
        monkeypatch.setattr(
            agent,
            "_store_round_memeye_style",
            lambda *_a, **_k: store_called.__setitem__("n", store_called["n"] + 1) or "stored",
        )
        monkeypatch.setattr(
            agent,
            "_bootstrap_omni",
            lambda: (MagicMock(return_value=mock_orch), MagicMock()),
        )
        monkeypatch.setattr(agent, "_build_config", lambda: MagicMock())
        monkeypatch.setattr(
            agent,
            "_build_ingest_rounds",
            lambda _conversations: [
                {
                    "text": "hello",
                    "image_items": [],
                    "tags": [],
                    "turn_count": 1,
                    "char_count": 5,
                    "image_count": 0,
                    "session_id": "sess_a",
                }
            ],
        )
        monkeypatch.setattr(
            agent,
            "_usage_helpers",
            lambda: {
                "reset_usage_tracker": lambda: tracker,
                "PHASE_MEMORY_CONSTRUCTION": "memory_construction",
            },
        )
        monkeypatch.setattr(agent, "_write_usage_json", lambda *_a, **_k: None)
        monkeypatch.setattr(agent, "_write_usage_by_session", lambda: None)

        agent.build_memory([_text_turn("hello", "sess_a")], None, [])

        assert reset_called["n"] == 0
        assert store_called["n"] == 0
        mock_orch.build_bm25_index.assert_called_once()
        assert agent._orchestrator is mock_orch
        assert agent._stored_image_items == 1

    def test_skip_ingest_requires_checkpoint(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.args.omnisimplemem_skip_ingest = True
        agent.runtime_root = tmp_path / "empty_ckpt"
        agent.runtime_root.mkdir(parents=True)
        with pytest.raises(RuntimeError, match="no MAU checkpoint"):
            agent.build_memory([], None, [])


class TestQaRelatedSessions:
    def test_extracts_conversation_names_from_evidence_assignment(self):
        qa = {
            "id": "qa1",
            "evidence_assignment": {
                "text_evidence_assignment": [
                    {"conversation_name": "group_chat_a", "insert_conversation_turn": 1}
                ],
                "image_evidence_assignment": [
                    {"conversation_name": "user_assistant_b", "insert_conversation_turn": 2}
                ],
            },
        }
        assert OmniSimpleMemAgent._qa_related_sessions(qa) == [
            "group_chat_a",
            "user_assistant_b",
        ]

    def test_empty_assignment_returns_empty_list(self):
        assert OmniSimpleMemAgent._qa_related_sessions({"id": "qa2"}) == []


class TestQaImageRefs:
    def test_prefers_top_level_images(self):
        qa = {
            "images": ["top.png"],
            "evidence": {"image_evidence": ["ev.png"]},
        }
        assert OmniSimpleMemAgent._qa_image_refs(qa) == ["top.png"]

    def test_falls_back_to_evidence_image_evidence(self):
        qa = {"evidence": {"image_evidence": ["M3_bench_495d8d17.png", ""]}}
        assert OmniSimpleMemAgent._qa_image_refs(qa) == ["M3_bench_495d8d17.png"]

    def test_empty_when_missing(self):
        assert OmniSimpleMemAgent._qa_image_refs({}) == []


class TestFunctionCallContextParts:
    def test_keeps_text_and_non_text_parts(self):
        bundle = {
            "context": "memory summary",
            "user_content": [
                {"type": "text", "text": "Based on these memories..."},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,abc"},
                },
            ],
        }
        parts = OmniSimpleMemAgent._function_call_context_parts(bundle)
        assert parts[0] == {"type": "text", "text": "memory summary"}
        assert parts[1]["type"] == "image_url"
        assert len(parts) == 2

    def test_empty_context_placeholder(self):
        parts = OmniSimpleMemAgent._function_call_context_parts(
            {"context": "", "user_content": "plain"}
        )
        assert parts == [{"type": "text", "text": "(no retrieved memories)"}]


class TestFunctionCallWiring:
    def test_fc_uses_retrieve_answer_context_and_multimodal_prompt(
        self, tmp_path, monkeypatch
    ):
        agent = _make_agent(tmp_path)
        img = tmp_path / "qa.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

        retrieval = SimpleNamespace(
            items=[
                {
                    "id": "mau_1",
                    "summary": "a place photo",
                    "modality_type": "text",
                    "raw_content": {
                        "type": "image",
                        "base64": "abc",
                        "pointer": str(img),
                    },
                }
            ],
            to_dict=lambda: {"items": [{"id": "mau_1"}], "total_candidates": 1},
        )
        bundle = {
            "context": "retrieved memory about Niagara",
            "user_content": [
                {"type": "text", "text": "Based on these memories..."},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,qq"},
                },
            ],
            "retrieval": retrieval,
            "empty": False,
        }
        mock_orch = MagicMock()
        mock_orch.retrieve_answer_context.return_value = bundle
        agent._orchestrator = mock_orch
        agent._function_call_candidate_tools = [
            {"function_name": "GOOGLE_MAPS_geocode", "function_comment": "geocode"}
        ]

        class _Tracker:
            def phase(self, *_a, **_k):
                return nullcontext()

            def snapshot(self):
                return {}

            def delta(self, _before):
                return {"by_phase": {}, "totals": {}}

        monkeypatch.setattr(
            agent,
            "_usage_helpers",
            lambda: {
                "get_usage_tracker": lambda: _Tracker(),
                "PHASE_RETRIEVAL": "retrieval",
            },
        )
        monkeypatch.setattr(agent, "_accumulate_retrieval_by_session", lambda *_a, **_k: None)
        monkeypatch.setattr(
            "agents.OmniSimpleMem.omni_simplemem_agent.get_response",
            lambda *_a, **_k: '{"calls": []}',
        )
        monkeypatch.setattr(
            "agents.OmniSimpleMem.omni_simplemem_agent.evaluate_function_call_response",
            lambda *_a, **_k: (False, []),
        )

        qa = {
            "id": "FC_sample_495d8d17",
            "category": "Function_Call",
            "question": "Based on Fig. ad0d90b0, geocode both places",
            "answer": [],
            "evidence": {"image_evidence": [str(img)]},
            "multi_choice_QA": {},
        }
        readable, read_message = agent.evaluate_single_qa(qa, [], None)

        mock_orch.retrieve_answer_context.assert_called_once()
        call_kwargs = mock_orch.retrieve_answer_context.call_args.kwargs
        assert call_kwargs["include_on_demand_images"] is True
        assert call_kwargs["question_images"] == [str(img.resolve())]

        msgs = read_message["messages"]["answer_messages"]
        assert msgs is not None
        user_content = msgs[1]["content"]
        assert isinstance(user_content, list)
        assert any(p.get("type") == "image_url" for p in user_content)
        assert read_message["messages"]["query_image_used"] is True
        assert read_message["messages"]["retrieval_result"]["items"][0]["id"] == "mau_1"
        assert readable["category"] == "Function_Call"
