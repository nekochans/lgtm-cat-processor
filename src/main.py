from contextvars import Context
from typing import TypedDict
from presentation.handle_process import handle_process


class Image(TypedDict):
    bucketName: str
    objectKey: str


class Event(TypedDict):
    process: str
    image: Image


class Response(TypedDict):
    image: Image


def format_response(bucket_name: str, object_key: str) -> Response:
    return {"image": {"bucketName": bucket_name, "objectKey": object_key}}


def lambda_handler(event: Event, context: Context) -> Response:
    process = event.get("process")
    bucket_name = event.get("image", {}).get("bucketName")
    object_key = event.get("image", {}).get("objectKey")

    if process is None or bucket_name is None or object_key is None:
        raise ValueError(
            "Invalid input: process, bucketName, objectKey が設定されていません。"
        )

    request_id = context.aws_request_id  # type: ignore

    handle_process(request_id, process, bucket_name, object_key)

    return format_response(bucket_name, object_key)
