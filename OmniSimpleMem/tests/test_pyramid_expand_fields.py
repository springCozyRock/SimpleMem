"""Regression: DETAILS expand must keep vision_on_demand eligibility fields."""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omni_memory.core.mau import MAUMetadata, ModalityType, MultimodalAtomicUnit
from omni_memory.retrieval.pyramid_retriever import (
    ExpansionRequest,
    PyramidRetriever,
    RetrievalLevel,
    mau_has_on_demand_raw,
)


def test_details_expand_sets_has_raw_data_for_vision_on_demand():
    mau = MultimodalAtomicUnit(
        modality_type=ModalityType.TEXT,
        summary="chart",
        embedding=[0.1] * 8,
    )
    mau.id = "mau_img"
    mau.timestamp = 1.0
    mau.details = {"full_text": "caption"}
    mau.raw_pointer = "/tmp/chart.png"
    mau.region_pointers = ["/tmp/chart.png"]
    mau.metadata = MAUMetadata(session_id="s", tags=["vision_on_demand"])

    mau_store = MagicMock()
    mau_store.get.return_value = mau
    cold = MagicMock()
    retriever = PyramidRetriever(
        mau_store=mau_store,
        vector_store=MagicMock(),
        cold_storage=cold,
    )

    assert mau_has_on_demand_raw(mau) is True

    result = retriever.expand(
        ExpansionRequest(mau_ids=["mau_img"], level=RetrievalLevel.DETAILS)
    )
    assert len(result.items) == 1
    item = result.items[0]
    assert item["has_raw_data"] is True
    assert "vision_on_demand" in item["tags"]
    assert "details" in item
    assert "score" not in item  # score still comes from preview merge
