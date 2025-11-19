# 絶対厳守：編集前に必ずAI実装ルールを読む
from domain.lgtm_image_repository_interface import LgtmImageRepositoryInterface
from infrastructure.lgtm_image import LgtmImage
from log.logging import AppLogger
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError


def create_lgtm_image_repository(
    session_factory: sessionmaker[Session],
    logger: AppLogger,
) -> LgtmImageRepositoryInterface:
    return LgtmImageRepository(session_factory, logger)


class LgtmImageRepository(LgtmImageRepositoryInterface):
    def __init__(
        self, session_factory: sessionmaker[Session], logger: AppLogger
    ) -> None:
        self.session_factory = session_factory
        self.logger = logger

    def save_lgtm_cat(self, file_name: str, path: str) -> int:
        self.logger.info("レコードのインサートを開始")
        try:
            with self.session_factory.begin() as session:
                lgtm_image = LgtmImage(filename=file_name, path=path)
                session.add(lgtm_image)
                session.flush()

                # IDがNoneでないことを確認（autoincrement=Trueのため通常は必ず値が設定される）
                if lgtm_image.id is None:
                    raise RuntimeError("画像IDの取得に失敗しました")

                self.logger.info(f"レコードのインサートが成功 (ID: {lgtm_image.id})")
                return lgtm_image.id

        except SQLAlchemyError as e:
            self.logger.error(f"レコードのインサート中にエラーが発生しました: {e}")
            raise
