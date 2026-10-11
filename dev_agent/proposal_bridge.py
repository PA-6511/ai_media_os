from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from dev_agent.file_bridge import REPO_ROOT, is_sensitive_path
from dev_agent.write_bridge import (
    CANARY_WRITE_FILES,
    MAX_FILE_BYTES,
    MAX_REPLACEMENT_BYTES,
    sha256_text,
)


PROPOSAL_DIR = REPO_ROOT / "dev_agent" / "proposals"
PROPOSAL_SCHEMA_VERSION = 1


def _canonical_json(data: dict) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _proposal_id(core: dict) -> str:
    digest = hashlib.sha256(
        _canonical_json(core).encode("utf-8")
    ).hexdigest()
    return f"proposal_v1_{digest}"


def create_write_proposal(
    *,
    relative_path: str,
    old_text: str,
    new_text: str,
) -> dict:
    raw_path = Path(relative_path)

    if raw_path.is_absolute():
        return {
            "status": "DENIED",
            "reason": "ABSOLUTE_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    if ".." in raw_path.parts:
        return {
            "status": "DENIED",
            "reason": "PARENT_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    normalized_path = raw_path.as_posix()

    if normalized_path not in CANARY_WRITE_FILES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_TARGET_NOT_ALLOWED",
            "path": normalized_path,
        }

    candidate = REPO_ROOT / raw_path
    resolved = candidate.resolve()

    try:
        relative_resolved = resolved.relative_to(REPO_ROOT)
    except ValueError:
        return {
            "status": "DENIED",
            "reason": "PATH_OUTSIDE_REPOSITORY",
            "path": normalized_path,
        }

    if is_sensitive_path(relative_resolved):
        return {
            "status": "DENIED",
            "reason": "SENSITIVE_PATH",
            "path": normalized_path,
        }

    if candidate.is_symlink():
        return {
            "status": "DENIED",
            "reason": "SYMLINK_NOT_ALLOWED",
            "path": normalized_path,
        }

    if resolved.suffix != ".py":
        return {
            "status": "DENIED",
            "reason": "ONLY_PYTHON_FILES_ALLOWED",
            "path": normalized_path,
        }

    if not resolved.exists():
        return {
            "status": "ERROR",
            "reason": "FILE_NOT_FOUND",
            "path": normalized_path,
        }

    if not resolved.is_file():
        return {
            "status": "ERROR",
            "reason": "NOT_A_FILE",
            "path": normalized_path,
        }

    if not old_text:
        return {
            "status": "DENIED",
            "reason": "OLD_TEXT_EMPTY",
            "path": normalized_path,
        }

    if len(old_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "OLD_TEXT_TOO_LARGE",
            "path": normalized_path,
        }

    if len(new_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "NEW_TEXT_TOO_LARGE",
            "path": normalized_path,
        }

    if resolved.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "FILE_TOO_LARGE",
            "path": normalized_path,
        }

    try:
        source_text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "status": "DENIED",
            "reason": "NON_UTF8_FILE",
            "path": normalized_path,
        }

    occurrence_count = source_text.count(old_text)

    if occurrence_count != 1:
        return {
            "status": "DENIED",
            "reason": (
                "OLD_TEXT_NOT_FOUND"
                if occurrence_count == 0
                else "OLD_TEXT_NOT_UNIQUE"
            ),
            "path": normalized_path,
            "occurrence_count": occurrence_count,
        }

    before_sha256 = sha256_text(source_text)

    core = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "relative_path": normalized_path,
        "old_text": old_text,
        "new_text": new_text,
        "before_sha256": before_sha256,
    }

    proposal_id = _proposal_id(core)

    record = {
        "proposal_id": proposal_id,
        **core,
    }

    PROPOSAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    proposal_path = PROPOSAL_DIR / f"{proposal_id}.json"

    try:
        proposal_file_display = str(
            proposal_path.relative_to(REPO_ROOT)
        )
    except ValueError:
        proposal_file_display = str(proposal_path)

    if proposal_path.exists():
        try:
            existing = json.loads(
                proposal_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {
                "status": "ERROR",
                "reason": "EXISTING_PROPOSAL_INVALID",
                "proposal_id": proposal_id,
            }

        if existing != record:
            return {
                "status": "ERROR",
                "reason": "PROPOSAL_ID_COLLISION",
                "proposal_id": proposal_id,
            }

        return {
            "status": "EXISTS",
            **record,
            "proposal_file": proposal_file_display,
            "source_write_performed": False,
        }

    fd, temp_name = tempfile.mkstemp(
        prefix=".proposal-",
        suffix=".tmp",
        dir=PROPOSAL_DIR,
    )

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                record,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp_name, proposal_path)

    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    return {
        "status": "CREATED",
        **record,
        "proposal_file": proposal_file_display,
        "source_write_performed": False,
    }


