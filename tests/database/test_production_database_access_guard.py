from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from sqlalchemy import text

from app.db.access_guard import (
    PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST,
    ProductionDatabaseAccessBlocked,
    assert_database_target_allowed,
    is_test_environment,
)
from app.db.config import (
    PRODUCTION_DATABASE_DIRECTORY,
    PRODUCTION_SQLITE_PATH,
)


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.mark.parametrize(
    "target",
    [
        str(PRODUCTION_SQLITE_PATH),
        f"sqlite:///{PRODUCTION_SQLITE_PATH}",
        f"sqlite+pysqlite:///{PRODUCTION_SQLITE_PATH}",
        f"file:{PRODUCTION_SQLITE_PATH}?mode=ro",
        f"sqlite:///file:{PRODUCTION_SQLITE_PATH}?uri=true",
    ],
)
def test_production_path_and_uri_variants_are_rejected(target: str) -> None:
    with pytest.raises(ProductionDatabaseAccessBlocked) as raised:
        assert_database_target_allowed(target, testing=True)
    assert PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST in str(raised.value)


def test_relative_path_resolving_to_production_is_rejected() -> None:
    with pytest.raises(ProductionDatabaseAccessBlocked):
        assert_database_target_allowed(
            "data/database/../database/ebook_affiliate.db",
            cwd=ROOT,
            testing=True,
        )


def test_symlink_to_production_is_rejected(tmp_path: Path) -> None:
    link = tmp_path / "production-link.db"
    link.symlink_to(PRODUCTION_SQLITE_PATH)
    with pytest.raises(ProductionDatabaseAccessBlocked):
        assert_database_target_allowed(link, testing=True)


def test_symlink_inside_protected_directory_cannot_escape_guard(
    tmp_path: Path,
) -> None:
    protected_directory = tmp_path / "protected"
    protected_directory.mkdir()
    protected = protected_directory / "production.db"
    protected.write_bytes(b"protected")
    safe_target = tmp_path / "safe.db"
    safe_target.write_bytes(b"safe")
    outward_link = protected_directory / "outward.db"
    outward_link.symlink_to(safe_target)

    with pytest.raises(ProductionDatabaseAccessBlocked):
        assert_database_target_allowed(
            outward_link,
            testing=True,
            production_database_path=protected,
            production_database_directory=protected_directory,
        )


def test_hard_link_inode_is_rejected_with_isolated_protected_file(
    tmp_path: Path,
) -> None:
    protected_directory = tmp_path / "protected"
    protected_directory.mkdir()
    protected = protected_directory / "production.db"
    protected.write_bytes(b"not a sqlite database")
    alias = tmp_path / "alias.db"
    os.link(protected, alias)

    with pytest.raises(ProductionDatabaseAccessBlocked, match="hard link"):
        assert_database_target_allowed(
            alias,
            testing=True,
            production_database_path=protected,
            production_database_directory=protected_directory,
        )


def test_other_database_inside_production_directory_is_rejected() -> None:
    with pytest.raises(ProductionDatabaseAccessBlocked):
        assert_database_target_allowed(
            PRODUCTION_DATABASE_DIRECTORY / "other-test.db",
            testing=True,
        )


def test_only_memory_and_tmp_database_targets_are_allowed(tmp_path: Path) -> None:
    assert assert_database_target_allowed(":memory:", testing=True) is None
    assert assert_database_target_allowed("sqlite:///:memory:", testing=True) is None
    assert assert_database_target_allowed("/tmp/explicit-test.db", testing=True) == Path(
        "/tmp/explicit-test.db"
    )
    assert assert_database_target_allowed(tmp_path / "fixture.db", testing=True) == (
        tmp_path / "fixture.db"
    ).resolve()
    with pytest.raises(ProductionDatabaseAccessBlocked):
        assert_database_target_allowed(ROOT / "test.db", testing=True)


def test_all_required_test_environment_signals_are_detected() -> None:
    assert is_test_environment(environ={"PYTEST_CURRENT_TEST": "x"}, argv=["python"])
    assert is_test_environment(environ={"APP_ENV": "test"}, argv=["python"])
    assert is_test_environment(
        environ={"AI_MEDIA_OS_TESTING": "1"}, argv=["python"]
    )
    assert is_test_environment(environ={}, argv=["pytest"])
    assert not is_test_environment(environ={}, argv=["python"])


