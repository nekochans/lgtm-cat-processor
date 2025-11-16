# 絶対厳守:編集前に必ずAI実装ルールを読む

from unittest.mock import Mock

import pytest

from domain.lgtm_image_repository_interface import LgtmImageRepositoryInterface
from log.logging import AppLogger
from usecase.store_to_db_usecase import StoreToDbUsecase, extract_filename_without_ext


class TestExtractFilenameWithoutExt:
    @pytest.mark.parametrize(
        "object_key,expected",
        [
            ("test.jpg", "test"),
            ("image.png", "image"),
            ("photo.webp", "photo"),
            ("path/to/file.jpg", "file"),
            ("a/b/c/image.png", "image"),
            ("file", "file"),
            ("file.test.jpg", "file.test"),
            ("my.image.test.png", "my.image.test"),
            ("", ""),
        ],
        ids=[
            "simple_jpg",
            "simple_png",
            "simple_webp",
            "nested_path",
            "deep_nested_path",
            "no_extension",
            "multiple_dots",
            "multiple_dots_complex",
            "empty_string",
        ],
    )
    def test_extract_filename_without_ext(self, object_key: str, expected: str) -> None:
        """様々なファイル名パターンで正しく拡張子を除去できること"""
        # Act
        result = extract_filename_without_ext(object_key)

        # Assert
        assert result == expected


class TestStoreToDbUsecase:
    @pytest.fixture
    def mock_lgtm_image_repository(self) -> Mock:
        """LgtmImageRepositoryInterfaceのモック"""
        return Mock(spec=LgtmImageRepositoryInterface)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def usecase(
        self,
        mock_lgtm_image_repository: Mock,
        mock_logger: Mock,
    ) -> StoreToDbUsecase:
        """StoreToDbUsecaseのインスタンス"""
        return StoreToDbUsecase(
            lgtm_image_repository=mock_lgtm_image_repository,
            bucket_name="test-bucket",
            object_key="test/path/image.webp",
            logger=mock_logger,
        )

    def test_execute_success(
        self,
        usecase: StoreToDbUsecase,
        mock_lgtm_image_repository: Mock,
    ) -> None:
        """正常にDB保存が完了してIDが返されること"""
        # Arrange
        expected_id = 123
        mock_lgtm_image_repository.save_lgtm_cat.return_value = expected_id

        # Act
        result = usecase.execute()

        # Assert
        assert result == expected_id
        mock_lgtm_image_repository.save_lgtm_cat.assert_called_once_with(
            "image", "test/path"
        )

    def test_execute_repository_error(
        self,
        usecase: StoreToDbUsecase,
        mock_lgtm_image_repository: Mock,
        mock_logger: Mock,
    ) -> None:
        """リポジトリエラー時に例外が伝播すること"""
        # Arrange
        error_message = "Database error"
        mock_lgtm_image_repository.save_lgtm_cat.side_effect = Exception(error_message)

        # Act & Assert
        with pytest.raises(Exception, match=error_message):
            usecase.execute()

        # エラーログが出力されることを確認
        mock_logger.error.assert_called_once()
        mock_lgtm_image_repository.save_lgtm_cat.assert_called_once()

    @pytest.mark.parametrize(
        "object_key,expected_filename,expected_path",
        [
            ("path/to/file.jpg", "file", "path/to"),
            ("a/b/c/image.png", "image", "a/b/c"),
            ("simple.webp", "simple", ""),
            ("dir/image.test.jpg", "image.test", "dir"),
        ],
        ids=[
            "nested_path",
            "deep_nested_path",
            "root_path",
            "multiple_dots_filename",
        ],
    )
    def test_execute_with_various_paths(
        self,
        mock_lgtm_image_repository: Mock,
        mock_logger: Mock,
        object_key: str,
        expected_filename: str,
        expected_path: str,
    ) -> None:
        """様々なobject_keyパターンで正しくファイル名とパスが抽出されること"""
        # Arrange
        usecase = StoreToDbUsecase(
            lgtm_image_repository=mock_lgtm_image_repository,
            bucket_name="test-bucket",
            object_key=object_key,
            logger=mock_logger,
        )
        expected_id = 789
        mock_lgtm_image_repository.save_lgtm_cat.return_value = expected_id

        # Act
        result = usecase.execute()

        # Assert
        assert result == expected_id
        mock_lgtm_image_repository.save_lgtm_cat.assert_called_once_with(
            expected_filename, expected_path
        )
