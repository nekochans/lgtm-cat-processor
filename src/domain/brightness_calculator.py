# 絶対厳守：編集前に必ずAI実装ルールを読む
from PIL import Image

class BrightnessCalculator:
    """
    画像の輝度計算とテキスト色の選択を行うドメインサービス

    責務:
    - 指定領域の平均輝度を計算
    - 輝度に基づいた最適なテキスト色を決定
    """

    # 輝度の閾値(0-255)。この値より大きい場合は黒文字、小さい場合は白文字
    BRIGHTNESS_THRESHOLD = 160

    def get_average_brightness(
        self, img: Image.Image, bbox: tuple[int, int, int, int]
    ) -> float:
        """
        指定領域の平均輝度を計算

        Args:
            img: PIL画像オブジェクト
            bbox: (left, top, right, bottom) のピクセル座標

        Returns:
            平均輝度 (0.0 ~ 255.0)
            エラー時や無効な領域の場合は 0.0
        """
        left, top, right, bottom = bbox

        # bboxを画像サイズ内にクリッピング
        img_width, img_height = img.size
        left = max(0, min(left, img_width))
        top = max(0, min(top, img_height))
        right = max(0, min(right, img_width))
        bottom = max(0, min(bottom, img_height))

        # クリッピング後の幅と高さを計算
        width = right - left
        height = bottom - top

        # 空のまたはゼロ面積のbboxに対する防御的チェック
        if width <= 0 or height <= 0:
            return 0.0

        # 指定領域を切り出してグレースケール化
        cropped = img.crop((left, top, right, bottom)).convert("L")

        # 平均輝度を計算
        pixels = list(cropped.getdata())

        # 空のピクセルシーケンスに対する防御的チェック
        if len(pixels) == 0:
            return 0.0

        average_brightness = float(sum(pixels) / len(pixels))

        return average_brightness

    def choose_text_color(
        self, brightness: float, threshold: int | None = None
    ) -> tuple[int, int, int]:
        """
        輝度に基づいて最適なテキスト色を選択

        Args:
            brightness: 輝度値 (0.0 ~ 255.0)
            threshold: 閾値 (省略時は BRIGHTNESS_THRESHOLD を使用)

        Returns:
            RGB色のタプル: 明るい背景なら黒(0,0,0)、暗い背景なら白(255,255,255)
        """
        if threshold is None:
            threshold = self.BRIGHTNESS_THRESHOLD

        # 輝度が閾値より大きい(明るい)場合は黒、それ以外は白
        return (0, 0, 0) if brightness > threshold else (255, 255, 255)
