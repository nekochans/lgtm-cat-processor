# LGTM画像初期インデックス作成スクリプト

既存のLGTM画像に対してS3 Vectorsインデックスを作成するスクリプトです。

## 概要

DBに登録されている全LGTM画像に対してLambda関数（`createImageIndex`プロセス）を実行し、画像検索用のベクトルインデックスをS3 Vectorsに作成します。

**注意**: このスクリプトは初回実行のみを想定しています。通常の運用では、画像アップロード時に自動的にインデックスが作成されます。

## 前提条件

1. AWS CLIの設定が完了していること
2. 適切なAWSプロファイルが設定されていること
3. Lambda関数が`createImageIndex`プロセスをサポートしていること（Issue #39対応済み）
4. S3 Vectorsインデックスが作成されていること（Terraformで設定済み）
5. 以下の環境変数が設定されていること：
   - `DB_HOSTNAME`: データベースホスト名
   - `DB_USERNAME`: データベースユーザー名
   - `DB_PASSWORD`: データベースパスワード
   - `DB_NAME`: データベース名

```bash
# 必要なパッケージのインストール（プロジェクトルートで実行）
uv sync
```

## 環境変数の設定

スクリプト実行前に、DB接続情報を環境変数として設定してください。

```bash
# 環境変数を設定
export DB_HOSTNAME="your-db-hostname"
export DB_USERNAME="your-db-username"
export DB_PASSWORD="your-db-password"
export DB_NAME="your-db-name"
```

**セキュリティ注意事項**:
- パスワードをシェルのヒストリーに残さないよう注意してください
- 本番環境では、AWS Secrets Managerや.envファイルの利用を検討してください

## 使用方法

### 基本的な使い方

```bash
# ステージング環境で全画像のインデックスを作成
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor

# 本番環境で全画像のインデックスを作成
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket prod-lgtmeow-images \
  --lambda-function prod-lgtm-image-processor

# AWSプロファイルを指定する場合
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor \
  --profile lgtm-cat
```

### ドライラン実行

実際のLambda実行を行わず、処理対象画像の確認のみを行います。

```bash
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor \
  --dry-run
```

## オプション一覧

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--bucket` | ✓ | - | S3バケット名 |
| `--lambda-function` | ✓ | - | Lambda関数名 |
| `--profile` | | - | AWSプロファイル名（指定しない場合はデフォルトプロファイルを使用） |
| `--dry-run` | | False | ドライラン実行 |
| `--log-dir` | | logs | ログファイルを保存するディレクトリ |

## 実行例

### ステップ1: 環境変数設定

```bash
# DB接続情報を環境変数に設定
export DB_HOSTNAME="your-db-hostname"
export DB_USERNAME="your-db-username"
export DB_PASSWORD="your-db-password"
export DB_NAME="your-db-name"
```

### ステップ2: ドライランで対象確認

```bash
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor \
  --dry-run
```

### ステップ3: 本実行

```bash
# ステージング環境で実行
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor

# 問題なければ本番環境で実行
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket prod-lgtmeow-images \
  --lambda-function prod-lgtm-image-processor
```

## ログファイル

スクリプト実行時、ログは以下の両方に出力されます：

1. **コンソール**: 実行中の進捗をリアルタイムで確認
2. **ログファイル**: 実行履歴を保存（デフォルト: `logs/create_initial_index_YYYYMMDD_HHMMSS.log`）

### ログファイル名の形式

```
logs/create_initial_index_20251113_120000.log
```

タイムスタンプ付きで保存されるため、複数回実行しても履歴が残ります。

### ログディレクトリの変更

```bash
# カスタムディレクトリを指定
uv run python -m scripts.create_initial_image_index.create_initial_image_index \
  --bucket stg-lgtmeow-images \
  --lambda-function stg-lgtm-image-processor \
  --log-dir /path/to/custom/logs
