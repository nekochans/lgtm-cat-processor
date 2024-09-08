import io
import boto3
from mypy_boto3_s3 import S3Client
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface


def create_s3_client() -> S3Client:
    return boto3.client("s3")


def create_s3_repository(s3_client: S3Client) -> ObjectStorageRepositoryInterface:
    return S3Repository(s3_client)


class S3Repository(ObjectStorageRepositoryInterface):
    def __init__(self, s3_client: S3Client) -> None:
        self.s3_client = s3_client

    def fetch_image(self, bucket_name: str, object_key: str) -> bytes:
        response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response["Body"].read()
        return content

    def upload_image(
        self,
        bucket_name: str,
        object_key: str,
        processed_image: io.BytesIO,
    ) -> None:
        self.s3_client.put_object(
            Bucket=bucket_name, Key=object_key, Body=processed_image
        )
