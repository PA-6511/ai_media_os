from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_abort_conditions_shared_s2 import evaluate_shared_abort_conditions


def test_shared_abort_detects_common_flags() -> None:
    data = {
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "auto_post": True,
    }
    reasons = evaluate_shared_abort_conditions(data)
    assert any("auto_post=true" in reason for reason in reasons)


def test_shared_abort_detects_unlock_token() -> None:
    data = {
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "unlock_token": "FORBIDDEN",
    }
    reasons = evaluate_shared_abort_conditions(data)
    assert any("unlock" in reason for reason in reasons)


def test_shared_abort_detects_env_output_flag() -> None:
    data = {
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "env_output_requested": False,
    }
    reasons = evaluate_shared_abort_conditions(data)
    assert any("env output flag" in reason for reason in reasons)
