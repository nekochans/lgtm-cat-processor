# 絶対厳守：編集前に必ずAI実装ルールを読む
import math
from typing import TypedDict


class CatBoundingBox(TypedDict):
    """
    猫の検出領域を表すバウンディングボックス

    座標は画像の幅・高さに対する相対値（0.0 ～ 1.0）
    Amazon Rekognition の BoundingBox 形式に準拠
    """

    left: float  # 左端のX座標（0.0 ～ 1.0）
    top: float  # 上端のY座標（0.0 ～ 1.0）
    width: float  # 幅（0.0 ～ 1.0）
    height: float  # 高さ（0.0 ～ 1.0）
    confidence: float  # 信頼度（0.0 ～ 100.0）


def to_pixel_coordinates(
    bbox: CatBoundingBox, image_width: int, image_height: int
) -> tuple[int, int, int, int]:
    """
    ピクセル座標に変換

    Args:
        bbox: バウンディングボックス
        image_width: 画像の幅（ピクセル）
        image_height: 画像の高さ（ピクセル）

    Returns:
        (left_px, top_px, right_px, bottom_px) のタプル
    """
    left_px = math.floor(bbox["left"] * image_width)
    top_px = math.floor(bbox["top"] * image_height)
    right_px = math.ceil((bbox["left"] + bbox["width"]) * image_width)
    bottom_px = math.ceil((bbox["top"] + bbox["height"]) * image_height)
    return (left_px, top_px, right_px, bottom_px)
