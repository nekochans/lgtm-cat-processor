# 絶対厳守：編集前に必ずAI実装ルールを読む

import base64
from unittest.mock import Mock

import pytest

from domain.image_embedding_repository_interface import (
    ImageEmbeddingRepositoryInterface,
)
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from domain.vector_index_storage_repository_interface import (
    VectorIndexStorageRepositoryInterface,
)
from log.logging import AppLogger
from usecase.create_image_index_usecase import CreateImageIndexUsecase


class TestCreateImageIndexUsecase:
    @pytest.fixture
    def mock_object_storage_repository(self) -> Mock:
        """ObjectStorageRepositoryのモック"""
        return Mock(spec=ObjectStorageRepositoryInterface)

    @pytest.fixture
    def mock_embedding_repository(self) -> Mock:
        """ImageEmbeddingRepositoryのモック"""
        return Mock(spec=ImageEmbeddingRepositoryInterface)

    @pytest.fixture
    def mock_vector_storage_repository(self) -> Mock:
        """VectorIndexStorageRepositoryInterfaceのモック"""
        return Mock(spec=VectorIndexStorageRepositoryInterface)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def usecase(
        self,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
        mock_logger: Mock,
    ) -> CreateImageIndexUsecase:
        """CreateImageIndexUsecaseのインスタンス"""
        return CreateImageIndexUsecase(
            s3_repository=mock_object_storage_repository,
            embedding_repository=mock_embedding_repository,
            vector_storage_repository=mock_vector_storage_repository,
            bucket_name="test-bucket",
            object_key="test-key.jpg",
            database_id=1,
            logger=mock_logger,
        )

    def test_execute_success(
        self,
        usecase: CreateImageIndexUsecase,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
    ) -> None:
        """正常に画像インデックスが作成できること"""
        # Arrange
        test_image_bytes = b"test image data"
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_base64 = base64.b64encode(test_image_bytes).decode("utf-8")

        mock_object_storage_repository.fetch_image.return_value = test_image_bytes
        mock_embedding_repository.generate_embedding.return_value = test_embedding

        # Act
        result = usecase.execute()

        # Assert
        assert result == ("test-bucket", "test-key.jpg")

        # 各メソッドが正しい引数で呼ばれたことを確認
        mock_object_storage_repository.fetch_image.assert_called_once_with(
            "test-bucket", "test-key.jpg"
        )
        mock_embedding_repository.generate_embedding.assert_called_once_with(
            expected_base64
        )
        mock_vector_storage_repository.save_vector_index.assert_called_once_with(
            "test-bucket", "test-key.jpg", 1, test_embedding
        )

    def test_execute_s3_fetch_error(
        self,
        usecase: CreateImageIndexUsecase,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
    ) -> None:
        """S3からの画像取得失敗時に例外が伝播すること"""
        # Arrange
        mock_object_storage_repository.fetch_image.side_effect = Exception(
            "S3 fetch error"
        )

        # Act & Assert
        with pytest.raises(Exception, match="S3 fetch error"):
            usecase.execute()

        # S3取得のみが呼ばれ、後続処理は呼ばれないこと
        mock_object_storage_repository.fetch_image.assert_called_once()
        mock_embedding_repository.generate_embedding.assert_not_called()
        mock_vector_storage_repository.save_vector_index.assert_not_called()

    def test_execute_embedding_generation_error(
        self,
        usecase: CreateImageIndexUsecase,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
    ) -> None:
        """埋め込み生成失敗時に例外が伝播すること"""
        # Arrange
        test_image_bytes = b"test image data"
        mock_object_storage_repository.fetch_image.return_value = test_image_bytes
        mock_embedding_repository.generate_embedding.side_effect = Exception(
            "Embedding generation error"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Embedding generation error"):
            usecase.execute()

        # S3取得と埋め込み生成が呼ばれ、ベクトル保存は呼ばれないこと
        mock_object_storage_repository.fetch_image.assert_called_once()
        mock_embedding_repository.generate_embedding.assert_called_once()
        mock_vector_storage_repository.save_vector_index.assert_not_called()

    def test_execute_vector_storage_error(
        self,
        usecase: CreateImageIndexUsecase,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
    ) -> None:
        """ベクトル保存失敗時に例外が伝播すること"""
        # Arrange
        test_image_bytes = b"test image data"
        test_embedding = [0.1, 0.2, 0.3]
        mock_object_storage_repository.fetch_image.return_value = test_image_bytes
        mock_embedding_repository.generate_embedding.return_value = test_embedding
        mock_vector_storage_repository.save_vector_index.side_effect = Exception(
            "Vector storage error"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Vector storage error"):
            usecase.execute()

        # 全てのメソッドが呼ばれること
        mock_object_storage_repository.fetch_image.assert_called_once()
        mock_embedding_repository.generate_embedding.assert_called_once()
        mock_vector_storage_repository.save_vector_index.assert_called_once()

    @pytest.mark.parametrize(
        "embedding_size",
        [
            256,
            512,
            1024,
            1536,
        ],
    )
    def test_execute_with_various_embedding_sizes(
        self,
        usecase: CreateImageIndexUsecase,
        mock_object_storage_repository: Mock,
        mock_embedding_repository: Mock,
        mock_vector_storage_repository: Mock,
        embedding_size: int,
    ) -> None:
        """様々なサイズの埋め込みベクトルで正常に処理できること"""
        # Arrange
        test_image_bytes = b"test image data"
        test_embedding = [0.1] * embedding_size
        mock_object_storage_repository.fetch_image.return_value = test_image_bytes
        mock_embedding_repository.generate_embedding.return_value = test_embedding

        # Act
        result = usecase.execute()

        # Assert
        assert result == ("test-bucket", "test-key.jpg")
        mock_vector_storage_repository.save_vector_index.assert_called_once_with(
            "test-bucket", "test-key.jpg", 1, test_embedding
        )
