#!/usr/bin/env python3
"""
既存のLGTM画像を再生成するスクリプト

S3バケット内の全画像に対してLambda関数を実行し、
テキスト配置が最適化されたLGTM画像を再生成します。
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


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
    log_file = log_path / f"regenerate_{timestamp}.log"

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


class LgtmImageRegenerator:
    """LGTM画像再生成クラス"""

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

        # AWS クライアント初期化
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session()
        self.s3_client = session.client("s3")
        self.lambda_client = session.client("lambda")

        # 統計情報
        self.total_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.skipped_count = 0
        self.skipped_date_count = 0

    def list_all_objects(
        self,
        prefix: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[str]:
        """
        S3バケット内の全オブジェクトキーを取得

        Args:
            prefix: オブジェクトキーのプレフィックス
            start_date: 開始日(YYYY/MM/DD形式)
            end_date: 終了日(YYYY/MM/DD形式)

        Returns:
            オブジェクトキーのリスト
        """
        logger.info(f"バケット '{self.bucket_name}' からオブジェクトキーを取得中...")

        object_keys: list[str] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]

                    # 画像ファイルのみを対象(.jpeg、.jpg、.png)
                    if not key.lower().endswith((".jpeg", ".jpg", ".png")):
                        continue

                    # 期間フィルタリング
                    if start_date or end_date:
                        if not self._is_within_date_range(key, start_date, end_date):
                            self.skipped_date_count += 1
                            continue

                    object_keys.append(key)

            logger.info(f"取得完了: {len(object_keys)}件の画像が見つかりました")
            if self.skipped_date_count > 0:
                logger.info(f"期間外でスキップ: {self.skipped_date_count}件")

            return object_keys

        except ClientError as e:
            logger.error(f"S3オブジェクト取得エラー: {e}")
            raise

    def _is_within_date_range(
        self, object_key: str, start_date: str | None, end_date: str | None
    ) -> bool:
        """
        オブジェクトキーが指定期間内かチェック

        Args:
            object_key: オブジェクトキー（例: 2025/11/07/11/xxx.jpeg）
            start_date: 開始日（YYYY/MM/DD形式）
            end_date: 終了日（YYYY/MM/DD形式）

        Returns:
            期間内ならTrue
        """
        # オブジェクトキーから日付部分を抽出（YYYY/MM/DD）
        parts = object_key.split("/")
        if len(parts) < 3:
            return True  # 日付構造でない場合はスキップしない

        try:
            obj_date_str = "/".join(parts[:3])  # YYYY/MM/DD
            obj_date = datetime.strptime(obj_date_str, "%Y/%m/%d")

            if start_date:
                start = datetime.strptime(start_date, "%Y/%m/%d")
                if obj_date < start:
                    return False

            if end_date:
                end = datetime.strptime(end_date, "%Y/%m/%d")
                if obj_date > end:
                    return False

            return True

        except ValueError:
            # 日付パースエラーの場合はスキップしない
            return True

    def invoke_lambda(self, object_key: str, dry_run: bool = False) -> dict[str, Any]:
        """
        Lambda関数を実行してLGTM画像を再生成

        Args:
            object_key: S3オブジェクトキー
            dry_run: ドライラン実行の場合True

        Returns:
            実行結果
        """
        payload = {
            "process": "generateLgtmImage",
            "image": {"bucketName": self.bucket_name, "objectKey": object_key},
        }

        if dry_run:
            logger.info(f"[DRY RUN] Lambda実行: {object_key}")
            return {"status": "skipped", "object_key": object_key}

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
                logger.info(f"✓ 成功: {object_key}")
                return {"status": "success", "object_key": object_key}
            else:
                # エラーログ出力（シンプル）
                function_error = response.get("FunctionError", "None")
                logger.error(f"✗ 失敗: {object_key} - FunctionError: {function_error}")
                logger.error(
                    f"  レスポンス: {json.dumps(response_payload, ensure_ascii=False)}"
                )

                return {
                    "status": "failure",
                    "object_key": object_key,
                    "error": f"FunctionError: {function_error}",
                }

        except ClientError as e:
            logger.error(f"✗ Lambda実行エラー: {object_key} - {str(e)}")
            return {"status": "failure", "object_key": object_key, "error": str(e)}
        except Exception as e:
            logger.error(
                f"✗ 予期しないエラー: {object_key} - {type(e).__name__}: {str(e)}"
            )
            return {"status": "failure", "object_key": object_key, "error": str(e)}

    def regenerate_all(
        self,
        object_keys: list[str],
        dry_run: bool = False,
    ) -> None:
        """
        全画像を逐次的に再生成

        Args:
            object_keys: オブジェクトキーのリスト
            dry_run: ドライラン実行の場合True
        """
        self.total_count = len(object_keys)

        if self.total_count == 0:
            logger.warning("処理対象の画像がありません")
            return

        logger.info(f"処理開始: {self.total_count}件の画像を処理します")
        if dry_run:
            logger.info("【ドライランモード】実際のLambda実行は行いません")

        for key in object_keys:
            result = self.invoke_lambda(key, dry_run)

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
        logger.info(f"期間外:     {self.skipped_date_count}")
        logger.info("=" * 60)


def main() -> None:
    """メイン処理"""
    parser = argparse.ArgumentParser(description="既存のLGTM画像を再生成するスクリプト")

    parser.add_argument(
        "--bucket",
        type=str,
        required=True,
        help="S3バケット名（例: stg-lgtmeow-cat-images）",
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
        "--start-date",
        type=str,
        help="開始日（YYYY/MM/DD形式、例: 2025/11/01）",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="終了日（YYYY/MM/DD形式、例: 2025/11/07）",
    )

    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="オブジェクトキーのプレフィックス（例: 2025/11/）",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン実行（実際のLambda実行は行わない）",
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="ログファイルを保存するディレクトリ（デフォルト: logs）",
    )

    args = parser.parse_args()

    # ロギング設定
    log_file = setup_logging(args.log_dir)
    logger.info("=" * 60)
    logger.info("LGTM画像再生成スクリプト開始")
    logger.info("=" * 60)
    logger.info(f"ログファイル: {log_file}")
    logger.info(f"バケット: {args.bucket}")
    logger.info(f"Lambda関数: {args.lambda_function}")
    if args.profile:
        logger.info(f"AWSプロファイル: {args.profile}")
    logger.info("=" * 60)

    try:
        regenerator = LgtmImageRegenerator(
            bucket_name=args.bucket,
            lambda_function_name=args.lambda_function,
            aws_profile=args.profile,
        )

        # オブジェクトキー取得
        object_keys = regenerator.list_all_objects(
            prefix=args.prefix,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        # 再生成実行
        regenerator.regenerate_all(object_keys, dry_run=args.dry_run)

        # サマリー出力
        regenerator.print_summary()

        # 失敗がある場合は終了コード1
        if regenerator.failure_count > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
