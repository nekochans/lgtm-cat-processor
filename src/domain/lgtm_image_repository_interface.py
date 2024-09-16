from typing import Protocol


class LgtmImageRepositoryInterface(Protocol):
    def save_lgtm_cat(
        self,
        bucket_name: str,
        object_key: str,
    ) -> None: ...
