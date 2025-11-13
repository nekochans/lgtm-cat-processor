#!/usr/bin/env python3
# 絶対厳守：編集前に必ずAI実装ルールを読む
"""
既存のLGTM画像の初期インデックスを作成するスクリプト

DBに登録されている全LGTM画像に対してLambda関数を実行し、
S3 Vectorsインデックスを作成します。
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# プロジェクトのモデルをインポート
from src.infrastructure.lgtm_image import LgtmImage


def setup_logging(log_dir: str = "logs") -> str:
    """
    ロギング設定を行い、コンソールとファイルの両方に出力

    Args:
        log_dir: ログファイルを保存するディレクトリ

    Returns:
        ログファイルのパス
    """
    # ログディレクトリ作成
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # ログファイル名（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"create_initial_index_{timestamp}.log"

    # ロガー設定
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # フォーマッター
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ファイルハンドラー
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # ハンドラーを追加
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return str(log_file)


logger = logging.getLogger(__name__)


def get_env_var(var_name: str) -> str:
    """
    環境変数を取得

    Args:
        var_name: 環境変数名

    Returns:
        環境変数の値

    Raises:
        ValueError: 環境変数が設定されていない場合
    """
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"環境変数 {var_name} が設定されていません")
    return value


class ImageIndexCreator:
    """画像インデックス作成クラス"""

    def __init__(
        self,
        bucket_name: str,
        lambda_function_name: str,
        aws_profile: str | None = None,
    ) -> None:
        """
        初期化

        Args:
            bucket_name: S3バケット名
            lambda_function_name: Lambda関数名
            aws_profile: AWSプロファイル名(Noneの場合はデフォルトプロファイルを使用)
        """
        self.bucket_name = bucket_name
        self.lambda_function_name = lambda_function_name

        # DB接続情報を環境変数から取得
        db_host = get_env_var("DB_HOSTNAME")
        db_user = get_env_var("DB_USERNAME")
        db_password = get_env_var("DB_PASSWORD")
        db_name = get_env_var("DB_NAME")

        # DB接続
        connection_string = (
            f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
        )
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # AWS クライアント初期化
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session()
        self.lambda_client = session.client("lambda")

        # 統計情報
        self.total_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.skipped_count = 0

    def fetch_all_images(self) -> list[tuple[int, str, str]]:
        """
        DBから全LGTM画像情報を取得

        Returns:
            (id, path, filename)のタプルのリスト
        """
        logger.info("DBから全LGTM画像情報を取得中...")

        session: Session = self.SessionLocal()
        try:
            images = session.query(
                LgtmImage.id, LgtmImage.path, LgtmImage.filename
            ).all()

            logger.info(f"取得完了: {len(images)}件の画像が見つかりました")
            return [(img.id, img.path, img.filename) for img in images]

        except Exception as e:
            logger.error(f"DB取得エラー: {e}")
            raise
        finally:
            session.close()

    def invoke_lambda(
        self, image_id: int, path: str, filename: str, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Lambda関数を実行して画像インデックスを作成

        Args:
            image_id: 画像ID
            path: S3パス
            filename: ファイル名
            dry_run: ドライラン実行の場合True

        Returns:
            実行結果
        """
        # S3オブジェクトキーを構築
        object_key = f"{path}/{filename}.webp"

        payload = {
            "process": "createImageIndex",
            "image": {
                "bucketName": self.bucket_name,
                "objectKey": object_key,
                "databaseId": image_id,
            },
        }

        if dry_run:
            logger.info(f"[DRY RUN] Lambda実行: ID={image_id}, key={object_key}")
            return {"status": "skipped", "image_id": image_id, "object_key": object_key}

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            status_code = response["StatusCode"]
            response_payload = json.loads(response["Payload"].read())

            # 成功判定: AWS Lambda APIが成功し、Lambda関数内でエラーが発生していない
            is_success = status_code == 200 and response.get("FunctionError") is None

            if is_success:
                logger.info(f"✓ 成功: ID={image_id}, key={object_key}")
                return {
                    "status": "success",
                    "image_id": image_id,
                    "object_key": object_key,
                }
            else:
                # エラーログ出力
                function_error = response.get("FunctionError", "None")
                logger.error(
                    f"✗ 失敗: ID={image_id}, key={object_key} - FunctionError: {function_error}"
                )
                logger.error(
                    f"  レスポンス: {json.dumps(response_payload, ensure_ascii=False)}"
                )

                return {
                    "status": "failure",
                    "image_id": image_id,
                    "object_key": object_key,
                    "error": f"FunctionError: {function_error}",
                }

        except ClientError as e:
            logger.error(
                f"✗ Lambda実行エラー: ID={image_id}, key={object_key} - {str(e)}"
            )
            return {
                "status": "failure",
                "image_id": image_id,
                "object_key": object_key,
                "error": str(e),
            }
        except Exception as e:
            logger.error(
                f"✗ 予期しないエラー: ID={image_id}, key={object_key} - {type(e).__name__}: {str(e)}"
            )
            return {
                "status": "failure",
                "image_id": image_id,
                "object_key": object_key,
                "error": str(e),
            }

    def create_all_indexes(
        self,
        images: list[tuple[int, str, str]],
        dry_run: bool = False,
    ) -> None:
        """
        全画像のインデックスを逐次的に作成

        Args:
            images: (id, path, filename)のタプルのリスト
            dry_run: ドライラン実行の場合True
        """
        self.total_count = len(images)

        if self.total_count == 0:
            logger.warning("処理対象の画像がありません")
            return

        logger.info(f"処理開始: {self.total_count}件の画像を処理します")
        if dry_run:
            logger.info("【ドライランモード】実際のLambda実行は行いません")

        for image_id, path, filename in images:
            result = self.invoke_lambda(image_id, path, filename, dry_run)

            if result["status"] == "success":
                self.success_count += 1
            elif result["status"] == "failure":
                self.failure_count += 1
            elif result["status"] == "skipped":
                self.skipped_count += 1

            # 進捗表示
            processed = self.success_count + self.failure_count + self.skipped_count
            logger.info(
                f"進捗: {processed}/{self.total_count} "
                f"(成功: {self.success_count}, 失敗: {self.failure_count}, ドライラン: {self.skipped_count})"
            )

    def print_summary(self) -> None:
        """実行結果のサマリーを出力"""
        logger.info("=" * 60)
        logger.info("実行結果サマリー")
        logger.info("=" * 60)
        logger.info(f"総件数:     {self.total_count}")
        logger.info(f"成功:       {self.success_count}")
        logger.info(f"失敗:       {self.failure_count}")
        logger.info(f"ドライラン: {self.skipped_count}")
        logger.info("=" * 60)


