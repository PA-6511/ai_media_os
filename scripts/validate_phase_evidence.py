#!/usr/bin/env python3
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHASE_EVIDENCE_DIR = ROOT / "reports" / "evidence" / "phaseXX_component_name"
EXPECTED_FILES = [
    "completion_report.json",
    "implementation_evidence.json",
    "approval_evidence.json",
    "hash_manifest.json",
]

SIDE_EFFECT_KEYS = [
    "wordpress_write",
    "external_send",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "vps_execution",
    "production_reflection",
]

REQUIRED_KEYS = [
    "timestamp_utc",
    "phase",
    "component",
    "mode",
    "status",
    "human_review_required",
    "production_status",
    "summary",
    "reason",
    "novelty",
    "files_changed",
    "tests_executed",
    "approval_state",
    "side_effect_policy",
    "sha256",
]


@dataclass
class ValidationIssue:
    status: str
    reason: str


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result(status: str, reason: str, details: dict | None = None) -> dict:
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase Evidence Standard v1",
        "component": "phase_evidence_validator",
        "mode": "DRY_RUN",
        "status": status,
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": reason,
        "reason": reason,
        "novelty": ["schema validation", "append-only evidence compatibility"],
        "files_changed": [],
        "tests_executed": [],
        "approval_state": "UNKNOWN",
        "side_effect_policy": {key: False for key in SIDE_EFFECT_KEYS},
        "sha256": "",
    }
    if details is not None:
        payload["details"] = details
    return payload


def _warn(reason: str, details: dict | None = None) -> dict:
    return _result("WARN", reason, details)


def _fail(reason: str, details: dict | None = None) -> dict:
    return _result("FAIL", reason, details)


def _abort(reason: str, details: dict | None = None) -> dict:
    return _result("ABORT", reason, details)


def _validate_side_effect_policy(policy: object) -> str | None:
    if not isinstance(policy, dict):
        return "side_effect_policy must be an object"
    for key in SIDE_EFFECT_KEYS:
        if key not in policy:
            return f"side_effect_policy.{key} is missing"
        if policy[key] is not False:
            return f"side_effect_policy.{key} must be false"
    extra = set(policy.keys()) - set(SIDE_EFFECT_KEYS)
    if extra:
        return f"side_effect_policy has unexpected keys: {sorted(extra)}"
    return None


def _validate_record(record: dict, source_name: str) -> str | None:
    for key in REQUIRED_KEYS:
        if key not in record:
            return f"{source_name}: missing required key {key}"

    if record["mode"] != "DRY_RUN":
        return f"{source_name}: mode must be DRY_RUN"
    if record["human_review_required"] is not True:
        return f"{source_name}: human_review_required must be true"
    if record["production_status"] != "NO_GO":
        return f"{source_name}: production_status must be NO_GO"
    if record["status"] not in {"PASS", "WARN", "FAIL", "ABORT"}:
        return f"{source_name}: invalid status {record['status']}"
    if not isinstance(record["novelty"], list):
        return f"{source_name}: novelty must be a list"
    if not isinstance(record["files_changed"], list):
        return f"{source_name}: files_changed must be a list"
    if not isinstance(record["tests_executed"], list):
        return f"{source_name}: tests_executed must be a list"

    try:
        datetime.fromisoformat(record["timestamp_utc"].replace("Z", "+00:00"))
    except Exception:
        return f"{source_name}: timestamp_utc must be ISO 8601"

    side_effect_error = _validate_side_effect_policy(record["side_effect_policy"])
    if side_effect_error:
        return f"{source_name}: {side_effect_error}"

    if record["status"] == "FAIL":
        return f"{source_name}: status FAIL is not allowed in stored evidence"
    if record["status"] == "ABORT":
        return f"{source_name}: status ABORT is not allowed in stored evidence"

    return None


def _validate_hash_manifest(manifest: dict, evidence_dir: Path) -> str | None:
    if not isinstance(manifest, dict):
        return "hash_manifest.json must be an object"

    for key in ["timestamp_utc", "files", "sha256"]:
        if key not in manifest:
            return f"hash_manifest.json missing required key {key}"

    files = manifest["files"]
    if not isinstance(files, dict):
        return "hash_manifest.files must be an object"

    for filename in EXPECTED_FILES[:-1]:
        if filename not in files:
            return f"hash_manifest.files missing {filename}"
        file_path = evidence_dir / filename
        if not file_path.exists():
            return f"missing evidence file: {file_path}"
        expected = files[filename]
        actual = _sha256(file_path)
        if expected != actual:
            return f"sha256 mismatch for {filename}"

    return None


def validate_phase_evidence(evidence_dir: Path | str | None = None) -> dict:
    evidence_dir = Path(evidence_dir or DEFAULT_PHASE_EVIDENCE_DIR)
    if not evidence_dir.exists():
        return _abort(f"evidence directory not found: {evidence_dir}")

    missing = [name for name in EXPECTED_FILES if not (evidence_dir / name).exists()]
    if missing:
        return _abort(f"missing required evidence files: {missing}")

    try:
        records = {name: _load_json(evidence_dir / name) for name in EXPECTED_FILES[:-1]}
    except json.JSONDecodeError as exc:
        return _fail(f"JSON syntax error: {exc}")

    try:
        manifest = _load_json(evidence_dir / "hash_manifest.json")
    except json.JSONDecodeError as exc:
        return _fail(f"hash_manifest.json JSON syntax error: {exc}")

    for filename, record in records.items():
        if not isinstance(record, dict):
            return _fail(f"{filename} must be a JSON object")
        issue = _validate_record(record, filename)
        if issue:
            if "missing required key" in issue or "must be false" in issue:
                return _abort(issue)
            return _fail(issue)

    manifest_issue = _validate_hash_manifest(manifest, evidence_dir)
    if manifest_issue:
        return _fail(manifest_issue)

    warnings = []
    for filename, record in records.items():
        if record.get("tests_executed") == []:
            warnings.append(f"{filename}: tests_executed is empty")
        if any(value == "UNKNOWN" for value in [record.get("approval_state"), record.get("summary"), record.get("reason")]):
            warnings.append(f"{filename}: UNKNOWN remains in required narrative fields")

    if warnings:
        return _warn("; ".join(warnings), {"warnings": warnings})

    return _result(
        "PASS",
        "phase evidence files, schema, and sha256 manifest are valid",
        {
            "evidence_dir": str(evidence_dir),
            "validated_files": EXPECTED_FILES,
        },
    )


def run_validation(evidence_dir: Path | str | None = None, output_path: Path | str | None = None) -> dict:
    result = validate_phase_evidence(evidence_dir=evidence_dir)
    output_path = Path(output_path) if output_path else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    evidence_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PHASE_EVIDENCE_DIR
    result = validate_phase_evidence(evidence_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())