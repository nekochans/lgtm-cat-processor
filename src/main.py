from contextvars import Context
from typing import NotRequired, TypedDict
from presentation.handle_process import handle_process


class Image(TypedDict):
    bucketName: str
    objectKey: str
    databaseId: NotRequired[int]


class Event(TypedDict):
    process: str
    image: Image


class Response(TypedDict):
    image: Image


def format_response(
    bucket_name: str, object_key: str, image_id: int | None = None
) -> Response:
    response: Response = {"image": {"bucketName": bucket_name, "objectKey": object_key}}
    if image_id is not None:
        response["image"]["databaseId"] = image_id
    return response


def lambda_handler(event: Event, context: Context) -> Response:
    process = event.get("process")
    bucket_name = event.get("image", {}).get("bucketName")
    object_key = event.get("image", {}).get("objectKey")
    database_id = event.get("image", {}).get("databaseId")

    if process is None or bucket_name is None or object_key is None:
        raise ValueError(
            "Invalid input: process, bucketName, objectKey が設定されていません。"
        )

    request_id = context.aws_request_id  # type: ignore

    upload_bucket_name, upload_object_key, image_id = handle_process(
        request_id, process, bucket_name, object_key, database_id
    )

    return format_response(upload_bucket_name, upload_object_key, image_id)
