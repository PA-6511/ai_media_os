#!/usr/bin/env python3
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

BLOCK_DIR = Path(__file__).resolve().parents[1]
POLICY_JSON = BLOCK_DIR / "config/real_data_import_policy.json"
INPUT_CSV = BLOCK_DIR / "data/incoming/sale_flash_candidates.csv"
FIXTURE_CSV = BLOCK_DIR / "fixtures/sample_sale_candidates.csv"
REPORT_JSON = BLOCK_DIR / "logs/real_data_import_dry_run_evidence.json"
REPORT_MD = BLOCK_DIR / "logs/real_data_import_dry_run_evidence.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixture_diff_summary(before_text: str, after_text: str) -> Dict[str, Any]:
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()

    unified = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="fixture_before",
            tofile="fixture_after",
            lineterm="",
        )
    )
    added = sum(1 for line in unified if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in unified if line.startswith("-") and not line.startswith("---"))

    preview = unified[:60]
    truncated = len(unified) > len(preview)

    return {
        "changed": before_text != after_text,
        "added_line_count": added,
        "removed_line_count": removed,
        "diff_line_count": len(unified),
        "diff_preview": preview,
        "diff_preview_truncated": truncated,
    }


def _write_markdown(report: Dict[str, Any], output_md: Path) -> None:
    diff = report.get("fixture_diff", {})
    pipeline = report.get("pipeline_dry_run", {})

    lines: List[str] = [
        "# SFB-11B Real-Data CSV Import DRY_RUN Evidence",
        "",
        f"- generated_at: {report.get('generated_at', '')}",
        f"- status: {report.get('status', 'FAIL')}",
        f"- phase: {report.get('phase', 'SFB-11B')}",
        f"- input_csv: {report.get('input_csv', '')}",
        f"- fixture_csv: {report.get('fixture_csv', '')}",
        f"- no_go_maintained: {report.get('no_go_maintained', False)}",
        "",
        "## Validation",
        f"- status: {report.get('validation', {}).get('status', 'FAIL')}",
        f"- accepted_row_count: {report.get('validation', {}).get('accepted_row_count', 0)}",
        f"- invalid_row_count: {report.get('validation', {}).get('invalid_row_count', 0)}",
        f"- duplicate_row_count: {report.get('validation', {}).get('duplicate_row_count', 0)}",
        "",
        "## Import",
        f"- status: {report.get('import', {}).get('status', 'FAIL')}",
        f"- imported_row_count: {report.get('import', {}).get('imported_row_count', 0)}",
        f"- backup_artifact_count: {len(report.get('import', {}).get('backup_artifacts', []))}",
        "",
        "## Fixture Diff",
        f"- changed: {diff.get('changed', False)}",
        f"- added_line_count: {diff.get('added_line_count', 0)}",
        f"- removed_line_count: {diff.get('removed_line_count', 0)}",
        "",
        "## Pipeline DRY_RUN",
        f"- status: {pipeline.get('status', 'FAIL')}",
        f"- production_status: {pipeline.get('production_status', 'UNKNOWN')}",
        f"- wordpress_write_executed: {pipeline.get('wordpress_write_executed', True)}",
        f"- external_api_called: {pipeline.get('external_api_called', True)}",
        f"- external_network_called: {pipeline.get('external_network_called', True)}",
        "",
        "## Step Summary",
    ]

    steps = pipeline.get("steps", {})
    if not isinstance(steps, dict) or not steps:
        lines.append("- none")
    else:
        for key in sorted(steps.keys()):
            lines.append(f"- {key}: {steps.get(key)}")

    lines.extend(["", "## Fixture Diff Preview"])
    preview = diff.get("diff_preview", [])
    if not preview:
        lines.append("- no diff")
    else:
        lines.append("```diff")
        lines.extend(preview)
        if diff.get("diff_preview_truncated", False):
            lines.append("... (truncated)")
        lines.append("```")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_real_data_import_dry_run_evidence(
    policy_json: Path = POLICY_JSON,
    input_csv: Path = INPUT_CSV,
    fixture_csv: Path = FIXTURE_CSV,
    report_json: Path = REPORT_JSON,
    report_md: Path = REPORT_MD,
    run_block_fn: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-11B",
        "generated_at": _iso_now(),
        "production_status": "NO_GO",
        "input_csv": str(input_csv),
        "fixture_csv": str(fixture_csv),
        "no_go_maintained": False,
        "validation": {},
        "import": {},
        "fixture_diff": {},
        "pipeline_dry_run": {},
    }

    try:
        validate_module = _load_module("validate_real_sale_csv", BLOCK_DIR / "scripts/validate_real_sale_csv.py")
        import_module = _load_module("import_real_sale_csv_to_fixture", BLOCK_DIR / "scripts/import_real_sale_csv_to_fixture.py")

        fixture_before = _read_text(fixture_csv)
        fixture_before_hash = _sha256(fixture_before)

        validation_result = validate_module.validate_real_sale_csv(
            policy_json=policy_json,
            input_csv=input_csv,
            write_report=True,
        )
        payload["validation"] = {
            "status": validation_result.get("status", "FAIL"),
            "total_rows": validation_result.get("total_rows", 0),
            "accepted_row_count": validation_result.get("accepted_row_count", 0),
            "invalid_row_count": validation_result.get("invalid_row_count", 0),
            "duplicate_row_count": validation_result.get("duplicate_row_count", 0),
        }

        import_result = import_module.import_real_sale_csv_to_fixture(
            policy_json=policy_json,
            input_csv=input_csv,
            fixture_csv=fixture_csv,
        )
        payload["import"] = {
            "status": import_result.get("status", "FAIL"),
            "imported_row_count": import_result.get("imported_row_count", 0),
            "backup_artifacts": import_result.get("backup_artifacts", []),
            "validation": import_result.get("validation", {}),
        }

        fixture_after = _read_text(fixture_csv)
        fixture_after_hash = _sha256(fixture_after)
        diff_summary = _fixture_diff_summary(fixture_before, fixture_after)
        payload["fixture_diff"] = {
            "before_sha256": fixture_before_hash,
            "after_sha256": fixture_after_hash,
            **diff_summary,
        }

        if run_block_fn is None:
            run_module = _load_module("sale_flash_block_run", BLOCK_DIR / "run.py")
            run_block_fn = run_module.run_block

        pipeline_result = run_block_fn()
        payload["pipeline_dry_run"] = pipeline_result

        no_go_maintained = (
            pipeline_result.get("production_status") == "NO_GO"
            and pipeline_result.get("mode") == "DRY_RUN"
            and pipeline_result.get("wordpress_write_executed") is False
            and pipeline_result.get("external_api_called") is False
            and pipeline_result.get("external_network_called") is False
        )
        payload["no_go_maintained"] = bool(no_go_maintained)

        statuses = [
            str(payload["validation"].get("status", "FAIL")),
            str(payload["import"].get("status", "FAIL")),
            str(pipeline_result.get("status", "FAIL")),
        ]

        if not no_go_maintained:
            payload["status"] = "FAIL"
            payload["reason"] = "no_go_invariant_broken"
        elif any(status == "FAIL" for status in statuses):
            payload["status"] = "FAIL"
        elif any(status == "WARN" for status in statuses):
            payload["status"] = "WARN"
        else:
            payload["status"] = "PASS"

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(payload, report_md)
    return payload


def main() -> int:
    result = generate_real_data_import_dry_run_evidence()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
