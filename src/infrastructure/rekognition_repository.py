# 絶対厳守：編集前に必ずAI実装ルールを読む
import boto3
from mypy_boto3_rekognition import RekognitionClient

from domain.cat_bounding_box import CatBoundingBox
from domain.cat_detection_repository_interface import CatDetectionRepositoryInterface
from log.logging import AppLogger


def create_rekognition_repository(logger: AppLogger) -> CatDetectionRepositoryInterface:
    return RekognitionRepository(logger)


class RekognitionRepository(CatDetectionRepositoryInterface):
    # 信頼度の閾値（80%以上を採用）
    CONFIDENCE_THRESHOLD = 80.0

    def __init__(self, logger: AppLogger) -> None:
        self.rekognition_client: RekognitionClient = boto3.client("rekognition")
        self.logger = logger

    def detect_cats(self, bucket_name: str, object_key: str) -> list[CatBoundingBox]:
        try:
            response = self.rekognition_client.detect_labels(
                Image={"S3Object": {"Bucket": bucket_name, "Name": object_key}},
                MaxLabels=50,  # 十分な数のラベルを取得
                MinConfidence=self.CONFIDENCE_THRESHOLD,
                Features=["GENERAL_LABELS"],  # 一般的なラベル検出
            )

            cat_boxes: list[CatBoundingBox] = []

            for label in response.get("Labels", []):
                # "Cat" ラベルを探す
                if label["Name"] == "Cat":
                    self.logger.info(
                        f"猫検出: 信頼度={label['Confidence']:.2f}%, "
                        f"インスタンス数={len(label.get('Instances', []))}"
                    )

                    # Instances に BoundingBox 情報が含まれる
                    for instance in label.get("Instances", []):
                        if "BoundingBox" in instance:
                            bbox = instance["BoundingBox"]

                            # インスタンスのConfidenceがない場合はラベルのConfidenceを使用
                            confidence = instance.get("Confidence")
                            if confidence is None:
                                confidence = label.get("Confidence")
                                if confidence is None:
                                    self.logger.warning(
                                        "インスタンスとラベルの両方にConfidenceがありません。スキップします。"
                                    )
                                    continue

                            cat_box: CatBoundingBox = {
                                "left": bbox["Left"],
                                "top": bbox["Top"],
                                "width": bbox["Width"],
                                "height": bbox["Height"],
                                "confidence": float(confidence),
                            }
                            cat_boxes.append(cat_box)

            if not cat_boxes:
                self.logger.warning("猫が検出されませんでした")

            return cat_boxes

        except Exception as e:
            self.logger.error(f"Rekognition API呼び出しエラー: {e}", exc_info=True)
            raise
