# 絶対厳守：編集前に必ずAI実装ルールを読む

import io
from typing import Any
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from infrastructure.s3_repository import S3Repository
from log.logging import AppLogger


class TestS3Repository:
    """S3Repositoryのテスト"""

    @pytest.fixture
    def mock_s3_client(self) -> Mock:
        """S3Clientのモック"""
        return Mock(spec=S3Client)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
    ) -> S3Repository:
        """S3Repositoryのインスタンス"""
        return S3Repository(
            s3_client=mock_s3_client,
            logger=mock_logger,
        )

    def test_fetch_image_success(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """画像の取得が正常に成功すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"
        expected_content = b"test image data"

        mock_body = Mock()
        mock_body.read.return_value = expected_content
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        # Act
        result = repository.fetch_image(bucket_name, object_key)

        # Assert
        assert result == expected_content
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=bucket_name, Key=object_key
        )

    @pytest.mark.parametrize(
        "error_code,error_message,description",
        [
            ("NoSuchKey", "The specified key does not exist.", "存在しないキー"),
            ("AccessDenied", "Access Denied", "アクセス権限なし"),
        ],
    )
    def test_fetch_image_client_errors(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
        error_code: str,
        error_message: str,
        description: str,
    ) -> None:
        """S3 ClientErrorが適切に発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"

        error_response: Any = {"Error": {"Code": error_code, "Message": error_message}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            repository.fetch_image(bucket_name, object_key)

        assert exc_info.value.response["Error"]["Code"] == error_code
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=bucket_name, Key=object_key
        )

    def test_fetch_image_generic_error(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """その他のS3エラーが発生した場合に適切に例外が発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"

        mock_s3_client.get_object.side_effect = Exception("S3 service error")

        # Act & Assert
        with pytest.raises(Exception, match="S3 service error"):
            repository.fetch_image(bucket_name, object_key)

        mock_s3_client.get_object.assert_called_once()

    def test_fetch_image_empty_body(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """空のBodyレスポンスが返された場合の挙動確認"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "empty-image.jpg"

        mock_body = Mock()
        mock_body.read.return_value = b""
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        # Act
        result = repository.fetch_image(bucket_name, object_key)

        # Assert
        assert result == b""
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=bucket_name, Key=object_key
        )

    def test_upload_image_success(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """画像のアップロードが正常に成功すること"""
        # Arrange
        bucket_name = "test-upload-bucket"
        object_key = "uploaded-image.webp"
        processed_image = io.BytesIO(b"processed image data")

        # Act
        repository.upload_image(bucket_name, object_key, processed_image)

        # Assert
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key,
            Body=processed_image,
            ContentType="image/webp",
        )

    def test_upload_image_s3_error(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """アップロード時にS3エラーが発生した場合に適切に例外が発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.webp"
        processed_image = io.BytesIO(b"test data")

        error_response: Any = {
            "Error": {"Code": "InternalError", "Message": "Internal Server Error"}
        }
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            repository.upload_image(bucket_name, object_key, processed_image)

        assert exc_info.value.response["Error"]["Code"] == "InternalError"
        mock_s3_client.put_object.assert_called_once()

    def test_upload_image_generic_error(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """アップロード時にその他のエラーが発生した場合に適切に例外が発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.webp"
        processed_image = io.BytesIO(b"test data")

        mock_s3_client.put_object.side_effect = Exception("Upload failed")

        # Act & Assert
        with pytest.raises(Exception, match="Upload failed"):
            repository.upload_image(bucket_name, object_key, processed_image)

        mock_s3_client.put_object.assert_called_once()
