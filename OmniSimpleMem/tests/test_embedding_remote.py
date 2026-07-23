"""Tests for remote embedding backend (shared HTTP server)."""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omni_memory.core.config import OmniMemoryConfig, EmbeddingConfig
from omni_memory.utils.embedding import EmbeddingService


class TestRemoteEmbeddingBackend:
    def test_detect_remote_from_config(self):
        cfg = OmniMemoryConfig(
            embedding=EmbeddingConfig(
                model_name="/tmp/fake-bge",
                embedding_dim=1024,
                server_url="http://127.0.0.1:8100",
            )
        )
        svc = EmbeddingService(cfg)
        assert svc._detect_text_backend() == "remote"
        assert svc._should_use_local() is False

    def test_detect_remote_from_env(self):
        cfg = OmniMemoryConfig(embedding=EmbeddingConfig(model_name="BAAI/bge-m3"))
        with patch.dict(os.environ, {"OMNI_EMBEDDING_SERVER_URL": "http://127.0.0.1:9100/"}, clear=False):
            svc = EmbeddingService(cfg)
            assert svc._server_url == "http://127.0.0.1:9100"
            assert svc._detect_text_backend() == "remote"

    def test_embed_text_calls_remote(self):
        cfg = OmniMemoryConfig(
            embedding=EmbeddingConfig(
                model_name="bge",
                embedding_dim=4,
                server_url="http://127.0.0.1:8100",
            )
        )
        svc = EmbeddingService(cfg)
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = {
            "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}],
            "usage": {"prompt_tokens": 3, "total_tokens": 3},
        }
        fake_client = MagicMock()
        fake_client.post.return_value = fake_resp
        svc._http_client = fake_client

        out = svc.embed_text("hello world")
        assert out == [0.1, 0.2, 0.3, 0.4]
        fake_client.post.assert_called_once()
        args, kwargs = fake_client.post.call_args
        assert args[0] == "http://127.0.0.1:8100/v1/embeddings"
        assert kwargs["json"]["input"] == "hello world"

    def test_embed_batch_remote(self):
        cfg = OmniMemoryConfig(
            embedding=EmbeddingConfig(server_url="http://127.0.0.1:8100", embedding_dim=2)
        )
        svc = EmbeddingService(cfg)
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }
        fake_client = MagicMock()
        fake_client.post.return_value = fake_resp
        svc._http_client = fake_client

        out = svc.embed_texts_batch(["a", "b"])
        assert out == [[0.1, 0.2], [0.3, 0.4]]
