#!/usr/bin/env python3
"""N-9: VPS再起動後の復帰手順シミュレーション DRY_RUN。

N-5と同じシナリオ方式だが、再起動後の復帰手順に特化した
5シナリオを検証する。実際のreboot/restart/shutdownは行わない。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/n9_post_reboot_recovery_simulation_policy.json"
REQUEST = ROOT / "exchange/examples/n9_post_reboot_recovery_simulation_request.example.json"
OUTPUT = ROOT / "exchange/logs/n9_post_reboot_recovery_simulation_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_simulation(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict:
    base = {
        "phase": "N-9",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "wordpress_post_created": False,
        "external_state_change": False,
        "executor_action_allowed": False,
        "network_observation_only": True,
        "communication_test_only": True,
        "system_restart_executed": False,
        "reboot_executed": False,
        "shutdown_executed": False,
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {**base, "status": "FAIL", "reason": f"input_load_error: {exc}", "scenarios": []}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    templates = policy.get("scenario_templates", {})
    scenario_names = req.get("scenarios", [])

    details = []
    all_matched = True
    for name in scenario_names:
        template = templates.get(name)
        if not template:
            all_matched = False
            details.append({
                "scenario": name,
                "expected_action": None,
                "recommended_action": None,
                "recovery_steps": [],
                "status": "FAIL",
                "reason": "scenario_template_not_found",
            })
            continue

        ok = bool(
            template.get("expected_action")
            and template.get("recommended_action")
            and template.get("recovery_steps")
        )
        if not ok:
            all_matched = False
        details.append({
            "scenario": name,
            "expected_action": template.get("expected_action"),
            "recommended_action": template.get("recommended_action"),
            "recovery_steps": template.get("recovery_steps", []),
            "status": "PASS" if ok else "FAIL",
        })

    result = {
        **base,
        "status": "PASS" if all_matched else "FAIL",
        "scenarios": details,
        "scenario_count": len(details),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_simulation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
