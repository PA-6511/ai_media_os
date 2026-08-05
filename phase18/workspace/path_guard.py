from __future__ import annotations

from pathlib import Path


def _resolve(path: str) -> Path:
    return Path(path).resolve()


def is_within_sandbox(target_path: str, sandbox_root: str) -> bool:
    target = _resolve(target_path)
    sandbox = _resolve(sandbox_root)
    return target.is_relative_to(sandbox)


def is_allowed_path(target_path: str, allowlist_root: str) -> bool:
    target = _resolve(target_path)
    allowlist = _resolve(allowlist_root)
    return target.is_relative_to(allowlist)
