from pathlib import Path


REPO_ROOT = Path("/home/deploy/ai_media_os").resolve()
MAX_READ_LINES = 400

BLOCKED_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
}

BLOCKED_NAME_FRAGMENTS = (
    "credential",
    "secret",
    "private_key",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
)


def is_inside_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def is_sensitive_path(path: Path) -> bool:
    for part in path.parts:
        lower = part.lower()

        if lower in BLOCKED_PATH_PARTS:
            return True

        if lower.startswith(".env"):
            return True

        if any(fragment in lower for fragment in BLOCKED_NAME_FRAGMENTS):
            return True

    return False


def read_repo_text(
    relative_path: str,
    start_line: int,
    end_line: int,
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

    if start_line < 1:
        return {
            "status": "DENIED",
            "reason": "START_LINE_MUST_BE_POSITIVE",
            "path": relative_path,
        }

    if end_line < start_line:
        return {
            "status": "DENIED",
            "reason": "INVALID_LINE_RANGE",
            "path": relative_path,
        }

    requested_lines = end_line - start_line + 1

    if requested_lines > MAX_READ_LINES:
        return {
            "status": "DENIED",
            "reason": "LINE_RANGE_TOO_LARGE",
            "path": relative_path,
        }

    resolved = (REPO_ROOT / raw_path).resolve()

    if not is_inside_repo(resolved):
        return {
            "status": "DENIED",
            "reason": "PATH_OUTSIDE_REPO",
            "path": relative_path,
        }

    relative_resolved = resolved.relative_to(REPO_ROOT)

    if is_sensitive_path(relative_resolved):
        return {
            "status": "DENIED",
            "reason": "SENSITIVE_PATH",
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

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "status": "DENIED",
            "reason": "NON_TEXT_FILE",
            "path": relative_path,
        }
    except OSError as exc:
        return {
            "status": "ERROR",
            "reason": f"READ_ERROR:{exc}",
            "path": relative_path,
        }

    lines = text.splitlines()
    selected = lines[start_line - 1:end_line]

    numbered = "\n".join(
        f"{line_number}: {line}"
        for line_number, line in enumerate(
            selected,
            start=start_line,
        )
    )

    return {
        "status": "EXECUTED",
        "path": str(relative_resolved),
        "start_line": start_line,
        "end_line": min(end_line, len(lines)),
        "total_lines": len(lines),
        "content": numbered,
    }
