from typing import Dict
from presentation.handle_process import handle_process


def format_response(bucket_name: str, object_key: str) -> Dict:
    return {"image": {"bucketName": bucket_name, "objectKey": object_key}}


def lambda_handler(event, context):
    process = event.get("process")
    bucket_name = event.get("image", {}).get("bucketName")
    object_key = event.get("image", {}).get("objectKey")

    handle_process(process, bucket_name, object_key)

    return format_response(bucket_name, object_key)
