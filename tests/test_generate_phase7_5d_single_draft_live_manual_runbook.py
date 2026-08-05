import json
import tempfile
from pathlib import Path

from scripts.generate_phase7_5d_single_draft_live_manual_runbook import run_generate

VALID_TOKEN = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _prepare_inputs(base: Path):
    p75a = base / "p75a.json"
    p75b = base / "p75b.json"
    p75c = base / "p75c.json"

    _write(
        p75a,
        {
            "phase7_5_decision": "FREEZE_RECOMMENDED",
            "live_execution_allowed": False,
        },
    )
    _write(
        p75b,
        {
            "status": "PASS",
            "approval_token": VALID_TOKEN,
        },
    )
    _write(
        p75c,
        {
            "status": "ABORT",
            "wordpress_write_executed": False,
        },
    )
    return p75a, p75b, p75c


def test_generate_pass_with_valid_inputs():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, p75c = _prepare_inputs(td)
        runbook_json = td / "runbook.json"
        runbook_md = td / "runbook.md"
        result_json = td / "result.json"

        result = run_generate(p75a, p75b, p75c, runbook_json, runbook_md, result_json)

        assert result["status"] == "PASS"
        assert result["runbook_generated"] is True
        assert result["fixed_procedure_item_count"] == 10
        assert result["live_execution_allowed"] is False
        assert result["wordpress_write_executed"] is False
        assert runbook_json.exists()
        assert runbook_md.exists()
        assert result_json.exists()


def test_missing_prerequisite_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, _ = _prepare_inputs(td)
        missing = td / "missing.json"
        result = run_generate(
            p75a,
            p75b,
            missing,
            td / "runbook.json",
            td / "runbook.md",
            td / "result.json",
        )
        assert result["status"] == "ABORT"


def test_invalid_phase7_5a_decision_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, p75c = _prepare_inputs(td)
        _write(p75a, {"phase7_5_decision": "GO_NOW"})

        result = run_generate(
            p75a,
            p75b,
            p75c,
            td / "runbook.json",
            td / "runbook.md",
            td / "result.json",
        )
        assert result["status"] == "ABORT"


def test_invalid_phase7_5b_token_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, p75c = _prepare_inputs(td)
        _write(
            p75b,
            {
                "status": "PASS",
                "approval_token": "APPROVE_SINGLE_DRAFT_CREATE_LIVE",
            },
        )

        result = run_generate(
            p75a,
            p75b,
            p75c,
            td / "runbook.json",
            td / "runbook.md",
            td / "result.json",
        )
        assert result["status"] == "ABORT"


def test_phase7_5c_already_executed_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, p75c = _prepare_inputs(td)
        _write(
            p75c,
            {
                "status": "PASS",
                "wordpress_write_executed": True,
            },
        )

        result = run_generate(
            p75a,
            p75b,
            p75c,
            td / "runbook.json",
            td / "runbook.md",
            td / "result.json",
        )
        assert result["status"] == "ABORT"


def test_result_contains_no_go_flags_on_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75a, p75b, p75c = _prepare_inputs(td)
        result_path = td / "result.json"

        run_generate(
            p75a,
            p75b,
            p75c,
            td / "runbook.json",
            td / "runbook.md",
            result_path,
        )

        saved = json.loads(result_path.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_post_enabled"] is False
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
