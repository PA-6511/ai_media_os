import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import scripts.register_amazon_x_tracking_id_pool as module
from app.db.models.amazon_x_tracking_id_pool import AmazonXTrackingIdPool
from app.db.repositories.amazon_x_tracking_id_pool_repository import (
    AmazonXTrackingIdPoolError,
    validate_controlled_tracking_id,
)


class FakeSession:
    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


class FakeRepository:
    created = True
    row = SimpleNamespace(
        tracking_id="x-sale-01",
        status="AVAILABLE",
    )

    def __init__(self, session):
        self.session = session

    def register_available(
        self,
        *,
        tracking_id,
    ):
        assert tracking_id == "x-sale-01"

        return (
            self.row,
            self.created,
        )


@pytest.fixture
def repository(monkeypatch):
    FakeRepository.created = True

    monkeypatch.setattr(
        module,
        "AmazonXTrackingIdPoolRepository",
        FakeRepository,
    )


def test_register_commits_once(repository):
    session = FakeSession()

    result = module.register_tracking_id(
        session=session,
        tracking_id="x-sale-01",
    )

    assert session.commit_count == 1
    assert session.rollback_count == 0
    assert result.tracking_id == "x-sale-01"
    assert result.status == "AVAILABLE"
    assert result.created is True


def test_idempotent_registration_still_commits_once(repository):
    FakeRepository.created = False

    session = FakeSession()

    result = module.register_tracking_id(
        session=session,
        tracking_id="x-sale-01",
    )

    assert session.commit_count == 1
    assert result.created is False


def test_direct_script_validation_from_repo_root():
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/register_amazon_x_tracking_id_pool.py",
            "--tracking-id",
            "p6-validation-01",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "VALIDATION=PASS" in completed.stdout
    assert "DB_OPENED=NO" in completed.stdout
    assert "DB_WRITE=NO" in completed.stdout


def test_shared_tracking_id_rejected_before_repository(repository):
    session = FakeSession()

    with pytest.raises(
        ValueError,
        match="shared_tracking_id_not_allowed",
    ):
        module.register_tracking_id(
            session=session,
            tracking_id="ktkr77-22",
        )

    assert session.commit_count == 0


def test_shared_tracking_id_validation_rejected(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        module,
        "AmazonXTrackingIdPoolRepository",
        FakeRepository,
    )

    with pytest.raises(
        ValueError,
        match="shared_tracking_id_not_allowed",
    ):
        module._reject_shared_tracking_id(
            "ktkr77-22"
        )


def test_gadget_shared_tracking_id_rejected_before_repository(repository):
    session = FakeSession()

    with pytest.raises(
        ValueError,
        match="shared_tracking_id_not_allowed",
    ):
        module.register_tracking_id(
            session=session,
            tracking_id="watermelon2-22",
        )

    assert session.commit_count == 0


def test_gadget_shared_tracking_id_validation_rejected():
    with pytest.raises(
        ValueError,
        match="shared_tracking_id_not_allowed",
    ):
        module._reject_shared_tracking_id(
            "watermelon2-22"
        )


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/register_amazon_x_tracking_id_pool.py"
INSTRUMENTATION = """
import json, runpy, sys
from pathlib import Path
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session
mode, cleanup_file, script, *arguments = sys.argv[1:]
counts = {"close": 0, "public_rollback": 0, "engine_rollback": 0, "commit": 0, "flush": 0}
original_close, original_rollback = Session.close, Session.rollback
original_commit, original_flush = Session.commit, Session.flush
def close(self):
    counts["close"] += 1
    try:
        value = original_close(self)
    finally:
        counts["in_transaction_after_close"] = self.in_transaction()
    if mode == "close":
        raise RuntimeError("sensitive-x-marker-01 [SQL: SECRET_SQL] [parameters: SECRET_PARAMETERS]")
    return value
def rollback(self):
    counts["public_rollback"] += 1
    if mode == "rollback_before":
        raise RuntimeError("sensitive-x-marker-01 SECRET_PARAMETERS")
    value = original_rollback(self)
    if mode == "rollback":
        raise RuntimeError("sensitive-x-marker-01 [SQL: SECRET_SQL] [parameters: SECRET_PARAMETERS]")
    return value
def commit(self):
    counts["commit"] += 1
    if mode in {"commit", "rollback", "rollback_before"}:
        self.flush()
        raise RuntimeError("sensitive-x-marker-01 [SQL: SECRET_SQL] [parameters: SECRET_PARAMETERS]")
    return original_commit(self)
def flush(self, *args, **kwargs):
    counts["flush"] += 1
    value = original_flush(self, *args, **kwargs)
    if mode == "flush":
        raise RuntimeError("sensitive-x-marker-01 [SQL: SECRET_SQL] [parameters: SECRET_PARAMETERS]")
    return value
def engine_rollback(connection):
    counts["engine_rollback"] += 1
event.listen(Engine, "rollback", engine_rollback)
Session.close, Session.rollback = close, rollback
Session.commit, Session.flush = commit, flush
sys.argv = [script, *arguments]
try:
    runpy.run_path(script, run_name="__main__")
finally:
    Path(cleanup_file).write_text(json.dumps(counts, sort_keys=True))
"""


