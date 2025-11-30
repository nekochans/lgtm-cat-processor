from enum import Enum

from domain.auth_repository_interface import AuthRepositoryInterface
from domain.image_embedding_repository_interface import (
    ImageEmbeddingRepositoryInterface,
)
from domain.image_judgment_repository_interface import (
    ImageJudgmentRepositoryInterface,
)
from domain.lgtm_image_repository_interface import LgtmImageRepositoryInterface
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from domain.vector_index_storage_repository_interface import (
    VectorIndexStorageRepositoryInterface,
)
from infrastructure.bedrock_repository import (
    create_bedrock_client,
    create_bedrock_repository,
)
from infrastructure.cognito_auth_repository import create_cognito_auth_repository
from infrastructure.db import create_db
from infrastructure.image_judgment_repository import create_image_judgment_repository
from infrastructure.lgtm_image_repository import create_lgtm_image_repository
from infrastructure.rekognition_repository import (
    create_rekognition_client,
    create_rekognition_repository,
)
from infrastructure.s3_repository import create_s3_client, create_s3_repository
from infrastructure.s3_vectors_repository import (
    create_s3_client_for_vector_storage,
    create_s3_vectors_repository,
)
from log.logging import AppLogger, setup_logger
from usecase.create_image_index_usecase import CreateImageIndexUsecase
from usecase.generate_lgtm_image_usecase import GenerateLgtmImageUsecase
from usecase.judge_image_usecase import JudgeImageUsecase
from usecase.store_to_db_usecase import StoreToDbUsecase


class ProcessType(Enum):
    JUDGE_IMAGE = "judgeImage"
    GENERATE_LGTM_IMAGE = "generateLgtmImage"
    STORE_TO_DB = "storeToDb"
    CREATE_IMAGE_INDEX = "createImageIndex"


def handle_process(
    request_id: str,
    process: str,
    bucket_name: str,
    object_key: str,
    database_id: int | None,
) -> tuple[str, str, int | None]:
    logger: AppLogger = setup_logger(request_id, process, bucket_name, object_key)
    s3_client = create_s3_client()
    s3_repository: ObjectStorageRepositoryInterface = create_s3_repository(
        s3_client, logger
    )

    if process not in [e.value for e in ProcessType]:
        logger.error(f"ProcessTypeで定義されていないprocessが指定されました: {process}")
        raise ValueError(f"想定外のprocessが指定されました: {process}")

    if process == ProcessType.JUDGE_IMAGE.value:
        auth_repository: AuthRepositoryInterface = create_cognito_auth_repository(
            logger
        )
        image_judgment_repository: ImageJudgmentRepositoryInterface = (
            create_image_judgment_repository(auth_repository, logger)
        )

        judge_image_usecase = JudgeImageUsecase(
            s3_repository,
            image_judgment_repository,
            bucket_name,
            object_key,
            logger,
        )

        result_bucket, result_key = judge_image_usecase.execute()
        return result_bucket, result_key, None
    elif process == ProcessType.GENERATE_LGTM_IMAGE.value:
        rekognition_client = create_rekognition_client()
        cat_detection_repository = create_rekognition_repository(
            rekognition_client, logger
        )
        generate_lgtm_image_usecase = GenerateLgtmImageUsecase(
            s3_repository,
            cat_detection_repository,
            bucket_name,
            object_key,
            logger,
        )

        result_bucket, result_key = generate_lgtm_image_usecase.execute()
        return result_bucket, result_key, None
    elif process == ProcessType.STORE_TO_DB.value:
        try:
            sessionLocal = create_db()
        except Exception as e:
            logger.error(f"DBへの接続エラー: {e}", exc_info=True)
            raise

        lgtm_image_repository: LgtmImageRepositoryInterface = (
            create_lgtm_image_repository(sessionLocal, logger)
        )

        store_to_db_usecase = StoreToDbUsecase(
            lgtm_image_repository, bucket_name, object_key, logger
        )

        image_id = store_to_db_usecase.execute()
        return bucket_name, object_key, image_id
    elif process == ProcessType.CREATE_IMAGE_INDEX.value:
        if database_id is None:
            logger.error("CREATE_IMAGE_INDEXプロセスにはdatabaseIdが必須です")
            raise ValueError("CREATE_IMAGE_INDEXプロセスにはdatabaseIdが必須です")

        # 画像埋め込みベクトル生成リポジトリ（Bedrock）
        bedrock_client = create_bedrock_client()
        embedding_repository: ImageEmbeddingRepositoryInterface = (
            create_bedrock_repository(bedrock_client, logger)
        )

        # ベクトルインデックス保存リポジトリ（S3）
        s3_vectors_client = create_s3_client_for_vector_storage()
        vector_storage_repository: VectorIndexStorageRepositoryInterface = (
            create_s3_vectors_repository(s3_vectors_client, logger)
        )

        create_image_index_usecase = CreateImageIndexUsecase(
            s3_repository,
            embedding_repository,
            vector_storage_repository,
            bucket_name,
            object_key,
            database_id,
            logger,
        )

        result_bucket, result_key = create_image_index_usecase.execute()
        return result_bucket, result_key, None
    else:
        logger.error(
            f"ProcessTypeで定義されたprocessに必要な処理が実行されていません: {process}"
        )
        raise RuntimeError(
            f"ProcessTypeで定義されたprocessに必要な処理が実行されていません: {process}"
        )
