# lgtm-cat-processor

S3にアップロードされた猫の画像からLGTM画像を生成するAWS Lambda関数です。

## 処理フロー

Lambda関数は以下の3つのプロセスを実行します：

1. **JUDGE_IMAGE** - アップロードされた画像の検証
2. **GENERATE_LGTM_IMAGE** - 猫画像に「LGTMeow」テキストを追加してWebP形式で出力
3. **STORE_TO_DB** - 画像情報をDBに保存

## 開発環境セットアップ

### 前提条件

- Python 3.12
- [uv](https://docs.astral.sh/uv/)（パッケージマネージャー）

### 依存関係のインストール

```bash
uv sync
```

## 開発コマンド

```bash
# リント
make lint

# リント（自動修正）
make fix

# フォーマット
make format

# 型チェック
make typecheck

# テスト
make test
```

## 動作確認

ローカルでの実行はサポートしていません。STG環境にデプロイして確認してください。

## ディレクトリ構成

```tree
src/
├── domain/          # インターフェース定義（Protocol）
├── infrastructure/  # 外部システムの具体実装（S3、DB）
├── usecase/         # ビジネスロジック
├── presentation/    # リクエストルーティング
├── log/             # ロギング
└── main.py          # Lambdaエントリーポイント
```

## デプロイ

デプロイはGitHub Actionsワークフロー内で自動的に実行されます。

- **ステージング**: mainブランチへのPRマージ時
- **本番**: セマンティックバージョニングに基づいたリリースタグ（例：v1.0.0）追加時

GitHub Actionsの`workflow_dispatch`を使用して手動でデプロイを実行することも可能です。

## フォント

LGTMテキストの追加に[M PLUS Rounded 1c](https://fonts.google.com/specimen/M+PLUS+Rounded+1c)（Google Fonts）を使用しています。
