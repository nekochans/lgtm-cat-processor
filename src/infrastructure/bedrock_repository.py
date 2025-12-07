# 絶対厳守：編集前に必ずAI実装ルールを読む
import json
import os
from typing import cast

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from domain.image_embedding_repository_interface import (
    ImageEmbeddingRepositoryInterface,
)
from log.logging import AppLogger


def create_bedrock_client() -> BedrockRuntimeClient:
    region_name = os.environ.get("BEDROCK_REGION", "ap-northeast-1")
    return boto3.client("bedrock-runtime", region_name=region_name)


def create_bedrock_repository(
    bedrock_client: BedrockRuntimeClient,
    logger: AppLogger,
) -> "BedrockRepository":
    return BedrockRepository(bedrock_client, logger)


class BedrockRepository(ImageEmbeddingRepositoryInterface):
    def __init__(
        self,
        bedrock_client: BedrockRuntimeClient,
        logger: AppLogger,
    ) -> None:
        self.bedrock_client = bedrock_client
        self.logger = logger
        self.model_id = os.environ.get("BEDROCK_MODEL_ID", "cohere.embed-v4:0")

    def generate_embedding(
        self, image_base64: str, image_mime_type: str = "image/webp"
    ) -> list[float]:
        try:
            self.logger.info("画像埋め込みベクトル生成開始")

            image_base64_uri = f"data:{image_mime_type};base64,{image_base64}"

            # Bedrockで画像の埋め込みベクトルを取得
            embedding_response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
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

            # レスポンスをパース
            response_body = json.loads(embedding_response["body"].read())
            embedding_vector = response_body["embeddings"]["float"][0]

            if not embedding_vector:
                raise ValueError("埋め込みベクトルの取得に失敗しました")

            self.logger.info(
                f"埋め込みベクトル取得成功: 次元数={len(embedding_vector)}"
            )

            return cast(list[float], embedding_vector)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                f"AWS ClientError: {error_code} - {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            raise
