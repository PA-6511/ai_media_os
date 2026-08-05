import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_37_first_trial_operation_runbook import validate


def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        path.write_text(data, encoding="utf-8")


REQUIRED_SECTIONS = [
    "目的", "現在の固定状態", "実行前提", "絶対禁止事項",
    "Credential Ready 確認", "Phase 8-36 handoff 確認",
    "初回1件対象の選定条件", "人間承認条件", "one-shot lock 条件",
    "実行直前 preflight", "実行中監視項目", "実行後 evidence",
    "WordPress 側確認項目", "Slack 通知方針",
    "rollback 条件", "freeze 条件", "ABORT 条件",
    "PASS 条件", "WARN 条件", "FAIL 条件",
    "再実行禁止条件", "secret 非露出ルール", "最終報告フォーマット",
]


def _make_policy(tmp: Path) -> Path:
    p = tmp / "config/policy.json"
    _write(p, {"required_runbook_sections": REQUIRED_SECTIONS})
    return p


def test_pass_when_all_sections_present(tmp_path: Path):
    policy = _make_policy(tmp_path)
    runbook = tmp_path / "runbook.md"
    content = "\n".join(f"## {s}" for s in REQUIRED_SECTIONS)
    _write(runbook, content)
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = validate(policy, runbook, out_r, out_j, out_m)
    assert result["status"] == "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"
    assert result["missing_section_count"] == 0
    assert result["wordpress_write_executed"] is False
    assert result["executed_external_changes"] == 0


def test_fail_when_section_missing(tmp_path: Path):
    policy = _make_policy(tmp_path)
    runbook = tmp_path / "runbook.md"
    # 最初の1セクションだけ省略
    content = "\n".join(f"## {s}" for s in REQUIRED_SECTIONS[1:])
    _write(runbook, content)
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = validate(policy, runbook, out_r, out_j, out_m)
    assert result["status"] == "ABORT_RUNBOOK_REQUIRED_SECTION_MISSING_NO_EXECUTION"
    assert result["missing_section_count"] >= 1


def test_fail_when_runbook_missing(tmp_path: Path):
    policy = _make_policy(tmp_path)
    out_r = tmp_path / "exchange/logs/result.json"
    out_j = tmp_path / "exchange/logs/report.json"
    out_m = tmp_path / "exchange/logs/report.md"

    result = validate(policy, tmp_path / "MISSING.md", out_r, out_j, out_m)
    assert result["status"] == "ABORT_RUNBOOK_REQUIRED_SECTION_MISSING_NO_EXECUTION"
    assert result["runbook_exists"] is False
