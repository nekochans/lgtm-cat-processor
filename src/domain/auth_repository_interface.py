# 絶対厳守：編集前に必ずAI実装ルールを読む
from typing import Protocol


class AuthRepositoryInterface(Protocol):
    def get_access_token(self) -> str: ...
