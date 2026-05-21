#!/usr/bin/env python3
"""analyze_draft_check_reports.py

47-C-2-b: draft_check レポートの WARN 内訳を集計し、
公開候補化ルールの判断材料を出力する。

使い方:
  python3 tools/analyze_draft_check_reports.py --min-date 20260521
  python3 tools/analyze_draft_check_reports.py --min-date 20260521 --output reports/warn_analysis_20260521.json
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"(\d{8})")


def _extract_date(path: str) -> str | None:
    m = DATE_RE.search(Path(path).name)
    return m.group(1) if m else None


def _file_rank(path: str) -> int:
    """同日重複時の優先順位: recheck_full > recheck > normal"""
    name = Path(path).name
    if "recheck_full" in name:
        return 3
    if "recheck" in name:
        return 2
    return 1


def _select_files(paths: list[str], min_date: str | None, max_date: str | None) -> list[str]:
    by_date: dict[str, str] = {}
    for p in sorted(paths):
        name = Path(p).name
        if "manual_test" in name:
            continue
        dt = _extract_date(p)
        if not dt:
            continue
        if min_date and dt < min_date:
            continue
        if max_date and dt > max_date:
            continue
        prev = by_date.get(dt)
        if prev is None or _file_rank(p) > _file_rank(prev):
            by_date[dt] = p
    return [by_date[k] for k in sorted(by_date.keys())]


def _pct(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round((n / d) * 100.0, 1)


def analyze(files: list[str]) -> dict[str, Any]:
    finals = Counter()
    warn_checks = Counter()
    fail_checks = Counter()
    warn_details: dict[str, Counter] = defaultdict(Counter)

    per_day: list[dict[str, Any]] = []
    total_posts = 0

    for f in files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        checks = data.get("checks", [])
        n = len(checks)
        total_posts += n

        day_warn = Counter()
        day_fail = Counter()
        day_final = Counter()

        for row in checks:
            fr = row.get("final_result", "UNKNOWN")
            finals[fr] += 1
            day_final[fr] += 1

            for name, info in row.get("checks", {}).items():
                res = info.get("result", "UNKNOWN")
                if res == "WARN":
                    warn_checks[name] += 1
                    day_warn[name] += 1
                    for detail in info.get("details", []):
                        warn_details[name][detail] += 1
                elif res == "FAIL":
                    fail_checks[name] += 1
                    day_fail[name] += 1

        dt = _extract_date(f) or "unknown"
        per_day.append(
            {
                "date": dt,
                "file": f,
                "total_drafts": n,
                "final": dict(day_final),
                "warn_rate": {
                    "pr_notice": _pct(day_warn["pr_notice"], n),
                    "urls": _pct(day_warn["urls"], n),
                    "cta": _pct(day_warn["cta"], n),
                    "featured_image": _pct(day_warn["featured_image"], n),
                    "content_quality": _pct(day_warn["content_quality"], n),
                },
            }
        )

    result = {
        "files": files,
        "days": len(files),
        "total_drafts": total_posts,
        "final_summary": dict(finals),
        "warn_rate": {
            "pr_notice": _pct(warn_checks["pr_notice"], total_posts),
            "urls": _pct(warn_checks["urls"], total_posts),
            "cta": _pct(warn_checks["cta"], total_posts),
            "featured_image": _pct(warn_checks["featured_image"], total_posts),
            "content_quality": _pct(warn_checks["content_quality"], total_posts),
        },
        "fail_rate": {
            "content_quality": _pct(fail_checks["content_quality"], total_posts),
            "urls": _pct(fail_checks["urls"], total_posts),
            "cta": _pct(fail_checks["cta"], total_posts),
            "pr_notice": _pct(fail_checks["pr_notice"], total_posts),
            "featured_image": _pct(fail_checks["featured_image"], total_posts),
        },
        "top_warn_reasons": {
            k: [{"reason": reason, "count": cnt} for reason, cnt in warn_details[k].most_common(5)]
            for k in ["pr_notice", "urls", "cta", "featured_image", "content_quality"]
        },
        "per_day": per_day,
        "policy_recommendation": {
            "block_publish_if_fail": True,
            "block_publish_if_warn": ["pr_notice", "urls", "cta"],
            "allow_with_manual_fix": ["featured_image", "content_quality"],
            "priority_order": ["pr_notice", "urls", "cta", "featured_image", "content_quality"],
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="draft_check レポート集計（47-C-2-b）")
    parser.add_argument("--glob", default="reports/draft_check*.json", help="対象ファイル glob")
    parser.add_argument("--min-date", default=None, help="対象開始日 (YYYYMMDD)")
    parser.add_argument("--max-date", default=None, help="対象終了日 (YYYYMMDD)")
    parser.add_argument("--output", default=None, help="出力JSONパス")
    args = parser.parse_args()

    files = _select_files(glob.glob(args.glob), args.min_date, args.max_date)
    if not files:
        raise SystemExit("対象ファイルがありません")

    analyzed = analyze(files)
    text = json.dumps(analyzed, ensure_ascii=False, indent=2)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"saved: {out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
