# 絶対厳守：編集前に必ずAI実装ルールを読む
import os

from domain.cat_detection_repository_interface import (
    CatDetectionRepositoryInterface,
)
from domain.lgtm_image_generator import LgtmImageGenerator
from domain.object_storage_repository_interface import (
    ObjectStorageRepositoryInterface,
)
from log.logging import AppLogger


def build_upload_object_key(object_key: str) -> str:
    directory, filename = os.path.split(object_key)
    imagename_without_ext = os.path.splitext(filename)[0]
    return os.path.join(directory, imagename_without_ext + ".webp")


class GenerateLgtmImageUsecase:
    def __init__(
        self,
        s3repository: ObjectStorageRepositoryInterface,
        cat_detection_repository: CatDetectionRepositoryInterface,
        bucket_name: str,
        object_key: str,
        logger: AppLogger,
    ) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.s3repository = s3repository
        self.cat_detection_repository = cat_detection_repository
        self.logger = logger

    def execute(self) -> tuple[str, str]:
        self.logger.info("LGTM画像の作成を開始")
        try:
            original_image = self.s3repository.fetch_image(
                self.bucket_name, self.object_key
            )

            font_path = os.path.join(
                os.environ["LAMBDA_TASK_ROOT"], "fonts", "MPLUSRounded1c-Medium.ttf"
            )
            generator = LgtmImageGenerator(
                cat_detector=self.cat_detection_repository,
                font_path=font_path,
                logger=self.logger,
            )
            generated_image = generator.generate(
                original_image, self.bucket_name, self.object_key
            )

            upload_bucket_name = os.getenv("GENERATE_LGTM_IMAGE_UPLOAD_BUCKET")
            if upload_bucket_name is None:
                raise ValueError(
                    "環境変数 GENERATE_LGTM_IMAGE_UPLOAD_BUCKET が設定されていません"
                )

            upload_object_key = build_upload_object_key(self.object_key)
            self.s3repository.upload_image(
                upload_bucket_name, upload_object_key, generated_image
            )

            self.logger.info("LGTM画像の作成に成功")

            return upload_bucket_name, upload_object_key

        except ValueError as e:
            self.logger.error(e, exc_info=True)
            raise

        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise
