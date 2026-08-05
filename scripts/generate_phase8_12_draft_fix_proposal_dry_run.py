#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_12_draft_fix_proposal_dry_run_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_12_draft_fix_proposal_dry_run_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_12_draft_fix_proposal_dry_run_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_phase8_12_draft_fix_proposal_dry_run(
    policy_path: Path = DEFAULT_POLICY,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    if not policy_path.exists():
        result = {
            "phase": "Phase 8-12",
            "status": "ABORT",
            "reason": f"missing_policy: {policy_path}",
            "production_status": "NO_GO",
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "auto_post": False,
            "errors": [f"missing_policy:{policy_path}"],
            "warnings": [],
            "safety_violations": ["missing_policy"],
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_path.write_text(_build_markdown(result), encoding="utf-8")
        return result

    policy = _load_json(policy_path)
    root = _resolve_root(policy_path)

    for key in [
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    evidence_summary: list[dict[str, Any]] = []
    phase811_payload: dict[str, Any] = {}
    missing_evidence = False

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(ev_path)
        st = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": st})
        phase811_payload = payload

    if missing_evidence:
        safety_violations.append("required evidence missing")
    else:
        if phase811_payload.get("status") != policy.get("required_phase8_11_status"):
            safety_violations.append(
                f"phase8_11 status must be {policy.get('required_phase8_11_status')}"
            )

        if phase811_payload.get("target_post_id") != policy.get("target_post_id"):
            safety_violations.append("target_post_id mismatch with phase8_11 result")

        required_checklist = policy.get("required_checklist_state", {})
        actual_checklist = phase811_payload.get("checklist", {})
        for key, expected in required_checklist.items():
            if actual_checklist.get(key) is not expected:
                safety_violations.append(f"checklist.{key} must be {expected}")

        for key in ["publish_allowed", "update_allowed", "delete_allowed", "export_allowed", "auto_post"]:
            if phase811_payload.get(key) is not False:
                safety_violations.append(f"phase8_11.{key} must be false")

    if safety_violations:
        status = "ABORT"
        reason = "policy/evidence gate failed"
        proposal = {}
        next_step = "fix_gate_or_evidence_then_retry_dry_run_generation"
    else:
        status = "PHASE8_12_DRAFT_FIX_PROPOSAL_READY_DRY_RUN_ONLY"
        reason = "draft fix proposal generated without WordPress write"
        proposal = {
            "target_post_id": policy.get("target_post_id"),
            "proposed_title": "サンプル漫画 1巻 セール紹介【PR】",
            "proposed_body_markdown": """【PR】この記事はアフィリエイトプログラムを利用しています。\n\n## サンプル漫画 1巻 セール情報\n期間限定で価格が下がっているため、まずは1巻を試したい方向けに情報を整理しました。\n\n## こんな人におすすめ\n- 少額で試し読みしたい\n- まず1巻だけ読んで判断したい\n- キャンペーン期間中に購入したい\n\n## 商品リンク\n- 公式商品ページ: https://example.com/replace-with-official-product-link\n- アフィリエイトリンク: https://example.com/replace-with-affiliate-link\n\n## 注意点\n- 価格や還元率は変動する可能性があります。\n- 最終的な購入前に販売ページで最新情報を確認してください。\n\n## まとめ\n1巻のセールを安全に活用したい方は、上記リンク先で条件を確認してから判断してください。\n""",
            "must_replace_placeholders": [
                "https://example.com/replace-with-official-product-link",
                "https://example.com/replace-with-affiliate-link"
            ],
            "fix_focus": [
                "preflight/test wording の除去",
                "PR表記の維持",
                "商品/アフィリエイトリンクの明示",
                "危険HTMLを含めない"
            ]
        }
        next_step = policy.get("allowed_next_step", "Phase 8-13 manual review")

    result = {
        "phase": "Phase 8-12",
        "status": status,
        "reason": reason,
        "production_status": "NO_GO",
        "mode": policy.get("mode", "DRAFT_FIX_PROPOSAL"),
        "execution": "DRY_RUN",
        "target_post_id": policy.get("target_post_id"),
        "proposal": proposal,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": next_step,
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")
    return result


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-12 Draft Fix Proposal DRY_RUN Report",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- reason: {result.get('reason')}",
        "",
        "## Safety Flags",
        f"- production_status: {result.get('production_status')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- update_allowed: {result.get('update_allowed')}",
        f"- delete_allowed: {result.get('delete_allowed')}",
        f"- export_allowed: {result.get('export_allowed')}",
        f"- auto_post: {result.get('auto_post')}",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        "",
        "## Evidence Summary",
    ]

    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    proposal = result.get("proposal", {})
    if proposal:
        lines.extend(
            [
                "",
                "## Proposal",
                f"- target_post_id: {proposal.get('target_post_id')}",
                f"- proposed_title: {proposal.get('proposed_title')}",
                "",
                "### Proposed Body (Markdown)",
                "```markdown",
                proposal.get("proposed_body_markdown", ""),
                "```",
                "",
                "### Placeholder Links To Replace",
            ]
        )
        for p in proposal.get("must_replace_placeholders", []):
            lines.append(f"- {p}")

    lines.extend(
        [
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    result = generate_phase8_12_draft_fix_proposal_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PHASE8_12_DRAFT_FIX_PROPOSAL_READY_DRY_RUN_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
