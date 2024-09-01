class GenerateLgtmImageUsecase:
    def __init__(self, bucket_name: str, object_key: str) -> None:
        self.bucket_name = bucket_name
        self.object_key = object_key

    def execute(self) -> None:
        print("LGTM画像を生成する")
        print(f"bucket_name: {self.bucket_name}")
        print(f"object_key: {self.object_key}")
