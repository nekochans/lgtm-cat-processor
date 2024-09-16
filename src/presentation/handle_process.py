from enum import Enum
from domain.lgtm_image_repository_interface import LgtmImageRepositoryInterface
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from infrastructure.db import create_db
from infrastructure.lgtm_image_repository import create_lgtm_image_repository
from log.logging import AppLogger, setup_logger
from infrastructure.s3_repository import (
    create_s3_client,
    create_s3_repository,
)
from usecase.generate_lgtmI_image_usecase import GenerateLgtmImageUsecase
from usecase.judge_image_usecase import JudgeImageUsecase
from usecase.store_to_db_usecase import StoreToDbUsecase


class ProcessType(Enum):
    JUDGE_IMAGE = "judgeImage"
    GENERATE_LGTM_IMAGE = "generateLgtmImage"
    STORE_TO_DB = "storeToDb"


def handle_process(
    request_id: str, process: str, bucket_name: str, object_key: str
) -> tuple[str, str]:
    logger: AppLogger = setup_logger(request_id, process, bucket_name, object_key)
    s3_client = create_s3_client()
    s3_repository: ObjectStorageRepositoryInterface = create_s3_repository(
        s3_client, logger
    )

    if process not in [e.value for e in ProcessType]:
        logger.error(f"ProcessTypeで定義されていないprocessが指定されました: {process}")
        raise ValueError(f"想定外のprocessが指定されました: {process}")

    if process == ProcessType.JUDGE_IMAGE.value:
        judge_image_usecase = JudgeImageUsecase(bucket_name, object_key)

        judge_image_usecase.execute()
        return bucket_name, object_key
    elif process == ProcessType.GENERATE_LGTM_IMAGE.value:
        generate_lgtm_image_usecase = GenerateLgtmImageUsecase(
            s3_repository, bucket_name, object_key, logger
        )

        return generate_lgtm_image_usecase.execute()
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

        store_to_db_usecase.execute()
        return bucket_name, object_key
    else:
        logger.error(
            f"ProcessTypeで定義されたprocessに必要な処理が実行されていません: {process}"
        )
        raise RuntimeError(
            f"ProcessTypeで定義されたprocessに必要な処理が実行されていません: {process}"
        )
