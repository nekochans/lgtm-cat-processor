# 絶対厳守：編集前に必ずAI実装ルールを読む

from array import array
from unittest.mock import Mock

import pytest
from mypy_boto3_s3vectors import S3VectorsClient

from infrastructure.s3_vectors_repository import S3VectorsRepository
from log.logging import AppLogger


class TestS3VectorsRepository:
    """S3VectorsRepositoryのテスト"""

    @pytest.fixture
    def mock_s3_client(self) -> Mock:
        """S3VectorsClientのモック"""
        return Mock(spec=S3VectorsClient)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> S3VectorsRepository:
        """S3VectorsRepositoryのインスタンス"""
        monkeypatch.setenv("VECTOR_INDEX_BUCKET", "test-vector-bucket")
        monkeypatch.setenv("VECTOR_INDEX_NAME", "test-index")
        return S3VectorsRepository(
            s3_client=mock_s3_client,
            logger=mock_logger,
        )

    def test_save_vector_index_success(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
    ) -> None:
        """ベクトルインデックスが正常に保存されること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        database_id = 1

        # Act
        repository.save_vector_index(source_bucket, source_key, database_id, embedding)

        # Assert
        mock_s3_client.put_vectors.assert_called_once()
        call_args = mock_s3_client.put_vectors.call_args[1]

        # バケット名とインデックス名の確認
        assert call_args["vectorBucketName"] == "test-vector-bucket"
        assert call_args["indexName"] == "test-index"

        # vectorsの内容を確認
        vectors = call_args["vectors"]
        assert len(vectors) == 1
        vector_data = vectors[0]

        # ベクトルキーが database_id であること
        assert vector_data["key"] == str(database_id)

        # ベクトルデータの確認（float32変換を考慮）
        expected_float32 = list(array("f", embedding))
        assert vector_data["data"]["float32"] == expected_float32

        # metadataに source_key が含まれていること
        assert vector_data["metadata"]["source_key"] == source_key

    @pytest.mark.parametrize(
        "embedding_size",
        [
            256,
            512,
            1024,
            1536,
        ],
    )
    def test_save_vector_index_with_various_embedding_sizes(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
        embedding_size: int,
    ) -> None:
        """様々な次元数の埋め込みベクトルが保存できること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1] * embedding_size
        database_id = 1

        # Act
        repository.save_vector_index(source_bucket, source_key, database_id, embedding)

        # Assert
        mock_s3_client.put_vectors.assert_called_once()
        call_args = mock_s3_client.put_vectors.call_args[1]

        vectors = call_args["vectors"]
        vector_data = vectors[0]

        assert len(vector_data["data"]["float32"]) == embedding_size
        assert vector_data["metadata"]["source_key"] == source_key

    def test_save_vector_index_with_custom_env_vars(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """環境変数が正しく適用されること"""
        # Arrange
        custom_bucket = "custom-vector-bucket"
        custom_index = "custom-index-name"
        monkeypatch.setenv("VECTOR_INDEX_BUCKET", custom_bucket)
        monkeypatch.setenv("VECTOR_INDEX_NAME", custom_index)

        repository = S3VectorsRepository(
            s3_client=mock_s3_client,
            logger=mock_logger,
        )

        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, 0.2, 0.3]
        database_id = 1

        # Act
        repository.save_vector_index(source_bucket, source_key, database_id, embedding)

        # Assert
        assert repository.vector_index_bucket == custom_bucket
        assert repository.vector_index_name == custom_index

        call_args = mock_s3_client.put_vectors.call_args[1]
        assert call_args["vectorBucketName"] == custom_bucket
        assert call_args["indexName"] == custom_index

    def test_save_vector_index_api_error(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
    ) -> None:
        """S3 Vectors APIエラー時に適切に例外が発生すること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, 0.2, 0.3]
        database_id = 1

        mock_s3_client.put_vectors.side_effect = Exception("S3 Vectors API error")

        # Act & Assert
        with pytest.raises(Exception, match="S3 Vectors API error"):
            repository.save_vector_index(
                source_bucket, source_key, database_id, embedding
            )

        mock_s3_client.put_vectors.assert_called_once()

    def test_save_vector_index_missing_env_vars(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """環境変数が未設定時にValueErrorが発生すること"""
        # Arrange
        # 両方の環境変数を削除
        monkeypatch.delenv("VECTOR_INDEX_BUCKET", raising=False)
        monkeypatch.delenv("VECTOR_INDEX_NAME", raising=False)

        # Act & Assert
        with pytest.raises(
            ValueError, match="環境変数 VECTOR_INDEX_BUCKET が設定されていません"
        ):
            S3VectorsRepository(
                s3_client=mock_s3_client,
                logger=mock_logger,
            )

    def test_save_vector_index_missing_bucket_env_var(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """VECTOR_INDEX_BUCKETが未設定時にValueErrorが発生すること"""
        # Arrange
        monkeypatch.delenv("VECTOR_INDEX_BUCKET", raising=False)
        monkeypatch.setenv("VECTOR_INDEX_NAME", "test-index")

        # Act & Assert
        with pytest.raises(
            ValueError, match="環境変数 VECTOR_INDEX_BUCKET が設定されていません"
        ):
            S3VectorsRepository(
                s3_client=mock_s3_client,
                logger=mock_logger,
            )

    def test_save_vector_index_missing_index_name_env_var(
        self,
        mock_s3_client: Mock,
        mock_logger: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """VECTOR_INDEX_NAMEが未設定時にValueErrorが発生すること"""
        # Arrange
        monkeypatch.setenv("VECTOR_INDEX_BUCKET", "test-bucket")
        monkeypatch.delenv("VECTOR_INDEX_NAME", raising=False)

        # Act & Assert
        with pytest.raises(
            ValueError, match="環境変数 VECTOR_INDEX_NAME が設定されていません"
        ):
            S3VectorsRepository(
                s3_client=mock_s3_client,
                logger=mock_logger,
            )

    def test_save_vector_index_with_nan_values(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
    ) -> None:
        """NaNを含む埋め込みベクトルでValueErrorが発生すること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, float("nan"), 0.3]
        database_id = 1

        # Act & Assert
        with pytest.raises(ValueError, match="埋め込みベクトルに NaN が含まれています"):
            repository.save_vector_index(
                source_bucket, source_key, database_id, embedding
            )

        # put_vectorsは呼ばれないはず
        mock_s3_client.put_vectors.assert_not_called()

    def test_save_vector_index_with_infinity_values(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
    ) -> None:
        """Infinityを含む埋め込みベクトルでValueErrorが発生すること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, float("inf"), 0.3]
        database_id = 1

        # Act & Assert
        with pytest.raises(
            ValueError, match="埋め込みベクトルに Infinity が含まれています"
        ):
            repository.save_vector_index(
                source_bucket, source_key, database_id, embedding
            )

        # put_vectorsは呼ばれないはず
        mock_s3_client.put_vectors.assert_not_called()

    def test_save_vector_index_with_negative_infinity_values(
        self,
        repository: S3VectorsRepository,
        mock_s3_client: Mock,
    ) -> None:
        """-Infinityを含む埋め込みベクトルでValueErrorが発生すること"""
        # Arrange
        source_bucket = "source-bucket"
        source_key = "images/cat.jpg"
        embedding = [0.1, float("-inf"), 0.3]
        database_id = 1

        # Act & Assert
        with pytest.raises(
            ValueError, match="埋め込みベクトルに Infinity が含まれています"
        ):
            repository.save_vector_index(
                source_bucket, source_key, database_id, embedding
            )

        # put_vectorsは呼ばれないはず
        mock_s3_client.put_vectors.assert_not_called()