def schema(database, *, reject=False):
    engine = create_engine(f"sqlite:///{database}")
    AmazonXTrackingIdPool.__table__.create(engine)
    engine.dispose()
    if reject:
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TRIGGER reject_registration BEFORE INSERT ON amazon_x_tracking_id_pool "
                "BEGIN SELECT RAISE(ABORT, 'sensitive-x-marker-01 SECRET_SQL SECRET_PARAMETERS'); END"
            )


def rows(database):
    with sqlite3.connect(database) as connection:
        return connection.execute(
            "SELECT tracking_id,status FROM amazon_x_tracking_id_pool ORDER BY tracking_id"
        ).fetchall()


def run_cli(tmp_path, *arguments, database=None, mode=None):
    database = database or tmp_path / "no-open.db"
    env = dict(
        os.environ,
        DATABASE_BACKEND="sqlite",
        DATABASE_URL=f"sqlite:///{database}",
        AI_MEDIA_OS_TESTING="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    cleanup = tmp_path / "cleanup.json"
    if mode is None:
        command = [sys.executable, "-B", str(SCRIPT), *arguments]
    else:
        command = [
            sys.executable, "-B", "-c", INSTRUMENTATION,
            mode, str(cleanup), str(SCRIPT), *arguments,
        ]
    process = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    stdout, stderr = process.communicate()
    record = {
        "arguments": list(arguments), "mode": mode, "returncode": process.returncode,
        "stdout": stdout, "stderr": stderr, "pid": process.pid,
        "cleanup": json.loads(cleanup.read_text()) if mode is not None else None,
    }
    audit_path = os.environ.get("POOL_AUDIT_LOG")
    if audit_path:
        events = [
            json.loads(line) for line in Path(audit_path).read_text().splitlines()
            if json.loads(line).get("pid") == process.pid
        ]
        record["sqlite_connections"] = [e for e in events if e["event"] == "sqlite3.connect"]
        record["module_origins"] = [e for e in events if e["event"] == "module_origins"]
        assert record["module_origins"]
        assert all(e["allowed"] for e in events)
    evidence_root = os.environ.get("POOL_EVIDENCE_ROOT")
    if evidence_root:
        transcripts = Path(evidence_root) / "cli-transcripts"
        transcripts.mkdir(exist_ok=True)
        (transcripts / f"{tmp_path.name}-{process.pid}.json").write_text(
            json.dumps(record, indent=2) + "\n"
        )
    return record


def assert_no_connection(result, database):
    assert not database.exists()
    if "sqlite_connections" in result:
        assert not result["sqlite_connections"]


def assert_redacted_failure(result, *, input_error=False):
    assert result["returncode"] == (2 if input_error else 1)
    assert result["stdout"] == ""
    assert result["stderr"] == (
        "ERROR=INPUT_INVALID\n" if input_error else "ERROR=REGISTRATION_FAILED\n"
    )
    for marker in ("Traceback", "sensitive-x-marker-01", "SECRET_SQL",
                   "SECRET_PARAMETERS", "[SQL:", "[parameters:"):
        assert marker not in result["stdout"] + result["stderr"]


def test_validator_identity():
    assert module.validate_controlled_tracking_id is validate_controlled_tracking_id


def test_validation_only_masks_id_without_session_or_connection(tmp_path):
    result = run_cli(tmp_path, "--tracking-id", "x-admin-output-01")
    assert result["returncode"] == 0 and result["stderr"] == ""
    assert result["stdout"] == (
        "VALIDATION=PASS\nTRACKING_ID= [REDACTED]\nDB_OPENED=NO\nDB_WRITE=NO\n"
    )
    assert "x-admin-output-01" not in result["stdout"] + result["stderr"]
    assert_no_connection(result, tmp_path / "no-open.db")
    if "module_origins" in result:
        assert "app.db.session" not in result["module_origins"][0]["modules"]


@pytest.mark.parametrize("tracking_id", [
    "ktkr77-22", "watermelon2-22", "bad", "", "   ",
])
@pytest.mark.parametrize("execute", [False, True])
def test_invalid_inputs_exit_two_without_traceback_or_connection(tmp_path, tracking_id, execute):
    arguments = ["--tracking-id", tracking_id] + (["--execute"] if execute else [])
    result = run_cli(tmp_path, *arguments)
    assert_redacted_failure(result, input_error=True)
    assert_no_connection(result, tmp_path / "no-open.db")
    if "module_origins" in result:
        assert "app.db.session" not in result["module_origins"][0]["modules"]


def test_missing_argument_is_sanitized_and_exits_two(tmp_path):
    result = run_cli(tmp_path)
    assert_redacted_failure(result, input_error=True)
    assert_no_connection(result, tmp_path / "no-open.db")


def test_actual_registration_is_idempotent_and_masks_output(tmp_path):
    database = tmp_path / "registration.db"
    schema(database)
    first = run_cli(
        tmp_path, "--tracking-id", "x-admin-output-01", "--execute",
        database=database, mode="normal",
    )
    assert first["returncode"] == 0 and first["stderr"] == ""
    assert first["stdout"] == (
        "REGISTRATION=PASS\nTRACKING_ID= [REDACTED]\nSTATUS= AVAILABLE\nCREATED= YES\n"
    )
    assert "x-admin-output-01" not in first["stdout"] + first["stderr"]
    assert first["cleanup"]["close"] == 1
    assert first["cleanup"]["public_rollback"] == 0
    assert first["cleanup"]["in_transaction_after_close"] is False
    second = run_cli(tmp_path, "--tracking-id", "x-admin-output-01", "--execute", database=database)
    assert second["returncode"] == 0 and "CREATED= NO" in second["stdout"]
    assert "x-admin-output-01" not in second["stdout"] + second["stderr"]
    assert rows(database) == [("x-admin-output-01", "AVAILABLE")]


@pytest.mark.parametrize("mode", ["commit", "flush", "integrity"])
def test_cli_failure_explicitly_rolls_back_closes_and_redacts(tmp_path, mode):
    database = tmp_path / "failure.db"
    schema(database, reject=mode == "integrity")
    result = run_cli(
        tmp_path, "--tracking-id", "sensitive-x-marker-01", "--execute",
        database=database, mode=mode,
    )
    assert_redacted_failure(result)
    assert rows(database) == []
    cleanup = result["cleanup"]
    assert cleanup["close"] == 1 and cleanup["public_rollback"] == 1
    assert cleanup["engine_rollback"] == 1
    assert cleanup["in_transaction_after_close"] is False


def test_actual_deferred_commit_failure_rolls_back_explicitly(tmp_path):
    database = tmp_path / "deferred-commit.db"
    schema(database)
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE parent_fixture(id INTEGER PRIMARY KEY);"
            "CREATE TABLE child_fixture(parent_id INTEGER, "
            "FOREIGN KEY(parent_id) REFERENCES parent_fixture(id) "
            "DEFERRABLE INITIALLY DEFERRED);"
            "CREATE TRIGGER defer_commit_failure AFTER INSERT ON amazon_x_tracking_id_pool "
            "BEGIN INSERT INTO child_fixture(parent_id) VALUES (999); END;"
        )
    result = run_cli(
        tmp_path, "--tracking-id", "sensitive-x-marker-01", "--execute",
        database=database, mode="normal",
    )
    assert_redacted_failure(result)
    assert result["cleanup"]["commit"] == 1
    assert result["cleanup"]["public_rollback"] == 1
    assert result["cleanup"]["close"] == 1
    assert result["cleanup"]["in_transaction_after_close"] is False
    assert rows(database) == []
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM child_fixture").fetchone() == (0,)


