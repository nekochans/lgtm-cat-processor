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

    def save_lgtm_cat(self, file_name: str, path: str) -> None:
        self.logger.info("レコードのインサートを開始")
        try:
            with self.session_factory() as session:
                lgtm_image = LgtmImage(filename=file_name, path=path)
                session.add(lgtm_image)
                session.commit()
                self.logger.info("レコードのインサートが成功")

        except SQLAlchemyError as e:
            self.logger.error(f"レコードのインサート中にエラーが発生しました: {e}")
            raise
