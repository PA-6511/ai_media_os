#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path("/home/deploy/ai_media_os").resolve()
DEV_AGENT_VENV_BIN = (
    REPO_ROOT / "dev_agent" / ".venv" / "bin"
).resolve()
DEFAULT_TIMEOUT = 120

ALLOWED_SIMPLE_COMMANDS = {
    "pwd",
    "ls",
    "pytest",
}

ALLOWED_GIT_SUBCOMMANDS = {
    "status",
    "diff",
    "log",
    "show",
    "rev-parse",
}

BLOCKED_GIT_OPTIONS = {
    "--no-index",
    "--ext-diff",
    "--textconv",
}

FORBIDDEN_SHELL_TOKENS = (
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
)


def is_inside_repo(path: Path) -> bool:
    try:
        path.relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def validate_argument_paths(argv):
    for arg in argv[1:]:
        candidates = []

        if "=" in arg:
            candidates.append(arg.split("=", 1)[1])

        if not arg.startswith("-"):
            candidates.append(arg)

        for candidate in candidates:
            if not candidate:
                continue

            path = Path(candidate)

            if path.is_absolute():
                return False, f"ABSOLUTE_PATH_NOT_ALLOWED:{candidate}"

            if ".." in path.parts:
                return False, f"PARENT_PATH_NOT_ALLOWED:{candidate}"

    return True, None


def validate_command(command: str):
    if not command.strip():
        return False, "EMPTY_COMMAND"

    for token in FORBIDDEN_SHELL_TOKENS:
        if token in command:
            return False, f"FORBIDDEN_SHELL_TOKEN:{token}"

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return False, f"INVALID_COMMAND:{exc}"

    if not argv:
        return False, "EMPTY_COMMAND"

    executable = Path(argv[0]).name

    path_ok, path_reason = validate_argument_paths(argv)
    if not path_ok:
        return False, path_reason

    if executable == "git":
        if len(argv) < 2:
            return False, "GIT_SUBCOMMAND_REQUIRED"

        subcommand = argv[1]

        if subcommand not in ALLOWED_GIT_SUBCOMMANDS:
            return False, f"GIT_SUBCOMMAND_NOT_ALLOWED:{subcommand}"

        for arg in argv[2:]:
            if arg in BLOCKED_GIT_OPTIONS:
                return False, f"GIT_OPTION_NOT_ALLOWED:{arg}"

            if arg.startswith("--output"):
                return False, f"GIT_OPTION_NOT_ALLOWED:{arg}"

        return True, argv

    if executable == "python3":
        if len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]:
            return True, argv

        return False, "PYTHON3_ONLY_PYTEST_ALLOWED"

    if executable not in ALLOWED_SIMPLE_COMMANDS:
        return False, f"COMMAND_NOT_ALLOWED:{executable}"

    if executable == "pwd" and len(argv) != 1:
        return False, "PWD_ARGUMENTS_NOT_ALLOWED"

    return True, argv


def build_execution_env():
    env = os.environ.copy()
    current_path = env.get("PATH", "")
    env["PATH"] = (
        f"{DEV_AGENT_VENV_BIN}{os.pathsep}{current_path}"
    )
    env["PYTHONNOUSERSITE"] = "1"
    return env


def run_command(command: str, cwd: str, timeout: int):
    cwd_path = Path(cwd).resolve()

    if not is_inside_repo(cwd_path):
        return {
            "status": "DENIED",
            "reason": "CWD_OUTSIDE_REPO",
            "command": command,
            "cwd": str(cwd_path),
        }

    valid, result = validate_command(command)

    if not valid:
        return {
            "status": "DENIED",
            "reason": result,
            "command": command,
            "cwd": str(cwd_path),
        }

    argv = result
    started = time.monotonic()

    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            env=build_execution_env(),
        )

        duration_ms = round((time.monotonic() - started) * 1000)

        return {
            "status": "EXECUTED",
            "command": command,
            "cwd": str(cwd_path),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_ms": duration_ms,
        }

    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.monotonic() - started) * 1000)

        return {
            "status": "TIMEOUT",
            "command": command,
            "cwd": str(cwd_path),
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "duration_ms": duration_ms,
        }

    except Exception as exc:
        duration_ms = round((time.monotonic() - started) * 1000)

        return {
            "status": "ERROR",
            "command": command,
            "cwd": str(cwd_path),
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "duration_ms": duration_ms,
        }


def main():
    parser = argparse.ArgumentParser(
        description="AI Media OS minimal command bridge prototype"
    )

    parser.add_argument("--command", required=True)
    parser.add_argument("--cwd", default=str(REPO_ROOT))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    args = parser.parse_args()

    result = run_command(
        command=args.command,
        cwd=args.cwd,
        timeout=args.timeout,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