@pytest.mark.parametrize("tracking_id", ["ktkr77-22", "bad"])
def test_execute_input_rejection_never_creates_session(tmp_path, tracking_id):
    result = run_cli(tmp_path, "--tracking-id", tracking_id, "--execute", mode="normal")
    assert_redacted_failure(result, input_error=True)
    assert_no_connection(result, tmp_path / "no-open.db")
    assert result["cleanup"]["close"] == 0
    assert result["cleanup"]["commit"] == 0
    assert result["cleanup"]["public_rollback"] == 0


@pytest.mark.parametrize("mode", ["commit", "flush"])
def test_direct_helper_rolls_back_but_caller_closes_session(tmp_path, mode):
    database = tmp_path / "direct-helper.db"
    schema(database)
    engine = create_engine(f"sqlite:///{database}")

    class ObservedSession(Session):
        def __init__(self, *args, **kwargs):
            self.rollback_calls = 0
            self.close_calls = 0
            super().__init__(*args, **kwargs)

        def commit(self):
            if mode == "commit":
                self.flush()
                raise RuntimeError("direct_commit_failure")
            return super().commit()

        def flush(self, *args, **kwargs):
            value = super().flush(*args, **kwargs)
            if mode == "flush":
                raise RuntimeError("direct_flush_failure")
            return value

        def rollback(self):
            self.rollback_calls += 1
            return super().rollback()

        def close(self):
            self.close_calls += 1
            return super().close()

    session = ObservedSession(engine, autoflush=False, expire_on_commit=False)
    try:
        with pytest.raises(RuntimeError, match="direct_" + mode + "_failure"):
            module.register_tracking_id(session=session, tracking_id="x-direct-01")
        assert session.rollback_calls == 1 and session.close_calls == 0
        assert not session.in_transaction()
        assert rows(database) == []
        session.rollback()
        assert session.rollback_calls == 2 and not session.in_transaction()
        assert rows(database) == []
    finally:
        session.close()
        engine.dispose()
    assert session.close_calls == 1


