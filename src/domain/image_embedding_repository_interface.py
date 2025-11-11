from typing import Protocol


class ImageEmbeddingRepositoryInterface(Protocol):
    def generate_embedding(self, image_base64: str) -> list[float]: ...
