import io
from typing import Protocol


class ObjectStorageRepositoryInterface(Protocol):
    def fetch_image(self, bucket_name: str, object_key: str) -> bytes: ...

    def upload_image(
        self, bucket_name: str, object_key: str, processed_image: io.BytesIO
    ) -> None: ...
