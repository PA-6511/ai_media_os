import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_13_operator_runbook import validate_runbook


BASE = """# Phase 7-13 First Controlled WordPress Draft Creation Operator Runbook

## 1. Purpose
ok
## 2. Current Status
Production status: NO_GO
Current phase does not execute WordPress write.
APPROVE_DRAFT_CREATE_ONLY is not active in Phase 7-13.
## 3. Absolute NO-GO Until Explicit Approval
Do not publish.
Do not update existing posts.
Do not delete posts.
Do not run bulk execution.
## 4. Required Preconditions
HUMAN_APPROVAL_REQUIRED=true
target_item_count=1
## 5. Human Approval Requirements
ok
## 6. Allowed Scope After Future Approval
ok
## 7. Blocked Operations
AUTO_POST=false
AUTO_UPDATE=false
AUTO_DELETE=false
AUTO_EXPORT=false
publish_allowed=false
wordpress_write_executed=false
wordpress_api_call_allowed=false
WordPress REST API POST is not allowed in Phase 7-13.
## 8. Single Item Execution Checklist
ok
## 9. Pre-execution Verification
If any mismatch is detected, immediately freeze and stop.
## 10. Execution Command Placeholder
DRY_RUN_PLACEHOLDER_ONLY: future command must be reviewed in Phase 8 before execution.
## 11. Evidence Checklist
ok
## 12. Freeze Conditions
ok
## 13. Rollback / Manual Cleanup
ok
## 14. Post-run Review
ok
## 15. Final Judgment
ok
## 16. Next Step
ok
"""


def run_case(tmp_path: Path, content: str) -> dict:
    runbook = tmp_path / "docs/runbooks/phase7_13_first_controlled_wordpress_draft_creation_operator_runbook.md"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    runbook.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text(content, encoding="utf-8")
    return validate_runbook(runbook, out_json, out_md)


def test_normal_pass_runbook_only(tmp_path: Path):
    assert run_case(tmp_path, BASE)["status"] == "PASS_RUNBOOK_ONLY"


def test_missing_section_fail(tmp_path: Path):
    bad = BASE.replace("## 16. Next Step", "## 16. Next")
    assert run_case(tmp_path, bad)["status"] == "FAIL"


def test_missing_no_go_line_fail(tmp_path: Path):
    bad = BASE.replace("Production status: NO_GO\n", "")
    assert run_case(tmp_path, bad)["status"] == "FAIL"


def test_missing_target_count_fail(tmp_path: Path):
    bad = BASE.replace("target_item_count=1\n", "")
    assert run_case(tmp_path, bad)["status"] == "FAIL"


def test_auto_post_true_abort(tmp_path: Path):
    bad = BASE + "\nAUTO_POST=true\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    bad = BASE + "\npublish_allowed=true\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_write_executed_true_abort(tmp_path: Path):
    bad = BASE + "\nwordpress_write_executed=true\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_api_allowed_true_abort(tmp_path: Path):
    bad = BASE + "\nwordpress_api_call_allowed=true\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_curl_post_abort(tmp_path: Path):
    bad = BASE + "\ncurl -X POST\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_requests_post_abort(tmp_path: Path):
    bad = BASE + "\nrequests.post(\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"


def test_wp_api_path_abort(tmp_path: Path):
    bad = BASE + "\nwp-json/wp/v2/posts\n"
    assert run_case(tmp_path, bad)["status"] == "ABORT"
