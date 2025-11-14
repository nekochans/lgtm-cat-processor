# 絶対厳守：編集前に必ずAI実装ルールを読む

from typing import Any
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from infrastructure.rekognition_repository import RekognitionRepository
from log.logging import AppLogger


class TestRekognitionRepository:
    """RekognitionRepositoryのテスト"""

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def mock_rekognition_client(self) -> Mock:
        """RekognitionClientのモック"""
        return Mock()

    @pytest.fixture
    def repository(
        self,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> RekognitionRepository:
        """RekognitionRepositoryのインスタンス"""
        return RekognitionRepository(
            rekognition_client=mock_rekognition_client, logger=mock_logger
        )

    def test_detect_cats_success_single_cat(
        self,
        repository: RekognitionRepository,
        mock_rekognition_client: Mock,
    ) -> None:
        """猫を1匹検出できること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "cat-image.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Cat",
                    "Confidence": 95.5,
                    "Instances": [
                        {
                            "BoundingBox": {
                                "Left": 0.1,
                                "Top": 0.2,
                                "Width": 0.3,
                                "Height": 0.4,
                            },
                            "Confidence": 95.5,
                        }
                    ],
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert len(result) == 1
        assert result[0]["left"] == 0.1
        assert result[0]["top"] == 0.2
        assert result[0]["width"] == 0.3
        assert result[0]["height"] == 0.4
        assert result[0]["confidence"] == 95.5

        mock_rekognition_client.detect_labels.assert_called_once_with(
            Image={"S3Object": {"Bucket": bucket_name, "Name": object_key}},
            MaxLabels=50,
            MinConfidence=80.0,
            Features=["GENERAL_LABELS"],
        )

    def test_detect_cats_success_multiple_cats(
        self,
        repository: RekognitionRepository,
        mock_rekognition_client: Mock,
    ) -> None:
        """複数の猫を検出できること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "multiple-cats.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Cat",
                    "Confidence": 90.0,
                    "Instances": [
                        {
                            "BoundingBox": {
                                "Left": 0.1,
                                "Top": 0.1,
                                "Width": 0.2,
                                "Height": 0.2,
                            },
                            "Confidence": 90.0,
                        },
                        {
                            "BoundingBox": {
                                "Left": 0.6,
                                "Top": 0.5,
                                "Width": 0.3,
                                "Height": 0.4,
                            },
                            "Confidence": 85.0,
                        },
                    ],
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert len(result) == 2
        assert result[0]["left"] == 0.1
        assert result[0]["confidence"] == 90.0
        assert result[1]["left"] == 0.6
        assert result[1]["confidence"] == 85.0

    def test_detect_cats_no_cat_detected(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> None:
        """猫が検出されない場合に空リストを返すこと"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "no-cat.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Dog",
                    "Confidence": 95.0,
                    "Instances": [],
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert result == []
        mock_logger.warning.assert_called_once_with("猫が検出されませんでした")

    def test_detect_cats_cat_label_without_instances(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> None:
        """Catラベルがあるがインスタンスがない場合に空リストを返すこと"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "cat-no-instance.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Cat",
                    "Confidence": 85.0,
                    "Instances": [],  # インスタンスなし
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert result == []
        mock_logger.warning.assert_called_once_with("猫が検出されませんでした")

    def test_detect_cats_instance_uses_label_confidence_when_missing(
        self,
        repository: RekognitionRepository,
        mock_rekognition_client: Mock,
    ) -> None:
        """インスタンスにConfidenceがない場合、ラベルのConfidenceを使用すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "cat-image.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Cat",
                    "Confidence": 92.0,
                    "Instances": [
                        {
                            "BoundingBox": {
                                "Left": 0.2,
                                "Top": 0.3,
                                "Width": 0.4,
                                "Height": 0.5,
                            },
                            # Confidenceなし
                        }
                    ],
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert len(result) == 1
        assert result[0]["confidence"] == 92.0

    def test_detect_cats_skip_when_both_confidences_missing(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> None:
        """インスタンスとラベル両方にConfidenceがない場合、スキップすること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "cat-image.jpg"

        mock_response = {
            "Labels": [
                {
                    "Name": "Cat",
                    # Confidenceなし
                    "Instances": [
                        {
                            "BoundingBox": {
                                "Left": 0.2,
                                "Top": 0.3,
                                "Width": 0.4,
                                "Height": 0.5,
                            },
                            # Confidenceなし
                        }
                    ],
                }
            ]
        }

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert result == []
        mock_logger.warning.assert_any_call(
            "インスタンスとラベルの両方にConfidenceがありません。スキップします。"
        )
        mock_logger.warning.assert_any_call("猫が検出されませんでした")

    def test_detect_cats_rekognition_api_error(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> None:
        """Rekognition APIエラー時に適切に例外が発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"

        error_response: Any = {
            "Error": {
                "Code": "InvalidImageFormatException",
                "Message": "Invalid image format",
            }
        }

        mock_rekognition_client.detect_labels.side_effect = ClientError(
            error_response, "DetectLabels"
        )

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            repository.detect_cats(bucket_name, object_key)

        assert exc_info.value.response["Error"]["Code"] == "InvalidImageFormatException"

        # エラーログが正しく出力されることを確認
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Rekognition API呼び出しエラー:" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

    def test_detect_cats_generic_exception(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
    ) -> None:
        """その他の例外が発生した場合に適切に例外が発生すること"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"

        mock_rekognition_client.detect_labels.side_effect = Exception(
            "Unexpected error"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Unexpected error"):
            repository.detect_cats(bucket_name, object_key)

        # エラーログが正しく出力されることを確認
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Rekognition API呼び出しエラー:" in call_args[0][0]
        assert "Unexpected error" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

    @pytest.mark.parametrize(
        "mock_response",
        [
            ({"Labels": []}),
            ({}),
        ],
        ids=["Labelsが空", "Labelsキーなし"],
    )
    def test_detect_cats_empty_responses(
        self,
        repository: RekognitionRepository,
        mock_logger: Mock,
        mock_rekognition_client: Mock,
        mock_response: dict[str, Any],
    ) -> None:
        """空のレスポンスの場合に空リストを返すこと"""
        # Arrange
        bucket_name = "test-bucket"
        object_key = "test-image.jpg"

        mock_rekognition_client.detect_labels.return_value = mock_response

        # Act
        result = repository.detect_cats(bucket_name, object_key)

        # Assert
        assert result == []
        mock_logger.warning.assert_called_once_with("猫が検出されませんでした")

    def test_detect_cats_confidence_threshold(
        self,
        repository: RekognitionRepository,
    ) -> None:
        """信頼度閾値が80.0に設定されていること"""
        # Assert
        assert repository.CONFIDENCE_THRESHOLD == 80.0
