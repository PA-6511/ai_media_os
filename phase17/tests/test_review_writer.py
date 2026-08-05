import json
from pathlib import Path

from phase17.reporting.review_writer import write_review_package


def test_write_review_package_creates_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "review_package.json"
    package = {
        "phase": "17",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "selected_candidate_id": "minimal",
        "status": "READY_FOR_HUMAN_REVIEW",
    }

    result = write_review_package(package, str(output))

    assert result["status"] == "PASS"
    assert result["package_status"] == "READY_FOR_HUMAN_REVIEW"
    assert output.exists()

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["phase"] == "17"
