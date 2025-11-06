# 絶対厳守：編集前に必ずAI実装ルールを読む
from dataclasses import dataclass

from domain.cat_bounding_box import CatBoundingBox, to_pixel_coordinates


@dataclass
class TextPositionResult:
    """
    テキスト配置計算の結果

    Attributes:
        x: X座標（描画位置）
        y: Y座標（描画位置）
        position_name: 配置位置の名前（例: "center", "top-left"）
        score: スコア（猫との重なりが少ないほど高い）
        reason: 配置理由（例: "no_cat_detected"）
    """

    x: float
    y: float
    position_name: str
    score: float
    reason: str | None = None


class TextPositionCalculator:
    """
    猫の位置を避けた最適なテキスト配置位置を計算するドメインサービス

    責務:
    - 画像内の複数の候補位置を定義
    - 猫との重なりを最小化する位置を選択
    """

    def calculate(
        self,
        image_width: int,
        image_height: int,
        text_bbox: tuple[float, float, float, float],
        cat_boxes: list[CatBoundingBox],
    ) -> TextPositionResult:
        """
        猫の位置を避けた最適なテキスト配置位置を計算

        Args:
            image_width: 画像の幅
            image_height: 画像の高さ
            text_bbox: (0, 0)を基準としたテキスト全体のbbox (left, top, right, bottom)
                      draw.textbboxの結果を組み合わせて計算したもの
            cat_boxes: 猫のバウンディングボックスのリスト

        Returns:
            TextPositionResult: テキストの描画位置と配置情報
        """
        bbox_left, bbox_top, bbox_right, bbox_bottom = text_bbox
        text_width = bbox_right - bbox_left
        text_height = bbox_bottom - bbox_top

        # bbox の中心のオフセット
        bbox_center_x = (bbox_left + bbox_right) / 2
        bbox_center_y = (bbox_top + bbox_bottom) / 2

        # 配置候補の「視覚的な中心位置」を定義（画像サイズの相対値）
        candidate_centers = [
            ("center", image_width / 2, image_height / 2),
            ("bottom", image_width / 2, image_height * 0.85 - text_height / 2),
            (
                "bottom-right",
                image_width - image_width * 0.1 - text_width / 2,
                image_height * 0.85 - text_height / 2,
            ),
            (
                "bottom-left",
                image_width * 0.1 + text_width / 2,
                image_height * 0.85 - text_height / 2,
            ),
            ("top", image_width / 2, image_height * 0.15 + text_height / 2),
            (
                "top-left",
                image_width * 0.1 + text_width / 2,
                image_height * 0.15 + text_height / 2,
            ),
            (
                "top-right",
                image_width - image_width * 0.1 - text_width / 2,
                image_height * 0.15 + text_height / 2,
            ),
        ]

        # 各中心位置から実際の描画位置を計算
        candidates = [
            (name, center_x - bbox_center_x, center_y - bbox_center_y)
            for name, center_x, center_y in candidate_centers
        ]

        # 猫が検出されていない場合は中央配置
        if not cat_boxes:
            center_name, center_x, center_y = next(
                (name, x, y) for name, x, y in candidates if name == "center"
            )
            return TextPositionResult(
                x=center_x,
                y=center_y,
                position_name=center_name,
                score=0.0,
                reason="no_cat_detected",
            )

        # 猫の座標をピクセル座標に変換
        cat_boxes_px = [
            to_pixel_coordinates(box, image_width, image_height) for box in cat_boxes
        ]

        # 各候補位置での重なりを計算
        best_position_name = "center"
        best_position_x = 0.0
        best_position_y = 0.0
        best_score = float("-inf")

        for name, x, y in candidates:
            # 画像境界内に収まるように調整
            x = max(-bbox_left, min(x, image_width - text_width - bbox_left))
            y = max(-bbox_top, min(y, image_height - text_height - bbox_top))

            # 実際の描画時の bbox を計算
            actual_bbox = (
                x + bbox_left,
                y + bbox_top,
                x + bbox_right,
                y + bbox_bottom,
            )

            # すべての猫との重なりの合計を計算
            total_overlap = 0.0

            for cat_left, cat_top, cat_right, cat_bottom in cat_boxes_px:
                # 重なり領域を計算
                inter_left = max(actual_bbox[0], cat_left)
                inter_top = max(actual_bbox[1], cat_top)
                inter_right = min(actual_bbox[2], cat_right)
                inter_bottom = min(actual_bbox[3], cat_bottom)

                # 重なりがある場合
                if inter_left < inter_right and inter_top < inter_bottom:
                    overlap_area = (inter_right - inter_left) * (
                        inter_bottom - inter_top
                    )
                    total_overlap -= overlap_area  # 負の値で重なりを表現

            # 重なりの合計が最小（0に最も近い負の値）の位置を選択
            if total_overlap > best_score:
                best_score = total_overlap
                best_position_x = x
                best_position_y = y
                best_position_name = name

        return TextPositionResult(
            x=best_position_x,
            y=best_position_y,
            position_name=best_position_name,
            score=best_score,
            reason=None,
        )
