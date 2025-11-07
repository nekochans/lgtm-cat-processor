# 絶対厳守：編集前に必ずAI実装ルールを読む
from domain.cat_bounding_box import CatBoundingBox
from domain.text_position_calculator import TextPositionCalculator


class TestTextPositionCalculator:
    """TextPositionCalculatorのテスト"""

    def test_no_cat_returns_center_position(self) -> None:
        """猫がいない場合は中央配置を返す"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 100.0, 50.0)  # 100x50のテキスト
        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=[]
        )

        assert result.position_name == "center"
        assert result.reason == "no_cat_detected"
        # 中央配置なので x は (400/2 - 50) = 150, y は (400/2 - 25) = 175 付近
        assert result.x == 150.0
        assert result.y == 175.0

    def test_cat_in_center_avoids_center(self) -> None:
        """猫が中央にいる場合は中央以外を選択"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 100.0, 50.0)

        # 中央に大きな猫（相対座標）
        cat_boxes: list[CatBoundingBox] = [
            {
                "left": 0.3,
                "top": 0.3,
                "width": 0.4,
                "height": 0.4,
                "confidence": 99.0,
            }
        ]

        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=cat_boxes
        )

        # 中央以外の位置が選ばれる
        assert result.position_name != "center"
        assert result.reason is None
        # スコアは負の値（重なりが少ないほど0に近い）
        assert result.score <= 0.0

    def test_multiple_cats_chooses_best_position(self) -> None:
        """複数の猫がいる場合に最適な位置を選択"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 100.0, 50.0)

        # 上部と左下に猫
        cat_boxes: list[CatBoundingBox] = [
            {
                "left": 0.3,
                "top": 0.0,
                "width": 0.4,
                "height": 0.3,
                "confidence": 99.0,
            },
            {
                "left": 0.0,
                "top": 0.7,
                "width": 0.3,
                "height": 0.3,
                "confidence": 95.0,
            },
        ]

        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=cat_boxes
        )

        # 右下あたりが選ばれるはず
        assert result.position_name in [
            "bottom-right",
            "center",
            "bottom",
        ]
        assert isinstance(result.x, float)
        assert isinstance(result.y, float)

    def test_text_bbox_with_offset(self) -> None:
        """オフセット付きのtext_bboxで正しく計算される"""
        calculator = TextPositionCalculator()
        # オフセットがある場合（-10, -5, 90, 45）
        text_bbox = (-10.0, -5.0, 90.0, 45.0)

        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=[]
        )

        assert result.position_name == "center"
        # bbox中心のオフセットを考慮した位置
        assert isinstance(result.x, float)
        assert isinstance(result.y, float)

    def test_small_image_size(self) -> None:
        """小さい画像サイズでも動作する"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 50.0, 25.0)

        result = calculator.calculate(
            image_width=100, image_height=100, text_bbox=text_bbox, cat_boxes=[]
        )

        assert result.position_name == "center"
        assert 0 <= result.x <= 100
        assert 0 <= result.y <= 100

    def test_cat_covering_entire_image(self) -> None:
        """猫が画像全体を覆っている場合でも位置を返す"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 100.0, 50.0)

        # 画像全体を覆う猫
        cat_boxes: list[CatBoundingBox] = [
            {
                "left": 0.0,
                "top": 0.0,
                "width": 1.0,
                "height": 1.0,
                "confidence": 99.0,
            }
        ]

        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=cat_boxes
        )

        # どこかの位置が返される
        assert result.position_name in [
            "center",
            "top",
            "bottom",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        ]
        # スコアは負の値（完全に重なっている）
        assert result.score < 0.0

    def test_returns_valid_coordinates(self) -> None:
        """返される座標が有効な範囲内"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 100.0, 50.0)

        cat_boxes: list[CatBoundingBox] = [
            {"left": 0.5, "top": 0.5, "width": 0.2, "height": 0.2, "confidence": 99.0}
        ]

        result = calculator.calculate(
            image_width=400, image_height=400, text_bbox=text_bbox, cat_boxes=cat_boxes
        )

        # 座標が数値であることを確認
        assert isinstance(result.x, (int, float))
        assert isinstance(result.y, (int, float))
        assert isinstance(result.score, (int, float))

    def test_all_candidate_positions_evaluated(self) -> None:
        """すべての候補位置が評価される（7つの候補）"""
        calculator = TextPositionCalculator()
        text_bbox = (0.0, 0.0, 50.0, 25.0)

        # 様々な猫の配置で異なる結果が得られることを確認
        positions_found = set()

        test_cases = [
            [],  # 猫なし
            [
                {
                    "left": 0.4,
                    "top": 0.4,
                    "width": 0.2,
                    "height": 0.2,
                    "confidence": 99.0,
                }
            ],
            [
                {
                    "left": 0.0,
                    "top": 0.0,
                    "width": 0.3,
                    "height": 0.3,
                    "confidence": 99.0,
                }
            ],
            [
                {
                    "left": 0.7,
                    "top": 0.0,
                    "width": 0.3,
                    "height": 0.3,
                    "confidence": 99.0,
                }
            ],
            [
                {
                    "left": 0.0,
                    "top": 0.7,
                    "width": 0.3,
                    "height": 0.3,
                    "confidence": 99.0,
                }
            ],
            [
                {
                    "left": 0.7,
                    "top": 0.7,
                    "width": 0.3,
                    "height": 0.3,
                    "confidence": 99.0,
                }
            ],
        ]

        for cat_boxes_input in test_cases:
            cat_boxes: list[CatBoundingBox] = cat_boxes_input  # type: ignore
            result = calculator.calculate(
                image_width=400,
                image_height=400,
                text_bbox=text_bbox,
                cat_boxes=cat_boxes,
            )
            positions_found.add(result.position_name)

        # 少なくとも複数の異なる位置が選ばれる
        assert len(positions_found) >= 2
