#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GATE_PATH = ROOT / "config/wordpress_draft_preflight_gate.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_2_preflight_gate_validation_result.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_2_preflight_gate_validation_result",
        "phase": "Phase 6-2",
        "status": "ABORT",
        "reason": reason,
        "gate_ready": False,
        "gate_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _result_pass(details: dict) -> dict:
    return {
        "package_type": "phase6_2_preflight_gate_validation_result",
        "phase": "Phase 6-2",
        "status": "PASS",
        "reason": "preflight gate design is valid and keeps NO_GO for real draft creation",
        "gate_ready": True,
        "gate_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_3_release_decision_design",
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _check_false_flags(data: dict, source_name: str) -> str | None:
    for key in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(key) is True:
            return f"{source_name}: {key}=true is forbidden"

    for key in ["wordpress_write_executed", "github_actions_triggered", "slack_notification_executed"]:
        if data.get(key) is True:
            return f"{source_name}: {key}=true is forbidden"

    safety = data.get("safety_flags")
    if isinstance(safety, dict):
        for key, value in safety.items():
            if value is True:
                return f"{source_name}: safety_flags.{key}=true is forbidden"

    return None


def validate_preflight_gate(gate: dict, sources: dict) -> dict:
    if gate.get("phase") != "Phase 6-2":
        return _abort("gate.phase must be Phase 6-2")
    if gate.get("mode") != "CONNECTION_TEST":
        return _abort("gate.mode must be CONNECTION_TEST")
    if gate.get("execution") != "DRY_RUN":
        return _abort("gate.execution must be DRY_RUN")
    if gate.get("gate_status") != "DESIGN_ONLY":
        return _abort("gate.gate_status must be DESIGN_ONLY")
    if gate.get("production_status") != "NO_GO":
        return _abort("gate.production_status must be NO_GO")
    if gate.get("wordpress_draft_creation") != "NO_GO":
        return _abort("gate.wordpress_draft_creation must be NO_GO")

    rules = gate.get("preflight_rules", {})
    if rules.get("post_count_limit") != 1:
        return _abort("preflight_rules.post_count_limit must be 1")
    if rules.get("post_status") != "draft":
        return _abort("preflight_rules.post_status must be draft")

    required_true = [
        "publish_forbidden",
        "update_forbidden",
        "delete_forbidden",
        "export_forbidden",
        "env_secret_auto_edit_forbidden",
        "wordpress_rest_execute_must_be_false",
        "github_actions_trigger_must_be_false",
        "slack_production_notification_must_be_false",
        "vps_self_builder_execution_must_be_false",
    ]
    for key in required_true:
        if rules.get(key) is not True:
            return _abort(f"preflight_rules.{key} must be true")

    extension = gate.get("decision_extension", {}).get("reserved_future", {})
    if extension.get("token") != "APPROVE_DRAFT_CREATE_ONLY":
        return _abort("decision_extension.reserved_future.token must be APPROVE_DRAFT_CREATE_ONLY")
    if extension.get("allowed") is not False:
        return _abort("decision_extension.reserved_future.allowed must be false")

    # Source evidence checks
    phase5 = sources["phase5_overall_report"]
    phase6_1 = sources["phase6_1_design_validation"]
    quality = sources["draft_candidate_quality_validation"]
    review = sources["draft_candidate_review_result"]

    allowed_phase5 = set(rules.get("allowed_phase5_completion_status", []))
    if phase5.get("completion_status") not in allowed_phase5:
        return _abort("phase5_overall_report.completion_status is not allowed")

    if phase6_1.get("policy_status") != rules.get("require_phase6_1_policy_status"):
        return _abort("phase6_1_design_validation.policy_status mismatch")
    if phase6_1.get("production_status") != rules.get("require_phase6_1_production_status"):
        return _abort("phase6_1_design_validation.production_status mismatch")

    allowed_quality = set(rules.get("allowed_quality_status", []))
    if quality.get("status") not in allowed_quality:
        return _abort("draft_candidate_quality_validation.status is not allowed")

    if quality.get("status") == "WARN" and rules.get("allow_warn_only_when_human_review_required") is True:
        if review.get("decision") != "APPROVE_DRY_RUN_ONLY":
            return _abort("quality WARN requires review decision APPROVE_DRY_RUN_ONLY")

    for name, data in {
        "phase5_overall_report": phase5,
        "phase6_1_design_validation": phase6_1,
        "draft_candidate_quality_validation": quality,
        "draft_candidate_review_result": review,
    }.items():
        err = _check_false_flags(data, name)
        if err:
            return _abort(err)

    details = {
        "phase5_completion_status": phase5.get("completion_status"),
        "phase6_1_policy_status": phase6_1.get("policy_status"),
        "quality_status": quality.get("status"),
        "review_decision": review.get("decision"),
        "reserved_future_decision": extension,
    }
    return _result_pass(details)


def run_validation(gate_path: Path | None = None, output_path: Path | None = None) -> dict:
    gate_path = Path(gate_path or DEFAULT_GATE_PATH)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not gate_path.exists():
        result = _abort(f"gate config not found: {gate_path}")
    else:
        gate = _load(gate_path)
        req = gate.get("required_inputs", {})

        required_keys = {
            "phase5_overall_report",
            "phase6_1_design_validation",
            "draft_candidate_quality_validation",
            "draft_candidate_review_result",
        }
        if not required_keys.issubset(set(req.keys())):
            result = _abort("gate.required_inputs is missing required keys")
        else:
            sources = {}
            missing = []
            for key in required_keys:
                p = ROOT / req[key]
                if not p.exists():
                    missing.append(str(p))
                else:
                    sources[key] = _load(p)

            if missing:
                result = _abort(f"required source files missing: {missing}")
            else:
                result = validate_preflight_gate(gate, sources)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
