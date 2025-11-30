# 絶対厳守：編集前に必ずAI実装ルールを読む
import base64
import os
import time

import requests

from domain.auth_repository_interface import AuthRepositoryInterface
from log.logging import AppLogger


def create_cognito_auth_repository(logger: AppLogger) -> AuthRepositoryInterface:
    return CognitoAuthRepository(logger)


class CognitoAuthRepository(AuthRepositoryInterface):
    def __init__(self, logger: AppLogger) -> None:
        self.logger = logger
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0

    def get_access_token(self) -> str:
        if self._is_token_valid():
            self.logger.info("キャッシュされたアクセストークンを使用")
            return self._cached_token  # type: ignore[return-value]

        self.logger.info("Cognitoからアクセストークンを取得開始")

        token_endpoint = os.environ.get("COGNITO_TOKEN_ENDPOINT")
        client_id = os.environ.get("COGNITO_CLIENT_ID")
        client_secret = os.environ.get("COGNITO_CLIENT_SECRET")

        if not token_endpoint or not client_id or not client_secret:
            self.logger.error(
                "Cognito認証に必要な環境変数が設定されていません: "
                "COGNITO_TOKEN_ENDPOINT, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET"
            )
            raise ValueError(
                "COGNITO_TOKEN_ENDPOINT, COGNITO_CLIENT_ID, "
                "COGNITO_CLIENT_SECRET must be set"
            )

        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(
                token_endpoint,
                headers=headers,
                data=data,
                timeout=30,
            )
            response.raise_for_status()

            token_response = response.json()
            access_token: str = token_response["access_token"]
            expires_in: int = token_response.get("expires_in", 3600)

            # 有効期限の60秒前にキャッシュを無効化
            self._cached_token = access_token
            self._token_expires_at = time.time() + expires_in - 60

            self.logger.info("アクセストークンの取得に成功")
            return access_token

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Cognito認証エラー: {e}", exc_info=True)
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Cognitoリクエストエラー: {e}", exc_info=True)
            raise
        except KeyError as e:
            self.logger.error(f"トークンレスポンスのパースエラー: {e}", exc_info=True)
            raise

    def _is_token_valid(self) -> bool:
        return self._cached_token is not None and time.time() < self._token_expires_at
