# 絶対厳守：編集前に必ずAI実装ルールを読む
import pytest
from PIL import Image

from domain.brightness_calculator import BrightnessCalculator


class TestBrightnessCalculator:
    """BrightnessCalculatorのテスト"""

    @pytest.mark.parametrize(
        "brightness, threshold, expected, test_description",
        [
            (200, 160, (30, 30, 30), "明るい背景では濃いグレー文字"),
            (100, 160, (255, 255, 255), "暗い背景では白文字"),
            (
                160,
                160,
                (255, 255, 255),
                "閾値ちょうどでは白文字（160 > 160 は False なので）",
            ),
            (150, 140, (30, 30, 30), "カスタム閾値: 150 > 140なので濃いグレー"),
            (130, 140, (255, 255, 255), "カスタム閾値: 130 < 140なので白"),
        ],
    )
    def test_choose_text_color(
        self,
        brightness: int,
        threshold: int,
        expected: tuple[int, int, int],
        test_description: str,
    ) -> None:
        """輝度と閾値に基づいた文字色の選択"""
        calculator = BrightnessCalculator()
        color = calculator.choose_text_color(brightness, threshold=threshold)
        assert color == expected

    @pytest.mark.parametrize(
        "color, expected_brightness, description",
        [
            ((128, 128, 128), 128.0, "グレー画像"),
            ((255, 255, 255), 255.0, "白画像"),
            ((0, 0, 0), 0.0, "黒画像"),
        ],
    )
    def test_get_average_brightness_uniform_image(
        self,
        color: tuple[int, int, int],
        expected_brightness: float,
        description: str,
    ) -> None:
        """単色画像の輝度計算"""
        calculator = BrightnessCalculator()
        img = Image.new("RGB", (100, 100), color)
        brightness = calculator.get_average_brightness(img, (0, 0, 100, 100))
        assert brightness == pytest.approx(expected_brightness, abs=1)

    def test_get_average_brightness_partial_region(self) -> None:
        """部分領域の輝度計算"""
        calculator = BrightnessCalculator()
        # 左半分が黒、右半分が白の画像
        img = Image.new("RGB", (200, 100), (0, 0, 0))
        for x in range(100, 200):
            for y in range(100):
                img.putpixel((x, y), (255, 255, 255))

        # 左半分の輝度
        brightness_left = calculator.get_average_brightness(img, (0, 0, 100, 100))
        assert brightness_left == pytest.approx(0.0, abs=1)

        # 右半分の輝度
        brightness_right = calculator.get_average_brightness(img, (100, 0, 200, 100))
        assert brightness_right == pytest.approx(255.0, abs=1)

    def test_get_average_brightness_out_of_bounds_bbox(self) -> None:
        """画像範囲外のbboxはクリッピングされる"""
        calculator = BrightnessCalculator()
        img = Image.new("RGB", (100, 100), (128, 128, 128))

        # 画像範囲を超えるbbox
        brightness = calculator.get_average_brightness(img, (-10, -10, 150, 150))
        # クリッピングされて (0, 0, 100, 100) として計算される
        assert brightness == pytest.approx(128.0, abs=1)

    @pytest.mark.parametrize(
        "bbox, description",
        [
            ((50, 50, 50, 80), "幅が0のbbox"),
            ((50, 50, 80, 50), "高さが0のbbox"),
            ((80, 80, 50, 50), "逆転したbbox"),
        ],
    )
    def test_get_average_brightness_invalid_bbox_returns_zero(
        self, bbox: tuple[int, int, int, int], description: str
    ) -> None:
        """無効なbbox(幅または高さが0以下)では0.0を返す"""
        calculator = BrightnessCalculator()
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        brightness = calculator.get_average_brightness(img, bbox)
        assert brightness == 0.0

    def test_get_average_brightness_empty_region_after_clipping(self) -> None:
        """クリッピング後に空領域になる場合は0.0を返す"""
        calculator = BrightnessCalculator()
        img = Image.new("RGB", (100, 100), (128, 128, 128))

        # 完全に画像外のbbox
        brightness = calculator.get_average_brightness(img, (200, 200, 300, 300))
        assert brightness == 0.0
