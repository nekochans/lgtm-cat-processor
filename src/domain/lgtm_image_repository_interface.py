from typing import Protocol


class LgtmImageRepositoryIntercase(Protocol):
    def save_lgtm_cat(
        self,
        bucket_name: str,
        object_key: str,
    ) -> None: ...
