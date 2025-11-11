from typing import cast

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
            with self.session_factory() as session:
                lgtm_image = LgtmImage(filename=file_name, path=path)
                session.add(lgtm_image)
                session.commit()
                session.refresh(lgtm_image)  # IDを取得するためにリフレッシュ

                # IDがNoneでないことを確認（autoincrement=Trueのため通常は必ず値が設定される）
                if lgtm_image.id is None:
                    raise RuntimeError("画像IDの取得に失敗しました")

                image_id = cast(int, lgtm_image.id)
                self.logger.info(f"レコードのインサートが成功 (ID: {image_id})")
                return image_id

        except SQLAlchemyError as e:
            self.logger.error(f"レコードのインサート中にエラーが発生しました: {e}")
            session.rollback()
            raise
