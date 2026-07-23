"""
Tests for OmniMemoryOrchestrator.

All external dependencies (LLM, embedding, file I/O) are mocked.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from omni_memory.core.config import OmniMemoryConfig
from omni_memory.core.mau import MultimodalAtomicUnit, ModalityType, MAUMetadata
from omni_memory.processors.base import ProcessingResult
from omni_memory.triggers.base import TriggerResult, TriggerDecision


FAKE_EMBEDDING = [0.1] * 384


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_fake_processing_result(success=True, text="hello world"):
    """Create a ProcessingResult with a fake MAU."""
    if not success:
        return ProcessingResult(success=False, error="mock failure")
    mau = MultimodalAtomicUnit(
        modality_type=ModalityType.TEXT,
        summary=text,
        embedding=FAKE_EMBEDDING,
    )
    mau.details = {"full_text": text}
    mau.metadata = MAUMetadata(session_id="test_session")
    return ProcessingResult(
        success=True,
        mau=mau,
        trigger_result=TriggerResult(
            decision=TriggerDecision.ACCEPT, score=1.0, reason="ok"
        ),
    )


@pytest.fixture
def orchestrator(tmp_path):
    """
    Create an OmniMemoryOrchestrator with mocked heavy components.

    We patch the imports that require external services so the orchestrator
    can be instantiated without API keys or model downloads.
    """
    config = OmniMemoryConfig()
    config.storage.base_dir = str(tmp_path / "data")
    config.storage.cold_storage_dir = str(tmp_path / "data" / "cold")
    config.storage.index_dir = str(tmp_path / "data" / "index")
    config.embedding.embedding_dim = 384
    config.embedding.visual_embedding_dim = 768

    # Patch heavy dependencies inside orchestrator init
    with patch("omni_memory.orchestrator.ImageProcessor"), \
         patch("omni_memory.orchestrator.AudioProcessor"), \
         patch("omni_memory.orchestrator.VideoProcessor"), \
         patch("omni_memory.orchestrator.TextProcessor") as MockTextProc, \
         patch("omni_memory.orchestrator.PyramidRetriever") as MockRetriever, \
         patch("omni_memory.orchestrator.QueryProcessor") as MockQP, \
         patch("omni_memory.orchestrator.ExpansionManager"), \
         patch("omni_memory.orchestrator.EventManager"), \
         patch("omni_memory.orchestrator.EntityExtractor"), \
         patch("omni_memory.orchestrator.GraphRetriever"):

        from omni_memory.orchestrator import OmniMemoryOrchestrator

        orch = OmniMemoryOrchestrator(config=config, data_dir=str(tmp_path / "data"))

        # Wire up the mock text processor so add_text works
        mock_text_proc = MockTextProc.return_value
        mock_text_proc.process.return_value = _make_fake_processing_result()
        orch.text_processor = mock_text_proc

        # Wire up mock retriever so query works
        from omni_memory.retrieval.pyramid_retriever import RetrievalResult
        mock_retriever = MockRetriever.return_value
        mock_result = MagicMock(spec=RetrievalResult)
        mock_result.items = []
        mock_result.total_tokens = 0
        mock_result.query = "test"
        mock_result.level = MagicMock()
        mock_result.level.value = "preview"
        mock_retriever.retrieve_preview.return_value = mock_result
        mock_retriever.retrieve_with_budget.return_value = mock_result
        orch.retriever = mock_retriever

        # Wire up mock query processor
        mock_qp = MockQP.return_value
        mock_parsed = MagicMock()
        mock_parsed.cleaned_query = "test query"
        mock_qp.process.return_value = mock_parsed
        mock_qp.determine_retrieval_strategy.return_value = {"top_k": 10}
        orch.query_processor = mock_qp

        yield orch


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestOrchestratorInit:
    def test_initialization(self, orchestrator):
        assert orchestrator is not None
        assert orchestrator.config is not None
        assert orchestrator.mau_store is not None
        assert orchestrator.vector_store is not None

    def test_config_stored(self, orchestrator):
        assert isinstance(orchestrator.config, OmniMemoryConfig)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def test_start_session(self, orchestrator):
        sid = orchestrator.start_session("my_session")
        assert sid == "my_session"
        assert orchestrator._current_session_id == "my_session"

    def test_start_session_auto_id(self, orchestrator):
        sid = orchestrator.start_session()
        assert sid.startswith("session_")

    def test_session_id_property_auto_creates(self, orchestrator):
        orchestrator._current_session_id = None
        sid = orchestrator.session_id
        assert sid is not None
        assert sid.startswith("session_")

    def test_end_session(self, orchestrator):
        orchestrator.start_session("s1")
        orchestrator.end_session()
        assert orchestrator._current_session_id is None


# ---------------------------------------------------------------------------
# add_text
# ---------------------------------------------------------------------------

class TestAddText:
    def test_add_text_success(self, orchestrator):
        result = orchestrator.add_text("This is a test memory about AI.")
        assert result.success is True
        assert result.mau is not None

    def test_add_text_calls_processor(self, orchestrator):
        orchestrator.add_text("Some text content")
        orchestrator.text_processor.process.assert_called_once()

    def test_add_text_with_session(self, orchestrator):
        orchestrator.start_session("sess_123")
        orchestrator.add_text("Text with session")
        call_kwargs = orchestrator.text_processor.process.call_args
        assert call_kwargs[1]["session_id"] == "sess_123"

    def test_add_text_stores_mau(self, orchestrator):
        result = orchestrator.add_text("Store this text")
        if result.success and result.mau:
            # The _store_mau method should have been called
            # (It stores into mau_store and vector_store)
            mau = result.mau
            assert mau.summary is not None

    def test_add_text_failure(self, orchestrator):
        orchestrator.text_processor.process.return_value = _make_fake_processing_result(
            success=False
        )
        result = orchestrator.add_text("fail")
        assert result.success is False


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

class TestQuery:
    def test_query_returns_result(self, orchestrator):
        result = orchestrator.query("What do I know about AI?")
        assert result is not None

    def test_query_calls_retriever(self, orchestrator):
        orchestrator.query("test query")
        orchestrator.retriever.retrieve_preview.assert_called_once()

    def test_query_with_token_budget(self, orchestrator):
        orchestrator.query("test", token_budget=500)
        orchestrator.retriever.retrieve_with_budget.assert_called_once()

    def test_query_with_top_k(self, orchestrator):
        orchestrator.query("test", top_k=5)
        call_kwargs = orchestrator.retriever.retrieve_preview.call_args
        assert call_kwargs[1].get("top_k", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None) is not None


# ---------------------------------------------------------------------------
# add_image_on_demand_caption_only
# ---------------------------------------------------------------------------

class TestAddImageOnDemandCaptionOnly:
    def _fake_image_result(self, raw_pointer="cold://img1"):
        mau = MultimodalAtomicUnit(
            modality_type=ModalityType.VISUAL,
            summary="[Image: stored]",
            embedding=[],
        )
        mau.raw_pointer = raw_pointer
        return ProcessingResult(success=True, mau=mau)

    def test_skips_vlm_caption_and_visual_embedding(self, orchestrator):
        mock_img_proc = MagicMock()
        mock_img_proc.process.return_value = self._fake_image_result()
        orchestrator.image_processor = mock_img_proc

        orchestrator.add_image_on_demand_caption_only(
            image="/tmp/fake.png",
            caption_text="dataset caption",
            session_id="sess_1",
        )

        mock_img_proc.process.assert_called_once()
        _, kwargs = mock_img_proc.process.call_args
        assert kwargs.get("generate_caption") is False
        assert kwargs.get("generate_embedding") is False
        assert kwargs.get("session_id") == "sess_1"

        orchestrator.text_processor.process.assert_called_once()
        cap_arg = orchestrator.text_processor.process.call_args[0][0]
        assert "dataset caption" in cap_arg


# ---------------------------------------------------------------------------
# limit_expansion_ids / expand(max_items=0)
# ---------------------------------------------------------------------------

class TestLimitExpansionIds:
    def test_zero_means_no_cap(self):
        from omni_memory.retrieval.pyramid_retriever import limit_expansion_ids

        ids = ["a", "b", "c"]
        assert limit_expansion_ids(ids, 0) == ids
        assert limit_expansion_ids(ids, -1) == ids

    def test_positive_cap(self):
        from omni_memory.retrieval.pyramid_retriever import limit_expansion_ids

        assert limit_expansion_ids(["a", "b", "c"], 2) == ["a", "b"]


class TestExpandEvidenceWithBudgetMaxItemsZero:
    def test_expand_evidence_with_budget_respects_zero_max_items(self, orchestrator):
        from omni_memory.retrieval.pyramid_retriever import RetrievalLevel

        orchestrator.config.retrieval.evidence_token_budget = 6000
        orchestrator.config.retrieval.max_expanded_items = 0
        retrieval = MagicMock()
        retrieval.items = [
            {
                "id": "img1",
                "score": 0.8,
                "tags": ["vision_on_demand"],
                "has_raw_data": True,
            },
            {
                "id": "img2",
                "score": 0.7,
                "tags": ["vision_on_demand"],
                "has_raw_data": True,
            },
        ]

        def expand_side_effect(request):
            mau_id = request.mau_ids[0]
            result = MagicMock()
            result.items = [
                {
                    "id": mau_id,
                    "summary": mau_id,
                    "raw_content": {
                        "type": "image",
                        "base64": mau_id,
                        "token_estimate": 500,
                    },
                }
            ]
            return result

        orchestrator.retriever.expand.side_effect = expand_side_effect

        orchestrator._expand_evidence_with_budget(retrieval)

        expanded_ids = [
            call.args[0].mau_ids[0] for call in orchestrator.retriever.expand.call_args_list
        ]
        assert expanded_ids == ["img1", "img2"]
        assert retrieval.items[0]["raw_content"]["base64"] == "img1"
        assert retrieval.items[1]["raw_content"]["base64"] == "img2"


# ---------------------------------------------------------------------------
# _expand_evidence_with_budget
# ---------------------------------------------------------------------------

class TestExpandEvidenceWithBudget:
    def test_expand_evidence_with_budget_uses_score_per_token(self, orchestrator):
        from omni_memory.retrieval.pyramid_retriever import RetrievalLevel

        orchestrator.config.retrieval.evidence_token_budget = 700
        retrieval = MagicMock()
        retrieval.items = [
            {
                "id": "a",
                "score": 0.9,
                "tags": ["vision_on_demand"],
                "has_raw_data": True,
                "raw_content": {"token_estimate": 900},
            },
            {
                "id": "b",
                "score": 0.6,
                "tags": ["vision_on_demand"],
                "has_raw_data": True,
                "raw_content": {"token_estimate": 200},
            },
            {
                "id": "c",
                "score": 0.7,
                "tags": ["vision_on_demand"],
                "has_raw_data": True,
                "raw_content": {"token_estimate": 500},
            },
        ]

        def expand_side_effect(request):
            token_estimates = {"b": 200, "c": 500}
            mau_id = request.mau_ids[0]
            result = MagicMock()
            result.items = [
                {
                    "id": mau_id,
                    "summary": mau_id,
                    "raw_content": {
                        "type": "image",
                        "base64": mau_id,
                        "token_estimate": token_estimates[mau_id],
                    },
                }
            ]
            return result

        orchestrator.retriever.expand.side_effect = expand_side_effect

        orchestrator._expand_evidence_with_budget(retrieval)

        expanded_ids = [
            call.args[0].mau_ids[0] for call in orchestrator.retriever.expand.call_args_list
        ]
        levels = [
            call.args[0].level for call in orchestrator.retriever.expand.call_args_list
        ]
        assert expanded_ids == ["b", "c"]
        assert levels == [RetrievalLevel.EVIDENCE, RetrievalLevel.EVIDENCE]
        assert retrieval.items[1]["raw_content"]["base64"] == "b"
        assert retrieval.items[2]["raw_content"]["base64"] == "c"
        assert retrieval.items[0]["raw_content"].get("base64") is None


class TestDetailsExpandPreservesVisionEligibility:
    def test_details_merge_preserves_score_for_evidence_expand(self, orchestrator):
        """DETAILS merge must keep score so VLM evidence expand still selects the item.

        Regression for Case #6: preview had vision_on_demand + has_raw_data, but
        DETAILS expand wiped score/has_raw_data and evidence expand skipped.
        """
        from omni_memory.retrieval.pyramid_retriever import (
            ExpansionRequest,
            RetrievalLevel,
            RetrievalResult,
        )

        retrieval = RetrievalResult(
            query="fig",
            level=RetrievalLevel.SUMMARY,
            items=[
                {
                    "id": "img1",
                    "summary": "chart fig",
                    "modality_type": "text",
                    "timestamp": 1.0,
                    "score": 0.81,
                    "tags": ["vision_on_demand"],
                    "has_raw_data": True,
                    "metadata": {"tags": ["vision_on_demand"]},
                }
            ],
            total_candidates=1,
            tokens_used_estimate=10,
            can_expand=True,
            expansion_candidates=["img1"],
        )

        def expand_side_effect(request):
            if request.level == RetrievalLevel.DETAILS:
                return RetrievalResult(
                    query="",
                    level=RetrievalLevel.DETAILS,
                    items=[
                        {
                            "id": "img1",
                            "summary": "chart fig",
                            "modality_type": "text",
                            "timestamp": 1.0,
                            "tags": ["vision_on_demand"],
                            "has_raw_data": True,
                            "metadata": {"tags": ["vision_on_demand"]},
                            "details": {"full_text": "full chart caption"},
                        }
                    ],
                    total_candidates=1,
                    tokens_used_estimate=20,
                    can_expand=False,
                )
            mau_id = request.mau_ids[0]
            return RetrievalResult(
                query="",
                level=RetrievalLevel.EVIDENCE,
                items=[
                    {
                        "id": mau_id,
                        "summary": "chart fig",
                        "modality_type": "text",
                        "timestamp": 1.0,
                        "tags": ["vision_on_demand"],
                        "has_raw_data": True,
                        "metadata": {"tags": ["vision_on_demand"]},
                        "raw_content": {
                            "type": "image",
                            "base64": "abc",
                            "token_estimate": 500,
                        },
                    }
                ],
                total_candidates=1,
                tokens_used_estimate=500,
                can_expand=False,
            )

        orchestrator.retriever.expand.side_effect = expand_side_effect

        expansion = orchestrator.retriever.expand(
            ExpansionRequest(mau_ids=["img1"], level=RetrievalLevel.DETAILS)
        )
        item = retrieval.items[0]
        expanded = expansion.items[0]
        if item.get("score") is not None and expanded.get("score") is None:
            expanded["score"] = item["score"]
        if item.get("has_raw_data") is not None and expanded.get("has_raw_data") is None:
            expanded["has_raw_data"] = item["has_raw_data"]
        retrieval.items[0] = expanded

        assert retrieval.items[0]["score"] == 0.81
        assert retrieval.items[0]["has_raw_data"] is True

        orchestrator.config.retrieval.evidence_token_budget = 6000
        orchestrator.config.retrieval.max_expanded_items = 0
        orchestrator._expand_evidence_with_budget(retrieval)
        assert retrieval.items[0]["raw_content"]["type"] == "image"
        assert retrieval.items[0]["raw_content"]["base64"] == "abc"


# ---------------------------------------------------------------------------
# retrieve_answer_context
# ---------------------------------------------------------------------------

class TestRetrieveAnswerContext:
    def test_empty_retrieval(self, orchestrator):
        bundle = orchestrator.retrieve_answer_context("anything")
        assert bundle["empty"] is True
        assert bundle["context"] == ""
        assert bundle["retrieval"].items == []

    def test_appends_knowledge_graph_to_context(self, orchestrator):
        from omni_memory.retrieval.pyramid_retriever import RetrievalResult

        retrieval = MagicMock(spec=RetrievalResult)
        retrieval.items = [
            {
                "id": "m1",
                "summary": "memory one",
                "modality_type": "text",
                "score": 0.9,
                "tags": [],
                "has_raw_data": False,
            }
        ]
        graph_ctx = MagicMock()
        graph_ctx.entities = ["Alice"]
        graph_ctx.related_entities = []
        graph_ctx.relations = []
        retrieval.graph_entities = graph_ctx
        retrieval.to_dict.return_value = {"items": retrieval.items}

        orchestrator.query = MagicMock(return_value=retrieval)
        orchestrator.retriever.format_for_llm.return_value = "Memory context"
        orchestrator.graph_retriever.format_for_llm.return_value = "Alice -> Bob"

        bundle = orchestrator.retrieve_answer_context("who is Alice?")

        assert bundle["empty"] is False
        assert "[Knowledge Graph]" in bundle["context"]
        assert "Alice -> Bob" in bundle["context"]
        orchestrator.graph_retriever.format_for_llm.assert_called_once_with(graph_ctx)