def test_session_import_does_not_create_engine_connect_or_run_pragma() -> None:
    code = """
import sqlite3
import sqlalchemy
def forbidden(*args, **kwargs):
    raise AssertionError('import attempted engine creation or SQLite connection')
sqlalchemy.create_engine = forbidden
sqlite3.connect = forbidden
import app.db.session as session
assert session._engine is None
assert session._session_factory is None
print('IMPORT_SIDE_EFFECT_FREE')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, "AI_MEDIA_OS_TESTING": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "IMPORT_SIDE_EFFECT_FREE"


def test_session_rejects_default_production_engine_before_creation() -> None:
    import app.db.session as session

    session.dispose_engine()
    with pytest.raises(ProductionDatabaseAccessBlocked):
        session.get_engine()
    assert session._engine is None


def test_test_database_crud_works_without_enabling_wal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.db.session as session

    database = tmp_path / "crud.db"
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"

    session.dispose_engine()
    monkeypatch.setattr(session, "DATABASE_URL", f"sqlite:///{database}")
    engine = session.get_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)"))
    with session.SessionLocal() as database_session:
        database_session.execute(
            text("INSERT INTO sample (value) VALUES (:value)"), {"value": "ok"}
        )
        database_session.commit()
        assert database_session.execute(text("SELECT value FROM sample")).scalar_one() == "ok"
    session.dispose_engine()

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_normal_runtime_engine_mode_can_be_created_only_on_a_temp_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.db.session as session

    database = tmp_path / "normal-runtime-mode.db"
    session.dispose_engine()
    monkeypatch.setattr(session, "DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setattr(session, "is_test_environment", lambda: False)
    engine = session.get_engine()
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
    session.dispose_engine()


def test_read_only_engine_does_not_change_journal_mode(tmp_path: Path) -> None:
    from app.db.read_only_session import create_sqlite_read_only_engine

    database = tmp_path / "read-only.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
        before = connection.execute("PRAGMA journal_mode").fetchone()[0]

    engine = create_sqlite_read_only_engine(database)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM sample")).scalar_one() == 0
    engine.dispose()

    with sqlite3.connect(database) as connection:
        after = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert after == before


def test_direct_sqlite_connect_to_production_is_globally_rejected() -> None:
    before = _sha256(PRODUCTION_SQLITE_PATH)
    with pytest.raises(ProductionDatabaseAccessBlocked):
        sqlite3.connect(PRODUCTION_SQLITE_PATH)
    assert _sha256(PRODUCTION_SQLITE_PATH) == before


def test_cli_subprocess_rejects_its_production_default() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/save_manual_amazon_offer.py"),
            "--ebook-item-id",
            "not-used",
            "--asin",
            "B000000000",
            "--tracking-id",
            "not-used-22",
        ],
        cwd=ROOT,
        env={**os.environ, "AI_MEDIA_OS_TESTING": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 4
    assert PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST in result.stderr


def test_arbitrary_python_subprocess_inherits_direct_sqlite_guard() -> None:
    code = (
        "import sqlite3; "
        f"sqlite3.connect({str(PRODUCTION_SQLITE_PATH)!r})"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST in result.stderr


def test_corrective_runner_rejects_production_even_for_dry_run() -> None:
    from scripts.run_ebook_database_corrective_reconciliation_once import (
        ReconciliationBlocked,
        run_reconciliation,
    )

    before = _sha256(PRODUCTION_SQLITE_PATH)
    with pytest.raises(
        ReconciliationBlocked,
        match=PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST,
    ):
        run_reconciliation(
            database_path=PRODUCTION_SQLITE_PATH,
            repo_root=ROOT,
            execute=False,
        )
    assert _sha256(PRODUCTION_SQLITE_PATH) == before


def test_corrective_cli_subprocess_rejects_production_dry_run() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ebook_database_corrective_reconciliation_once.py"),
            "--database",
            str(PRODUCTION_SQLITE_PATH),
        ],
        cwd=ROOT,
        env={**os.environ, "AI_MEDIA_OS_TESTING": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST in result.stdout


def test_production_main_and_wal_content_match_session_start_fingerprint() -> None:
    from conftest import PRODUCTION_FINGERPRINT_BEFORE

    assert _sha256(PRODUCTION_SQLITE_PATH) == PRODUCTION_FINGERPRINT_BEFORE[
        "database"
    ]["sha256"]
    assert _sha256(Path(f"{PRODUCTION_SQLITE_PATH}-wal")) == (
        PRODUCTION_FINGERPRINT_BEFORE["wal"]["sha256"]
    )
