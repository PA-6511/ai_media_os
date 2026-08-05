from __future__ import annotations


def build_verify_command() -> list[str]:
    """Return the standardized verify command."""
    return ["python", "-m", "pytest", "-q"]
