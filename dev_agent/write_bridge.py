import hashlib
import os
import stat
from pathlib import Path

from dev_agent.file_bridge import REPO_ROOT, is_sensitive_path


PROBE_ROOT = (REPO_ROOT / "dev_agent" / "probes").resolve()

CANARY_WRITE_FILES = frozenset({
    "app/services/ebook_new_release_autonomy_shadow_compare.py",
    "tests/services/test_ebook_new_release_autonomy_shadow_compare.py",
})

MAX_FILE_BYTES = 64 * 1024
MAX_REPLACEMENT_BYTES = 8 * 1024


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def replace_probe_text(
    relative_path: str,
    old_text: str,
    new_text: str,
):
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

    candidate = REPO_ROOT / raw_path
    resolved = candidate.resolve()

    if not is_inside(resolved, PROBE_ROOT):
        return {
            "status": "DENIED",
            "reason": "WRITE_OUTSIDE_PROBE_ROOT",
            "path": relative_path,
        }

    relative_resolved = resolved.relative_to(REPO_ROOT)

    if is_sensitive_path(relative_resolved):
        return {
            "status": "DENIED",
            "reason": "SENSITIVE_PATH",
            "path": relative_path,
        }

    if resolved.suffix != ".py":
        return {
            "status": "DENIED",
            "reason": "ONLY_PYTHON_FILES_ALLOWED",
            "path": relative_path,
        }

    if candidate.is_symlink():
        return {
            "status": "DENIED",
            "reason": "SYMLINK_NOT_ALLOWED",
            "path": relative_path,
        }

    if not resolved.exists():
        return {
            "status": "ERROR",
            "reason": "FILE_NOT_FOUND",
            "path": relative_path,
        }

    if not resolved.is_file():
        return {
            "status": "ERROR",
            "reason": "NOT_A_FILE",
            "path": relative_path,
        }

    if not old_text:
        return {
            "status": "DENIED",
            "reason": "OLD_TEXT_EMPTY",
            "path": relative_path,
        }

    if len(old_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "OLD_TEXT_TOO_LARGE",
            "path": relative_path,
        }

    if len(new_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "NEW_TEXT_TOO_LARGE",
            "path": relative_path,
        }

    if resolved.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "FILE_TOO_LARGE",
            "path": relative_path,
        }

    try:
        original = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "status": "DENIED",
            "reason": "NON_TEXT_FILE",
            "path": relative_path,
        }

    match_count = original.count(old_text)

    if match_count == 0:
        return {
            "status": "ERROR",
            "reason": "OLD_TEXT_NOT_FOUND",
            "path": relative_path,
        }

    if match_count != 1:
        return {
            "status": "ERROR",
            "reason": f"OLD_TEXT_NOT_UNIQUE:{match_count}",
            "path": relative_path,
        }

    updated = original.replace(
        old_text,
        new_text,
        1,
    )

    before_sha256 = sha256_text(original)
    after_sha256 = sha256_text(updated)

    original_mode = stat.S_IMODE(
        resolved.stat().st_mode
    )

    temp_path = resolved.with_name(
        f".{resolved.name}.dev-agent-{os.getpid()}.tmp"
    )

    try:
        with temp_path.open(
            "x",
            encoding="utf-8",
        ) as handle:
            handle.write(updated)

        os.chmod(temp_path, original_mode)
        os.replace(temp_path, resolved)

    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {
        "status": "EXECUTED",
        "path": str(relative_resolved),
        "replacement_count": 1,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
    }


def replace_approved_text(
    relative_path: str,
    old_text: str,
    new_text: str,
    bridge_allowed_files,
):
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

    allowed = {
        Path(item).as_posix()
        for item in bridge_allowed_files
    }

    if normalized_path not in allowed:
        return {
            "status": "DENIED",
            "reason": "BRIDGE_FILE_NOT_ALLOWED",
            "path": relative_path,
        }

    candidate = REPO_ROOT / raw_path
    resolved = candidate.resolve()

    if not is_inside(resolved, REPO_ROOT):
        return {
            "status": "DENIED",
            "reason": "WRITE_OUTSIDE_REPO",
            "path": relative_path,
        }

    relative_resolved = resolved.relative_to(REPO_ROOT)

    if is_sensitive_path(relative_resolved):
        return {
            "status": "DENIED",
            "reason": "SENSITIVE_PATH_NOT_ALLOWED",
            "path": relative_path,
        }

    if resolved.suffix != ".py":
        return {
            "status": "DENIED",
            "reason": "ONLY_PYTHON_FILES_ALLOWED",
            "path": relative_path,
        }

    if candidate.is_symlink():
        return {
            "status": "DENIED",
            "reason": "SYMLINK_NOT_ALLOWED",
            "path": relative_path,
        }

    if not resolved.exists():
        return {
            "status": "ERROR",
            "reason": "FILE_NOT_FOUND",
            "path": relative_path,
        }

    if not resolved.is_file():
        return {
            "status": "ERROR",
            "reason": "NOT_A_FILE",
            "path": relative_path,
        }

    if not old_text:
        return {
            "status": "DENIED",
            "reason": "EMPTY_OLD_TEXT_NOT_ALLOWED",
            "path": relative_path,
        }

    if len(old_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "OLD_TEXT_TOO_LARGE",
            "path": relative_path,
        }

    if len(new_text.encode("utf-8")) > MAX_REPLACEMENT_BYTES:
        return {
            "status": "DENIED",
            "reason": "NEW_TEXT_TOO_LARGE",
            "path": relative_path,
        }

    if resolved.stat().st_size > MAX_FILE_BYTES:
        return {
            "status": "DENIED",
            "reason": "FILE_TOO_LARGE",
            "path": relative_path,
        }

    try:
        original = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "status": "DENIED",
            "reason": "NON_UTF8_FILE_NOT_ALLOWED",
            "path": relative_path,
        }

    match_count = original.count(old_text)

    if match_count == 0:
        return {
            "status": "ERROR",
            "reason": "OLD_TEXT_NOT_FOUND",
            "path": relative_path,
        }

    if match_count != 1:
        return {
            "status": "ERROR",
            "reason": f"OLD_TEXT_NOT_UNIQUE:{match_count}",
            "path": relative_path,
        }

    updated = original.replace(
        old_text,
        new_text,
        1,
    )

    before_sha256 = sha256_text(original)
    after_sha256 = sha256_text(updated)

    original_mode = stat.S_IMODE(
        resolved.stat().st_mode
    )

    temp_path = resolved.with_name(
        f".{resolved.name}.dev-agent-{os.getpid()}.tmp"
    )

    try:
        with temp_path.open(
            "x",
            encoding="utf-8",
        ) as handle:
            handle.write(updated)

        os.chmod(
            temp_path,
            original_mode,
        )

        os.replace(
            temp_path,
            resolved,
        )

    finally:
        temp_path.unlink(
            missing_ok=True,
        )

    return {
        "status": "EXECUTED",
        "path": normalized_path,
        "replacement_count": 1,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
    }