```

## 出力例

### コンソール出力（ログファイルにも同じ内容が保存される）

```
2025-11-13 12:00:00 - INFO - ============================================================
2025-11-13 12:00:00 - INFO - LGTM画像初期インデックス作成スクリプト開始
2025-11-13 12:00:00 - INFO - ============================================================
2025-11-13 12:00:00 - INFO - ログファイル: logs/create_initial_index_20251113_120000.log
2025-11-13 12:00:00 - INFO - バケット: stg-lgtmeow-images
2025-11-13 12:00:00 - INFO - Lambda関数: stg-lgtm-image-processor
2025-11-13 12:00:00 - INFO - ============================================================
2025-11-13 12:00:00 - INFO - DB接続情報を環境変数から取得中...
2025-11-13 12:00:00 - INFO - DB接続情報の取得完了
2025-11-13 12:00:00 - INFO - DBから全LGTM画像情報を取得中...
2025-11-13 12:00:05 - INFO - 取得完了: 150件の画像が見つかりました
2025-11-13 12:00:05 - INFO - 処理開始: 150件の画像を処理します
2025-11-13 12:00:10 - INFO - ✓ 成功: ID=1, key=2025/11/07/11/xxx.webp
2025-11-13 12:00:11 - INFO - 進捗: 1/150 (成功: 1, 失敗: 0, ドライラン: 0)
...
2025-11-13 12:10:00 - INFO - ============================================================
2025-11-13 12:10:00 - INFO - 実行結果サマリー
2025-11-13 12:10:00 - INFO - ============================================================
2025-11-13 12:10:00 - INFO - 総件数:     150
2025-11-13 12:10:00 - INFO - 成功:       148
2025-11-13 12:10:00 - INFO - 失敗:       2
2025-11-13 12:10:00 - INFO - ドライラン: 0
2025-11-13 12:10:00 - INFO - ============================================================
```

## Lambda関数へのペイロード

スクリプトは以下の形式でLambda関数を呼び出します：

```json
{
  "process": "createImageIndex",
  "image": {
    "bucketName": "stg-lgtmeow-images",
    "objectKey": "2025/11/07/11/xxx.webp",
    "databaseId": 123
  }
}
```

## エラーハンドリング

- Lambda実行が失敗した場合でも処理は継続されます
- 失敗した画像はログに詳細情報と共に記録されます
- 最終的に失敗が1件以上ある場合、終了コード1で終了します

### 成功判定

Lambda関数が正常に実行されたかどうかは、以下の条件で判定されます：

- `StatusCode == 200`: AWS Lambda APIの呼び出しが成功
- `FunctionError is None`: Lambda関数内でエラーが発生していない

これらの条件を全て満たす場合、成功と判定されます。

### エラーログの詳細

Lambda実行が失敗した場合、以下の情報がログに出力されます：

```
2025-11-13 12:57:15 - ERROR - ✗ 失敗: ID=123, key=2025/11/04/11/xxx.webp - FunctionError: Unhandled
2025-11-13 12:57:15 - ERROR -   レスポンス: {"errorType":"RuntimeError","errorMessage":"Failed to process image","stackTrace":[...]}
```

出力される情報：
- **FunctionError**: Lambda関数実行エラーの種類（Unhandled/Handledなど、エラーがない場合はNone）
- **レスポンス**: Lambda関数からの完全なレスポンス（JSON形式、1行）

## 注意事項

1. **処理時間**: 画像は1つずつ逐次的に処理されるため、大量の画像がある場合は時間がかかります
2. **コスト**: 大量の画像を処理する場合、Lambda実行コストとBedrock API呼び出しコストが発生します
3. **初回実行のみ**: このスクリプトは既存画像の初期インデックス作成用です。以降は画像アップロード時に自動作成されます
4. **テスト推奨**: 本番環境で実行する前に、必ずステージング環境でテストしてください
5. **環境変数**: DB接続情報を環境変数から取得するため、実行前に必ず設定してください

## トラブルシューティング

### 環境変数エラー

```
環境変数エラー: 環境変数 DB_HOSTNAME が設定されていません
```

**解決方法**:
```bash
# 必要な環境変数を設定
export DB_HOSTNAME="your-db-hostname"
export DB_USERNAME="your-db-username"
export DB_PASSWORD="your-db-password"
export DB_NAME="your-db-name"
```

### AWS認証エラー

```bash
# デフォルトプロファイルを確認
aws configure list

# 特定のプロファイルを確認
aws configure list --profile lgtm-cat

# 必要に応じてプロファイルを設定
aws configure --profile lgtm-cat
```

### パッケージがインストールされていない

```bash
# プロジェクトルートで実行
uv sync
```

### DB接続エラー

- DB接続情報が正しいか確認してください
- データベースサーバーにアクセス可能か確認してください
- ファイアウォールやセキュリティグループの設定を確認してください

## 関連Issue

- [Issue #44](https://github.com/nekochans/lgtm-cat-processor/issues/44): 既存のLGTM画像の初期インデックスを登録する
- [Issue #39](https://github.com/nekochans/lgtm-cat-processor/issues/39): Bedrockを用いた画像インデックス作成処理を追加
