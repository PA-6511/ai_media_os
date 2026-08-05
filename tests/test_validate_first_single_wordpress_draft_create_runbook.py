import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_first_single_wordpress_draft_create_runbook import run_validation, validate_runbook_text


VALID_RUNBOOK = """# Phase 6-8 初回1件限定 WordPress実下書き作成ランブック

## 1. Purpose
x

## 2. Current Status
Production status: NO_GO
Current phase does not allow WordPress write execution.
AUTO_POST=false
AUTO_UPDATE=false
AUTO_DELETE=false
AUTO_EXPORT=false
HUMAN_APPROVAL_REQUIRED=true
execution=DRY_RUN
publish_allowed=false
wordpress_write_executed=false
max_items=1
APPROVE_DRAFT_CREATE_ONLY is reserved for future controlled unlock only.

## 3. Absolute NO-GO
If any mismatch is detected, immediately freeze and stop.

## 4. Required Preconditions
- Phase 6-5 execution spec PASS
- Phase 6-6 quality gate PASS or acceptable WARN reviewed by human
- Phase 6-7 Slack approval DRY_RUN PASS
- Phase 6-9 preflight gate PASS
- Target item count equals 1
- Duplicate check passed
- PR notice exists
- CTA URL exists
- affiliate link uses https
- rollback/freeze path exists
- human approval evidence exists

## 5. GO Conditions
x

## 6. NO-GO Conditions
x

## 7. Execution Scope
- Only one item
- Draft creation only in future unlock
- No publish
- No update
- No delete
- No export
- No bulk run
- No retry storm
- No automatic escalation

## 8. Operator Checklist
x

## 9. Evidence Checklist
x

## 10. Freeze / Rollback
- freeze flag を立てる
- Slack通知はDRY_RUNまたは手動
- 証跡JSONを保存
- 該当候補を再実行不可にする
- 人間レビューまで停止

## 11. Post-run Review
x

## 12. Next Step
x
"""


def test_valid_runbook_passes():
    result = validate_runbook_text(VALID_RUNBOOK)
    assert result["status"] == "PASS_DRY_RUN_ONLY"


def test_missing_section_fails():
    text = VALID_RUNBOOK.replace("## 12. Next Step", "")
    result = validate_runbook_text(text)
    assert result["status"] == "FAIL"


def test_auto_post_true_aborts():
    text = VALID_RUNBOOK + "\nAUTO_POST=true\n"
    result = validate_runbook_text(text)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_aborts():
    text = VALID_RUNBOOK + "\npublish_allowed=true\n"
    result = validate_runbook_text(text)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    text = VALID_RUNBOOK + "\nwordpress_write_executed=true\n"
    result = validate_runbook_text(text)
    assert result["status"] == "ABORT"


def test_missing_max_items_fails():
    text = VALID_RUNBOOK.replace("max_items=1\n", "")
    result = validate_runbook_text(text)
    assert result["status"] == "FAIL"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "runbook.md"
        out = Path(td) / "result.json"
        inp.write_text(VALID_RUNBOOK, encoding="utf-8")
        result = run_validation(inp, out)
        assert out.exists()
        assert result["status"] == "PASS_DRY_RUN_ONLY"
