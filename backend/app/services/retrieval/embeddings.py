import hashlib
import math
from abc import ABC, abstractmethod

from app.core.config import Settings


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class LocalHashEmbeddings(EmbeddingProvider):
    """
    Local deterministic hash-based embedding provider.

    Supported dimensions:
        - 256
        - 384
    """

    SUPPORTED_DIMENSIONS = {256, 384}

    def __init__(self, dimensions: int = 384):
        if dimensions not in self.SUPPORTED_DIMENSIONS:
            raise ValueError(
                f"Unsupported embedding dimension: {dimensions}. "
                f"Supported dimensions are: "
                f"{sorted(self.SUPPORTED_DIMENSIONS)}"
            )

        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        for text in texts:
            values = [0.0] * self.dimensions

            # Simple deterministic tokenization
            for token in text.lower().split():
                digest = hashlib.sha256(
                    token.encode("utf-8")
                ).digest()

                # Convert hash into an index within the configured
                # embedding dimension.
                index = (
                    int.from_bytes(digest[:4], "big")
                    % self.dimensions
                )

                values[index] += 1.0

            # L2 normalization
            norm = math.sqrt(
                sum(value * value for value in values)
            ) or 1.0

            vectors.append(
                [value / norm for value in values]
            )

        return vectors


def embedding_provider(s: Settings) -> EmbeddingProvider:
    """
    Create the configured embedding provider.

    The dimension comes from Settings.embedding_dimension.

    .env examples:

        EMBEDDING_DIMENSION=256

    or:

        EMBEDDING_DIMENSION=384
    """

    return LocalHashEmbeddings(
        dimensions=s.embedding_dimension
    )