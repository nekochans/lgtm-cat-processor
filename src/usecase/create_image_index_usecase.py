import base64

from domain.image_embedding_repository_interface import (
    ImageEmbeddingRepositoryInterface,
)
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from domain.vector_index_storage_repository_interface import (
    VectorIndexStorageRepositoryInterface,
)
from log.logging import AppLogger


class CreateImageIndexUsecase:
    """画像インデックス作成のユースケース"""

    def __init__(
        self,
        s3_repository: ObjectStorageRepositoryInterface,
        embedding_repository: ImageEmbeddingRepositoryInterface,
        vector_storage_repository: VectorIndexStorageRepositoryInterface,
        bucket_name: str,
        object_key: str,
        database_id: int,
        logger: AppLogger,
    ) -> None:
        self.s3_repository = s3_repository
        self.embedding_repository = embedding_repository
        self.vector_storage_repository = vector_storage_repository
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.database_id = database_id
        self.logger = logger

    def execute(self) -> tuple[str, str]:
        self.logger.info("画像インデックス作成を開始")
        try:
            image_bytes = self.s3_repository.fetch_image(
                self.bucket_name, self.object_key
            )
            self.logger.info("S3から画像を取得しました")

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            self.logger.info("画像をBase64エンコードしました")

            embedding = self.embedding_repository.generate_embedding(image_base64)
            self.logger.info(
                f"埋め込みベクトルを生成しました（次元数: {len(embedding)}）"
            )

            self.vector_storage_repository.save_vector_index(
                self.bucket_name,
                self.object_key,
                self.database_id,
                embedding,
            )
            self.logger.info("ベクトルインデックスを保存しました")

            self.logger.info("画像インデックス作成に成功")

            return self.bucket_name, self.object_key

        except Exception as e:
            self.logger.error(f"画像インデックス作成に失敗: {e}", exc_info=True)
            raise
