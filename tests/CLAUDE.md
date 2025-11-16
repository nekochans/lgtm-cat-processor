# /tests ディレクトリのテストコード実装ガイド

このドキュメントは `/tests` ディレクトリ配下のテストコード実装ルールを説明します。

## テストファイル構造

```
tests/
├── domain/          # ドメイン層のテスト
├── infrastructure/  # インフラ層のテスト
├── usecase/         # ユースケース層のテスト
└── presentation/    # プレゼンテーション層のテスト
```

各ディレクトリは `src/` の構造と対応しています。

## ファイル命名規則

- テストファイル名: `test_<対象モジュール名>.py`
  - 例: `src/infrastructure/s3_repository.py` → `tests/infrastructure/test_s3_repository.py`
- テストクラス名: `Test<対象クラス名>`
  - 例: `S3Repository` → `TestS3Repository`
- テストメソッド名: `test_<メソッド名>_<シナリオ>`
  - 例: `test_fetch_image_success`, `test_fetch_image_s3_error`

## 必須コメント

全てのテストファイルの先頭に以下のコメントを記載してください：

```python
# 絶対厳守:編集前に必ずAI実装ルールを読む
```

## AAA（Arrange-Act-Assert）パターンの厳守

全てのテストは以下の3ステップで構成してください：

```python
def test_example(self) -> None:
    """テスト内容を日本語で説明"""
    # Arrange（準備）
    # テストデータとモックの準備
    test_data = "example"
    mock_obj.method.return_value = expected_result

    # Act（実行）
    # テスト対象メソッドの実行
    result = target.execute(test_data)

    # Assert（検証）
    # 結果の検証
    assert result == expected_result
    mock_obj.method.assert_called_once_with(test_data)
```

## pytest.mark.parametrizeのids指定（必須）

`@pytest.mark.parametrize`を使用する際は、**必ず`ids`パラメータを指定**してテストケースを識別可能にしてください。

**理由**: テスト実行時に`test_function[0]`ではなく`test_function[simple_jpg]`のように意味のある名前で表示されるため、テスト失敗時の原因特定が容易になります。

**推奨例**:
```python
@pytest.mark.parametrize(
    "object_key,expected",
    [
        ("test.jpg", "test"),
        ("path/to/file.jpg", "file"),
        ("file.test.jpg", "file.test"),
    ],
    ids=[
        "simple_jpg",
        "nested_path",
        "multiple_dots",
    ],
)
def test_extract_filename(object_key: str, expected: str) -> None:
    """様々なファイル名パターンで正しく拡張子を除去できること"""
    result = extract_filename(object_key)
    assert result == expected
```

**非推奨例**:
```python
@pytest.mark.parametrize(
    "object_key,expected",
    [
        ("test.jpg", "test"),
        ("path/to/file.jpg", "file"),
    ],
)  # ❌ idsパラメータがない
def test_extract_filename(object_key: str, expected: str) -> None:
    result = extract_filename(object_key)
    assert result == expected
```

## pytest fixture の活用

共通のモック設定やテスト対象インスタンスは fixture として定義してください：

```python
class TestExampleRepository:
    @pytest.fixture
    def mock_client(self) -> Mock:
        """外部クライアントのモック"""
        return Mock(spec=ExternalClient)

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """ロガーのモック"""
        return Mock(spec=AppLogger)

    @pytest.fixture
    def repository(
        self,
        mock_client: Mock,
        mock_logger: Mock,
    ) -> ExampleRepository:
        """テスト対象インスタンス"""
        return ExampleRepository(
            client=mock_client,
            logger=mock_logger,
        )
```

## モックの検証

モックが正しく呼ばれたことを検証してください：

```python
# 呼び出し回数と引数の検証
mock_obj.method.assert_called_once_with(expected_arg1, expected_arg2)

# 呼び出されていないことの検証
mock_obj.method.assert_not_called()

# 例外を発生させる
mock_obj.method.side_effect = Exception("error message")
```

## 異常系テストでの pytest.raises() 使用

例外が発生することを検証する場合は `pytest.raises()` を使用してください：