def test_direct_integrity_failure_resets_session_before_reraising(tmp_path):
    database = tmp_path / "direct-integrity.db"
    schema(database, reject=True)
    engine = create_engine(f"sqlite:///{database}")
    session = Session(engine, autoflush=False)
    try:
        with pytest.raises(IntegrityError):
            module.register_tracking_id(session=session, tracking_id="x-direct-01")
        assert session.is_active and not session.in_transaction()
        assert rows(database) == []
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("tracking_id", ["ktkr77-22", "watermelon2-22"])
def test_direct_shared_rejection_keeps_session_unused(tmp_path, tracking_id):
    engine = create_engine(f"sqlite:///{tmp_path / 'unused.db'}")
    with Session(engine) as session:
        with pytest.raises(AmazonXTrackingIdPoolError, match="shared_tracking_id_not_allowed"):
            module.register_tracking_id(session=session, tracking_id=tracking_id)
        assert not session.in_transaction()
    assert not (tmp_path / "unused.db").exists()
    engine.dispose()


@pytest.mark.parametrize("arguments", [
    ["--tracking-id", "sensitive-x-marker-01", "--unknown=sensitive-x-marker-01"],
    ["--tracking-id", "sensitive-x-marker-01", "sensitive-x-marker-01"],
    ["--tracking-id"],
    ["--tracking-id", "sensitive-x-marker-01", "--execute=sensitive-x-marker-01"],
])
def test_argument_parser_never_echoes_input_values(tmp_path, arguments):
    result = run_cli(tmp_path, *arguments)
    assert_redacted_failure(result, input_error=True)
    assert_no_connection(result, tmp_path / "no-open.db")


@pytest.mark.parametrize("mode", ["rollback", "rollback_before", "close"])
def test_cleanup_failure_is_reported_without_exception_text(tmp_path, mode):
    database = tmp_path / "cleanup-failure.db"
    schema(database)
    result = run_cli(
        tmp_path, "--tracking-id", "sensitive-x-marker-01", "--execute",
        database=database, mode=mode,
    )
    assert_redacted_failure(result)
    assert result["cleanup"]["close"] == 1
    assert result["cleanup"]["in_transaction_after_close"] is False
    if mode in {"rollback", "rollback_before"}:
        assert result["cleanup"]["public_rollback"] == 1
        assert result["cleanup"]["engine_rollback"] == 1
        assert rows(database) == []
    else:
        assert result["cleanup"]["public_rollback"] == 0
        assert rows(database) == [("sensitive-x-marker-01", "AVAILABLE")]


def test_session_factory_failure_is_sanitized(monkeypatch, capsys):
    import app.db.session as sessions

    def fail():
        raise RuntimeError("sensitive-x-marker-01 SECRET_PARAMETERS")

    monkeypatch.setattr(sessions, "SessionLocal", fail)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--tracking-id", "x-sale-01", "--execute"])
    assert module.main() == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "ERROR=REGISTRATION_FAILED\n"


def test_repeated_rollback_and_close_have_no_persistent_side_effects(tmp_path):
    database = tmp_path / "repeat-cleanup.db"
    schema(database)
    engine = create_engine(f"sqlite:///{database}")
    session = Session(engine, expire_on_commit=False)
    module.register_tracking_id(session=session, tracking_id="x-persisted-01")
    session.rollback()
    session.rollback()
    session.close()
    session.close()
    assert not session.in_transaction()
    assert rows(database) == [("x-persisted-01", "AVAILABLE")]
    engine.dispose()