def _valid_proposal_id(value: str) -> bool:
    prefix = "proposal_v1_"

    if not value.startswith(prefix):
        return False

    digest = value[len(prefix):]

    return (
        len(digest) == 64
        and all(
            char in "0123456789abcdef"
            for char in digest
        )
    )


def verify_write_contract_source(
    *,
    relative_path: str,
    expected_sha256: str,
) -> dict:
    raw_path = Path(relative_path)

    if raw_path.is_absolute():
        return {
            "status": "DENIED",
            "reason": "ABSOLUTE_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    if ".." in raw_path.parts:
        return {
            "status": "DENIED",
            "reason": "PARENT_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    normalized_path = raw_path.as_posix()

    if normalized_path not in CANARY_WRITE_FILES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_TARGET_NOT_ALLOWED",
            "path": normalized_path,
        }

    if (
        len(expected_sha256) != 64
        or any(
            char not in "0123456789abcdef"
            for char in expected_sha256
        )
    ):
        return {
            "status": "DENIED",
            "reason": "INVALID_EXPECTED_SHA256",
            "path": normalized_path,
        }

    candidate = REPO_ROOT / raw_path
    resolved = candidate.resolve()

    try:
        relative_resolved = resolved.relative_to(REPO_ROOT)
    except ValueError:
        return {
            "status": "DENIED",
            "reason": "PATH_OUTSIDE_REPOSITORY",
            "path": normalized_path,
        }

    if is_sensitive_path(relative_resolved):
        return {
            "status": "DENIED",
            "reason": "SENSITIVE_PATH",
            "path": normalized_path,
        }

    if candidate.is_symlink():
        return {
            "status": "DENIED",
            "reason": "SYMLINK_NOT_ALLOWED",
            "path": normalized_path,
        }

    if not resolved.exists():
        return {
            "status": "ERROR",
            "reason": "FILE_NOT_FOUND",
            "path": normalized_path,
        }

    if not resolved.is_file():
        return {
            "status": "ERROR",
            "reason": "NOT_A_FILE",
            "path": normalized_path,
        }

    if resolved.suffix != ".py":
        return {
            "status": "DENIED",
            "reason": "ONLY_PYTHON_FILES_ALLOWED",
            "path": normalized_path,
        }

    if resolved.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "FILE_TOO_LARGE",
            "path": normalized_path,
        }

    try:
        source_text = resolved.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        return {
            "status": "DENIED",
            "reason": "NON_UTF8_FILE",
            "path": normalized_path,
        }

    current_sha256 = sha256_text(source_text)

    if current_sha256 != expected_sha256:
        return {
            "status": "DENIED",
            "reason": "STALE_PROPOSAL_SOURCE_CHANGED",
            "path": normalized_path,
            "expected_sha256": expected_sha256,
            "current_sha256": current_sha256,
        }

    return {
        "status": "VALID",
        "path": normalized_path,
        "expected_sha256": expected_sha256,
        "current_sha256": current_sha256,
    }


