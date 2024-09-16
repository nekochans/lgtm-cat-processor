from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class LgtmImage(Base):
    __tablename__ = "lgtm_images"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    filename = Column(String(255), unique=True, nullable=False)
    path = Column(String(255), index=True, nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
