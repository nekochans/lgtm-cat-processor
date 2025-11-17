# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ソースファイル先頭コメント必須

全てのソースファイル（.py）の先頭に必ず以下のコメントを記載してください。

```python
# 絶対厳守：編集前に必ずAI実装ルールを読む
```

既存ファイルにコメントがない場合は必ず追加してください。

## 他のファイルへの参照

**以下のように @<path> の形式で書かれている場合は別のファイルへの参照になりますので、対象ファイルを探して内容を確認してください。**

**以下に記載例を示します。**

@src/main.py（src/main.py を参照）
@.github/PULL_REQUEST_TEMPLATE.md （.github/PULL_REQUEST_TEMPLATE.md を参照）

## プロジェクト概要

S3にアップロードされた猫の画像からLGTM画像を生成するAWS Lambda関数です。画像を処理して「LGTMeow」テキストを追加し、メタデータをMySQLデータベースに保存します。

## アーキテクチャ

このプロジェクトは**クリーンアーキテクチャ**に従っています。

**詳細な設計原則と各層の責務については @src/CLAUDE.md を参照してください。**

## 処理フロー

Lambdaハンドラー（`main.py:lambda_handler`）は`handle_process`経由で3つのプロセスのいずれかにルーティングします：

1. **JUDGE_IMAGE**: アップロードされた画像の検証
2. **GENERATE_LGTM_IMAGE**: 猫画像にLGTMオーバーレイを作成
   - S3から画像を取得
   - アスペクト比を維持してリサイズ（最大400px）
   - M PLUS Rounded 1cフォントで「LGTMeow」テキストを追加
   - WebP形式に変換
   - 宛先バケットにアップロード（環境変数：`GENERATE_LGTM_IMAGE_UPLOAD_BUCKET`）
3. **STORE_TO_DB**: 画像メタデータをMySQLに永続化

**重要な実装詳細：**
- S3アップロード時は画像フォーマットを明示的に`image/webp`に設定
- フォントパスは`LAMBDA_TASK_ROOT`環境変数を使用
- 各プロセスは`(bucket_name, object_key)`のタプルを返す

## 開発コマンド

依存関係は**uv**で管理（pipではありません）：

```bash
# 依存関係のインストール/同期
uv sync

# リント
make lint              # ruffでチェック
make fix               # ruffで自動修正
make format            # コードフォーマット

# 型チェック
make typecheck         # mypy --strictで実行

# テスト
make test              # pytestで実行
```

## デプロイ

**コンテナベースのLambdaデプロイ：**
- ベースイメージ：`public.ecr.aws/lambda/python:3.12`
- Dockerfileで`src/`と`fonts/`を`LAMBDA_TASK_ROOT`にコピー
- エントリーポイント：`main.lambda_handler`

**デプロイ先：**
- **ステージング**: `main`ブランチへのマージ時にトリガー
- **本番**: セマンティックバージョンタグ（例：`v1.0.0`）追加時にトリガー

デプロイはAWS CodeBuild（`buildspec.yml`）を使用してLambda関数コードを更新します。

## テストとCI

CIワークフロー（`.github/workflows/ci.yml`）は4つのジョブを実行：
1. `uv run ruff check` - リント
2. `uv run ruff format --check` - フォーマット検証
3. `uv run mypy src/ tests/ --strict` - 型チェック
4. `uv run pytest -vv -s src/ tests/` - ユニットテスト

**テストコード実装のルールについては @tests/CLAUDE.md を参照してください。**

## 依存関係

主要な依存パッケージ：
- `boto3` + `boto3-stubs[s3,rekognition,s3vectors,bedrock-runtime]` - AWS S3、Rekognition、S3 Vectors、Bedrock操作
- `pillow` - 画像処理
- `sqlalchemy` + `mysql-connector-python` - データベース操作

## 主要な環境変数

