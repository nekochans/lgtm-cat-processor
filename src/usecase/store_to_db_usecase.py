import os
from domain.lgtm_image_repository_interface import LgtmImageRepositoryInterface
from log.logging import AppLogger


def extract_filename_without_ext(object_key: str) -> str:
    base = os.path.basename(object_key)
    ext = os.path.splitext(base)[1]
    return base[: len(base) - len(ext)]


class StoreToDbUsecase:
    def __init__(
        self,
        lgtm_image_repository: LgtmImageRepositoryInterface,
        bucket_name: str,
        object_key: str,
        logger: AppLogger,
    ) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.logger = logger
        self.lgtm_image_repository = lgtm_image_repository

    def execute(self) -> None:
        self.logger.info("LGTM画像情報のDBへの保存を開始")
        try:
            path = os.path.dirname(self.object_key)
            filenameWithoutExt = extract_filename_without_ext(self.object_key)

            self.lgtm_image_repository.save_lgtm_cat(filenameWithoutExt, path)
            self.logger.info("LGTM画像情報のDBへの保存が成功")
        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise
