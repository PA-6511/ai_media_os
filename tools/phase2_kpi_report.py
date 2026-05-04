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

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.governance.auto_freeze_judge import FREEZE_THRESHOLDS, judge_auto_freeze


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


def _extract_latest_kpi(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        kpi = event.get("kpi")
        if isinstance(kpi, dict):
            return kpi
    return {}


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
    judge = judge_auto_freeze(latest_kpi)
    decision = judge.decision.value
    reasons = judge.reasons

    report = {
        "input": str(args.input),
        "event_count": len(events),
        "decision_counts": _count_by_key(events, "decision"),
        "result_counts": _count_by_key(events, "result"),
        "latest_kpi": judge.normalized_kpi,
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
