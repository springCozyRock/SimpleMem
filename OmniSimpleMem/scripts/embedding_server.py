#!/usr/bin/env python3
"""
Shared text embedding HTTP server for OmniSimpleMem.

Loads sentence-transformers (e.g. BGE-M3) once on one GPU and serves
OpenAI-compatible POST /v1/embeddings so many cluster workers can share it.

Usage:
  CUDA_VISIBLE_DEVICES=4 \
  OMNI_EMBEDDING_MODEL=/path/to/BAAI__bge-m3 \
  OMNI_EMBEDDING_DIM=1024 \
  python scripts/embedding_server.py --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

import argparse
import os
import threading
import time
from typing import Any, Dict, List, Union

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = ""
    encoding_format: str = "float"


class EmbeddingServer:
    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = max(1, int(batch_size))
        self._lock = threading.Lock()
        self._model = None
        self._dim = 0
        self._load_count = 0
        self._call_count = 0
        self._total_texts = 0

    def load(self) -> None:
        from sentence_transformers import SentenceTransformer

        print(f"[embedding_server] loading model: {self.model_name}", flush=True)
        t0 = time.perf_counter()
        self._model = SentenceTransformer(self.model_name)
        # Probe dimension
        probe = self._model.encode(["ping"], normalize_embeddings=True)
        self._dim = int(probe.shape[-1])
        self._load_count += 1
        print(
            f"[embedding_server] ready dim={self._dim} "
            f"load_s={time.perf_counter() - t0:.1f}",
            flush=True,
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            raise RuntimeError("model not loaded")
        cleaned = [((t or "")[:8000] or " ") for t in texts]
        with self._lock:
            vectors = self._model.encode(
                cleaned,
                normalize_embeddings=True,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
            self._call_count += 1
            self._total_texts += len(cleaned)
        return [v.tolist() for v in vectors]

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok" if self._model is not None else "loading",
            "model": self.model_name,
            "embedding_dim": self._dim,
            "calls": self._call_count,
            "texts": self._total_texts,
        }


def build_app(server: EmbeddingServer) -> FastAPI:
    app = FastAPI(title="OmniSimpleMem Embedding Server", version="1.0.0")

    @app.get("/health")
    def health():
        return server.health()

    @app.post("/v1/embeddings")
    def create_embeddings(req: EmbeddingRequest):
        if isinstance(req.input, str):
            texts = [req.input]
        else:
            texts = list(req.input or [])
        if not texts:
            raise HTTPException(status_code=400, detail="input is empty")
        try:
            vectors = server.embed(texts)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        data = [
            {"object": "embedding", "index": i, "embedding": vec}
            for i, vec in enumerate(vectors)
        ]
        # Approximate token usage for client-side accounting.
        prompt_tokens = sum(max(1, len(t) // 4) for t in texts)
        return {
            "object": "list",
            "model": req.model or server.model_name,
            "data": data,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "total_tokens": prompt_tokens,
            },
        }

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniSimpleMem shared embedding server")
    parser.add_argument("--host", default=os.environ.get("OMNI_EMBEDDING_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OMNI_EMBEDDING_PORT", "8100")),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OMNI_EMBEDDING_MODEL", "BAAI/bge-m3"),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("OMNI_EMBEDDING_BATCH_SIZE", "32")),
    )
    args = parser.parse_args()

    server = EmbeddingServer(model_name=args.model, batch_size=args.batch_size)
    server.load()
    app = build_app(server)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
