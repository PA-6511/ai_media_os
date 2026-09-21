from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


VALID_MODES = frozenset({
    "dry_run",
    "execute",
})

DEFAULT_TIMEOUT_SECONDS = 90
MAX_DIAGNOSTIC_CHARS = 3000


class FastIntakeSingleRunnerError(RuntimeError):
    def __init__(
        self,
        code: str,
        diagnostic: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.diagnostic = diagnostic


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_fast_intake_single(
    asin: str,
    title: str,
    mode: str,
    *,
    root: Path | str | None = None,
    python_executable: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Mapping[str, Any]:
    normalized_mode = str(mode or "").strip()

    if normalized_mode not in VALID_MODES:
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_MODE_INVALID"
        )

    repository_root = (
        Path(root)
        if root is not None
        else _repository_root()
    )

    script = (
        repository_root
        / "scripts"
        / "database"
        / "import_new_release_from_asin_fast.py"
    )

    if not script.is_file():
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_SCRIPT_NOT_FOUND",
            str(script),
        )

    executable = (
        str(python_executable)
        if python_executable
        else sys.executable
    )

    command = [
        executable,
        str(script),
        str(asin),
        "--title",
        str(title),
    ]

    if normalized_mode == "execute":
        command.append("--execute")

    try:
        completed = subprocess.run(
            command,
            cwd=str(repository_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_TIMEOUT",
            str(exc),
        ) from exc
    except OSError as exc:
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_SUBPROCESS_ERROR",
            str(exc),
        ) from exc

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if completed.returncode != 0:
        diagnostic = (
            stderr
            or stdout
            or "unknown execution error"
        )

        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_EXECUTION_FAILED",
            diagnostic[-MAX_DIAGNOSTIC_CHARS:],
        )

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_INVALID_RESULT",
            stdout[-MAX_DIAGNOSTIC_CHARS:],
        ) from exc

    if not isinstance(payload, dict):
        raise FastIntakeSingleRunnerError(
            "FAST_INTAKE_INVALID_RESULT",
            stdout[-MAX_DIAGNOSTIC_CHARS:],
        )

    return payload
