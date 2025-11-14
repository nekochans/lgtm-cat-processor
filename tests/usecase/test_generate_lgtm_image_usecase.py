# 絶対厳守：編集前に必ずAI実装ルールを読む

import os
from unittest.mock import Mock, patch

import pytest

from domain.cat_detection_repository_interface import (
    CatDetectionRepositoryInterface,
)
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger
from usecase.generate_lgtm_image_usecase import (
    GenerateLgtmImageUsecase,
    build_upload_object_key,
)


class TestBuildUploadObjectKey:
    @pytest.mark.parametrize(
        ("input_key", "expected_key"),
        [
            ("image.jpg", "image.webp"),
            ("image.png", "image.webp"),
            ("path/to/image.jpg", "path/to/image.webp"),
            ("nested/path/to/image.png", "nested/path/to/image.webp"),
            ("image.jpeg", "image.webp"),
            ("path/image", "path/image.webp"),
        ],
        ids=[
            "jpg拡張子",
            "png拡張子",
            "ディレクトリ付きjpg",
            "深いネストのpng",
            "jpeg拡張子",
            "拡張子なし",
        ],
    )
    def test_build_upload_object_key_various_patterns(
        self, input_key: str, expected_key: str
    ) -> None:
        """様々なパターンのobject_keyからwebp形式のキーが生成されること"""
        # Act
        result = build_upload_object_key(input_key)

        # Assert
        assert result == expected_key


