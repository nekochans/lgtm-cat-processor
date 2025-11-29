# 絶対厳守：編集前に必ずAI実装ルールを読む

from unittest.mock import Mock, patch

import pytest
import requests

from infrastructure.cognito_auth_repository import CognitoAuthRepository
from log.logging import AppLogger


class TestCognitoAuthRepository:
    """CognitoAuthRepositoryのテスト"""

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(self, mock_logger: Mock) -> CognitoAuthRepository:
        """CognitoAuthRepositoryのインスタンス"""
        return CognitoAuthRepository(logger=mock_logger)

    @pytest.fixture
    def mock_env_vars(self) -> dict[str, str]:
        """環境変数のモック値"""
        return {
            "COGNITO_TOKEN_ENDPOINT": "https://auth.example.com/oauth2/token",
            "COGNITO_CLIENT_ID": "test-client-id",
            "COGNITO_CLIENT_SECRET": "test-client-secret",
        }

    def test_get_access_token_success(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """正常にアクセストークンを取得できること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act
            result = repository.get_access_token()

            # Assert
            assert result == "test-access-token"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == mock_env_vars["COGNITO_TOKEN_ENDPOINT"]
            assert call_args[1]["data"] == {"grant_type": "client_credentials"}
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Content-Type"] == (
                "application/x-www-form-urlencoded"
            )

    def test_get_access_token_uses_cache(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """キャッシュされたトークンを再利用すること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act - 1回目の呼び出し
            result1 = repository.get_access_token()
            # Act - 2回目の呼び出し（キャッシュを使用）
            result2 = repository.get_access_token()

            # Assert
            assert result1 == result2 == "test-access-token"
            assert mock_post.call_count == 1  # 1回しか呼ばれない

    def test_get_access_token_refreshes_expired_cache(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """キャッシュの有効期限が切れた場合は新しいトークンを取得すること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()

        # キャッシュを期限切れ状態に設定
        repository._cached_token = "old-access-token"
        repository._token_expires_at = 0.0  # 過去の時刻

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act
            result = repository.get_access_token()

            # Assert
            assert result == "new-access-token"
            mock_post.assert_called_once()

    def test_get_access_token_missing_env_vars(
        self,
        repository: CognitoAuthRepository,
    ) -> None:
        """環境変数が設定されていない場合はValueErrorが発生すること"""
        # Arrange
        empty_env: dict[str, str] = {}

        with patch.dict("os.environ", empty_env, clear=True):
            # Act & Assert
            with pytest.raises(ValueError, match="COGNITO_TOKEN_ENDPOINT"):
                repository.get_access_token()

    def test_get_access_token_http_error(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """HTTP認証エラー時にHTTPErrorが発生すること"""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(requests.exceptions.HTTPError):
                repository.get_access_token()

    def test_get_access_token_network_error(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """ネットワークエラー時にRequestExceptionが発生すること"""
        # Arrange
        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Connection refused"
            )

            # Act & Assert
            with pytest.raises(requests.exceptions.RequestException):
                repository.get_access_token()

    def test_get_access_token_parse_error(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """レスポンスにaccess_tokenがない場合はKeyErrorが発生すること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
        ):
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(KeyError):
                repository.get_access_token()

    def test_get_access_token_default_expires_in(
        self,
        repository: CognitoAuthRepository,
        mock_env_vars: dict[str, str],
    ) -> None:
        """expires_inがない場合はデフォルト値（3600秒）を使用すること"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            # expires_in is missing
        }
        mock_response.raise_for_status = Mock()

        with (
            patch.dict("os.environ", mock_env_vars),
            patch("infrastructure.cognito_auth_repository.requests.post") as mock_post,
            patch("infrastructure.cognito_auth_repository.time.time") as mock_time,
        ):
            mock_post.return_value = mock_response
            mock_time.return_value = 1000.0

            # Act
            result = repository.get_access_token()

            # Assert
            assert result == "test-access-token"
            # 3600 - 60 = 3540秒後に期限切れ
            assert repository._token_expires_at == 1000.0 + 3600 - 60
