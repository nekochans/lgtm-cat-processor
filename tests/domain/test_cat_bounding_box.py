# 絶対厳守：編集前に必ずAI実装ルールを読む

from domain.cat_bounding_box import CatBoundingBox, to_pixel_coordinates


import pytest


class TestToPixelCoordinates:
    """to_pixel_coordinates関数のテスト"""

    @pytest.mark.parametrize(
        "bbox,image_width,image_height,expected_tuple,test_id",
        [
            (
                # 中間的な値での座標変換が正しく動作すること
                {
                    "left": 0.25,
                    "top": 0.30,
                    "width": 0.40,
                    "height": 0.35,
                    "confidence": 95.0,
                },
                800,
                600,
                (200, 180, 520, 390),
                "normal_coordinate_conversion",
            ),
            (
                # 境界値(left=0.0, top=0.0)での座標変換が正しく動作すること
                {
                    "left": 0.0,
                    "top": 0.0,
                    "width": 0.5,
                    "height": 0.5,
                    "confidence": 90.0,
                },
                400,
                300,
                (0, 0, 200, 150),
                "boundary_values_zero",
            ),
            (
                # 境界値(right=1.0, bottom=1.0)での座標変換が正しく動作すること
                {
                    "left": 0.5,
                    "top": 0.5,
                    "width": 0.5,
                    "height": 0.5,
                    "confidence": 85.0,
                },
                1000,
                800,
                (500, 400, 1000, 800),
                "boundary_values_one",
            ),
            (
                # left/topにはfloor、right/bottomにはceilが適用されること
                {
                    "left": 0.333,  # 0.333 * 900 = 299.7
                    "top": 0.444,  # 0.444 * 600 = 266.4
                    "width": 0.1,  # (0.333 + 0.1) * 900 = 389.7
                    "height": 0.1,  # (0.444 + 0.1) * 600 = 326.4
                    "confidence": 90.0,
                },
                900,
                600,
                (299, 266, 390, 327),
                "rounding_floor_and_ceil",
            ),
            (
                # 画像サイズが0の場合の挙動確認
                {
                    "left": 0.5,
                    "top": 0.5,
                    "width": 0.2,
                    "height": 0.2,
                    "confidence": 90.0,
                },
                0,
                0,
                (0, 0, 0, 0),
                "zero_image_size",
            ),
        ],
    )
    def test_to_pixel_coordinates(
        self,
        bbox: CatBoundingBox,
        image_width: int,
        image_height: int,
        expected_tuple: tuple[int, int, int, int],
        test_id: str,
    ) -> None:
        """to_pixel_coordinates関数が様々なケースで正しく動作すること"""
        # Act
        result = to_pixel_coordinates(bbox, image_width, image_height)

        # Assert
        assert result == expected_tuple