def main() -> None:
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="既存のLGTM画像の初期インデックスを作成するスクリプト"
    )

    parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="S3バケット名（例: stg-lgtmeow-images）",
    )

    parser.add_argument(
        "--lambda-function",
        type=str,
        required=True,
        help="Lambda関数名（例: stg-lgtm-image-processor）",
    )

    parser.add_argument(
        "--profile",
        type=str,
        help="AWSプロファイル名（指定しない場合はデフォルトプロファイルを使用）",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン実行（実際のLambda実行は行わない）",
    )

    args = parser.parse_args()

    # ロギング設定
    log_file = setup_logging()
    logger.info("=" * 60)
    logger.info("LGTM画像初期インデックス作成スクリプト開始")
    logger.info("=" * 60)
    logger.info(f"ログファイル: {log_file}")
    logger.info(f"バケット: {args.bucket}")
    logger.info(f"Lambda関数: {args.lambda_function}")
    if args.profile:
        logger.info(f"AWSプロファイル: {args.profile}")
    logger.info("=" * 60)

    try:
        # 環境変数の存在確認
        logger.info("DB接続情報を環境変数から取得中...")
        get_env_var("DB_HOSTNAME")
        get_env_var("DB_USERNAME")
        get_env_var("DB_PASSWORD")
        get_env_var("DB_NAME")
        logger.info("DB接続情報の取得完了")

        creator = ImageIndexCreator(
            bucket_name=args.bucket,
            lambda_function_name=args.lambda_function,
            aws_profile=args.profile,
        )

        # DB から全画像取得
        images = creator.fetch_all_images()

        # インデックス作成実行
        creator.create_all_indexes(images, dry_run=args.dry_run)

        # サマリー出力
        creator.print_summary()

        # 失敗がある場合は終了コード1
        if creator.failure_count > 0:
            sys.exit(1)

    except ValueError as e:
        logger.error(f"環境変数エラー: {e}")
        logger.error("必要な環境変数: DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_NAME")
        sys.exit(1)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
