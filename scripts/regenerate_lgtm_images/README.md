# LGTM画像再生成スクリプト

既存のLGTM画像を再生成して、テキスト配置を最適化するスクリプトです。

## 概要

S3バケット内の全画像に対してLambda関数を実行し、「LGTMeow」のテキストが猫の顔に重ならないように最適化されたLGTM画像を再生成します。

## 前提条件

1. AWS CLIの設定が完了していること
2. 適切なAWSプロファイルが設定されていること
3. boto3がインストールされていること

```bash
# boto3のインストール（プロジェクトルートで実行）
uv sync
```

## 使用方法

### 基本的な使い方

```bash
# ステージング環境で全画像を再生成
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor

# 本番環境で全画像を再生成
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket prod-lgtmeow-cat-images \
  --lambda-function prod-lgtm-image-processor

# AWSプロファイルを指定する場合
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --profile lgtm-cat
```

### テスト実行（期間指定）

```bash
# 2025年11月7日の画像のみを再生成
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --start-date 2025/11/07 \
  --end-date 2025/11/07

# 2025年11月の画像のみを再生成（プレフィックス指定）
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --prefix 2025/11/
```

### ドライラン実行

実際のLambda実行を行わず、対象画像の確認のみを行います。

```bash
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --dry-run
```

## オプション一覧

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--bucket` | ✓ | - | S3バケット名 |
| `--lambda-function` | ✓ | - | Lambda関数名 |
| `--profile` | | - | AWSプロファイル名（指定しない場合はデフォルトプロファイルを使用） |
| `--start-date` | | - | 開始日（YYYY/MM/DD形式） |
| `--end-date` | | - | 終了日（YYYY/MM/DD形式） |
| `--prefix` | | "" | オブジェクトキーのプレフィックス |
| `--dry-run` | | False | ドライラン実行 |
| `--log-dir` | | logs | ログファイルを保存するディレクトリ |

## 実行例

### ステップ1: ドライランで対象確認

```bash
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --start-date 2025/11/07 \
  --end-date 2025/11/07 \
  --dry-run
```

### ステップ2: 小規模テスト実行

```bash
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --start-date 2025/11/07 \
  --end-date 2025/11/07
```

### ステップ3: 本番実行

```bash
# まずステージング環境で全画像を再生成
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor

# 問題なければ本番環境で実行
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket prod-lgtmeow-cat-images \
  --lambda-function prod-lgtm-image-processor
```

## ログファイル

スクリプト実行時、ログは以下の両方に出力されます：

1. **コンソール**: 実行中の進捗をリアルタイムで確認
2. **ログファイル**: 実行履歴を保存（デフォルト: `logs/regenerate_YYYYMMDD_HHMMSS.log`）

### ログファイル名の形式

```
logs/regenerate_20251107_120000.log
```

タイムスタンプ付きで保存されるため、複数回実行しても履歴が残ります。

### ログディレクトリの変更

```bash
# カスタムディレクトリを指定
uv run python scripts/regenerate_lgtm_images/regenerate_lgtm_images.py \
  --bucket stg-lgtmeow-cat-images \
  --lambda-function stg-lgtm-image-processor \
  --log-dir /path/to/custom/logs
```

## 出力例

### コンソール出力（ログファイルにも同じ内容が保存される）

```
2025-11-07 12:00:00 - INFO - ============================================================
2025-11-07 12:00:00 - INFO - LGTM画像再生成スクリプト開始
2025-11-07 12:00:00 - INFO - ============================================================
2025-11-07 12:00:00 - INFO - ログファイル: logs/regenerate_20251107_120000.log
2025-11-07 12:00:00 - INFO - バケット: stg-lgtmeow-cat-images
2025-11-07 12:00:00 - INFO - Lambda関数: stg-lgtm-image-processor
2025-11-07 12:00:00 - INFO - ============================================================
2025-11-07 12:00:00 - INFO - バケット 'stg-lgtmeow-cat-images' からオブジェクトキーを取得中...
2025-11-07 12:00:05 - INFO - 取得完了: 150件の画像が見つかりました
2025-11-07 12:00:05 - INFO - 処理開始: 150件の画像を処理します
2025-11-07 12:00:10 - INFO - ✓ 成功: 2025/11/07/11/xxx.jpeg
2025-11-07 12:00:11 - INFO - 進捗: 1/150 (成功: 1, 失敗: 0)
...
2025-11-07 12:10:00 - INFO - ============================================================
2025-11-07 12:10:00 - INFO - 実行結果サマリー
2025-11-07 12:10:00 - INFO - ============================================================
2025-11-07 12:10:00 - INFO - 総件数:     150
2025-11-07 12:10:00 - INFO - 成功:       148
2025-11-07 12:10:00 - INFO - 失敗:       2
2025-11-07 12:10:00 - INFO - スキップ:   0
2025-11-07 12:10:00 - INFO - ============================================================
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

**注意**: `StatusCode == 200` だけでは不十分です。Lambda関数内でエラーが発生した場合でも、API呼び出し自体は成功するため `StatusCode` は 200 になりますが、`FunctionError` フィールドが設定されます。

### エラーログの詳細

Lambda実行が失敗した場合、以下の情報がログに出力されます：

```
2025-11-07 22:57:15 - ERROR - ✗ 失敗: 2025/11/04/11/xxx.jpg - FunctionError: Unhandled
2025-11-07 22:57:15 - ERROR -   レスポンス: {"errorType":"RuntimeError","errorMessage":"Failed to process image","stackTrace":[...]}
```

出力される情報：
- **FunctionError**: Lambda関数実行エラーの種類（Unhandled/Handledなど、エラーがない場合はNone）
- **レスポンス**: Lambda関数からの完全なレスポンス（JSON形式、1行）

## 注意事項

1. **処理時間**: 画像は1つずつ逐次的に処理されるため、大量の画像がある場合は時間がかかります
2. **コスト**: 大量の画像を処理する場合、Lambda実行コストが発生します
3. **S3上書き**: 既存の画像は同じオブジェクトキーで上書きされます
4. **テスト推奨**: 本番環境で実行する前に、必ずステージング環境でテストしてください

## トラブルシューティング

### AWS認証エラー

```bash
# デフォルトプロファイルを確認
aws configure list

# 特定のプロファイルを確認
aws configure list --profile lgtm-cat

# 必要に応じてプロファイルを設定
aws configure --profile lgtm-cat
```

### boto3がインストールされていない

```bash
# プロジェクトルートで実行
uv sync
```
