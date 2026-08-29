"""Embedding service using sentence-transformers.

Default model: all-MiniLM-L6-v2 (384 dimensions)
  — runs fully locally, no API key required
  — ~80 MB download on first use
  — ~0.5 ms per sentence on CPU

Caching strategy:
  Before generating a new embedding, check if the evidence_document row
  already has an embedding AND the content_hash matches the current content.
  If so, reuse the existing embedding. This avoids regenerating embeddings
  for immutable historical records.

The embedding model is loaded once at module level (lazy init on first call).
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Optional

import numpy as np

from app.core.config import get_settings


def _content_hash(text: str) -> str:
    """SHA-256 (hex, first 16 chars) of content for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Model loading (lazy, cached) ──────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_model():
    """Load the sentence-transformer model once per process."""
    from sentence_transformers import SentenceTransformer
    model_name = get_settings().EMBEDDING_MODEL
    # Strip "sentence-transformers/" prefix if present (ST handles it)
    if model_name.startswith("sentence-transformers/"):
        model_name = model_name[len("sentence-transformers/"):]
    model = SentenceTransformer(model_name)
    return model


# ── Public API ────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a list[float] of length EMBEDDING_DIM."""
    model = _load_model()
    vec: np.ndarray = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed multiple texts. Returns list of embedding vectors."""
    model = _load_model()
    vecs: np.ndarray = model.encode(
        texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=True
    )
    return [v.tolist() for v in vecs]


def compute_content_hash(text: str) -> str:
    return _content_hash(text)


def should_re_embed(current_hash: Optional[str], new_content: str) -> bool:
    """Return True if the content has changed and we need a new embedding."""
    if current_hash is None:
        return True
    return current_hash != _content_hash(new_content)
