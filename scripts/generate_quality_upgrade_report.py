#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_ranking_policy import check_policy

BUILDER_PATH = ROOT / "blocks/ebook_affiliate/draft_payload_builder.py"
LOG_DIR = ROOT / "logs"
JSON_OUT = LOG_DIR / "quality_upgrade_report.json"
MD_OUT = LOG_DIR / "quality_upgrade_report.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check_draft_template(builder_text: str) -> Dict[str, Any]:
    required_tokens = [
        "## 作品概要",
        "## こんな人におすすめ",
        "## 見どころ",
        "## 読者評価ポイント",
        "## 購入はこちら",
        "## PR表記",
    ]
    missing = [token for token in required_tokens if token not in builder_text]
    status = "PASS" if not missing else "FAIL"
    return {
        "status": status,
        "required_sections": required_tokens,
        "missing_sections": missing,
    }


def _check_seo(builder_text: str) -> Dict[str, Any]:
    required_tokens = [
        "## よくある質問",
        "## 関連作品",
        "## 関連記事",
        '"seo_version": "v1"',
        '"generated_sections": [',
    ]
    missing = [token for token in required_tokens if token not in builder_text]
    status = "PASS" if not missing else "FAIL"
    return {
        "status": status,
        "required_tokens": required_tokens,
        "missing_tokens": missing,
    }


def _check_reader_profile(builder_text: str) -> Dict[str, Any]:
    required_tokens = [
        "## この作品が刺さる読者",
        "幅広い読者におすすめ",
        '"reader_profile_version": "v1"',
    ]
    missing = [token for token in required_tokens if token not in builder_text]
    status = "PASS" if not missing else "FAIL"
    return {
        "status": status,
        "required_tokens": required_tokens,
        "missing_tokens": missing,
    }


def _overall_status(statuses: List[str]) -> str:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "WARN"
    return "PASS"


def generate_report() -> Dict[str, Any]:
    if not BUILDER_PATH.exists():
        payload = {
            "status": "FAIL",
            "reason": f"builder not found: {BUILDER_PATH}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        MD_OUT.write_text("# Quality Upgrade Report\n\n- status: FAIL\n", encoding="utf-8")
        return payload

    builder_text = _read_text(BUILDER_PATH)
    draft_template = _check_draft_template(builder_text)
    seo = _check_seo(builder_text)
    reader_profile = _check_reader_profile(builder_text)
    ranking_policy = check_policy()

    statuses = [
        draft_template.get("status", "FAIL"),
        seo.get("status", "FAIL"),
        reader_profile.get("status", "FAIL"),
        ranking_policy.get("status", "FAIL"),
    ]
    overall = _overall_status(statuses)

    payload = {
        "status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "draft_template": draft_template,
            "seo": seo,
            "reader_profile": reader_profile,
            "ranking_policy": ranking_policy,
        },
        "production_status_unchanged": True,
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Quality Upgrade Report v1",
        "",
        f"- overall_status: {overall}",
        f"- generated_at: {payload['generated_at']}",
        "- production_status: unchanged",
        "",
        "## Draft Template",
        f"- status: {draft_template['status']}",
        f"- missing_sections: {', '.join(draft_template['missing_sections']) or 'none'}",
        "",
        "## SEO",
        f"- status: {seo['status']}",
        f"- missing_tokens: {', '.join(seo['missing_tokens']) or 'none'}",
        "",
        "## Reader Profile",
        f"- status: {reader_profile['status']}",
        f"- missing_tokens: {', '.join(reader_profile['missing_tokens']) or 'none'}",
        "",
        "## Ranking Policy",
        f"- status: {ranking_policy['status']}",
        f"- errors: {', '.join(ranking_policy.get('errors', [])) or 'none'}",
        f"- warnings: {', '.join(ranking_policy.get('warnings', [])) or 'none'}",
    ]
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    result = generate_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