def load_write_proposal(
    proposal_id: str,
) -> dict:
    if not isinstance(proposal_id, str):
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_ID_MUST_BE_STRING",
        }

    if not _valid_proposal_id(proposal_id):
        return {
            "status": "DENIED",
            "reason": "INVALID_PROPOSAL_ID",
            "proposal_id": proposal_id,
        }

    proposal_path = (
        PROPOSAL_DIR / f"{proposal_id}.json"
    )

    if proposal_path.is_symlink():
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_SYMLINK_NOT_ALLOWED",
            "proposal_id": proposal_id,
        }

    if not proposal_path.exists():
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_NOT_FOUND",
            "proposal_id": proposal_id,
        }

    if not proposal_path.is_file():
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_NOT_A_FILE",
            "proposal_id": proposal_id,
        }

    if proposal_path.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_FILE_TOO_LARGE",
            "proposal_id": proposal_id,
        }

    try:
        data = json.loads(
            proposal_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_JSON_INVALID",
            "proposal_id": proposal_id,
        }

    if not isinstance(data, dict):
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_RECORD_INVALID",
            "proposal_id": proposal_id,
        }

    required_keys = {
        "proposal_id",
        "schema_version",
        "relative_path",
        "old_text",
        "new_text",
        "before_sha256",
    }

    if set(data) != required_keys:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_SCHEMA_KEYS_INVALID",
            "proposal_id": proposal_id,
        }

    if data.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_SCHEMA_VERSION_INVALID",
            "proposal_id": proposal_id,
        }

    if data.get("proposal_id") != proposal_id:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_ID_MISMATCH",
            "proposal_id": proposal_id,
        }

    for field in (
        "relative_path",
        "old_text",
        "new_text",
        "before_sha256",
    ):
        if not isinstance(data.get(field), str):
            return {
                "status": "DENIED",
                "reason": (
                    "PROPOSAL_FIELD_TYPE_INVALID"
                ),
                "field": field,
                "proposal_id": proposal_id,
            }

    normalized_path = Path(
        data["relative_path"]
    ).as_posix()

    if normalized_path != data["relative_path"]:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_PATH_NOT_NORMALIZED",
            "proposal_id": proposal_id,
        }

    if normalized_path not in CANARY_WRITE_FILES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_TARGET_NOT_ALLOWED",
            "proposal_id": proposal_id,
            "path": normalized_path,
        }

    core = {
        "schema_version": data["schema_version"],
        "relative_path": data["relative_path"],
        "old_text": data["old_text"],
        "new_text": data["new_text"],
        "before_sha256": data["before_sha256"],
    }

    recalculated_id = _proposal_id(core)

    if recalculated_id != proposal_id:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_ID_MISMATCH",
            "proposal_id": proposal_id,
            "recalculated_proposal_id": (
                recalculated_id
            ),
        }

    proposal_state = get_proposal_state(
        proposal_id
    )

    if proposal_state["status"] != "VALID":
        return proposal_state

    if (
        proposal_state["proposal_state"]
        == "EXECUTED"
    ):
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_ALREADY_EXECUTED",
            "proposal_id": proposal_id,
            "proposal_state": "EXECUTED",
        }

    if (
        proposal_state["proposal_state"]
        == "EXECUTING"
    ):
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_EXECUTION_ALREADY_CLAIMED",
            "proposal_id": proposal_id,
            "proposal_state": "EXECUTING",
        }

    source_check = verify_write_contract_source(
        relative_path=normalized_path,
        expected_sha256=data["before_sha256"],
    )

    if source_check["status"] != "VALID":
        return {
            **source_check,
            "proposal_id": proposal_id,
        }

    source_path = REPO_ROOT / normalized_path
    source_text = source_path.read_text(
        encoding="utf-8"
    )

    occurrence_count = source_text.count(
        data["old_text"]
    )

    if occurrence_count != 1:
        return {
            "status": "DENIED",
            "reason": (
                "PROPOSAL_OLD_TEXT_NOT_FOUND"
                if occurrence_count == 0
                else "PROPOSAL_OLD_TEXT_NOT_UNIQUE"
            ),
            "proposal_id": proposal_id,
            "path": normalized_path,
            "occurrence_count": occurrence_count,
        }

    return {
        "status": "VALID",
        "proposal_id": proposal_id,
        "relative_path": normalized_path,
        "old_text": data["old_text"],
        "new_text": data["new_text"],
        "before_sha256": data["before_sha256"],
        "current_sha256": (
            source_check["current_sha256"]
        ),
        "proposal_state": (
            proposal_state["proposal_state"]
        ),
        "proposal_file": str(
            proposal_path.relative_to(REPO_ROOT)
        ),
    }


PROPOSAL_STATE_DIR = (
    REPO_ROOT / "dev_agent" / "proposal_states"
)

PROPOSAL_STATES = frozenset({
    "PENDING",
    "APPROVED",
    "EXECUTING",
    "EXECUTED",
})


def _proposal_state_path(
    proposal_id: str,
) -> Path:
    return (
        PROPOSAL_STATE_DIR
        / f"{proposal_id}.json"
    )


