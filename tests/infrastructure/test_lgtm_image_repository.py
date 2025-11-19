# 絶対厳守:編集前に必ずAI実装ルールを読む

from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.lgtm_image import LgtmImage
from infrastructure.lgtm_image_repository import LgtmImageRepository
from log.logging import AppLogger


class TestLgtmImageRepository:
    """LgtmImageRepositoryのテスト"""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Sessionのモック"""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_session_factory(self, mock_session: Mock) -> Mock:
        """sessionmakerのモック"""
        mock_factory = Mock(spec=sessionmaker)
        # session_factory.begin()がコンテキストマネージャーとして動作するようにする
        mock_factory.begin.return_value.__enter__ = Mock(return_value=mock_session)
        mock_factory.begin.return_value.__exit__ = Mock(return_value=None)
        return mock_factory

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_session_factory: Mock,
        mock_logger: Mock,
    ) -> LgtmImageRepository:
        """LgtmImageRepositoryのインスタンス"""
        return LgtmImageRepository(
            session_factory=mock_session_factory,
            logger=mock_logger,
        )

    def test_save_lgtm_cat_success(
        self,
        repository: LgtmImageRepository,
        mock_session: Mock,
    ) -> None:
        """正常にレコードを保存してIDを取得できること"""
        # Arrange
        test_filename = "test_image"
        test_path = "test/path"
        test_id = 123

        # モックの設定
        mock_session.add.side_effect = (
            lambda obj: setattr(obj, "id", test_id)
            if isinstance(obj, LgtmImage)
            else None
        )
        mock_session.flush.return_value = None

        # Act
        result = repository.save_lgtm_cat(test_filename, test_path)

        # Assert
        assert result == test_id
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_save_lgtm_cat_sqlalchemy_error(
        self,
        repository: LgtmImageRepository,
        mock_session: Mock,
    ) -> None:
        """SQLAlchemyエラー時に例外が伝播すること"""
        # Arrange
        test_filename = "test_image"
        test_path = "test/path"
        error_message = "Database connection error"

        mock_session.add.return_value = None
        mock_session.flush.side_effect = SQLAlchemyError(error_message)

        # Act & Assert
        with pytest.raises(SQLAlchemyError, match=error_message):
            repository.save_lgtm_cat(test_filename, test_path)

        # 適切なメソッドが呼ばれたことを確認
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_save_lgtm_cat_id_is_none(
        self,
        repository: LgtmImageRepository,
        mock_session: Mock,
    ) -> None:
        """ID取得失敗時にRuntimeErrorが発生すること"""
        # Arrange
        test_filename = "test_image"
        test_path = "test/path"

        # flushしてもidがNoneのままのケース
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        # IDが設定されないケースをシミュレート（addのside_effectでIDを設定しない）

        # Act & Assert
        with pytest.raises(RuntimeError, match="画像IDの取得に失敗しました"):
            repository.save_lgtm_cat(test_filename, test_path)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.parametrize(
        "test_filename,test_path,test_id",
        [
            ("image1", "path/to/dir", 1),
            ("image2", "", 2),
            ("image3", "a/b/c/d", 3),
        ],
        ids=[
            "nested_path",
            "empty_path",
            "deep_nested_path",
        ],
    )
    def test_save_lgtm_cat_with_various_paths(
        self,
        repository: LgtmImageRepository,
        mock_session: Mock,
        test_filename: str,
        test_path: str,
        test_id: int,
    ) -> None:
        """様々なパス形式で正常に保存できること"""

        # Arrange
        mock_session.add.side_effect = (
            lambda obj: setattr(obj, "id", test_id)
            if isinstance(obj, LgtmImage)
            else None
        )
        mock_session.flush.return_value = None

        # Act
        result = repository.save_lgtm_cat(test_filename, test_path)

        # Assert
        assert result == test_id
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
