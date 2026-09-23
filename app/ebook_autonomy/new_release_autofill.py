from __future__ import annotations

from pathlib import Path

from .types import CommandSpec


ROOT = Path(
    "/home/deploy/ai_media_os"
)


def command_spec() -> CommandSpec | None:
    python = (
        ROOT
        / ".venv"
        / "bin"
        / "python"
    )

    runner = (
        ROOT
        / "scripts"
        / "run_ebook_autonomy_new_release_autofill.py"
    )

    if not python.is_file():
        return None

    if not runner.is_file():
        return None

    return CommandSpec(
        component="new_release_autofill",
        argv=(
            str(python),
            str(runner),
        ),
        cwd=str(ROOT),
    )
