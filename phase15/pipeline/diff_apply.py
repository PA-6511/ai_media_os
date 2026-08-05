from __future__ import annotations

from pathlib import Path


def _is_within_allowlist(target_path: Path, allowlist_root: Path) -> bool:
    target_resolved = target_path.resolve()
    allowlist_resolved = allowlist_root.resolve()
    return Path(target_resolved).is_relative_to(allowlist_resolved)


def apply_file_change(
    target_path: str,
    content: str,
    allowlist_root: str,
    dry_run: bool = True,
) -> dict:
    """Apply a safe file content update constrained by allowlist and dry-run rules."""
    target = Path(target_path)
    root = Path(allowlist_root)

    if not _is_within_allowlist(target, root):
        return {
            "status": "POLICY_VIOLATION",
            "action": "blocked",
            "target_path": str(target),
            "dry_run": dry_run,
        }

    if dry_run:
        return {
            "status": "OK",
            "action": "would_write",
            "target_path": str(target),
            "dry_run": dry_run,
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "status": "OK",
        "action": "written",
        "target_path": str(target),
        "dry_run": dry_run,
    }
