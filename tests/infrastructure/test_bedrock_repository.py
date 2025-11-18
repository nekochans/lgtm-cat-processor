# 絶対厳守：編集前に必ずAI実装ルールを読む

import json
from io import BytesIO
from typing import Any
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from infrastructure.bedrock_repository import BedrockRepository
from log.logging import AppLogger


class TestBedrockRepository:
    """BedrockRepositoryのテスト"""

    @pytest.fixture
    def mock_bedrock_client(self) -> Mock:
        """BedrockRuntimeClientのモック"""
        return Mock(spec=BedrockRuntimeClient)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_bedrock_client: Mock,
        mock_logger: Mock,
    ) -> BedrockRepository:
        """BedrockRepositoryのインスタンス"""
        return BedrockRepository(
            bedrock_client=mock_bedrock_client,
            logger=mock_logger,
        )

    def test_generate_embedding_success(
        self,
        repository: BedrockRepository,
        mock_bedrock_client: Mock,
    ) -> None:
        """Base64画像から正常に埋め込みベクトルを生成できること"""
        # Arrange
        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"  # "test image data" in base64
        image_mime_type = "image/webp"
        image_base64_uri = f"data:{image_mime_type};base64,{test_image_base64}"
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        mock_response = {
            "body": BytesIO(
                json.dumps({"embeddings": {"float": [test_embedding]}}).encode("utf-8")
            )
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        # Act
        result = repository.generate_embedding(test_image_base64)

        # Assert
        assert result == test_embedding
        mock_bedrock_client.invoke_model.assert_called_once_with(
            modelId="cohere.embed-v4:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(
                {
                    "input_type": "search_document",
                    "images": [image_base64_uri],
                    "embedding_types": ["float"],
                }
            ),
        )

    def test_generate_embedding_custom_model_id(
        self,
        mock_bedrock_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """カスタムモデルIDが環境変数で指定できること"""
        # Arrange
        custom_model_id = "custom-model-id"
        monkeypatch.setenv("BEDROCK_MODEL_ID", custom_model_id)

        repository = BedrockRepository(
            bedrock_client=mock_bedrock_client,
            logger=mock_logger,
        )

        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"
        image_mime_type = "image/webp"
        image_base64_uri = f"data:{image_mime_type};base64,{test_image_base64}"
        test_embedding = [0.1, 0.2, 0.3]

        mock_response = {
            "body": BytesIO(
                json.dumps({"embeddings": {"float": [test_embedding]}}).encode("utf-8")
            )
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        # Act
        result = repository.generate_embedding(test_image_base64)

        # Assert
        assert result == test_embedding
        assert repository.model_id == custom_model_id
        mock_bedrock_client.invoke_model.assert_called_once_with(
            modelId=custom_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(
                {
                    "input_type": "search_document",
                    "images": [image_base64_uri],
                    "embedding_types": ["float"],
                }
            ),
        )

    def test_generate_embedding_default_model_id(
        self,
        repository: BedrockRepository,
    ) -> None:
        """デフォルトモデルIDが使用されること"""
        # Assert
        assert repository.model_id == "cohere.embed-v4:0"

    def test_generate_embedding_api_error(
        self,
        repository: BedrockRepository,
        mock_bedrock_client: Mock,
        mock_logger: Mock,
    ) -> None:
        """Bedrock APIエラー時に適切に例外が発生すること"""
        # Arrange
        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock API error")

        # Act & Assert
        with pytest.raises(Exception, match="Bedrock API error"):
            repository.generate_embedding(test_image_base64)

        mock_bedrock_client.invoke_model.assert_called_once()

        # ログが正しく記録されたことを検証
        mock_logger.error.assert_called_once()
        error_log_call = mock_logger.error.call_args
        assert "Unexpected error" in error_log_call[0][0]
        assert error_log_call[1]["exc_info"] is True

    def test_generate_embedding_client_error(
        self,
        repository: BedrockRepository,
        mock_bedrock_client: Mock,
        mock_logger: Mock,
    ) -> None:
        """ClientError発生時に適切にログ記録され例外が再raiseされること"""
        # Arrange
        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"
        error_response: Any = {
            "Error": {
                "Code": "InvalidParameterException",
                "Message": "Invalid parameter",
            }
        }
        client_error = ClientError(error_response, "invoke_model")
        mock_bedrock_client.invoke_model.side_effect = client_error

        # Act & Assert
        with pytest.raises(ClientError):
            repository.generate_embedding(test_image_base64)

        # ログが正しく記録されたことを検証
        mock_logger.error.assert_called_once()
        error_log_call = mock_logger.error.call_args
        assert "AWS ClientError" in error_log_call[0][0]
        assert "InvalidParameterException" in error_log_call[0][0]
        assert error_log_call[1]["exc_info"] is True

    @pytest.mark.parametrize(
        "test_id,response_body,expected_exception,description",
        [
            (
                "missing_embeddings_field",
                json.dumps({}).encode("utf-8"),
                KeyError,
                "embeddingsフィールドが欠けている",
            ),
            (
                "empty_float_list",
                json.dumps({"embeddings": {"float": []}}).encode("utf-8"),
                IndexError,
                "floatリストが空",
            ),
            (
                "empty_embedding_vector",
                json.dumps({"embeddings": {"float": [[]]}}).encode("utf-8"),
                ValueError,
                "埋め込みベクトルが空リスト",
            ),
            (
                "invalid_json",
                b"invalid json",
                Exception,
                "無効なJSON",
            ),
        ],
    )
    def test_generate_embedding_error_cases(
        self,
        repository: BedrockRepository,
        mock_bedrock_client: Mock,
        test_id: str,
        response_body: bytes,
        expected_exception: type[Exception],
        description: str,
    ) -> None:
        """各種エラーケースで適切に例外が発生すること"""
        # Arrange
        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"
        mock_response = {"body": BytesIO(response_body)}
        mock_bedrock_client.invoke_model.return_value = mock_response

        # Act & Assert
        with pytest.raises(expected_exception):
            repository.generate_embedding(test_image_base64)

    @pytest.mark.parametrize(
        "embedding_size",
        [
            256,
            512,
            1024,
            1536,
        ],
    )
    def test_generate_embedding_various_sizes(
        self,
        repository: BedrockRepository,
        mock_bedrock_client: Mock,
        embedding_size: int,
    ) -> None:
        """様々なサイズの埋め込みベクトルが生成できること"""
        # Arrange
        test_image_base64 = "dGVzdCBpbWFnZSBkYXRh"
        test_embedding = [0.1] * embedding_size

        mock_response = {
            "body": BytesIO(
                json.dumps({"embeddings": {"float": [test_embedding]}}).encode("utf-8")
            )
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        # Act
        result = repository.generate_embedding(test_image_base64)

        # Assert
        assert result == test_embedding
        assert len(result) == embedding_size
