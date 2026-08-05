from __future__ import annotations

from datetime import datetime, timezone


def run_block() -> dict:
    return {
        "block_id": "dashboard_seed_block",
        "status": "WARN",
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "reason": "scaffold only; execution not enabled",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
