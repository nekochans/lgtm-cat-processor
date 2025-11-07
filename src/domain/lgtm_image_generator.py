# 絶対厳守：編集前に必ずAI実装ルールを読む
import io

from PIL import Image, ImageDraw, ImageFont

from domain.brightness_calculator import BrightnessCalculator
from domain.cat_detection_repository_interface import CatDetectionRepositoryInterface
from domain.lgtm_image_spec import LgtmImageSpec
from domain.text_position_calculator import TextPositionCalculator
from log.logging import AppLogger


class LgtmImageGenerator:
    """
    LGTM画像を生成するドメインサービス

    責務:
    - 猫の検出
    - 画像のリサイズ（アスペクト比維持）
    - テキストの描画位置と色を計算
    - LGTM画像の生成
    """

    def __init__(
        self,
        cat_detector: CatDetectionRepositoryInterface,
        font_path: str,
        logger: AppLogger,
    ) -> None:
        self.cat_detector = cat_detector
        self.font_path = font_path
        self.logger = logger
        self.brightness_calculator = BrightnessCalculator()
        self.text_position_calculator = TextPositionCalculator()

    def calculate_resize_dimensions(
        self, width: int, height: int, max_size: int
    ) -> tuple[int, int]:
        """
        アスペクト比を維持したリサイズ寸法を計算

        Args:
            width: 元画像の幅
            height: 元画像の高さ
            max_size: 最大サイズ

        Returns:
            (new_width, new_height) リサイズ後の寸法

        Raises:
            ValueError: width または height が 0 以下の場合
        """
        if width <= 0 or height <= 0:
            raise ValueError(
                f"width and height must be positive integers, got width={width}, height={height}"
            )

        if width > height:
            new_width = max_size
            new_height = int((height / width) * new_width)
        else:
            new_height = max_size
            new_width = int((width / height) * new_height)
        return new_width, new_height

    def generate(
        self,
        original_image: bytes,
        bucket_name: str,
        object_key: str,
        spec: LgtmImageSpec | None = None,
    ) -> io.BytesIO:
        """
        LGTM画像を生成

        Args:
            original_image: 元画像のバイトデータ
            bucket_name: S3バケット名（猫検出に使用）
            object_key: S3オブジェクトキー（猫検出に使用）
            spec: LGTM画像の仕様（省略時はデフォルト値）

        Returns:
            生成されたLGTM画像のバイトストリーム（WebP形式）
        """
        if spec is None:
            spec = LgtmImageSpec()

        # 猫を検出（エラーが発生した場合は空リストとして処理）
        try:
            cat_boxes = self.cat_detector.detect_cats(bucket_name, object_key)
            self.logger.info(f"猫を{len(cat_boxes)}匹検出しました")
        except Exception as e:
            self.logger.error(f"猫検出に失敗、中央配置にフォールバック: {e}")
            cat_boxes = []

        with Image.open(io.BytesIO(original_image)) as img:
            width, height = img.size

            # アスペクト比を維持しながらリサイズ
            new_width, new_height = self.calculate_resize_dimensions(
                width, height, spec.max_size
            )
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(img)
            font_lgtm = ImageFont.truetype(self.font_path, spec.lgtm_font_size)
            font_meow = ImageFont.truetype(self.font_path, spec.meow_font_size)

            # テキストのサイズを計測
            bbox_lgtm = draw.textbbox((0, 0), spec.lgtm_text, font=font_lgtm)
            bbox_meow = draw.textbbox((0, 0), spec.meow_text, font=font_meow)

            text_width_lgtm = bbox_lgtm[2] - bbox_lgtm[0]
            text_height_lgtm = bbox_lgtm[3] - bbox_lgtm[1]
            text_width_meow = bbox_meow[2] - bbox_meow[0]
            text_height_meow = bbox_meow[3] - bbox_meow[1]

            # テキスト全体のbbox（LGTMとeowを合わせた範囲）
            total_text_bbox = (
                bbox_lgtm[0],
                bbox_lgtm[1],
                bbox_lgtm[0] + text_width_lgtm + text_width_meow,
                bbox_lgtm[3],
            )

            # 猫の位置を避けてテキストの最適位置を計算
            position_result = self.text_position_calculator.calculate(
                new_width, new_height, total_text_bbox, cat_boxes
            )

            x_lgtm, y_lgtm = position_result.x, position_result.y

            # meowの位置を計算
            x_meow = x_lgtm + text_width_lgtm
            y_meow = y_lgtm + text_height_lgtm - text_height_meow

            # テキスト描画範囲のbboxを作成（輝度計算用）
            left = int(x_lgtm + bbox_lgtm[0])
            top = int(y_lgtm + bbox_lgtm[1])
            right = int(x_lgtm + bbox_lgtm[0] + text_width_lgtm + text_width_meow)
            bottom = int(y_lgtm + bbox_lgtm[3])
            text_bbox = (left, top, right, bottom)

            # 背景の輝度を算出してテキスト色を決定
            brightness = self.brightness_calculator.get_average_brightness(
                img, text_bbox
            )
            text_color = self.brightness_calculator.choose_text_color(brightness)

            # テキストを描画
            draw.text((x_lgtm, y_lgtm), spec.lgtm_text, font=font_lgtm, fill=text_color)
            draw.text((x_meow, y_meow), spec.meow_text, font=font_meow, fill=text_color)

            # WebP形式でバッファに保存
            buffer = io.BytesIO()
            img.save(buffer, format=spec.output_format)
            buffer.seek(0)
            return buffer
