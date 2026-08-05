from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_phase_s3_overall_result import (  # noqa: E402
    generate_security_phase_s3_overall_result,
)


def test_overall_result_pass_dry_run_only() -> None:
    result = generate_security_phase_s3_overall_result()
    assert result["final_status"] in {"PASS_DRY_RUN_ONLY", "OBSERVABILITY_REVIEW_REQUIRED"}
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
    assert result["detector_only"] is True
    assert result["recommendation_only"] is True
    assert result["executor_action_allowed"] is False
    assert result["freeze_executed"] is False
    assert result["revoke_executed"] is False
    assert result["isolation_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
