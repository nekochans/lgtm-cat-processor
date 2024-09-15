from typing import List, Tuple
import pymysql
from pymysql.connections import Connection
from domain.lgtm_image_repository_interface import LgtmImageRepositoryIntercase
from log.logging import AppLogger


def create_lgtm_image_repository(
    connection: Connection, logger: AppLogger
) -> LgtmImageRepositoryIntercase:
    return LtgmImageRepository(connection, logger)


class LtgmImageRepository(LgtmImageRepositoryIntercase):
    def __init__(self, connection: Connection, logger: AppLogger) -> None:
        self.connection = connection
        self.logger = logger

    def save_lgtm_cat(
        self,
        file_name: str,
        path: str,
    ) -> None:
        self.logger.info("レコードのインサートを開始")
        try:
            with self.connection.cursor() as cursor:
                sql = "INSERT INTO lgtm_images(filename, `path`) VALUES (%s, %s)"
                values: List[Tuple[str, str]] = [(file_name, path)]
                cursor.executemany(sql, values)

            self.connection.commit()
            self.logger.info(f"{len(values)} 件のレコードのインサートが成功")

        except pymysql.Error as e:
            self.logger.error(f"レコードのインサート中にエラーが発生しました: {e}")
            self.connection.rollback()
            raise
