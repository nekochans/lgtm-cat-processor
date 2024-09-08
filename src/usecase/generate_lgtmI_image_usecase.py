import io
import os
from PIL import Image, ImageDraw, ImageFont
from domain.s3_repository_interface import S3RepositoryInterface


class GenerateLgtmImageUsecase:
    def __init__(
        self, s3repository: S3RepositoryInterface, bucket_name: str, object_key: str
    ) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.font_path = os.path.join(
            os.environ["LAMBDA_TASK_ROOT"], "fonts", "MPLUSRounded1c-Medium.ttf"
        )
        self.s3repository = s3repository

    def gemerate_lgtm_image(self, image_data: bytes) -> io.BytesIO:
        with Image.open(io.BytesIO(image_data)) as img:
            width, height = img.size

            # アスペクト比を維持しながら幅または高さを調整する
            if width > height:
                new_width = 400
                new_height = int((height / width) * new_width)
            else:
                new_height = 400
                new_width = int((width / height) * new_height)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(img)
            font_path = self.font_path
            font_lgtm = ImageFont.truetype(font_path, 60)
            font_meow = ImageFont.truetype(font_path, 30)

            # テキストのサイズを計測
            lgtm_text = "LGTM"
            meow_text = "eow"

            bbox_lgtm = draw.textbbox((0, 0), lgtm_text, font=font_lgtm)
            bbox_meow = draw.textbbox((0, 0), meow_text, font=font_meow)

            text_width_lgtm = bbox_lgtm[2] - bbox_lgtm[0]
            text_height_lgtm = bbox_lgtm[3] - bbox_lgtm[1]
            text_width_meow = bbox_meow[2] - bbox_meow[0]
            text_height_meow = bbox_meow[3] - bbox_meow[1]

            _, descender = font_lgtm.getmetrics()

            # 画像の中央にテキストを配置するための座標計算
            total_width = text_width_lgtm + text_width_meow
            x_lgtm = (new_width / 2) - (total_width / 2)
            x_meow = x_lgtm + text_width_lgtm

            y_lgtm = (new_height / 2) - (text_height_lgtm / 2) - descender
            y_meow = y_lgtm + text_height_lgtm - text_height_meow

            # テキストを描画
            draw.text((x_lgtm, y_lgtm), lgtm_text, font=font_lgtm, fill=(255, 255, 255))
            draw.text((x_meow, y_meow), meow_text, font=font_meow, fill=(255, 255, 255))

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer

    def execute(self) -> None:
        try:
            cat_image = self.s3repository.fetch_image(self.bucket_name, self.object_key)

            processed_image = self.gemerate_lgtm_image(cat_image)

            upload_bucket_name = os.getenv("GENERATE_LGTM_IMAGE_UPLOAD_BUCKET")
            if upload_bucket_name is None:
                raise ValueError(
                    "環境変数 GENERATE_LGTM_IMAGE_UPLOAD_BUCKET が設定されていません"
                )

            self.s3repository.upload_image(
                upload_bucket_name, self.object_key, processed_image
            )

        except ValueError as e:
            print(f"error: {e}")
            raise

        except Exception as e:
            print(f"Unexpected error: {e}")
            raise
