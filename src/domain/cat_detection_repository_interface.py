# 絶対厳守：編集前に必ずAI実装ルールを読む
from typing import Protocol

from domain.cat_bounding_box import CatBoundingBox


class CatDetectionRepositoryInterface(Protocol):
    def detect_cats(
        self, bucket_name: str, object_key: str
    ) -> list[CatBoundingBox]: ...
