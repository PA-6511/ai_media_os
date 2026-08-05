from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


SAFETY_GUARDS = {
    "external_api_called": False,
    "external_network_called": False,
    "wordpress_called": False,
    "publish_executed": False,
    "update_executed": False,
    "delete_executed": False,
    "export_executed": False,
}


def run_sample_block() -> Dict[str, Any]:
    """Run a dry-run-only sample block and return evidence payload."""
    return {
        "block_id": "sample_block",
        "status": "PASS",
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "result": "simulated_execution_only",
        "safety_guards": SAFETY_GUARDS,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
