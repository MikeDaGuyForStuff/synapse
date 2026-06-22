"""Local embedding generation using sentence-transformers. No API key needed."""

from __future__ import annotations

from typing import Optional

import numpy as np


class EmbeddingProvider:
    """Generates embeddings locally using sentence-transformers.

    Falls back to a lightweight hash-based embedding if sentence-transformers
    is not installed, so the engine is always usable.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._fallback = False

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except (ImportError, OSError):
                self._fallback = True
                self._model = _FallbackEmbedder()
        return self._model

    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector.

        Returns a list of floats (384 dims for MiniLM, 128 for fallback).
        """
        vec = self.model.encode([text])[0]
        if isinstance(vec, np.ndarray):
            return vec.tolist()
        return list(vec)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts at once (batched)."""
        vecs = self.model.encode(texts)
        return [v.tolist() if isinstance(v, np.ndarray) else list(v) for v in vecs]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_np = np.array(a, dtype=np.float32)
        b_np = np.array(b, dtype=np.float32)
        norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
        if norm == 0:
            return 0.0
        return float(np.dot(a_np, b_np) / norm)


class _FallbackEmbedder:
    """Lightweight fallback that produces fixed-dimension embeddings from
    character n-gram hashing. Used when sentence-transformers is unavailable."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        results = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            for i in range(len(text)):
                h = hash(text[i : i + 3]) % self.dim
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            results.append(vec)
        return np.array(results)