# /src ディレクトリ構成ガイド

このドキュメントは `/src` ディレクトリ配下の設計原則と各層の責務を説明します。

## ディレクトリ構造

```
src/
├── domain/          # ドメイン層：インターフェース定義（Protocol）
├── infrastructure/  # インフラ層：外部システムの具体実装（S3、DB）
├── usecase/         # ユースケース層：ビジネスロジック
├── presentation/    # プレゼンテーション層：リクエストルーティング
├── log/             # ロギング（全層で共有）
└── main.py          # Lambdaエントリーポイント
```

## 各層の責務

### domain/ - ドメイン層
- **役割**: システムの契約をProtocolで定義
- **依存**: なし（最も内側の層）
- **例**: `ObjectStorageRepositoryInterface`, `LgtmImageRepositoryInterface`

### infrastructure/ - インフラ層
- **役割**: 外部システム（S3、MySQL）との実際の接続・操作
- **依存**: domainのインターフェースを実装
- **例**: `S3Repository`, `LgtmImageRepository`, SQLAlchemyモデル

### usecase/ - ユースケース層
- **役割**: ビジネスロジックの実装
- **依存**: domainのインターフェースのみに依存（infrastructureの具象クラスに直接依存しない）
- **例**: `JudgeImageUsecase`, `GenerateLgtmImageUsecase`, `StoreToDbUsecase`

### presentation/ - プレゼンテーション層
- **役割**: リクエスト受付と適切なusecaseへの振り分け
- **依存**: usecaseとinfrastructureに依存（DIでusecaseにリポジトリを注入）
- **例**: `handle_process()` - `ProcessType`に応じたusecase実行

### log/ - ロギング
- **役割**: 構造化ロギング（JSON形式）の提供
- **依存**: なし（全層から利用可能）

## 依存関係のフロー

```
main.py
  ↓
presentation/  ← infrastructure/のインスタンスを生成
  ↓                      ↓
usecase/  ←─────── domain/ (インターフェース定義)
                         ↑
              infrastructure/ (インターフェース実装)
```

**重要な原則**:
- 依存関係は内側（domain）に向かう
- usecaseはinfrastructureの具象クラスを直接知らない
- presentation層でDI（依存性注入）を行う

## 新機能追加時の指針

### 1. 新しいプロセスタイプを追加
1. `presentation/handle_process.py`の`ProcessType` Enumに値を追加
2. `usecase/`配下に新しいusecaseクラスを作成
3. 外部システム連携が必要なら:
   - `domain/`にProtocolインターフェースを定義
   - `infrastructure/`に実装クラスを作成
4. `presentation/handle_process()`に分岐処理を追加

### 2. 既存処理の拡張
- ビジネスロジック変更 → `usecase/`を編集
- S3/DB操作変更 → `infrastructure/`を編集
- インターフェース変更が必要なら → `domain/`から更新

### 3. ロギング
- `log/logging.py`の`setup_logger()`で生成されたロガーを使用
- JSON形式のログを維持

## クリーンアーキテクチャの利点

- **テスタビリティ**: usecaseは`Protocol`に依存するのでモックが容易
- **保守性**: 各層の責務が明確で変更影響範囲を限定できる
- **拡張性**: 新しい外部システム（例: DynamoDB）追加時もusecaseを変更不要

## コーディングルール

### インポートパス

`src/`配下のモジュールをインポートする際は、`src.`プレフィックスを付けずにインポートしてください。

```python
# 正しい
from domain.auth_repository_interface import AuthRepositoryInterface
from log.logging import AppLogger

# 誤り（mypyエラーの原因になる）
from src.domain.auth_repository_interface import AuthRepositoryInterface
from src.log.logging import AppLogger
```

これは`pyproject.toml`の`pythonpath = ["src"]`設定に基づいています。

### TypedDictの型ヒント

APIレスポンスなど外部データ構造をTypedDictで定義する場合は、`Required`/`NotRequired`を明示的に使用して可読性を高めてください。

```python
# 推奨
from typing import NotRequired, Required, TypedDict

class ApiResponse(TypedDict):
    id: Required[int]              # 必須フィールド
    name: Required[str]            # 必須フィールド
    description: NotRequired[str]  # オプショナルフィールド

# 非推奨（デフォルトでRequiredだが意図が不明確）
class ApiResponse(TypedDict):
    id: int
    name: str
    description: NotRequired[str]
```

**使い分け**:
- `Required[T]`: キーが必ず存在する
- `NotRequired[T]`: キー自体が存在しない可能性がある
- `T | None`: キーは存在するが値がNoneの可能性がある
