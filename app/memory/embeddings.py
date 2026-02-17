"""Pluggable embedding providers: Ollama, OpenAI, and local TF-IDF fallback."""

from __future__ import annotations

import abc
import logging
from typing import Any

import numpy as np

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(abc.ABC):
    """Abstract base for all embedding providers."""

    @abc.abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        ...

    @abc.abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        ...

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    async def embed_text(self, text: str) -> list[float]:
        """Compatibility alias used by semantic retrieval modules."""
        return await self.embed(text)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embeddings via Ollama (e.g. nomic-embed-text)."""

    def __init__(self, base_url: str, model: str, dim: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim

    async def embed(self, text: str) -> list[float]:
        import ollama as _ollama

        client = _ollama.AsyncClient(host=self._base_url)
        try:
            response = await client.embed(model=self._model, input=text)
            
            # Handle both dict-like and attribute-like responses
            if hasattr(response, "get"):
                embeddings = response.get("embeddings", [])
                if not embeddings:
                    # Some versions might use singular 'embedding'
                    embeddings = response.get("embedding", [])
                    if isinstance(embeddings, list) and embeddings and not isinstance(embeddings[0], list):
                        # Singular case: wrap in list to match expected list-of-lists format
                        embeddings = [embeddings]
            else:
                embeddings = getattr(response, "embeddings", [])
                if not embeddings:
                    embeddings = getattr(response, "embedding", [])
                    if isinstance(embeddings, list) and embeddings and not isinstance(embeddings[0], list):
                        embeddings = [embeddings]
            
            if not embeddings:
                raise ValueError(f"No embeddings returned from Ollama for model {self._model}")
            
            # Return the first embedding (most common case)
            first_embedding = embeddings[0]
            
            # Ensure we have the right dimension
            if len(first_embedding) != self._dim:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self._dim}, got {len(first_embedding)}"
                )
            
            return first_embedding

        except Exception as e:
            logger.error(f"Error generating embedding with Ollama: {e}")
            raise

    async def embed_text(self, text: str) -> list[float]:
        """Alias for embed method for compatibility."""
        return await self.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import ollama as _ollama

        client = _ollama.AsyncClient(host=self._base_url)
        try:
            response = await client.embed(model=self._model, input=texts)
            
            if hasattr(response, "get"):
                embeddings = response.get("embeddings", [])
                if not embeddings:
                    embeddings = response.get("embedding", [])
            else:
                embeddings = getattr(response, "embeddings", [])
                if not embeddings:
                    embeddings = getattr(response, "embedding", [])

            if embeddings and len(embeddings) == len(texts):
                return embeddings
                
            logger.warning("Ollama batch embed returned mismatch or empty. len(texts)=%d, len(embs)=%d", 
                           len(texts), len(embeddings) if embeddings else 0)
            
            # Fallback: embed one by one
            results = []
            for t in texts:
                results.append(await self.embed(t))
            return results
        except Exception as e:
            logger.error("Error during Ollama batch embedding: %s", e)
            # Last resort fallback if single embed also fails: return dummy vectors or propagate
            results = []
            for t in texts:
                results.append(await self.embed(t))
            return results

    @property
    def dimension(self) -> int:
        return self._dim


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embeddings via OpenAI-compatible API."""

    def __init__(self, api_key: str, base_url: str | None, model: str, dim: int) -> None:
        self._api_key = api_key
        self._base_url = base_url or None
        self._model = model
        self._dim = dim

    async def embed(self, text: str) -> list[float]:
        import httpx

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"input": text, "model": self._model}
        url = f"{self._base_url}/embeddings" if self._base_url else "https://api.openai.com/v1/embeddings"

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {"input": texts, "model": self._model}
        url = f"{self._base_url}/embeddings" if self._base_url else "https://api.openai.com/v1/embeddings"

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return [d["embedding"] for d in data["data"]]

    @property
    def dimension(self) -> int:
        return self._dim


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local TF-IDF fallback — no external services needed."""

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim
        self._fitted = False

    async def embed(self, text: str) -> list[float]:
        return self._hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        """Deterministic hash-based embedding for local use."""
        import hashlib

        tokens = text.lower().split()
        vec = np.zeros(self._dim, dtype=np.float32)
        for i, token in enumerate(tokens):
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            indices = []
            for j in range(min(8, self._dim)):
                indices.append((h + j * 7919) % self._dim)
            for idx in indices:
                vec[idx] += 1.0 / (1.0 + i * 0.1)
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @property
    def dimension(self) -> int:
        return self._dim


# ── Factory ────────────────────────────────────────────────────────
_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider (cached)."""
    global _provider
    if _provider is not None:
        return _provider

    settings = get_settings()
    provider_name = settings.embedding_provider.lower()

    if provider_name == "ollama":
        _provider = OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model,
            dim=settings.embedding_dim,
        )
        logger.info("Using Ollama embedding provider: %s", settings.embedding_model)
    elif provider_name == "openai":
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, falling back to local embeddings")
            _provider = LocalEmbeddingProvider(dim=settings.embedding_dim)
        else:
            _provider = OpenAIEmbeddingProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
                model=settings.embedding_model,
                dim=settings.embedding_dim,
            )
            logger.info("Using OpenAI embedding provider: %s", settings.embedding_model)
    else:
        _provider = LocalEmbeddingProvider(dim=settings.embedding_dim)
        logger.info("Using local embedding provider (hash-based)")

    return _provider
