"""
Livello di connessione al database.

Espone:
- `engine`      : il motore SQLAlchemy collegato al file SQLite.
- `SessionLocal`: factory di sessioni.
- `Base`        : classe base dichiarativa per i modelli ORM.
- `get_session()`: context manager che apre/chiude una sessione con commit/rollback.

Centralizzare qui la creazione dell'engine evita connessioni sparse nel codice
e rende banale, in futuro, sostituire SQLite con PostgreSQL (basta cambiare DB_URL).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from utils.config import DB_URL


class Base(DeclarativeBase):
    """Classe base per tutti i modelli ORM."""
    pass


_is_sqlite = DB_URL.startswith("sqlite")

# check_same_thread è necessario solo per SQLite.
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine: Engine = create_engine(
    DB_URL,
    echo=False,
    future=True,
    connect_args=_connect_args,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:
    """Abilita i foreign key su SQLite (su PostgreSQL sono sempre attivi)."""
    if _is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager per una sessione transazionale.

    Esempio:
        with get_session() as session:
            session.add(obj)
        # commit automatico all'uscita; rollback in caso di eccezione.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
