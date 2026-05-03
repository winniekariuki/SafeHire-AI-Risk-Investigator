"""Chroma persistent client and collection helpers for evidence embeddings."""

from __future__ import annotations

from pathlib import Path

import chromadb
import chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 as _onnx_ef
from chromadb.api.models.Collection import Collection

# Keep ONNX model cache inside the repo (avoids ~/.cache permission issues in CI/sandbox).
_EMBED_ROOT = Path(__file__).resolve().parent / ".embedding_models"
_onnx_ef.ONNXMiniLM_L6_V2.DOWNLOAD_PATH = _EMBED_ROOT / _onnx_ef.ONNXMiniLM_L6_V2.MODEL_NAME

COLLECTION_NAME = "safehire_evidence"

_chroma_path = Path(__file__).resolve().parent / ".chroma"
_client: chromadb.PersistentClient | None = None


def get_chroma_path() -> Path:
    return _chroma_path


def get_client(persist_path: Path | None = None) -> chromadb.PersistentClient:
    """Return a persistent Chroma client (default under ``rag/.chroma``)."""
    global _client
    path = (persist_path or _chroma_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if persist_path is not None:
        return chromadb.PersistentClient(path=str(path))
    if _client is None:
        _client = chromadb.PersistentClient(path=str(path))
    return _client


def get_collection(
    *,
    client: chromadb.PersistentClient | None = None,
    reset: bool = False,
) -> Collection:
    c = client or get_client()
    if reset:
        try:
            c.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return c.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "SafeHire worker evidence chunks"},
    )
