# 絶対厳守：編集前に必ずAI実装ルールを読む
import os

import requests

from domain.auth_repository_interface import AuthRepositoryInterface
from domain.image_judgment_repository_interface import (
    ImageJudgmentRepositoryInterface,
    ImageJudgmentResult,
)
from log.logging import AppLogger


def create_image_judgment_repository(
    auth_repository: AuthRepositoryInterface,
    logger: AppLogger,
) -> ImageJudgmentRepositoryInterface:
    return ImageJudgmentRepository(auth_repository, logger)


class ImageJudgmentRepository(ImageJudgmentRepositoryInterface):
    def __init__(
        self,
        auth_repository: AuthRepositoryInterface,
        logger: AppLogger,
    ) -> None:
        self.auth_repository = auth_repository
        self.logger = logger

    def judge_image(self, bucket_name: str, object_key: str) -> ImageJudgmentResult:
        self.logger.info("画像判定API呼び出し開始")

        api_url = os.environ.get("JUDGE_IMAGE_API_URL")
        if not api_url:
            raise ValueError("JUDGE_IMAGE_API_URL must be set")

        endpoint = f"{api_url}/cat-images/validate/s3"

        access_token = self.auth_repository.get_access_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        payload = {
            "bucketName": bucket_name,
            "objectKey": object_key,
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            response_data = response.json()
            is_acceptable: bool = response_data["isAcceptableCatImage"]

            result: ImageJudgmentResult = {"is_acceptable": is_acceptable}

            if not is_acceptable:
                not_acceptable_reason = response_data.get("notAcceptableReason")
                if not_acceptable_reason:
                    result["not_acceptable_reason"] = not_acceptable_reason

            self.logger.info(f"画像判定結果: is_acceptable={is_acceptable}")
            return result

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"画像判定APIエラー: {e}", exc_info=True)
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"画像判定APIリクエストエラー: {e}", exc_info=True)
            raise
        except KeyError as e:
            self.logger.error(
                f"画像判定APIレスポンスのパースエラー: {e}", exc_info=True
            )
            raise
