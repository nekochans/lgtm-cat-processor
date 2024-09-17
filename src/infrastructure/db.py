import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def get_env_var(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"環境変数 {var_name} が設定されていません")
    return value


def create_db() -> sessionmaker[Session]:
    host = get_env_var("DB_HOSTNAME")
    user = get_env_var("DB_USERNAME")
    password = get_env_var("DB_PASSWORD")
    database = get_env_var("DB_NAME")

    connection_string = f"mysql+mysqlconnector://{user}:{password}@{host}/{database}"
    engine = create_engine(connection_string)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal
