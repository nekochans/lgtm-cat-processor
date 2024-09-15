import os
from pymysql.connections import Connection
import pymysql


def get_env_var(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"環境変数 {var_name} が設定されていません")
    return value


def create_db_connection() -> Connection:  # type: ignore[type-arg]
    host = get_env_var("DB_HOSTNAME")
    user = get_env_var("DB_USERNAME")
    password = get_env_var("DB_PASSWORD")
    database = get_env_var("DB_NAME")

    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        ssl={
            "ca": "/etc/ssl/certs/ca-certificates.crt",
        },
    )
    return connection