```python
def test_error_case(self, repository: Repository, mock_client: Mock) -> None:
    """エラー時に適切に例外が発生すること"""
    # Arrange
    mock_client.method.side_effect = Exception("API error")

    # Act & Assert
    with pytest.raises(Exception, match="API error"):
        repository.execute()
```

## 日本語 docstring の使用

各テストメソッドには日本語で明確な説明を記載してください：

```python
def test_save_lgtm_cat_success(self) -> None:
    """正常にレコードを保存してIDを取得できること"""
    # テスト実装
```

## 層別のテストパターン

### Domain層のテストパターン

計算ロジックや変換ロジックをテストします。外部依存がないため、モックは不要です。

```python
class TestBrightnessCalculator:
    def test_calculate_brightness_from_dark_color(self) -> None:
        """暗い色から正しく明るさを計算できること"""
        # Arrange
        dark_color = (0, 0, 0)  # 黒

        # Act
        brightness = calculate_brightness(dark_color)

        # Assert
        assert brightness == 0.0
```

### Infrastructure層のテストパターン

外部システム（S3、DB、AWS API）との連携をテストします。必ず外部クライアントをモック化してください。

```python
class TestS3Repository:
    @pytest.fixture
    def mock_s3_client(self) -> Mock:
        """S3クライアントのモック"""
        return Mock(spec=S3Client)

    @pytest.fixture
    def repository(self, mock_s3_client: Mock, mock_logger: Mock) -> S3Repository:
        """S3Repositoryのインスタンス"""
        return S3Repository(s3_client=mock_s3_client, logger=mock_logger)

    def test_fetch_image_success(
        self,
        repository: S3Repository,
        mock_s3_client: Mock,
    ) -> None:
        """S3から正常に画像を取得できること"""
        # Arrange
        test_image_bytes = b"test image data"
        mock_s3_client.get_object.return_value = {
            "Body": Mock(read=Mock(return_value=test_image_bytes))
        }

        # Act
        result = repository.fetch_image("test-bucket", "test-key.jpg")

        # Assert
        assert result == test_image_bytes
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-key.jpg"
        )
```

### Usecase層のテストパターン

ビジネスロジックをテストします。依存するリポジトリインターフェースをモック化してください。

```python
class TestGenerateLgtmImageUsecase:
    @pytest.fixture
    def mock_s3_repository(self) -> Mock:
        """S3Repositoryのモック"""
        return Mock(spec=ObjectStorageRepositoryInterface)

    @pytest.fixture
    def usecase(
        self,
        mock_s3_repository: Mock,
        mock_logger: Mock,
    ) -> GenerateLgtmImageUsecase:
        """GenerateLgtmImageUsecaseのインスタンス"""
        return GenerateLgtmImageUsecase(
            s3_repository=mock_s3_repository,
            bucket_name="test-bucket",
            object_key="test-key.jpg",
            logger=mock_logger,
        )

    def test_execute_success(
        self,
        usecase: GenerateLgtmImageUsecase,
        mock_s3_repository: Mock,
    ) -> None:
        """正常にLGTM画像が生成されること"""
        # Arrange
        mock_s3_repository.fetch_image.return_value = b"test data"

        # Act
        result = usecase.execute()

        # Assert
        assert result == ("test-bucket", "test-key.jpg")
        mock_s3_repository.fetch_image.assert_called_once()
```

## テストすべきこと・テストしないこと

### テストすべき ✅
- ビジネスロジック
- 計算処理・変換処理
- 外部システムとの連携
- エラーハンドリング
- 境界値・エッジケース

### テストしない ❌
- 単純なデータクラス（dataclass、TypedDict）
- 単純なgetter/setter
- フレームワークの機能そのもの

## テスト実装時のチェックリスト

- [ ] ファイル先頭に必須コメントを記載
- [ ] テストクラス・メソッド名が命名規則に従っている
- [ ] 各テストに日本語docstringがある
- [ ] AAAパターンに従っている
- [ ] pytest fixtureを適切に使用している
- [ ] `@pytest.mark.parametrize`に`ids`パラメータがある
- [ ] モックの呼び出しを検証している
- [ ] 異常系テストで`pytest.raises()`を使用している
- [ ] 正常系と異常系の両方をカバーしている
