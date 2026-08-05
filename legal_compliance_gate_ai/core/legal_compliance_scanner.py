import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ALLOWED_STATUSES = {
    "PASS",
    "WARN",
    "FAIL",
    "ABORT",
    "LEGAL_REVIEW_REQUIRED",
}

API_TERMS_SERVICES = {
    "amazon_pa_api",
    "rakuten_api",
    "dmm_api",
    "x_api",
    "discord_api",
    "slack_api",
}


def load_registry(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _detect_risks(input_payload: Dict[str, Any], registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    signals = set(input_payload.get("signals", []))
    external_services = set(input_payload.get("external_services", []))

    # Use boolean flags as additional virtual signals for deterministic matching.
    if input_payload.get("contains_personal_data"):
        signals.add("personal_data")
    if input_payload.get("contains_secret_like_text"):
        signals.add("secret")

    observed = signals | external_services

    detected: List[Dict[str, Any]] = []
    for risk in registry.get("risks", []):
        triggers = set(risk.get("triggers", []))
        matched_triggers = sorted(observed & triggers)

        if risk.get("risk_id") == "API_TERMS_CHECK_REQUIRED":
            matched_triggers = sorted(external_services & API_TERMS_SERVICES)

        if matched_triggers:
            detected.append(
                {
                    "risk_id": risk.get("risk_id"),
                    "domain": risk.get("domain"),
                    "severity": risk.get("severity"),
                    "release_blocking": bool(risk.get("release_blocking", False)),
                    "matched_triggers": matched_triggers,
                    "required_actions": list(risk.get("required_actions", [])),
                }
            )

    return detected


def scan_legal_compliance(input_payload: Dict[str, Any], registry: Dict[str, Any]) -> Dict[str, Any]:
    detected_risks = _detect_risks(input_payload, registry)
    required_actions: List[str] = []
    for risk in detected_risks:
        for action in risk.get("required_actions", []):
            if action not in required_actions:
                required_actions.append(action)

    disclosure_required = bool(
        {"affiliate_link", "monetized_article"} & set(input_payload.get("signals", []))
    )
    disclosure_checked = bool(input_payload.get("disclosure_checked", False))
    contains_secret_like_text = bool(input_payload.get("contains_secret_like_text", False))

    # Registry mentions API terms evidence; here we treat empty policy_sources as unresolved.
    policy_sources = input_payload.get("policy_sources", []) or []
    has_release_blocking_risk = any(risk.get("release_blocking", False) for risk in detected_risks)
    has_api_terms_risk = any(
        risk.get("risk_id") == "API_TERMS_CHECK_REQUIRED" for risk in detected_risks
    )
    api_terms_unresolved = has_api_terms_risk and not policy_sources

    status = "PASS"
    human_review_required = False

    if contains_secret_like_text:
        status = "ABORT"
        human_review_required = True
    elif disclosure_required and not disclosure_checked:
        status = "LEGAL_REVIEW_REQUIRED"
        human_review_required = True
    elif has_release_blocking_risk and api_terms_unresolved:
        status = "LEGAL_REVIEW_REQUIRED"
        human_review_required = True
    elif has_release_blocking_risk:
        status = "LEGAL_REVIEW_REQUIRED"
        human_review_required = True
    elif detected_risks:
        status = "WARN"

    if status not in ALLOWED_STATUSES:
        status = "FAIL"

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "block_id": registry.get("block_id", "legal_compliance_gate_ai"),
        "execution": input_payload.get("execution", registry.get("mode", "DRY_RUN")),
        "task_id": input_payload.get("task_id"),
        "source_block_id": input_payload.get("source_block_id"),
        "detected_risks": detected_risks,
        "required_actions": required_actions,
        "human_review_required": human_review_required,
        "core_final_decision_required": True,
        "auto_operation_flags": {
            "auto_post": bool(input_payload.get("auto_post", False)),
            "auto_update": bool(input_payload.get("auto_update", False)),
            "auto_delete": bool(input_payload.get("auto_delete", False)),
            "auto_export": bool(input_payload.get("auto_export", False)),
        },
        "auto_operations_executed": False,
        "notes": [
            "DRY_RUN only: no external communication, posting, deleting, updating, or exporting is performed.",
            "This block only detects risks and requests human/legal review; final decision remains with Core AI + Human Review.",
        ],
    }

    return result


def write_scan_report(result: Dict[str, Any], output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
