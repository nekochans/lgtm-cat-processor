class StoreToDbUsecase:
    def __init__(self, bucket_name: str, object_key: str) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key

    def execute(self) -> None:
        print("画像情報を永続化する")
        print(f"bucket_name: {self.bucket_name}")
        print(f"object_key: {self.object_key}")
