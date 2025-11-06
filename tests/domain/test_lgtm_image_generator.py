# 絶対厳守：編集前に必ずAI実装ルールを読む
from unittest.mock import Mock

import pytest

from domain.lgtm_image_generator import LgtmImageGenerator
from domain.lgtm_image_spec import LgtmImageSpec


class TestLgtmImageGenerator:
    """LgtmImageGeneratorのテスト"""

    def test_calculate_resize_dimensions_landscape(self) -> None:
        """横長画像のリサイズ寸法計算"""
        # モックを使ってLgtmImageGeneratorをインスタンス化
        generator = LgtmImageGenerator(
            cat_detector=Mock(), font_path="/mock/path/font.ttf", logger=Mock()
        )
        new_width, new_height = generator.calculate_resize_dimensions(800, 600, 400)

        assert new_width == 400
        assert new_height == 300  # 600 * (400 / 800) = 300

    def test_calculate_resize_dimensions_portrait(self) -> None:
        """縦長画像のリサイズ寸法計算"""
        generator = LgtmImageGenerator(
            cat_detector=Mock(), font_path="/mock/path/font.ttf", logger=Mock()
        )
        new_width, new_height = generator.calculate_resize_dimensions(600, 800, 400)

        assert new_width == 300  # 600 * (400 / 800) = 300
        assert new_height == 400

    def test_calculate_resize_dimensions_square(self) -> None:
        """正方形画像のリサイズ寸法計算"""
        generator = LgtmImageGenerator(
            cat_detector=Mock(), font_path="/mock/path/font.ttf", logger=Mock()
        )
        new_width, new_height = generator.calculate_resize_dimensions(500, 500, 400)

        # 正方形の場合は高さ基準でリサイズ（height > widthではないため）
        assert new_width == 400
        assert new_height == 400

    def test_lgtm_image_spec_default_values(self) -> None:
        """LgtmImageSpecのデフォルト値を確認"""
        spec = LgtmImageSpec()

        assert spec.max_size == 400
        assert spec.lgtm_font_size == 60
        assert spec.meow_font_size == 30
        assert spec.lgtm_text == "LGTM"
        assert spec.meow_text == "eow"
        assert spec.output_format == "WEBP"

    def test_lgtm_image_spec_custom_values(self) -> None:
        """LgtmImageSpecのカスタム値を確認"""
        spec = LgtmImageSpec(
            max_size=800,
            lgtm_font_size=80,
            meow_font_size=40,
            lgtm_text="OK",
            meow_text="!",
            output_format="PNG",
        )

        assert spec.max_size == 800
        assert spec.lgtm_font_size == 80
        assert spec.meow_font_size == 40
        assert spec.lgtm_text == "OK"
        assert spec.meow_text == "!"
        assert spec.output_format == "PNG"

    def test_lgtm_image_spec_is_frozen(self) -> None:
        """LgtmImageSpecがfrozen（不変）であることを確認"""
        spec = LgtmImageSpec()

        with pytest.raises(AttributeError):
            spec.max_size = 500  # type: ignore
