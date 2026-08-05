#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/phase6_hardening_preflight_gate.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase6_9_hardening_preflight_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase6_9_hardening_preflight_report.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _overall_status(statuses: list[str], acceptable: set[str], warn_statuses: set[str], reject: set[str]) -> str:
    if any(status == "ABORT" for status in statuses):
        return "ABORT"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status in warn_statuses for status in statuses):
        return "PASS_DRY_RUN_ONLY_WITH_WARN"
    if statuses and all(status in acceptable for status in statuses):
        return "PASS_DRY_RUN_ONLY"
    return "FAIL"


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 6-9 Hardening Preflight Report",
        "",
        "## Overall Status",
        f"- {report['overall_status']}",
        "",
        "## Production Status",
        f"- {report['production_status']}",
        f"- wordpress_draft_creation: {report['wordpress_draft_creation']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- auto_post: {report['auto_post']}",
        f"- auto_update: {report['auto_update']}",
        f"- auto_delete: {report['auto_delete']}",
        f"- auto_export: {report['auto_export']}",
        f"- publish_allowed: {report['publish_allowed']}",
        "",
        "## Evidence Summary",
    ]

    for item in report["evidence_summary"]:
        lines.append(f"- {item['path']}: {item['status']}")

    lines += [
        "",
        "## Blocked Operations",
    ]

    for op in report.get("blocked_next_steps", []):
        lines.append(f"- {op}")

    lines += [
        "",
        "## Allowed Next Step",
        f"- {report.get('allowed_next_step')}",
        "",
        "## Human Review Required",
        f"- {report.get('human_approval_required')}",
        "",
        "## Final Judgment",
        f"- {report.get('final_judgment')}",
        "",
        f"- checked_at: {report.get('checked_at')}",
    ]
    return "\n".join(lines) + "\n"


def generate_report(config: dict) -> dict:
    errors = []
    warnings = []

    if config.get("production_status") != "NO_GO":
        errors.append("production_status must be NO_GO")
    if config.get("wordpress_draft_creation") != "NO_GO":
        errors.append("wordpress_draft_creation must be NO_GO")
    if config.get("wordpress_write_executed") is not False:
        errors.append("wordpress_write_executed must be false")

    dangerous = config.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            errors.append(f"dangerous_operations.{key} must be false")

    if errors:
        return {
            "phase": "Phase 6-9",
            "overall_status": "ABORT",
            "final_judgment": "ABORT",
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "human_approval_required": True,
            "evidence_summary": [],
            "errors": errors,
            "warnings": warnings,
            "blocked_next_steps": config.get("blocked_next_steps", []),
            "allowed_next_step": config.get("allowed_next_step"),
            "checked_at": _now_iso()
        }

    required_evidence = config.get("required_evidence", [])
    acceptable = set(config.get("acceptable_statuses", []))
    warn_statuses = set(config.get("warn_statuses", []))
    reject = set(config.get("reject_statuses", []))

    statuses = []
    summary = []
    missing = []

    for rel in required_evidence:
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
            summary.append({"path": rel, "status": "MISSING"})
            continue
        data = load_json(path)
        status = str(data.get("status", "UNKNOWN"))
        statuses.append(status)
        summary.append({"path": rel, "status": status})

    if missing:
        overall = "FAIL"
        errors.append(f"missing evidence: {missing}")
    else:
        overall = _overall_status(statuses, acceptable, warn_statuses, reject)

    if any(status not in acceptable | warn_statuses | reject for status in statuses):
        warnings.append("unknown evidence status included")

    return {
        "phase": "Phase 6-9",
        "overall_status": overall,
        "final_judgment": overall,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "publish_allowed": False,
        "human_approval_required": bool(config.get("human_approval_required", True)),
        "evidence_summary": summary,
        "errors": errors,
        "warnings": warnings,
        "blocked_next_steps": config.get("blocked_next_steps", []),
        "allowed_next_step": config.get("allowed_next_step"),
        "checked_at": _now_iso()
    }


def run_report(config_path: Path | None = None, output_json: Path | None = None, output_md: Path | None = None) -> dict:
    config_path = Path(config_path or DEFAULT_CONFIG)
    output_json = Path(output_json or DEFAULT_OUTPUT_JSON)
    output_md = Path(output_md or DEFAULT_OUTPUT_MD)

    if not config_path.exists():
        result = {
            "phase": "Phase 6-9",
            "overall_status": "ABORT",
            "final_judgment": "ABORT",
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "human_approval_required": True,
            "evidence_summary": [],
            "errors": [f"config not found: {config_path}"],
            "warnings": [],
            "blocked_next_steps": [],
            "allowed_next_step": None,
            "checked_at": _now_iso()
        }
    else:
        result = generate_report(load_json(config_path))

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(build_markdown(result), encoding="utf-8")
    return result


def main() -> int:
    result = run_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("overall_status") in {"PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY_WITH_WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
