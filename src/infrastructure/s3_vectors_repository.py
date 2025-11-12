# 絶対厳守：編集前に必ずAI実装ルールを読む

import math
import os
from array import array

import boto3
from mypy_boto3_s3vectors import S3VectorsClient
from mypy_boto3_s3vectors.type_defs import PutInputVectorTypeDef, VectorDataTypeDef

from domain.vector_index_storage_repository_interface import (
    VectorIndexStorageRepositoryInterface,
)
from log.logging import AppLogger


def create_s3_client_for_vector_storage() -> S3VectorsClient:
    region_name = os.environ.get("S3_VECTORS_REGION", "us-east-1")
    return boto3.client("s3vectors", region_name=region_name)


def create_s3_vectors_repository(
    s3_client: S3VectorsClient,
    logger: AppLogger,
) -> "S3VectorsRepository":
    return S3VectorsRepository(s3_client, logger)


class S3VectorsRepository(VectorIndexStorageRepositoryInterface):
    def __init__(
        self,
        s3_client: S3VectorsClient,
        logger: AppLogger,
    ) -> None:
        self.s3_client = s3_client
        self.logger = logger

        # 環境変数の取得とバリデーション
        vector_index_bucket = os.environ.get("VECTOR_INDEX_BUCKET")
        vector_index_name = os.environ.get("VECTOR_INDEX_NAME")

        if not vector_index_bucket:
            raise ValueError("環境変数 VECTOR_INDEX_BUCKET が設定されていません")
        if not vector_index_name:
            raise ValueError("環境変数 VECTOR_INDEX_NAME が設定されていません")

        self.vector_index_bucket = vector_index_bucket
        self.vector_index_name = vector_index_name

    def save_vector_index(
        self,
        source_bucket: str,
        source_key: str,
        database_id: int,
        embedding: list[float],
    ) -> None:
        try:
            self.logger.info(
                f"ベクトルインデックス保存開始: source={source_bucket}/{source_key}, database_id={database_id}"
            )

            # float64 → float32 変換（AWS S3 Vectors の仕様に準拠）
            float32_embedding = array("f", embedding)

            # NaN/Infinity のバリデーション
            for value in float32_embedding:
                if math.isnan(value):
                    raise ValueError(
                        f"埋め込みベクトルに NaN が含まれています: database_id={database_id}"
                    )
                if math.isinf(value):
                    raise ValueError(
                        f"埋め込みベクトルに Infinity が含まれています: database_id={database_id}"
                    )

            # ベクトルデータを作成
            vector_values: VectorDataTypeDef = {"float32": list(float32_embedding)}
            vector_data: PutInputVectorTypeDef = {
                "key": str(database_id),
                "data": vector_values,
                "metadata": {
                    "source_key": source_key,
                },
            }
            vectors = [vector_data]

            # S3 Vectorsにベクトルを保存
            self.s3_client.put_vectors(
                vectorBucketName=self.vector_index_bucket,
                indexName=self.vector_index_name,
                vectors=vectors,
            )

            self.logger.info(
                f"ベクトルインデックス保存完了: bucket={self.vector_index_bucket}, index={self.vector_index_name}, key={database_id}, database_id={database_id}"
            )

        except Exception as e:
            self.logger.error(
                f"ベクトルインデックス保存エラー: source={source_bucket}/{source_key}, database_id={database_id}, error={e}",
                exc_info=True,
            )
            raise
