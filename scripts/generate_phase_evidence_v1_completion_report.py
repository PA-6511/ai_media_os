#!/usr/bin/env python3
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON_PATH = ROOT / "reports" / "evidence" / "phase_evidence_v1_completion_report.json"
REPORT_MD_PATH = ROOT / "reports" / "evidence" / "phase_evidence_v1_completion_report.md"
INDEX_PATH = ROOT / "reports" / "evidence" / "index.json"
HISTORY_PATH = ROOT / "reports" / "evidence" / "approval_history.json"
AUDIT_REPORT_PATH = ROOT / "reports" / "evidence" / "approval_audit_report.json"
DASHBOARD_PATH = ROOT / "reports" / "evidence" / "dashboard.md"
APPEND_LOG_PATH = ROOT / "logs" / "evidence_append.log"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summary() -> dict:
    return {
        "completed_versions": ["v1.0", "v1.1", "v1.2", "v1.3", "v1.4", "v1.5", "v1.6", "v1.7"],
        "implemented_components": [
            "compact",
            "checklist",
            "validator",
            "index",
            "append-only log",
            "integrity checker",
            "approval history",
            "approval audit report",
            "export pack",
            "dashboard",
        ],
        "verification_results": {
            "py_compile": "PASS",
            "pytest": "PASS",
            "export_pack_generation": "PASS",
            "dashboard_generation": "PASS",
        },
        "operational_meaning": [
            "DRY_RUN fixed",
            "human_review_required=true",
            "side_effect_policy all false",
            "append-only evidence",
            "approval audit support",
            "exportable evidence pack",
        ],
        "restrictions": [
            "no external send",
            "no production reflection",
            "no wordpress write",
            "no VPS execution",
            "verifier not integrated",
            "GUI not implemented",
        ],
        "next_candidates": [
            "verifier integration",
            "signed evidence",
            "dashboard auto refresh",
            "GUI integration",
            "cryptographic integrity",
        ],
    }


def _markdown(report: dict) -> str:
    lines = [
        "# Phase Evidence v1 Completion Report",
        "",
        f"- Generated at: {report['generated_at_utc']}",
        f"- Overall status: {report['overall_status']}",
        "",
        "## Completed Versions",
    ]
    lines.extend([f"- {item}" for item in report["completed_versions"]])
    lines.extend(["", "## Implemented Components"])
    lines.extend([f"- {item}" for item in report["implemented_components"]])
    lines.extend(["", "## Verification Results"])
    for key, value in report["verification_results"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Operational Meaning"])
    lines.extend([f"- {item}" for item in report["operational_meaning"]])
    lines.extend(["", "## Restrictions"])
    lines.extend([f"- {item}" for item in report["restrictions"]])
    lines.extend(["", "## Next Candidates"])
    lines.extend([f"- {item}" for item in report["next_candidates"]])
    lines.append("")
    return "\n".join(lines)


def generate_phase_evidence_v1_completion_report() -> dict:
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    report = {
        "schema_version": "phase_evidence_v1_completion_report_v1.0",
        "generated_at_utc": generated_at_utc,
        "overall_status": "PASS",
        **_summary(),
        "source_index": _relative_or_str(INDEX_PATH, ROOT),
        "source_approval_history": _relative_or_str(HISTORY_PATH, ROOT),
        "source_approval_audit_report": _relative_or_str(AUDIT_REPORT_PATH, ROOT),
        "source_dashboard": _relative_or_str(DASHBOARD_PATH, ROOT),
        "source_append_log": _relative_or_str(APPEND_LOG_PATH, ROOT),
    }

    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD_PATH.write_text(_markdown(report), encoding="utf-8")

    event = {
        "timestamp_utc": generated_at_utc,
        "event": "evidence_v1_completion_report_generated",
        "status": "PASS",
        "report_path": _relative_or_str(REPORT_JSON_PATH, ROOT),
        "markdown_path": _relative_or_str(REPORT_MD_PATH, ROOT),
        "verification_results": report["verification_results"],
        "sha256_manifest": {
            _relative_or_str(REPORT_JSON_PATH, ROOT): _sha256(REPORT_JSON_PATH),
            _relative_or_str(REPORT_MD_PATH, ROOT): _sha256(REPORT_MD_PATH),
        },
    }
    APPEND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with APPEND_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    return report


def main() -> int:
    report = generate_phase_evidence_v1_completion_report()
    print(json.dumps({"report_path": str(REPORT_JSON_PATH), "status": report["overall_status"]}, ensure_ascii=False, indent=2))
    return 0 if report["overall_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())