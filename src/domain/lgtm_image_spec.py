# 絶対厳守：編集前に必ずAI実装ルールを読む
from dataclasses import dataclass


@dataclass(frozen=True)
class LgtmImageSpec:
    """
    LGTM画像生成の仕様を定義する値オブジェクト

    Attributes:
        max_size: リサイズ時の最大サイズ（px）
        lgtm_font_size: "LGTM"テキストのフォントサイズ（px）
        meow_font_size: "eow"テキストのフォントサイズ（px）
        lgtm_text: メインテキスト
        meow_text: サブテキスト
        output_format: 出力画像フォーマット
    """

    max_size: int = 400
    lgtm_font_size: int = 60
    meow_font_size: int = 30
    lgtm_text: str = "LGTM"
    meow_text: str = "eow"
    output_format: str = "WEBP"
