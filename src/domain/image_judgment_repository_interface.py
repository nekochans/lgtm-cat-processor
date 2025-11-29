# 絶対厳守：編集前に必ずAI実装ルールを読む
from typing import NotRequired, Protocol, Required, TypedDict


class ImageJudgmentResult(TypedDict):
    is_acceptable: Required[bool]
    not_acceptable_reason: NotRequired[str]


class ImageJudgmentRepositoryInterface(Protocol):
    def judge_image(self, bucket_name: str, object_key: str) -> ImageJudgmentResult: ...
