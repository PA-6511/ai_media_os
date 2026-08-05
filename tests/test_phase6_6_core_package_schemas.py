import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_required_fields(schema: dict, payload: dict):
    missing = [key for key in schema.get("required", []) if key not in payload]
    assert not missing, f"missing required fields: {missing}"


def test_decision_package_schema_accepts_example_required_fields():
    schema = load_json(ROOT / "schemas/decision_package.schema.json")
    payload = load_json(ROOT / "exchange/incoming/decision_package.example.json")

    assert schema["$schema"].endswith("/draft/2020-12/schema")
    assert_required_fields(schema, payload)
    assert payload["package_type"] == "decision_package"
    assert payload["mode"] == "CONNECTION_TEST"
    assert payload["execution"] == "DRY_RUN"


def test_review_result_schema_accepts_phase8_2_required_fields():
    schema = load_json(ROOT / "schemas/review_result.schema.json")
    payload = load_json(ROOT / "exchange/logs/phase8_2_manual_pre_publish_review_result.json")

    assert schema["$schema"].endswith("/draft/2020-12/schema")
    assert_required_fields(schema, payload)
    assert payload["status"] in {"PASS", "WARN", "FAIL", "ABORT"}
    assert payload["mode"] == "CONNECTION_TEST"
    assert payload["execution"] == "DRY_RUN"


def test_approval_evidence_schema_accepts_dry_run_approval_evidence_required_fields():
    schema = load_json(ROOT / "schemas/approval_evidence.schema.json")
    payload = load_json(ROOT / "exchange/logs/dry_run_approval_evidence.json")

    assert schema["$schema"].endswith("/draft/2020-12/schema")
    assert_required_fields(schema, payload)
    assert payload["status"] in {"PASS", "WARN", "FAIL", "ABORT"}
    assert payload["mode"] == "CONNECTION_TEST"
    assert payload["execution"] == "DRY_RUN"
    assert payload["human_approval_required"] is True