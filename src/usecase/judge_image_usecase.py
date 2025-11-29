# 絶対厳守：編集前に必ずAI実装ルールを読む
import os

from domain.image_judgment_repository_interface import (
    ImageJudgmentRepositoryInterface,
)
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger


class JudgeImageUsecase:
    def __init__(
        self,
        s3_repository: ObjectStorageRepositoryInterface,
        image_judgment_repository: ImageJudgmentRepositoryInterface,
        bucket_name: str,
        object_key: str,
        logger: AppLogger,
    ) -> None:
        self.s3_repository = s3_repository
        self.image_judgment_repository = image_judgment_repository
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.logger = logger

    def execute(self) -> tuple[str, str]:
        self.logger.info("画像判定処理を開始")

        try:
            judgment_result = self.image_judgment_repository.judge_image(
                self.bucket_name, self.object_key
            )

            if not judgment_result["is_acceptable"]:
                reason = judgment_result.get("not_acceptable_reason", "unknown reason")
                self.logger.error(f"画像が不適切と判定されました: {reason}")
                raise ValueError(f"画像が不適切と判定されました: {reason}")

            self.logger.info("画像が適切と判定されました。S3への転送を開始")

            upload_bucket_name = os.environ.get("JUDGE_IMAGE_UPLOAD_BUCKET")
            if not upload_bucket_name:
                raise ValueError("JUDGE_IMAGE_UPLOAD_BUCKET must be set")

            self.s3_repository.copy_image(
                self.bucket_name,
                self.object_key,
                upload_bucket_name,
                self.object_key,
            )

            self.logger.info("画像判定処理が完了")
            return upload_bucket_name, self.object_key

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"画像判定処理中にエラーが発生: {e}", exc_info=True)
            raise