def get_proposal_state(
    proposal_id: str,
) -> dict:
    if not isinstance(proposal_id, str):
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_ID_MUST_BE_STRING",
        }

    if not _valid_proposal_id(proposal_id):
        return {
            "status": "DENIED",
            "reason": "INVALID_PROPOSAL_ID",
            "proposal_id": proposal_id,
        }

    state_path = _proposal_state_path(
        proposal_id
    )

    if state_path.is_symlink():
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_STATE_SYMLINK_NOT_ALLOWED",
            "proposal_id": proposal_id,
        }

    if not state_path.exists():
        return {
            "status": "VALID",
            "proposal_id": proposal_id,
            "proposal_state": "PENDING",
            "state_file_exists": False,
        }

    if not state_path.is_file():
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_STATE_NOT_A_FILE",
            "proposal_id": proposal_id,
        }

    if state_path.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_STATE_FILE_TOO_LARGE",
            "proposal_id": proposal_id,
        }

    try:
        data = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {
            "status": "ERROR",
            "reason": "PROPOSAL_STATE_JSON_INVALID",
            "proposal_id": proposal_id,
        }

    if set(data) != {
        "proposal_id",
        "status",
    }:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_STATE_SCHEMA_INVALID",
            "proposal_id": proposal_id,
        }

    if data.get("proposal_id") != proposal_id:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_STATE_ID_MISMATCH",
            "proposal_id": proposal_id,
        }

    state = data.get("status")

    if state not in PROPOSAL_STATES:
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_STATE_VALUE_INVALID",
            "proposal_id": proposal_id,
        }

    return {
        "status": "VALID",
        "proposal_id": proposal_id,
        "proposal_state": state,
        "state_file_exists": True,
    }


def _write_proposal_state(
    *,
    proposal_id: str,
    state: str,
) -> dict:
    if state not in PROPOSAL_STATES:
        return {
            "status": "ERROR",
            "reason": "INVALID_TARGET_PROPOSAL_STATE",
            "proposal_id": proposal_id,
        }

    PROPOSAL_STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    state_path = _proposal_state_path(
        proposal_id
    )

    record = {
        "proposal_id": proposal_id,
        "status": state,
    }

    fd, temp_name = tempfile.mkstemp(
        prefix=".proposal-state-",
        suffix=".tmp",
        dir=PROPOSAL_STATE_DIR,
    )

    try:
        os.fchmod(fd, 0o600)

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                record,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temp_name,
            state_path,
        )

    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    try:
        state_file = str(
            state_path.relative_to(REPO_ROOT)
        )
    except ValueError:
        state_file = str(state_path)

    return {
        "status": "VALID",
        "proposal_id": proposal_id,
        "proposal_state": state,
        "state_file": state_file,
    }


def _transition_proposal_state(
    *,
    proposal_id: str,
    allowed_from: set[str],
    target_state: str,
) -> dict:
    current = get_proposal_state(
        proposal_id
    )

    if current["status"] != "VALID":
        return current

    current_state = current[
        "proposal_state"
    ]

    if (
        current_state == target_state
        and target_state == "APPROVED"
    ):
        return current

    if current_state == "EXECUTED":
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_ALREADY_EXECUTED",
            "proposal_id": proposal_id,
            "proposal_state": current_state,
        }

    if (
        current_state == "EXECUTING"
        and target_state != "EXECUTED"
    ):
        return {
            "status": "DENIED",
            "reason": "PROPOSAL_EXECUTION_ALREADY_CLAIMED",
            "proposal_id": proposal_id,
            "proposal_state": current_state,
        }

    if current_state not in allowed_from:
        return {
            "status": "DENIED",
            "reason": "INVALID_PROPOSAL_STATE_TRANSITION",
            "proposal_id": proposal_id,
            "proposal_state": current_state,
            "target_state": target_state,
        }

    return _write_proposal_state(
        proposal_id=proposal_id,
        state=target_state,
    )


def mark_proposal_approved(
    proposal_id: str,
) -> dict:
    return _transition_proposal_state(
        proposal_id=proposal_id,
        allowed_from={
            "PENDING",
            "APPROVED",
        },
        target_state="APPROVED",
    )


def claim_proposal_execution(
    proposal_id: str,
) -> dict:
    return _transition_proposal_state(
        proposal_id=proposal_id,
        allowed_from={"APPROVED"},
        target_state="EXECUTING",
    )


def mark_proposal_executed(
    proposal_id: str,
) -> dict:
    current = get_proposal_state(
        proposal_id
    )

    if current["status"] != "VALID":
        return current

    if (
        current["proposal_state"]
        == "EXECUTED"
    ):
        return current

    return _transition_proposal_state(
        proposal_id=proposal_id,
        allowed_from={"EXECUTING"},
        target_state="EXECUTED",
    )
