# 絶対厳守：編集前に必ずAI実装ルールを読む

from unittest.mock import Mock, patch

import pytest

from domain.image_judgment_repository_interface import (
    ImageJudgmentRepositoryInterface,
)
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger
from usecase.judge_image_usecase import JudgeImageUsecase


class TestJudgeImageUsecase:
    """JudgeImageUsecaseのテスト"""

    @pytest.fixture
    def mock_s3_repository(self) -> Mock:
        """ObjectStorageRepositoryInterfaceのモック"""
        return Mock(spec=ObjectStorageRepositoryInterface)

    @pytest.fixture
    def mock_image_judgment_repository(self) -> Mock:
        """ImageJudgmentRepositoryInterfaceのモック"""
        return Mock(spec=ImageJudgmentRepositoryInterface)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def usecase(
        self,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
        mock_logger: Mock,
    ) -> JudgeImageUsecase:
        """JudgeImageUsecaseのインスタンス"""
        return JudgeImageUsecase(
            s3_repository=mock_s3_repository,
            image_judgment_repository=mock_image_judgment_repository,
            bucket_name="source-bucket",
            object_key="test-image.jpg",
            logger=mock_logger,
        )

    def test_execute_success(
        self,
        usecase: JudgeImageUsecase,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
    ) -> None:
        """適切判定でS3コピー成功時にタプルを返すこと"""
        # Arrange
        mock_image_judgment_repository.judge_image.return_value = {
            "is_acceptable": True,
        }

        with patch.dict("os.environ", {"JUDGE_IMAGE_UPLOAD_BUCKET": "upload-bucket"}):
            # Act
            result = usecase.execute()

            # Assert
            assert result == ("upload-bucket", "test-image.jpg")
            mock_image_judgment_repository.judge_image.assert_called_once_with(
                "source-bucket", "test-image.jpg"
            )
            mock_s3_repository.copy_image.assert_called_once_with(
                "source-bucket",
                "test-image.jpg",
                "upload-bucket",
                "test-image.jpg",
            )

    def test_execute_not_acceptable_image(
        self,
        usecase: JudgeImageUsecase,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
    ) -> None:
        """不適切判定でValueErrorが発生すること"""
        # Arrange
        mock_image_judgment_repository.judge_image.return_value = {
            "is_acceptable": False,
            "not_acceptable_reason": "not cat image",
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="画像が不適切と判定されました: not cat image"
        ):
            usecase.execute()

        mock_s3_repository.copy_image.assert_not_called()

    def test_execute_judgment_api_error(
        self,
        usecase: JudgeImageUsecase,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
    ) -> None:
        """画像判定API呼び出し失敗時に例外が発生すること"""
        # Arrange
        mock_image_judgment_repository.judge_image.side_effect = Exception(
            "API connection error"
        )

        # Act & Assert
        with pytest.raises(Exception, match="API connection error"):
            usecase.execute()

        mock_s3_repository.copy_image.assert_not_called()

    def test_execute_s3_copy_error(
        self,
        usecase: JudgeImageUsecase,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
    ) -> None:
        """S3コピー失敗時に例外が発生すること"""
        # Arrange
        mock_image_judgment_repository.judge_image.return_value = {
            "is_acceptable": True,
        }
        mock_s3_repository.copy_image.side_effect = Exception("S3 copy error")

        with patch.dict("os.environ", {"JUDGE_IMAGE_UPLOAD_BUCKET": "upload-bucket"}):
            # Act & Assert
            with pytest.raises(Exception, match="S3 copy error"):
                usecase.execute()

    def test_execute_missing_upload_bucket_env(
        self,
        usecase: JudgeImageUsecase,
        mock_s3_repository: Mock,
        mock_image_judgment_repository: Mock,
    ) -> None:
        """JUDGE_IMAGE_UPLOAD_BUCKET未設定時にValueErrorが発生すること"""
        # Arrange
        mock_image_judgment_repository.judge_image.return_value = {
            "is_acceptable": True,
        }

        with patch.dict("os.environ", {}, clear=True):
            # Act & Assert
            with pytest.raises(
                ValueError, match="JUDGE_IMAGE_UPLOAD_BUCKET must be set"
            ):
                usecase.execute()

        mock_s3_repository.copy_image.assert_not_called()
