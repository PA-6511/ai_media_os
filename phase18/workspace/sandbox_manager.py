from __future__ import annotations

from pathlib import Path


def prepare_sandbox_workspace(base_dir: str, run_id: str) -> dict:
    sandbox_root = Path(base_dir).resolve() / f"phase18_sandbox_{run_id}"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    return {
        "status": "PASS",
        "sandbox_root": str(sandbox_root),
        "run_id": run_id,
        "mode": "DRY_RUN",
    }
