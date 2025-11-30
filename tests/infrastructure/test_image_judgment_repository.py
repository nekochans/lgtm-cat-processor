# 絶対厳守：編集前に必ずAI実装ルールを読む

from unittest.mock import Mock, patch

import pytest
import requests

from domain.auth_repository_interface import AuthRepositoryInterface
from infrastructure.image_judgment_repository import ImageJudgmentRepository
from log.logging import AppLogger


class TestImageJudgmentRepository:
    """ImageJudgmentRepositoryのテスト"""

    @pytest.fixture
    def mock_auth_repository(self) -> Mock:
        """AuthRepositoryInterfaceのモック"""
        mock = Mock(spec=AuthRepositoryInterface)
        mock.request_access_token.return_value = "test-access-token"
        return mock

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_auth_repository: Mock,
        mock_logger: Mock,
    ) -> ImageJudgmentRepository:
        """ImageJudgmentRepositoryのインスタンス"""
        return ImageJudgmentRepository(
            auth_repository=mock_auth_repository,
            logger=mock_logger,
        )

    @pytest.fixture
    def mock_env_vars(self) -> dict[str, str]:
        """環境変数のモック値"""
        return {
            "JUDGE_IMAGE_API_URL": "https://api.example.com",
        }

    def test_judge_image_acceptable(
        self,
        repository: ImageJudgmentRepository,
        mock_auth_repository: Mock,
        mock_env_vars: dict[str, str],
    ) -> None:
        """適切な画像と判定された場合にis_acceptable=Trueを返すこと"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "isAcceptableCatImage": True,
        }
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch(
                "infrastructure.image_judgment_repository.requests.post"
            ) as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act
            result = repository.judge_image("test-bucket", "test-key.jpg")

            # Assert
            assert result["is_acceptable"] is True
            assert "not_acceptable_reason" not in result
            mock_auth_repository.request_access_token.assert_called_once()
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.example.com/cat-images/validate/s3"
            assert call_args[1]["json"] == {
                "bucketName": "test-bucket",
                "objectKey": "test-key.jpg",
            }
            assert (
                call_args[1]["headers"]["Authorization"] == "Bearer test-access-token"
            )

    def test_judge_image_not_acceptable(
        self,
        repository: ImageJudgmentRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """不適切な画像と判定された場合にis_acceptable=Falseと理由を返すこと"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "isAcceptableCatImage": False,
            "notAcceptableReason": "not cat image",
        }
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch(
                "infrastructure.image_judgment_repository.requests.post"
            ) as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act
            result = repository.judge_image("test-bucket", "test-key.jpg")

            # Assert
            assert result["is_acceptable"] is False
            assert result["not_acceptable_reason"] == "not cat image"

    def test_judge_image_missing_env_var(
        self,
        repository: ImageJudgmentRepository,
    ) -> None:
        """環境変数が設定されていない場合はValueErrorが発生すること"""
        # Arrange
        empty_env: dict[str, str] = {}

        with patch.dict("os.environ", empty_env, clear=True):
            # Act & Assert
            with pytest.raises(ValueError, match="JUDGE_IMAGE_API_URL must be set"):
                repository.judge_image("test-bucket", "test-key.jpg")

    def test_judge_image_http_error(
        self,
        repository: ImageJudgmentRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """HTTPエラー時にHTTPErrorが発生すること"""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Internal Server Error"
        )

        with (
            patch.dict("os.environ", mock_env_vars),
            patch(
                "infrastructure.image_judgment_repository.requests.post"
            ) as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(requests.exceptions.HTTPError):
                repository.judge_image("test-bucket", "test-key.jpg")

    def test_judge_image_network_error(
        self,
        repository: ImageJudgmentRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """ネットワークエラー時にRequestExceptionが発生すること"""
        # Arrange
        with (
            patch.dict("os.environ", mock_env_vars),
            patch(
                "infrastructure.image_judgment_repository.requests.post"
            ) as mock_post,
        ):
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Connection refused"
            )

            # Act & Assert
            with pytest.raises(requests.exceptions.RequestException):
                repository.judge_image("test-bucket", "test-key.jpg")

    def test_judge_image_parse_error(
        self,
        repository: ImageJudgmentRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """レスポンスにisAcceptableCatImageがない場合はKeyErrorが発生すること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"error": "invalid_request"}
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch(
                "infrastructure.image_judgment_repository.requests.post"
            ) as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(KeyError):
                repository.judge_image("test-bucket", "test-key.jpg")
