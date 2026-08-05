import json
from pathlib import Path
from typing import Any, Dict

from core.legal_compliance_scanner import (
    scan_legal_compliance,
    write_scan_report,
)


def _build_failure_result(error: Exception) -> Dict[str, Any]:
    return {
        "status": "FAIL",
        "block_id": "legal_compliance_gate_ai",
        "execution": "DRY_RUN",
        "detected_risks": [],
        "required_actions": ["実行エラーを確認し再実行する"],
        "human_review_required": True,
        "core_final_decision_required": True,
        "auto_operation_flags": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
        },
        "auto_operations_executed": False,
        "error": str(error),
        "notes": [
            "DRY_RUN only: no external communication, posting, deleting, updating, or exporting is performed.",
        ],
    }


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "examples" / "legal_scan_input.example.json"
    registry_path = base_dir / "config" / "legal_risk_registry.json"
    output_path = base_dir / "reports" / "legal_compliance_scan_result.json"

    try:
        input_payload = json.loads(input_path.read_text(encoding="utf-8"))
        registry = json.loads(registry_path.read_text(encoding="utf-8"))

        result = scan_legal_compliance(input_payload, registry)
        write_scan_report(result, str(output_path))

        print(f"status: {result.get('status')}")
        print("detected_risks:")
        for risk in result.get("detected_risks", []):
            print(f"- {risk.get('risk_id')}")

        return 0
    except Exception as exc:
        failure_result = _build_failure_result(exc)
        write_scan_report(failure_result, str(output_path))
        print("status: FAIL")
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
