from enum import Enum
import sys

from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger, setup_logger
from infrastructure.s3_repository import (
    create_s3_client,
    create_s3_repository,
)
from usecase.convert_to_webp_usecase import ConvertToWebpUsecase
from usecase.generate_lgtmI_image_usecase import GenerateLgtmImageUsecase
from usecase.judge_image_usecase import JudgeImageUsecase
from usecase.store_to_db_usecase import StoreToDbUsecase


class ProcessType(Enum):
    JUDGE_IMAGE = "judgeImage"
    GENERATE_LGTM_IMAGE = "generateLgtmImage"
    CONVERT_TO_WEBP = "convertToWebp"
    STORE_TO_DB = "storeToDb"


def handle_process(
    request_id: str, process: str, bucket_name: str, object_key: str
) -> None:
    logger: AppLogger = setup_logger(request_id, process, bucket_name, object_key)
    s3_client = create_s3_client()
    s3_repository: ObjectStorageRepositoryInterface = create_s3_repository(
        s3_client, logger
    )

    judge_image_usecase = JudgeImageUsecase(bucket_name, object_key)
    generate_lgtm_image_usecase = GenerateLgtmImageUsecase(
        s3_repository, bucket_name, object_key, logger
    )
    convert_to_webp_usecase = ConvertToWebpUsecase(bucket_name, object_key)
    store_to_db_usecase = StoreToDbUsecase(bucket_name, object_key)

    if process not in [e.value for e in ProcessType]:
        print("想定外のprocessが指定された場合は終了する")
        sys.exit(1)

    if process == ProcessType.JUDGE_IMAGE.value:
        judge_image_usecase.execute()
    elif process == ProcessType.GENERATE_LGTM_IMAGE.value:
        generate_lgtm_image_usecase.execute()
    elif process == ProcessType.CONVERT_TO_WEBP.value:
        convert_to_webp_usecase.execute()
    elif process == ProcessType.STORE_TO_DB.value:
        store_to_db_usecase.execute()
