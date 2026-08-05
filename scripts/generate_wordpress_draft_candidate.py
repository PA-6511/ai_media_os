#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/incoming/decision_package.realdata.normal.example.json"
DEFAULT_CANDIDATE_OUTPUT = ROOT / "exchange/outgoing/wordpress_draft_candidate.example.json"
DEFAULT_RESULT_OUTPUT = ROOT / "exchange/logs/wordpress_draft_candidate_result.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str) -> dict:
    return {
        "package_type": "wordpress_draft_candidate_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "ABORT",
        "reason": reason,
        "candidate_generated": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _validate_decision_package(data: dict) -> dict | None:
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")
    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")

    for flag in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden")

    if data.get("requested_action") in {"publish", "update", "delete", "export"}:
        return abort_result("requested_action indicates production operation")

    origin = data.get("self_builder_origin", {})
    if isinstance(origin, dict) and origin.get("execution_allowed") is True:
        return abort_result("self_builder_origin.execution_allowed=true is forbidden")

    return None


def _safe_text(value: str, fallback: str) -> str:
    v = str(value).strip() if value is not None else ""
    return v if v else fallback


def build_candidate(data: dict) -> dict:
    summary = _safe_text(data.get("summary", ""), "電子書籍セール候補")
    risk_level = _safe_text(data.get("risk_level", "LOW"), "LOW")

    title = f"【DRY_RUN候補】{summary}"
    content_html = (
        "<p>これは WordPress 下書き候補です。まだ投稿は実行されません。</p>"
        f"<p>概要: {summary}</p>"
        f"<p>リスクレベル: {risk_level}</p>"
        "<ul>"
        "<li>本番投稿: 未実行</li>"
        "<li>本番更新: 未実行</li>"
        "<li>外部Export: 未実行</li>"
        "</ul>"
    )

    return {
        "package_type": "wordpress_draft_candidate",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "title_candidate": title,
        "content_html_candidate": content_html,
        "category_candidates": ["電子書籍", "セール"],
        "tag_candidates": ["Kindle", "漫画", "セール"],
        "source_builder": data.get("self_builder_origin", {
            "type": "LOCAL_SELF_BUILDER",
            "location": "local",
            "execution_allowed": False,
            "vps_migration_ready": False,
        }),
        "next_step": "human_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_wordpress_draft_candidate(
    input_path: Path | None = None,
    candidate_output: Path | None = None,
    result_output: Path | None = None,
    overwrite: bool = False,
) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    candidate_output = Path(candidate_output or DEFAULT_CANDIDATE_OUTPUT)
    result_output = Path(result_output or DEFAULT_RESULT_OUTPUT)

    if not input_path.exists():
        result = abort_result(f"decision_package not found: {input_path}")
    elif (candidate_output.exists() or result_output.exists()) and not overwrite:
        target = candidate_output if candidate_output.exists() else result_output
        result = abort_result(f"output already exists: {target}")
    else:
        data = load_json(input_path)
        validation_error = _validate_decision_package(data)
        if validation_error:
            result = validation_error
        else:
            candidate = build_candidate(data)
            candidate_output.parent.mkdir(parents=True, exist_ok=True)
            candidate_output.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = {
                "package_type": "wordpress_draft_candidate_result",
                "mode": "CONNECTION_TEST",
                "execution": "DRY_RUN",
                "status": "PASS",
                "reason": "wordpress draft candidate generated for human_review",
                "candidate_generated": True,
                "candidate_output": str(candidate_output),
                "input_source": str(input_path),
                "wordpress_write_executed": False,
                "auto_post": False,
                "auto_update": False,
                "auto_delete": False,
                "auto_export": False,
                "next_step": "human_review",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

    result_output.parent.mkdir(parents=True, exist_ok=True)
    result_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> int:
    result = generate_wordpress_draft_candidate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
