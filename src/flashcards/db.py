import os
from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from flashcards import models  # noqa: F401 - registriert die Tabellen in den Metadaten

DATABASE_URL = f"sqlite:///{os.environ.get('LERNKARTEI_DB', 'lernkartei.db')}"


def make_engine(url: str = DATABASE_URL, **kwargs) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    # SQLite prüft Fremdschlüssel nur, wenn das pro Verbindung eingeschaltet wird.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = make_engine()


def init_db(target: Engine | None = None) -> None:
    SQLModel.metadata.create_all(target or engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
