"""Phase2 KPI reporter with auto-FREEZE judgement.

Usage:
    python3 tools/phase2_kpi_report.py --input path/to/phase2_runtime.log
    python3 tools/phase2_kpi_report.py --input path/to/events.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FREEZE_THRESHOLDS = {
    "failsafe_coverage_min": 1.00,
    "freeze_correctness_min": 0.90,
    "policy_deny_delta_max": 2.0,
    "warning_streak_freeze": 2,
}


def _load_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    events: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {i}: invalid JSON ({exc})") from exc
        if isinstance(obj, dict):
            events.append(obj)
    return events


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _extract_latest_kpi(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        kpi = event.get("kpi")
        if isinstance(kpi, dict):
            return kpi
    return {}


def _freeze_reasons(kpi: dict[str, Any]) -> list[str]:
    reasons: list[str] = []

    failsafe_coverage = _safe_float(kpi.get("failsafe_coverage"), 0.0)
    freeze_correctness = _safe_float(kpi.get("freeze_correctness"), 0.0)
    policy_deny_delta = _safe_float(kpi.get("policy_deny_delta"), 0.0)
    warning_streak = _safe_int(kpi.get("warning_streak"), 0)

    if failsafe_coverage < FREEZE_THRESHOLDS["failsafe_coverage_min"]:
        reasons.append(
            f"failsafe_coverage<{FREEZE_THRESHOLDS['failsafe_coverage_min']:.2f} ({failsafe_coverage:.4f})"
        )
    if freeze_correctness < FREEZE_THRESHOLDS["freeze_correctness_min"]:
        reasons.append(
            f"freeze_correctness<{FREEZE_THRESHOLDS['freeze_correctness_min']:.2f} ({freeze_correctness:.4f})"
        )
    if policy_deny_delta >= FREEZE_THRESHOLDS["policy_deny_delta_max"]:
        reasons.append(
            f"policy_deny_delta>={FREEZE_THRESHOLDS['policy_deny_delta_max']:.1f} ({policy_deny_delta:.4f})"
        )
    if warning_streak >= FREEZE_THRESHOLDS["warning_streak_freeze"]:
        reasons.append(
            f"warning_streak>={FREEZE_THRESHOLDS['warning_streak_freeze']} ({warning_streak})"
        )

    return reasons


def _count_by_key(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = str(event.get(key, "UNKNOWN"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[0]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase2 KPI report")
    parser.add_argument("--input", type=Path, required=True, help="Path to JSON/NDJSON runtime log")
    parser.add_argument("--json", action="store_true", help="Print report JSON")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"[ERROR] input not found: {args.input}", file=sys.stderr)
        return 1

    try:
        events = _load_events(args.input)
    except ValueError as exc:
        print(f"[ERROR] failed to parse input: {exc}", file=sys.stderr)
        return 1

    latest_kpi = _extract_latest_kpi(events)
    reasons = _freeze_reasons(latest_kpi)
    decision = "FREEZE" if reasons else "CONTINUE"

    report = {
        "input": str(args.input),
        "event_count": len(events),
        "decision_counts": _count_by_key(events, "decision"),
        "result_counts": _count_by_key(events, "result"),
        "latest_kpi": {
            "failsafe_coverage": _safe_float(latest_kpi.get("failsafe_coverage"), 0.0),
            "freeze_correctness": _safe_float(latest_kpi.get("freeze_correctness"), 0.0),
            "policy_deny_delta": _safe_float(latest_kpi.get("policy_deny_delta"), 0.0),
            "warning_streak": _safe_int(latest_kpi.get("warning_streak"), 0),
        },
        "freeze_thresholds": FREEZE_THRESHOLDS,
        "final_decision": decision,
        "freeze_reasons": reasons,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"input={report['input']}")
        print(f"event_count={report['event_count']}")
        print(f"decision_counts={report['decision_counts']}")
        print(f"result_counts={report['result_counts']}")
        print(f"latest_kpi={report['latest_kpi']}")
        print(f"final_decision={report['final_decision']}")
        if reasons:
            print("freeze_reasons:")
            for r in reasons:
                print(f"- {r}")
        else:
            print("freeze_reasons: none")

    return 0


if __name__ == "__main__":
    sys.exit(main())
