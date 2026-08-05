#!/usr/bin/env python3
"""SFB-14: SFB dashboard aggregation (NO_GO / DRY_RUN only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/sfb_14_dashboard_aggregation_policy.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_load(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    try:
        return True, _read_json(path)
    except Exception:
        return False, {}


def _resolve(root: Path, raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else root / p


def _pick_status(payload: dict[str, Any]) -> str:
    for key in ["status", "phase_status", "result"]:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "UNKNOWN"


def _pick_phase(payload: dict[str, Any], fallback: str) -> str:
    for key in ["phase", "phase_id", "name"]:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# SFB-14 Dashboard Aggregation",
        "",
        f"- status: {result['status']}",
        f"- phase: {result['phase']}",
        f"- mode: {result['mode']}",
        f"- production_status: {result['production_status']}",
        f"- artifact_total: {result['artifact_total']}",
        f"- artifact_found: {result['artifact_found']}",
        f"- artifact_missing: {result['artifact_missing']}",
        "",
        "## Artifact Summary",
    ]

    for item in result.get("artifacts", []):
        lines.append(
            f"- {item['id']}: found={str(item['found']).lower()} status={item['status']} path={item['path']}"
        )

    lines.extend(
        [
            "",
            "## Mapping Guard",
            f"- undefined_phase_mapping_count: {result['undefined_phase_mapping_count']}",
            "",
            "## Safety",
            f"- wordpress_write_executed: {str(result['wordpress_write_executed']).lower()}",
            f"- external_api_called: {str(result['external_api_called']).lower()}",
            f"- external_network_called: {str(result['external_network_called']).lower()}",
            f"- approval_token_consumed: {str(result['approval_token_consumed']).lower()}",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = _read_json(policy_path)

    out_json = _resolve(ROOT, policy["output_paths"]["report_json"])
    out_md = _resolve(ROOT, policy["output_paths"]["report_md"])

    artifacts_cfg: dict[str, str] = dict(policy.get("artifacts", {}))
    display_name_mapping: dict[str, str] = dict(policy.get("display_name_mapping", {}))
    mapping_guard: dict[str, Any] = dict(policy.get("mapping_guard", {}))
    warn_on_undefined = bool(mapping_guard.get("warn_on_undefined_phase_mapping", True))
    stop_on_undefined = bool(mapping_guard.get("stop_on_undefined_phase_mapping", False))
    artifacts: list[dict[str, Any]] = []
    missing_ids: list[str] = []
    undefined_phase_mappings: list[dict[str, str]] = []

    for artifact_id, raw_path in artifacts_cfg.items():
        abs_path = _resolve(ROOT, raw_path)
        found, payload = _safe_load(abs_path)
        status = _pick_status(payload) if found else "MISSING"
        phase_raw = _pick_phase(payload, artifact_id) if found else artifact_id
        mapping_defined = artifact_id in display_name_mapping
        phase_display = display_name_mapping.get(artifact_id, phase_raw)

        if not found:
            missing_ids.append(artifact_id)
        elif warn_on_undefined and not mapping_defined:
            undefined_phase_mappings.append(
                {
                    "id": artifact_id,
                    "phase_raw": phase_raw,
                    "phase_display": phase_display,
                }
            )

        artifacts.append(
            {
                "id": artifact_id,
                "phase": phase_display,
                "phase_raw": phase_raw,
                "mapping_defined": mapping_defined,
                "status": status,
                "found": found,
                "path": str(abs_path),
                "checked_at": _now_iso(),
            }
        )

    warn_list = [f"missing_artifact: {aid}" for aid in missing_ids]
    warn_list.extend(
        [
            f"undefined_phase_mapping: {item['id']} (phase_raw={item['phase_raw']})"
            for item in undefined_phase_mappings
        ]
    )

    has_blocking_undefined = stop_on_undefined and bool(undefined_phase_mappings)
    if has_blocking_undefined:
        status = "SFB14_DASHBOARD_AGGREGATION_BLOCKED_UNDEFINED_MAPPING"
    elif missing_ids:
        status = "SFB14_DASHBOARD_AGGREGATION_WARN_MISSING_ARTIFACTS"
    elif undefined_phase_mappings:
        status = "SFB14_DASHBOARD_AGGREGATION_READY_WITH_WARNINGS"
    else:
        status = "SFB14_DASHBOARD_AGGREGATION_READY"

    result: dict[str, Any] = {
        "phase": "SFB-14",
        "phase_name": "SFB Dashboard Aggregation",
        "checked_at": _now_iso(),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "external_api_called": False,
        "external_network_called": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "human_approval_consumed": False,
        "status": status,
        "artifact_total": len(artifacts_cfg),
        "artifact_found": len(artifacts_cfg) - len(missing_ids),
        "artifact_missing": len(missing_ids),
        "missing_artifact_ids": missing_ids,
        "undefined_phase_mapping_count": len(undefined_phase_mappings),
        "undefined_phase_mappings": undefined_phase_mappings,
        "artifacts": artifacts,
        "fail_list": [],
        "warn_list": warn_list,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(result, out_md)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="policy json path")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = ROOT / policy_path

    result = generate(policy_path=policy_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ready = result.get("status") in {
        "SFB14_DASHBOARD_AGGREGATION_READY",
        "SFB14_DASHBOARD_AGGREGATION_WARN_MISSING_ARTIFACTS",
        "SFB14_DASHBOARD_AGGREGATION_READY_WITH_WARNINGS",
    }
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
