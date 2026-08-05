#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
POLICY_JSON = BLOCK_DIR / "config/real_data_import_policy.json"
INPUT_CSV = BLOCK_DIR / "data/incoming/sale_flash_candidates.csv"
FIXTURE_CSV = BLOCK_DIR / "fixtures/sample_sale_candidates.csv"
REPORT_JSON = BLOCK_DIR / "logs/real_sale_csv_import_report.json"
REPORT_MD = BLOCK_DIR / "logs/real_sale_csv_import_report.md"


def _load_validator():
    script_path = Path(__file__).resolve().parent / "validate_real_sale_csv.py"
    spec = importlib.util.spec_from_file_location("validate_real_sale_csv", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load validator module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(base: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (base / path)


def _write_markdown(report: Dict[str, Any], output_md: Path) -> None:
    lines = [
        "# SFB-11 Real Sale CSV Import Report",
        "",
        f"- generated_at: {report.get('generated_at', '')}",
        f"- status: {report.get('status', 'FAIL')}",
        f"- phase: {report.get('phase', 'SFB-11')}",
        f"- input_csv: {report.get('input_csv', '')}",
        f"- fixture_csv: {report.get('fixture_csv', '')}",
        f"- imported_row_count: {report.get('imported_row_count', 0)}",
        f"- invalid_row_count: {report.get('validation', {}).get('invalid_row_count', 0)}",
        f"- duplicate_row_count: {report.get('validation', {}).get('duplicate_row_count', 0)}",
        "",
        "## Backup Artifacts",
    ]

    backups = report.get("backup_artifacts", [])
    if not backups:
        lines.append("- none")
    else:
        for item in backups:
            lines.append(f"- {item}")

    lines.extend(["", "## Validation Status", f"- {report.get('validation', {}).get('status', 'FAIL')}"])

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def import_real_sale_csv_to_fixture(
    policy_json: Path = POLICY_JSON,
    input_csv: Path = INPUT_CSV,
    fixture_csv: Path = FIXTURE_CSV,
    report_json: Path = REPORT_JSON,
    report_md: Path = REPORT_MD,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-11",
        "generated_at": _iso_now(),
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "input_csv": str(input_csv),
        "fixture_csv": str(fixture_csv),
        "imported_row_count": 0,
        "backup_artifacts": [],
        "validation": {},
    }

    try:
        policy = _read_json(policy_json)
        fixture_columns = list(policy.get("fixture_columns", []))
        paths = dict(policy.get("paths", {}))
        history_dir = _resolve(BLOCK_DIR, str(paths.get("history_dir", "data/import_history")))

        validator = _load_validator()
        validation = validator.validate_real_sale_csv(
            policy_json=policy_json,
            input_csv=input_csv,
            report_json=report_json,
            report_md=report_md,
            write_report=False,
        )
        payload["validation"] = {
            "status": validation.get("status", "FAIL"),
            "total_rows": validation.get("total_rows", 0),
            "accepted_row_count": validation.get("accepted_row_count", 0),
            "invalid_row_count": validation.get("invalid_row_count", 0),
            "duplicate_row_count": validation.get("duplicate_row_count", 0),
        }

        if validation.get("status") not in {"PASS", "WARN"}:
            payload["status"] = "FAIL"
            payload["reason"] = "validation_failed"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_markdown(payload, report_md)
            return payload

        accepted_rows: List[Dict[str, Any]] = list(validation.get("accepted_rows", []))
        if not accepted_rows:
            payload["status"] = "WARN"
            payload["reason"] = "no_rows_to_import"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_markdown(payload, report_md)
            return payload

        history_dir.mkdir(parents=True, exist_ok=True)
        stamp = _stamp()

        if fixture_csv.exists():
            fixture_backup = history_dir / f"sample_sale_candidates.fixture_backup.{stamp}.csv"
            shutil.copy2(fixture_csv, fixture_backup)
            payload["backup_artifacts"].append(str(fixture_backup))

        incoming_backup = history_dir / f"sale_flash_candidates.incoming_backup.{stamp}.csv"
        shutil.copy2(input_csv, incoming_backup)
        payload["backup_artifacts"].append(str(incoming_backup))

        fixture_csv.parent.mkdir(parents=True, exist_ok=True)
        with fixture_csv.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fixture_columns)
            writer.writeheader()
            for row in accepted_rows:
                writer.writerow({col: row.get(col, "") for col in fixture_columns})

        payload["imported_row_count"] = len(accepted_rows)
        payload["status"] = "PASS" if validation.get("invalid_row_count", 0) == 0 else "WARN"

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(payload, report_md)
    return payload


def main() -> int:
    result = import_real_sale_csv_to_fixture()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
