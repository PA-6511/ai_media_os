"""Phase2 runtime logs validator.

Usage:
    python3 tools/validate_phase2_logs.py --input path/to/phase2_runtime.log
    python3 tools/validate_phase2_logs.py --input path/to/events.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = BASE_DIR / "schemas" / "phase2_runtime_log.schema.json"

ALLOWED_PHASE = {"PHASE1_5", "PHASE2"}
ALLOWED_DECISION = {"APPROVE", "ESCALATE", "DENY"}
ALLOWED_RESULT = {"SUCCESS", "FAIL", "SKIP"}


def _load_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    # JSON array first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # NDJSON fallback
    events: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {i}: invalid JSON ({exc})") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {i}: event is not object")
        events.append(obj)
    return events


def _validate_event(event: dict[str, Any], idx: int) -> list[str]:
    errors: list[str] = []

    required = [
        "timestamp",
        "run_id",
        "phase",
        "component",
        "action",
        "decision",
        "result",
        "kpi",
    ]
    for key in required:
        if key not in event:
            errors.append(f"[{idx}] missing required key: {key}")

    phase = event.get("phase")
    if phase is not None and phase not in ALLOWED_PHASE:
        errors.append(f"[{idx}] invalid phase: {phase!r}")

    decision = event.get("decision")
    if decision is not None and decision not in ALLOWED_DECISION:
        errors.append(f"[{idx}] invalid decision: {decision!r}")

    result = event.get("result")
    if result is not None and result not in ALLOWED_RESULT:
        errors.append(f"[{idx}] invalid result: {result!r}")

    for key in ("run_id", "component", "action"):
        value = event.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"[{idx}] {key} must be non-empty string")

    kpi = event.get("kpi")
    if not isinstance(kpi, dict):
        errors.append(f"[{idx}] kpi must be object")
        return errors

    kpi_required = [
        "failsafe_coverage",
        "freeze_correctness",
        "policy_deny_delta",
        "warning_streak",
    ]
    for key in kpi_required:
        if key not in kpi:
            errors.append(f"[{idx}] missing kpi key: {key}")

    for key in ("failsafe_coverage", "freeze_correctness", "policy_deny_delta"):
        if key in kpi and not isinstance(kpi[key], (int, float)):
            errors.append(f"[{idx}] kpi.{key} must be number")

    if "warning_streak" in kpi and not isinstance(kpi["warning_streak"], int):
        errors.append(f"[{idx}] kpi.warning_streak must be integer")

    fc = kpi.get("failsafe_coverage")
    if isinstance(fc, (int, float)) and not (0 <= float(fc) <= 1):
        errors.append(f"[{idx}] kpi.failsafe_coverage out of range [0,1]: {fc}")

    fz = kpi.get("freeze_correctness")
    if isinstance(fz, (int, float)) and not (0 <= float(fz) <= 1):
        errors.append(f"[{idx}] kpi.freeze_correctness out of range [0,1]: {fz}")

    pd = kpi.get("policy_deny_delta")
    if isinstance(pd, (int, float)) and float(pd) < 0:
        errors.append(f"[{idx}] kpi.policy_deny_delta must be >= 0: {pd}")

    ws = kpi.get("warning_streak")
    if isinstance(ws, int) and ws < 0:
        errors.append(f"[{idx}] kpi.warning_streak must be >= 0: {ws}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Phase2 runtime logs")
    parser.add_argument("--input", type=Path, required=True, help="Path to JSON/NDJSON log file")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Schema reference path (default: {DEFAULT_SCHEMA_PATH})",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"[ERROR] input not found: {args.input}", file=sys.stderr)
        return 1

    if not args.schema.exists():
        print(f"[ERROR] schema not found: {args.schema}", file=sys.stderr)
        return 1

    try:
        events = _load_events(args.input)
    except ValueError as exc:
        print(f"[ERROR] failed to parse input: {exc}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for i, event in enumerate(events, start=1):
        all_errors.extend(_validate_event(event, i))

    print(f"schema_ref={args.schema}")
    print(f"input={args.input}")
    print(f"event_count={len(events)}")

    if all_errors:
        print(f"invalid_count={len(all_errors)}")
        for err in all_errors:
            print(f"- {err}")
        return 2

    print("valid_count=0")
    print("result=OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
