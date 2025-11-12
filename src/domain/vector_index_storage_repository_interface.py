from typing import Protocol


class VectorIndexStorageRepositoryInterface(Protocol):
    """ベクトルインデックスストレージのインターフェース"""

    def save_vector_index(
        self,
        source_bucket: str,
        source_key: str,
        database_id: int,
        embedding: list[float],
    ) -> None:
        """
        画像の埋め込みベクトルをベクトルインデックスに保存する

        Args:
            source_bucket: 元画像が保存されているS3バケット名（ログ用）
            source_key: 元画像のS3オブジェクトキー（metadataに保存）
            database_id: データベースの主キー（ベクトルのkeyとして使用）
            embedding: 画像の埋め込みベクトル

        Note:
            - database_idがベクトルストレージのkeyとして使用されます
            - source_keyはmetadataとしてデバッグ用に保存されます
            - source_bucketはログ出力にのみ使用されます（保存されません）
        """
        ...
