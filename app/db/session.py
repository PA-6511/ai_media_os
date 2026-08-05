from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.access_guard import assert_database_target_allowed, is_test_environment
from app.db.config import DATABASE_BACKEND, DATABASE_URL, validate_database_config


_engine: Engine | None = None
_engine_testing_mode: bool | None = None
_session_factory: sessionmaker[Session] | None = None


def _sqlite_connect_pragmas(
    dbapi_connection: object,
    connection_record: object,
    *,
    enable_wal: bool,
) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        if enable_wal:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()


def get_engine() -> Engine:
    """Create the configured engine on first use, never during import."""

    global _engine, _engine_testing_mode
    validate_database_config()
    testing = is_test_environment()
    if DATABASE_BACKEND == "sqlite":
        assert_database_target_allowed(
            DATABASE_URL,
            operation="SQLAlchemy write engine creation",
            testing=testing,
        )
    if _engine is not None and _engine_testing_mode == testing:
        return _engine
    if _engine is not None:
        dispose_engine()

    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if DATABASE_BACKEND == "sqlite":
        engine_options["connect_args"] = {
            "check_same_thread": False,
            "timeout": 30,
        }
    candidate = create_engine(DATABASE_URL, **engine_options)
    if DATABASE_BACKEND == "sqlite":
        event.listen(
            candidate,
            "connect",
            lambda connection, record: _sqlite_connect_pragmas(
                connection,
                record,
                enable_wal=not testing,
            ),
        )
    _engine = candidate
    _engine_testing_mode = testing
    return candidate


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    engine = get_engine()
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


def SessionLocal() -> Session:
    """Compatibility callable backed by the lazily-created session factory."""

    return get_session_factory()()


def dispose_engine() -> None:
    """Dispose and clear lazy state (primarily for isolated configuration tests)."""

    global _engine, _engine_testing_mode, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_testing_mode = None
    _session_factory = None


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