- `LAMBDA_TASK_ROOT` - フォントとリソースのベースパス（Lambda実行環境で設定）
- `GENERATE_LGTM_IMAGE_UPLOAD_BUCKET` - 処理済み画像のアップロード先S3バケット
- `VECTOR_INDEX_BUCKET` - ベクトルインデックス保存用のS3 Vectorsバケット名
- `VECTOR_INDEX_NAME` - S3 Vectorsのインデックス名
- `BEDROCK_REGION` - AWS Bedrockのリージョン（デフォルト: us-east-1）
- `BEDROCK_MODEL_ID` - Bedrockで使用する画像埋め込みモデルID（デフォルト: cohere.embed-v4:0）
- `S3_VECTORS_REGION` - AWS S3 Vectorsのリージョン（デフォルト: us-east-1）

## GitとGitHubワークフロールール

### GitHubの利用ルール

GitHubのMCPサーバーを利用してGitHubへのPRを作成する事が可能です。

許可されている操作は以下の通りです。

- GitHubへのPRの作成
- GitHubへのPRへのコメントの追加
- GitHub Issueへのコメントの追加

### PR作成ルール

- ブランチはユーザーが作成しますので現在のブランチをそのまま利用します
- PRのタイトルは日本語で入力します
- PRの作成先は特別な指示がない場合は `main` ブランチになります
- PRの説明欄は @.github/PULL_REQUEST_TEMPLATE.md を参考に入力します
- 対応issueがある場合は、PRの説明欄に `#<issue番号>` を記載します
- Issue番号は現在のブランチ名から取得出来ます、例えば `feature/issue7/add-docs` の場合は `7` がIssue番号になります
- PRの説明欄には主に以下の情報を含めてください

#### PRの説明欄に含めるべき情報

- 変更内容の詳細説明よりも、なぜその変更が必要なのかを重視
- 他に影響を受ける機能やAPIエンドポイントがあれば明記

#### 以下の情報はPRの説明欄に記載する事を禁止する

- 1つのissueで1つのPRとは限らないので `fix #issue番号` や `close #issue番号` のようなコメントは禁止します
- 全てのテストをパス、Linter、型チェックを通過などのコメント（テストやCIが通過しているのは当たり前でわざわざ書くべき事ではない）

## コーディング時に利用可能なツール

コーディングを効率的に行う為のツールです。必ず以下に目を通してください。

### Serena MCP ― コード検索・編集ツールセット（必ず優先）

| 分類                        | 主要ツール (mcp**serena**)                                                                        | 典型的な用途                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **ファイル / ディレクトリ** | `list_dir` / `find_file`                                                                          | ツリー俯瞰・ファイル名で高速検索                 |
| **全文検索**                | `search_for_pattern` / `replace_regex`                                                            | 正規表現を含む横断検索・一括置換                 |
| **シンボル検索**            | `get_symbols_overview` / `find_symbol` / `find_referencing_symbols`                               | 定義探索・参照逆引き                             |
| **シンボル編集**            | `insert_after_symbol` / `insert_before_symbol` / `replace_symbol_body`                            | 挿入・追記・リファクタ                           |
| **メモリ管理**              | `write_memory` / `read_memory` / `list_memories` / `delete_memory`                                | `.serena/memories/` への長期知識 CRUD            |
| **メンテナンス**            | `restart_language_server` / `switch_modes` / `summarize_changes` / `prepare_for_new_conversation` | LSP 再起動・モード切替・変更要約・新チャット準備 |

> **禁止**: 組み込み `Search / Read / Edit / Write` ツールは使用しない。

Serena MCPが使えない環境では仕方ないので通常の `Search / Read / Edit / Write` を使用しても良いが、Serena MCPの機能を優先的に利用すること。

### Gemini CLI ― Web 検索専用

外部情報を取得する必要がある場合は、次の Bash ツール呼び出しを **唯一の手段として使用** する。

```bash
gemini --prompt "WebSearch: <query>"
```

`gemini` が使えない環境の場合は通常のWeb検索ツールを使っても良い。

## **絶対禁止事項**

1. **依頼内容に関係のない無駄な修正を行う行為は絶体に禁止。**
2. **ビジネスロジックが誤っている状態で、テストコードを“上書きしてまで”合格させる行為は絶対に禁止。**
