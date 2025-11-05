# 絶対厳守：編集前に必ずAI実装ルールを読む
import io
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from domain.object_storage_repository_interface import ObjectStorageRepositoryInterface
from log.logging import AppLogger


def build_upload_object_key(object_key: str) -> str:
    directory, filename = os.path.split(object_key)
    imagename_without_ext = os.path.splitext(filename)[0]
    return os.path.join(directory, imagename_without_ext + ".webp")


class GenerateLgtmImageUsecase:
    # 輝度の閾値（0-255）。この値より大きい場合は黒文字、小さい場合は白文字
    BRIGHTNESS_THRESHOLD = 160

    # 猫顔検出のパラメータ
    # scaleFactor: 画像を縮小する際のスケール係数（1.05 = 5%ずつ縮小、より細かく検出）
    FACE_DETECTION_SCALE_FACTOR = 1.05
    # minNeighbors: 検出を確定するために必要な近傍矩形の数（小さいほど検出感度が高い）
    FACE_DETECTION_MIN_NEIGHBORS = 1
    # minSize: 検出する顔の最小サイズ（ピクセル）
    FACE_DETECTION_MIN_SIZE = (20, 20)

    def __init__(
        self,
        s3repository: ObjectStorageRepositoryInterface,
        bucket_name: str,
        object_key: str,
        logger: AppLogger,
    ) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.font_path = os.path.join(
            os.environ["LAMBDA_TASK_ROOT"], "fonts", "MPLUSRounded1c-Medium.ttf"
        )
        self.s3repository = s3repository
        self.logger = logger

    def get_average_brightness(
        self, img: Image.Image, bbox: tuple[int, int, int, int]
    ) -> float:
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
            self.logger.warning(
                f"輝度測定領域が無効です: bbox=({left}, {top}, {right}, {bottom}), "
                f"image_size=({img_width}, {img_height})"
            )
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

    def choose_text_color_by_brightness(
        self, brightness: float, threshold: int = BRIGHTNESS_THRESHOLD
    ) -> tuple[int, int, int]:
        # 輝度が閾値より大きい（明るい）場合は黒、それ以外は白
        return (0, 0, 0) if brightness > threshold else (255, 255, 255)

    def detect_cat_faces(self, image_data: bytes) -> list[tuple[int, int, int, int]]:
        """
        猫の顔を検出する

        Args:
            image_data: 画像のバイトデータ

        Returns:
            list of (x, y, width, height) tuples - 検出された猫の顔の座標とサイズ
        """
        # バイトデータをnumpy配列に変換
        nparr = np.frombuffer(image_data, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_cv is None:
            self.logger.warning("画像のデコードに失敗しました。顔検出をスキップします")
            return []

        img_height, img_width = img_cv.shape[:2]
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 画像サイズに応じた最小顔サイズを計算
        # 短辺の3%を最小サイズとする（バランスを取った値）
        min_dimension = min(img_width, img_height)
        dynamic_min_size = int(min_dimension * 0.03)
        # 最小値を20pxに制限（極端に小さい画像への対応）
        dynamic_min_size = max(20, dynamic_min_size)
        min_face_size = (dynamic_min_size, dynamic_min_size)

        self.logger.info(
            "顔検出パラメータ",
            extra={
                "image_size": (img_width, img_height),
                "min_dimension": min_dimension,
                "dynamic_min_size": dynamic_min_size,
                "min_face_size": min_face_size,
            },
        )

        # カスケードファイルのパス
        cascade_path = os.path.join(
            os.getenv("LAMBDA_TASK_ROOT", "."),
            "cascades",
            "haarcascade_frontalcatface_extended.xml",
        )

        cat_cascade = cv2.CascadeClassifier(cascade_path)

        # カスケードファイルのロード失敗をチェック
        if cat_cascade.empty():
            self.logger.warning(
                f"カスケードファイルの読み込みに失敗しました: {cascade_path}. 顔検出をスキップします"
            )
            return []

        # 顔検出（動的に計算した最小サイズを使用）
        faces = cat_cascade.detectMultiScale(
            gray,
            scaleFactor=self.FACE_DETECTION_SCALE_FACTOR,
            minNeighbors=self.FACE_DETECTION_MIN_NEIGHBORS,
            minSize=min_face_size,
        )

        faces_list = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

        self.logger.info(
            "顔検出の詳細",
            extra={
                "detected_faces_count": len(faces_list),
                "detected_faces": faces_list,
            },
        )

        return faces_list

    def calculate_overlap(
        self,
        text_bbox: tuple[float, float, float, float],
        face_bbox: tuple[int, int, int, int],
    ) -> float:
        """
        2つのbboxの重なり度合いを計算（負の重なり面積を返す）

        Args:
            text_bbox: (x_min, y_min, x_max, y_max) テキストのbbox
            face_bbox: (x, y, width, height) 猫の顔のbbox

        Returns:
            重なり面積の負の値（重なりが少ないほど大きい値）
            重なりがない場合は float('inf')
        """
        text_x_min, text_y_min, text_x_max, text_y_max = text_bbox
        face_x_min, face_y_min, face_width, face_height = face_bbox
        face_x_max = face_x_min + face_width
        face_y_max = face_y_min + face_height

        # 重なり領域の計算
        inter_x_min = max(text_x_min, face_x_min)
        inter_y_min = max(text_y_min, face_y_min)
        inter_x_max = min(text_x_max, face_x_max)
        inter_y_max = min(text_y_max, face_y_max)

        if inter_x_min >= inter_x_max or inter_y_min >= inter_y_max:
            return float("inf")  # 重なりなし

        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        return -inter_area  # 重なりが少ないほど大きい値

    def calculate_text_position(
        self,
        image_width: int,
        image_height: int,
        text_bbox: tuple[float, float, float, float],
        cat_faces: list[tuple[int, int, int, int]],
    ) -> tuple[float, float]:
        """
        猫の顔を避けてテキストの最適位置を計算

        Args:
            image_width: 画像の幅
            image_height: 画像の高さ
            text_bbox: テキストのbbox (left, top, right, bottom)
                      textbbox((0, 0), text, font) の結果
            cat_faces: 検出された猫の顔のリスト [(x, y, w, h), ...]

        Returns:
            (x, y) テキストの描画位置（draw.textに渡す座標）
        """
        bbox_left, bbox_top, bbox_right, bbox_bottom = text_bbox
        text_width = bbox_right - bbox_left
        text_height = bbox_bottom - bbox_top

        # bbox の中心のオフセット
        bbox_center_x = (bbox_left + bbox_right) / 2
        bbox_center_y = (bbox_top + bbox_bottom) / 2

        # 配置候補の「視覚的な中心位置」を定義
        candidate_centers = [
            ("bottom", image_width / 2, image_height * 0.85 - text_height / 2),
            (
                "bottom-left",
                image_width * 0.1 + text_width / 2,
                image_height * 0.85 - text_height / 2,
            ),
            (
                "bottom-right",
                image_width - image_width * 0.1 - text_width / 2,
                image_height * 0.85 - text_height / 2,
            ),
            ("center", image_width / 2, image_height / 2),
        ]

        # 各中心位置から実際の描画位置を計算
        candidates = [
            (name, center_x - bbox_center_x, center_y - bbox_center_y)
            for name, center_x, center_y in candidate_centers
        ]

        # 猫の顔がない場合は中央
        if not cat_faces:
            center_x = image_width / 2
            center_y = image_height / 2
            x = center_x - bbox_center_x
            y = center_y - bbox_center_y
            self.logger.info(
                "テキストポジション決定",
                extra={
                    "position": "center",
                    "reason": "no_cat_faces",
                    "x": x,
                    "y": y,
                    "bbox_center_x": bbox_center_x,
                    "bbox_center_y": bbox_center_y,
                    "image_center_y": center_y,
                },
            )
            return x, y

        # 各候補位置と顔の重なりをチェック
        best_position = None
        best_position_name = None
        best_score = float("-inf")

        candidates_debug = []

        for name, x, y in candidates:
            # 画像境界内に収まるように調整
            x = max(-bbox_left, min(x, image_width - text_width - bbox_left))
            y = max(-bbox_top, min(y, image_height - text_height - bbox_top))

            # 実際の描画時の bbox を計算
            actual_bbox = (x + bbox_left, y + bbox_top, x + bbox_right, y + bbox_bottom)

            # すべての顔との重なりの合計を計算
            total_overlap = 0.0
            overlaps_detail = []
            for face in cat_faces:
                overlap = self.calculate_overlap(actual_bbox, face)
                overlaps_detail.append(
                    {
                        "face": face,
                        "overlap": overlap,
                    }
                )
                if overlap != float("inf"):  # 重なりがある場合のみ加算
                    total_overlap += overlap

            candidates_debug.append(
                {
                    "name": name,
                    "x": x,
                    "y": y,
                    "actual_bbox": actual_bbox,
                    "total_overlap": total_overlap,
                    "overlaps_detail": overlaps_detail,
                }
            )

            # 重なりの合計が最小（0に最も近い負の値）の位置を選択
            if total_overlap > best_score:
                best_score = total_overlap
                best_position = (x, y)
                best_position_name = name

        self.logger.info(
            "候補位置の評価結果",
            extra={
                "candidates": candidates_debug,
            },
        )

        # デフォルトは下部中央
        if best_position:
            self.logger.info(
                "テキストポジション決定",
                extra={
                    "position": best_position_name,
                    "x": best_position[0],
                    "y": best_position[1],
                    "score": best_score,
                    "cat_faces_count": len(cat_faces),
                },
            )
            return best_position
        else:
            # デフォルト: 下部中央
            center_x = image_width / 2
            center_y = image_height * 0.85
            x = center_x - bbox_center_x
            y = center_y - text_height / 2 - bbox_top
            self.logger.info(
                "テキストポジション決定",
                extra={
                    "position": "bottom",
                    "reason": "default",
                    "x": x,
                    "y": y,
                },
            )
            return x, y

    def gemerate_lgtm_image(self, image_data: bytes) -> io.BytesIO:
        # 猫の顔を検出（リサイズ前の画像で検出）
        cat_faces_original = self.detect_cat_faces(image_data)

        with Image.open(io.BytesIO(image_data)) as img:
            original_width, original_height = img.size

            # アスペクト比を維持しながら幅または高さを調整する
            if original_width > original_height:
                new_width = 400
                new_height = int((original_height / original_width) * new_width)
            else:
                new_height = 400
                new_width = int((original_width / original_height) * new_height)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 検出された顔の座標をリサイズ後の画像サイズに合わせてスケーリング
            scale_x = new_width / original_width
            scale_y = new_height / original_height
            cat_faces = [
                (
                    int(x * scale_x),
                    int(y * scale_y),
                    int(w * scale_x),
                    int(h * scale_y),
                )
                for (x, y, w, h) in cat_faces_original
            ]

            self.logger.info(
                "猫の顔検出結果",
                extra={
                    "original_size": (original_width, original_height),
                    "resized_size": (new_width, new_height),
                    "scale": (scale_x, scale_y),
                    "cat_faces_original": cat_faces_original,
                    "cat_faces_scaled": cat_faces,
                },
            )

            draw = ImageDraw.Draw(img)
            font_path = self.font_path
            font_lgtm = ImageFont.truetype(font_path, 60)
            font_meow = ImageFont.truetype(font_path, 30)

            # テキストのサイズを計測
            lgtm_text = "LGTM"
            meow_text = "eow"

            bbox_lgtm = draw.textbbox((0, 0), lgtm_text, font=font_lgtm)
            bbox_meow = draw.textbbox((0, 0), meow_text, font=font_meow)

            self.logger.info(
                "テキストbbox情報",
                extra={
                    "bbox_lgtm": bbox_lgtm,
                    "bbox_meow": bbox_meow,
                    "image_size": (new_width, new_height),
                },
            )

            text_width_lgtm = bbox_lgtm[2] - bbox_lgtm[0]
            text_height_lgtm = bbox_lgtm[3] - bbox_lgtm[1]
            text_width_meow = bbox_meow[2] - bbox_meow[0]
            text_height_meow = bbox_meow[3] - bbox_meow[1]

            # テキスト全体のbbox（LGTMとeowを合わせた範囲）
            total_bbox = (
                bbox_lgtm[0],
                bbox_lgtm[1],
                bbox_lgtm[0] + text_width_lgtm + text_width_meow,
                bbox_lgtm[3],
            )

            # 猫の顔を避けてテキストの最適位置を計算
            x_lgtm, y_lgtm = self.calculate_text_position(
                new_width, new_height, total_bbox, cat_faces
            )

            # meowの位置を計算
            x_meow = x_lgtm + text_width_lgtm
            y_meow = y_lgtm + text_height_lgtm - text_height_meow

            # テキスト描画範囲のbboxを作成（輝度計算用）
            left = int(x_lgtm + bbox_lgtm[0])
            top = int(y_lgtm + bbox_lgtm[1])
            right = int(x_lgtm + bbox_lgtm[0] + text_width_lgtm + text_width_meow)
            bottom = int(y_lgtm + bbox_lgtm[3])
            text_bbox = (left, top, right, bottom)

            # 背景の輝度を算出
            brightness = self.get_average_brightness(img, text_bbox)
            text_color = self.choose_text_color_by_brightness(brightness)

            # テキストを描画
            draw.text((x_lgtm, y_lgtm), lgtm_text, font=font_lgtm, fill=text_color)
            draw.text((x_meow, y_meow), meow_text, font=font_meow, fill=text_color)

            buffer = io.BytesIO()
            img.save(buffer, format="WEBP")
            buffer.seek(0)
            return buffer

    def execute(self) -> tuple[str, str]:
        self.logger.info("LGTM画像の作成を開始")
        try:
            cat_image = self.s3repository.fetch_image(self.bucket_name, self.object_key)

            processed_image = self.gemerate_lgtm_image(cat_image)

            upload_bucket_name = os.getenv("GENERATE_LGTM_IMAGE_UPLOAD_BUCKET")
            if upload_bucket_name is None:
                raise ValueError(
                    "環境変数 GENERATE_LGTM_IMAGE_UPLOAD_BUCKET が設定されていません"
                )

            upload_object_key = build_upload_object_key(self.object_key)

            self.s3repository.upload_image(
                upload_bucket_name, upload_object_key, processed_image
            )

            self.logger.info("LGTM画像の作成に成功")

            return upload_bucket_name, upload_object_key

        except ValueError as e:
            self.logger.error(e, exc_info=True)
            raise

        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise
