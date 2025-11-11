from typing import Protocol


class LgtmImageRepositoryInterface(Protocol):
    def save_lgtm_cat(
        self,
        file_name: str,
        path: str,
    ) -> int: ...