class TestGenerateLgtmImageUsecase:
    @pytest.fixture
    def mock_s3_repository(self) -> Mock:
        """ObjectStorageRepositoryのモック"""
        return Mock(spec=ObjectStorageRepositoryInterface)

    @pytest.fixture
    def mock_cat_detection_repository(self) -> Mock:
        """CatDetectionRepositoryのモック"""
        return Mock(spec=CatDetectionRepositoryInterface)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """AppLoggerのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def usecase(
        self,
        mock_s3_repository: Mock,
        mock_cat_detection_repository: Mock,
        mock_logger: Mock,
    ) -> GenerateLgtmImageUsecase:
        """GenerateLgtmImageUsecaseのインスタンス"""
        return GenerateLgtmImageUsecase(
            s3repository=mock_s3_repository,
            cat_detection_repository=mock_cat_detection_repository,
            bucket_name="test-bucket",
            object_key="test-key.jpg",
            logger=mock_logger,
        )

    @patch.dict(
        os.environ,
        {
            "LAMBDA_TASK_ROOT": "/test/lambda",
            "GENERATE_LGTM_IMAGE_UPLOAD_BUCKET": "upload-bucket",
        },
    )
    @patch("usecase.generate_lgtm_image_usecase.LgtmImageGenerator")
    def test_execute_success(
        self,
        mock_generator_class: Mock,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """正常にLGTM画像が生成・アップロードできること"""
        # Arrange
        test_image_bytes = b"test original image"
        test_generated_image = b"test lgtm image"

        mock_s3_repository.fetch_image.return_value = test_image_bytes

        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = test_generated_image
        mock_generator_class.return_value = mock_generator_instance

        # Act
        result = usecase.execute()

        # Assert
        assert result == ("upload-bucket", "test-key.webp")

        # S3からの画像取得が正しい引数で呼ばれたこと
        mock_s3_repository.fetch_image.assert_called_once_with(
            "test-bucket", "test-key.jpg"
        )

        # LgtmImageGeneratorが正しいパラメータでインスタンス化されたこと
        mock_generator_class.assert_called_once_with(
            cat_detector=usecase.cat_detection_repository,
            font_path="/test/lambda/fonts/MPLUSRounded1c-Medium.ttf",
            logger=usecase.logger,
        )

        # generateメソッドが正しい引数で呼ばれたこと
        mock_generator_instance.generate.assert_called_once_with(
            test_image_bytes, "test-bucket", "test-key.jpg"
        )

        # S3へのアップロードが正しい引数で呼ばれたこと
        mock_s3_repository.upload_image.assert_called_once_with(
            "upload-bucket", "test-key.webp", test_generated_image
        )

    @patch.dict(
        os.environ,
        {
            "LAMBDA_TASK_ROOT": "/test/lambda",
            "GENERATE_LGTM_IMAGE_UPLOAD_BUCKET": "upload-bucket",
        },
    )
    @patch("usecase.generate_lgtm_image_usecase.LgtmImageGenerator")
    def test_execute_s3_fetch_error(
        self,
        mock_generator_class: Mock,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """S3からの画像取得失敗時に例外が伝播すること"""
        # Arrange
        mock_s3_repository.fetch_image.side_effect = Exception("S3 fetch error")

        # Act & Assert
        with pytest.raises(Exception, match="S3 fetch error"):
            usecase.execute()

        # S3取得のみが呼ばれ、後続処理は呼ばれないこと
        mock_s3_repository.fetch_image.assert_called_once()
        mock_generator_class.assert_not_called()
        mock_s3_repository.upload_image.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "LAMBDA_TASK_ROOT": "/test/lambda",
            "GENERATE_LGTM_IMAGE_UPLOAD_BUCKET": "upload-bucket",
        },
    )
    @patch("usecase.generate_lgtm_image_usecase.LgtmImageGenerator")
    def test_execute_image_generation_error(
        self,
        mock_generator_class: Mock,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """画像生成失敗時に例外が伝播すること"""
        # Arrange
        test_image_bytes = b"test original image"
        mock_s3_repository.fetch_image.return_value = test_image_bytes

        mock_generator_instance = Mock()
        mock_generator_instance.generate.side_effect = Exception(
            "Image generation error"
        )
        mock_generator_class.return_value = mock_generator_instance

        # Act & Assert
        with pytest.raises(Exception, match="Image generation error"):
            usecase.execute()

        # S3取得と画像生成が呼ばれ、アップロードは呼ばれないこと
        mock_s3_repository.fetch_image.assert_called_once()
        mock_generator_instance.generate.assert_called_once()
        mock_s3_repository.upload_image.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "LAMBDA_TASK_ROOT": "/test/lambda",
            "GENERATE_LGTM_IMAGE_UPLOAD_BUCKET": "upload-bucket",
        },
    )
    @patch("usecase.generate_lgtm_image_usecase.LgtmImageGenerator")
    def test_execute_s3_upload_error(
        self,
        mock_generator_class: Mock,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """S3アップロード失敗時に例外が伝播すること"""
        # Arrange
        test_image_bytes = b"test original image"
        test_generated_image = b"test lgtm image"

        mock_s3_repository.fetch_image.return_value = test_image_bytes
        mock_s3_repository.upload_image.side_effect = Exception("S3 upload error")

        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = test_generated_image
        mock_generator_class.return_value = mock_generator_instance

        # Act & Assert
        with pytest.raises(Exception, match="S3 upload error"):
            usecase.execute()

        # 全てのメソッドが呼ばれること
        mock_s3_repository.fetch_image.assert_called_once()
        mock_generator_instance.generate.assert_called_once()
        mock_s3_repository.upload_image.assert_called_once()

    @patch.dict(os.environ, {"LAMBDA_TASK_ROOT": "/test/lambda"}, clear=True)
    @patch("usecase.generate_lgtm_image_usecase.LgtmImageGenerator")
    def test_execute_missing_upload_bucket_env(
        self,
        mock_generator_class: Mock,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """環境変数GENERATE_LGTM_IMAGE_UPLOAD_BUCKETが未設定の場合に例外が発生すること"""
        # Arrange
        test_image_bytes = b"test original image"
        test_generated_image = b"test lgtm image"

        mock_s3_repository.fetch_image.return_value = test_image_bytes

        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = test_generated_image
        mock_generator_class.return_value = mock_generator_instance

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="環境変数 GENERATE_LGTM_IMAGE_UPLOAD_BUCKET が設定されていません",
        ):
            usecase.execute()
