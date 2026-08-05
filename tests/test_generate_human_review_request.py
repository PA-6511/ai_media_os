import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_human_review_request import generate_review_request


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_validation_result():
    return {
        "package_type": "exchange_connection_dry_run_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "human_review_required": True,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "overall_status": "WARN",
        "results": [
            {
                "package_type": "decision_package",
                "status": "PASS",
                "issues": [],
            },
            {
                "package_type": "test_report",
                "status": "WARN",
                "issues": ["WARN: tests.wp_post='NOT_EXECUTED'"],
            },
        ],
    }


def test_generate_review_required_from_warn_result():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        write_json(input_path, base_validation_result())

        result = generate_review_request(input_path, output_path)

        assert result["status"] == "WARN"
        assert result["review_required_generated"] is True
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["execution"] == "DRY_RUN"
        assert data["review_status"] == "REQUIRED"
        assert "APPROVE_DRY_RUN_ONLY" in data["review_options"]
        assert "REQUEST_FIX" in data["review_options"]
        assert "REJECT" in data["review_options"]
        assert "ABORT" in data["review_options"]


def test_execution_live_aborts():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        payload = base_validation_result()
        payload["execution"] = "LIVE"
        write_json(input_path, payload)

        result = generate_review_request(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        payload = base_validation_result()
        payload["auto_post"] = True
        write_json(input_path, payload)

        result = generate_review_request(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        payload = base_validation_result()
        payload["wordpress_write_executed"] = True
        write_json(input_path, payload)

        result = generate_review_request(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_existing_review_required_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        write_json(input_path, base_validation_result())
        write_json(output_path, {"existing": True})

        result = generate_review_request(input_path, output_path)

        assert result["status"] == "ABORT"
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data == {"existing": True}


def test_generated_review_keeps_production_flags_false():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "validation_result.json"
        output_path = Path(tmpdir) / "review_required.json"
        write_json(input_path, base_validation_result())

        result = generate_review_request(input_path, output_path)
        assert result["review_required_generated"] is True

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["auto_post"] is False
        assert data["auto_update"] is False
        assert data["auto_delete"] is False
        assert data["auto_export"] is False
        assert data["wordpress_write_executed"] is False
        assert data["slack_notification_executed"] is False
        assert data["github_actions_triggered"] is False
