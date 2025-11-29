# 絶対厳守：編集前に必ずAI実装ルールを読む
import io

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger


def create_s3_client() -> S3Client:
    return boto3.client("s3")


def create_s3_repository(
    s3_client: S3Client, logger: AppLogger
) -> ObjectStorageRepositoryInterface:
    return S3Repository(s3_client, logger)


class S3Repository(ObjectStorageRepositoryInterface):
    def __init__(self, s3_client: S3Client, logger: AppLogger) -> None:
        self.s3_client = s3_client
        self.logger = logger

    def fetch_image(self, bucket_name: str, object_key: str) -> bytes:
        try:
            self.logger.info("画像の取得を開始")

            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response["Body"].read()
            return content

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"AWS ClientError: {error_code} - {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    def upload_image(
        self,
        bucket_name: str,
        object_key: str,
        processed_image: io.BytesIO,
    ) -> None:
        try:
            self.logger.info("画像のアップロードを開始")

            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=processed_image,
                ContentType="image/webp",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"AWS ClientError: {error_code} - {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    def copy_image(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
    ) -> None:
        try:
            self.logger.info(
                f"画像のコピーを開始: {source_bucket}/{source_key} -> "
                f"{dest_bucket}/{dest_key}"
            )

            self.s3_client.copy_object(
                CopySource={"Bucket": source_bucket, "Key": source_key},
                Bucket=dest_bucket,
                Key=dest_key,
            )

            self.logger.info("画像のコピーが完了")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"AWS ClientError: {error_code} - {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            raise
