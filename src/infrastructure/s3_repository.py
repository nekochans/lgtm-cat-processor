import io
import boto3
import mimetypes
from mypy_boto3_s3 import S3Client
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger


def create_s3_client() -> S3Client:
    return boto3.client("s3")


def create_s3_repository(
    s3_client: S3Client, logger: AppLogger
) -> ObjectStorageRepositoryInterface:
    return S3Repository(s3_client, logger)


def get_content_type(file_name: str) -> str:
    content_type, _ = mimetypes.guess_type(file_name)
    if content_type is None:
        return "application/octet-stream"
    return content_type


class S3Repository(ObjectStorageRepositoryInterface):
    def __init__(self, s3_client: S3Client, logger: AppLogger) -> None:
        self.s3_client = s3_client
        self.logger = logger

    def fetch_image(self, bucket_name: str, object_key: str) -> bytes:
        self.logger.info("画像の取得を開始")

        response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response["Body"].read()
        return content

    def upload_image(
        self,
        bucket_name: str,
        object_key: str,
        processed_image: io.BytesIO,
    ) -> None:
        self.logger.info("画像のアップロードを開始")

        content_type = get_content_type(object_key)

        self.s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=processed_image,
            ContentType=content_type,
        )
