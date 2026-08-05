#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_12_no_secret_leak_audit_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_12_no_secret_leak_audit_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_12_no_secret_leak_audit_result.md"

# Lines containing these substrings are treated as prohibition/documentation context
# and are excluded from forbidden-pattern matching.
ALLOWED_CONTEXTS = [
    "Do not",
    "do not",
    "must not",
    "must Never",
    "must never",
    "prohibited",
    "Prohibited",
    "forbidden",
    "Forbidden",
    "# ",
    "no_secret_leak",
    "secret_output_policy",
    "print_values",
    "write_values_to_logs",
    "print_lengths",
    "print_prefix_suffix",
    "hash_values",
    "allowed_output",
    "DRY_RUN_PLACEHOLDER",
    "\"print(os.environ\"",
    "'print(os.environ'",
    "\"print(env\"",
    "'print(env'",
    "forbidden_patterns",
    "FORBIDDEN",
    "ABORT if",
    "ABORT when",
    "-> ABORT",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _is_allowed_context(line: str) -> bool:
    for ctx in ALLOWED_CONTEXTS:
        if ctx in line:
            return True
    return False


def audit_no_secret_leak(
    policy_path: Path = DEFAULT_POLICY,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    findings: list[dict[str, str]] = []
    scanned_files: list[dict[str, Any]] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        status = "ABORT"
        result = _build_result(status, scanned_files, findings, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("audit_is_execution_permission") is not False:
        safety_violations.append("audit_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, scanned_files, findings, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    root = _resolve_root(policy_path)

    evidence_summary: list[dict[str, Any]] = []
    phase811_status = None
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(ev_path)
        st = payload.get("status") or payload.get("overall_status")
        phase811_status = st
        evidence_summary.append({"path": rel, "exists": True, "status": st})

    if missing_evidence:
        safety_violations.append("required evidence missing")
    elif phase811_status != policy.get("required_phase8_11_status"):
        safety_violations.append(
            f"phase8_11 status must be {policy.get('required_phase8_11_status')} but got {phase811_status}"
        )

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, scanned_files, findings, errors, warnings, safety_violations, policy)
        result["evidence_summary"] = evidence_summary
        _write_outputs(result, output_json_path, output_md_path)
        return result

    forbidden_patterns = policy.get("forbidden_patterns", [])
    scan_targets = policy.get("scan_targets", [])
    missing_targets: list[str] = []

    for rel in scan_targets:
        target_path = root / rel
        if not target_path.exists():
            missing_targets.append(rel)
            scanned_files.append({"path": rel, "exists": False, "findings": []})
            continue

        content = target_path.read_text(encoding="utf-8")
        file_findings: list[str] = []
        for pattern in forbidden_patterns:
            for lineno, line in enumerate(content.splitlines(), start=1):
                if _is_allowed_context(line):
                    continue
                if pattern in line:
                    file_findings.append(f"pattern={pattern!r} at line {lineno}")
                    findings.append({
                        "file": rel,
                        "pattern": pattern,
                        "line": lineno,
                    })
        scanned_files.append({"path": rel, "exists": True, "findings": file_findings})

    if findings:
        for f in findings:
            safety_violations.append(f"forbidden_pattern_found: {f.get('pattern')} in {f.get('file')}:{f.get('line')}")
        status = "ABORT"
    elif missing_targets:
        for t in missing_targets:
            errors.append(f"missing_scan_target: {t}")
        status = "FAIL"
    else:
        status = policy.get("decision_rules", {}).get("no_forbidden_patterns", "NO_SECRET_LEAK_AUDIT_PASS")

    result = _build_result(status, scanned_files, findings, errors, warnings, safety_violations, policy)
    result["evidence_summary"] = evidence_summary
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    scanned_files: list,
    findings: list,
    errors: list,
    warnings: list,
    safety_violations: list,
    policy: dict,
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-12",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "audit_is_execution_permission": False,
        "secret_values_written": False,
        "scanned_files": scanned_files,
        "findings": findings,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-13 post-credential readiness recheck gate",
        ),
        "checked_at": _now_iso(),
    }


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-12 No-Secret-Leak Audit Report",
        "",
        "## Purpose",
        "Audit credential-handling scripts, logs, and runbooks for secret-leak patterns.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(["", "## Scan Targets"])
    for sf in result.get("scanned_files", []):
        lines.append(f"- {sf.get('path')}: exists={sf.get('exists')} findings={len(sf.get('findings', []))}")

    lines.extend(["", "## Findings"])
    if result.get("findings"):
        for f in result["findings"]:
            lines.append(f"- pattern={f.get('pattern')} file={f.get('file')} line={f.get('line')}")
    else:
        lines.append("- no forbidden patterns found")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- audit_is_execution_permission: {result.get('audit_is_execution_permission')}",
            f"- secret_values_written: {result.get('secret_values_written')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = audit_no_secret_leak()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "NO_SECRET_LEAK_AUDIT_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
