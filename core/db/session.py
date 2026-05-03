"""Database session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

from core.db.models import Base


class SessionFactory:
    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls, database_url: str = None):
        if cls._engine is None:
            if database_url is None:
                database_url = os.environ.get(
                    "DATABASE_URL", "sqlite:///pdt.db"
                )
            cls._engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
            Base.metadata.create_all(cls._engine)
        return cls._engine

    @classmethod
    def get_session_factory(cls, database_url: str = None):
        if cls._session_factory is None:
            engine = cls.get_engine(database_url)
            cls._session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        return cls._session_factory

    @classmethod
    def get_session(cls, database_url: str = None) -> Generator[Session, None, None]:
        factory = cls.get_session_factory(database_url)
        session = factory()
        try:
            yield session
        finally:
            session.close()

    @classmethod
    def session(cls, database_url: str = None) -> Session:
        factory = cls.get_session_factory(database_url)
        return factory()


def get_db() -> Generator[Session, None, None]:
    yield from SessionFactory.get_session()
