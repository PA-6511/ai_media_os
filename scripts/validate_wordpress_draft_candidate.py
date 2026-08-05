#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/outgoing/wordpress_draft_candidate.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/wordpress_draft_candidate_validation_result.json"

FORBIDDEN_HTML_PATTERNS = [
    r"<script\b",
    r"<iframe\b",
    r"onerror\s*=",
    r"onload\s*=",
    r"javascript:",
]

AFFILIATE_HINTS = ["tag=", "aff", "affiliate", "ref="]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _abort(reason: str) -> dict:
    return {
        "package_type": "wordpress_draft_candidate_validation_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "ABORT",
        "reason": reason,
        "quality_checks": {},
        "warnings": [],
        "issues": [reason],
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_urls(html: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']+)["\']', html or "", flags=re.IGNORECASE)


def _looks_affiliate(url: str) -> bool:
    l = url.lower()
    return any(h in l for h in AFFILIATE_HINTS)


def validate_candidate(data: dict) -> dict:
    issues = []
    warnings = []
    checks = {}

    # Hard safety gates
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("human_approval_required") is not True:
        return _abort("human_approval_required must be true")

    for flag in ["wordpress_write_executed", "auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return _abort(f"{flag}=true is forbidden")

    # 1) title length
    title = str(data.get("title_candidate", "")).strip()
    if not title:
        checks["title_presence"] = "FAIL"
        issues.append("title_candidate is empty")
    else:
        checks["title_presence"] = "PASS"
        if len(title) < 12 or len(title) > 80:
            checks["title_length"] = "WARN"
            warnings.append(f"title length is out of recommended range: {len(title)}")
        else:
            checks["title_length"] = "PASS"

    # 2) content presence
    content = str(data.get("content_html_candidate", "")).strip()
    if not content:
        checks["content_presence"] = "FAIL"
        issues.append("content_html_candidate is empty")
    else:
        checks["content_presence"] = "PASS"

    # 3) html safety
    html_low = content.lower()
    bad_hits = [p for p in FORBIDDEN_HTML_PATTERNS if re.search(p, html_low)]
    if bad_hits:
        checks["html_safety"] = "FAIL"
        issues.append(f"forbidden html patterns detected: {bad_hits}")
    else:
        checks["html_safety"] = "PASS"

    # 4) PR labeling
    if ("pr" in html_low) or ("広告" in content):
        checks["pr_label"] = "PASS"
    else:
        checks["pr_label"] = "WARN"
        warnings.append("PR/広告 表記が content_html_candidate に見つかりません")

    # 5) category/tag presence
    categories = data.get("category_candidates", [])
    tags = data.get("tag_candidates", [])

    non_empty_categories = [c for c in categories if isinstance(c, str) and c.strip()]
    non_empty_tags = [t for t in tags if isinstance(t, str) and t.strip()]

    if non_empty_categories:
        checks["category_presence"] = "PASS"
    else:
        checks["category_presence"] = "FAIL"
        issues.append("category_candidates is empty")

    if non_empty_tags:
        checks["tag_presence"] = "PASS"
    else:
        checks["tag_presence"] = "FAIL"
        issues.append("tag_candidates is empty")

    # 6) URL & affiliate hint checks
    urls = _extract_urls(content)
    if not urls:
        checks["url_presence"] = "WARN"
        warnings.append("本文にリンクURLが見つかりません")
        checks["affiliate_hint"] = "WARN"
        warnings.append("affiliate tag の確認対象URLがありません")
    else:
        checks["url_presence"] = "PASS"
        invalid_scheme = []
        affiliate_like = 0
        for u in urls:
            scheme = urlparse(u).scheme.lower()
            if scheme not in {"http", "https"}:
                invalid_scheme.append(u)
            if _looks_affiliate(u):
                affiliate_like += 1

        if invalid_scheme:
            checks["url_scheme"] = "FAIL"
            issues.append(f"non-http(s) urls detected: {invalid_scheme}")
        else:
            checks["url_scheme"] = "PASS"

        if affiliate_like > 0:
            checks["affiliate_hint"] = "PASS"
        else:
            checks["affiliate_hint"] = "WARN"
            warnings.append("affiliate tag の兆候がURLに見つかりません")

    if issues:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "package_type": "wordpress_draft_candidate_validation_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": status,
        "reason": "wordpress draft candidate quality/safety validation completed",
        "quality_checks": checks,
        "warnings": warnings,
        "issues": issues,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "human_review" if status in {"PASS", "WARN"} else "fix_required",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"candidate file not found: {input_path}")
    else:
        data = load_json(input_path)
        result = validate_candidate(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ABORT":
        return 2
    if result.get("status") == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
