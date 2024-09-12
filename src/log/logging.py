import logging
import json
from typing import Any


class JSONFormatter(logging.Formatter):
    def __init__(
        self, request_id: str, process_type: str, bucket_name: str, object_key: str
    ) -> None:
        super().__init__()
        self.request_id = request_id
        self.process_type = process_type
        self.bucket_name = bucket_name
        self.object_key = object_key

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "requestId": self.request_id,
            "processType": self.process_type,
            "bucketName": self.bucket_name,
            "objectKey": self.object_key,
            "filename": record.filename,
            "funcName": record.funcName,
            "levelname": record.levelname,
            "lineno": record.lineno,
            "module": record.module,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        def json_default(obj: Any) -> str:
            return str(obj)

        return json.dumps(log_data, default=json_default)


class AppLogger(logging.Logger):
    def __init__(
        self,
        name: str,
        request_id: str,
        process_type: str,
        bucket_name: str,
        object_key: str,
    ) -> None:
        super().__init__(name)
        self.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = JSONFormatter(request_id, process_type, bucket_name, object_key)
        handler.setFormatter(formatter)

        self.addHandler(handler)


def setup_logger(
    request_id: str, process_type: str, bucket_name: str, object_key: str
) -> AppLogger:
    logger = AppLogger(__name__, request_id, process_type, bucket_name, object_key)
    return logger
