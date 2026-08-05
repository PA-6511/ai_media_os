import json
import tempfile
from pathlib import Path

from scripts.validate_phase7_4_single_draft_create_execution_gate import run_gate

ROOT = Path(__file__).resolve().parents[1]
VALID_P72 = ROOT / "exchange/logs/phase7_2_single_draft_create_execution_dry_run_result.json"
VALID_P73 = ROOT / "exchange/logs/phase7_3_single_draft_create_final_approval_result.json"
VALID_PAYLOAD = ROOT / "exchange/outgoing/wordpress_draft_create_payload.dry_run.json"


def _p72(td: str) -> Path:
    p = Path(td) / "p72.json"
    p.write_text(json.dumps({
        "status": "PASS",
        "dry_run_completed": True,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
    }), encoding="utf-8")
    return p


def _p73(td: str, decision: str = "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY") -> Path:
    p = Path(td) / "p73.json"
    p.write_text(json.dumps({
        "status": "PASS",
        "decision": decision,
        "checklist_all_confirmed": True,
        "reviewer_is_human": True,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
    }), encoding="utf-8")
    return p


def _payload(td: str, dry_run: bool = True, status: str = "draft") -> Path:
    p = Path(td) / "payload.json"
    p.write_text(json.dumps({
        "dry_run": dry_run,
        "wordpress_post_must_not_be_called": True,
        "status": status,
        "title": "テスト下書き",
    }), encoding="utf-8")
    return p


def test_all_conditions_pass():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_gate(_p72(td), _p73(td), _payload(td), out)
        assert result["status"] == "PASS"
        assert result["gate_passed"] is True
        assert result["wordpress_post_enabled"] is False
        assert result["real_write_enabled"] is False
        assert result["production_status"] == "NO_GO"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["wordpress_write_executed"] is False


def test_phase7_2_not_pass_aborts():
    with tempfile.TemporaryDirectory() as td:
        p72 = Path(td) / "p72.json"
        p72.write_text(json.dumps({
            "status": "ABORT",
            "dry_run_completed": False,
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
            "wordpress_write_executed": False,
        }), encoding="utf-8")
        result = run_gate(p72, _p73(td), _payload(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"
        assert result["gate_passed"] is False


def test_payload_status_not_draft_aborts():
    with tempfile.TemporaryDirectory() as td:
        result = run_gate(
            _p72(td), _p73(td), _payload(td, status="publish"), Path(td) / "r.json"
        )
        assert result["status"] == "ABORT"


def test_phase7_3_decision_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        result = run_gate(
            _p72(td),
            _p73(td, decision="APPROVE_SINGLE_DRAFT_CREATE_LIVE"),
            _payload(td),
            Path(td) / "r.json",
        )
        assert result["status"] == "ABORT"


def test_phase7_3_reviewer_not_human_aborts():
    with tempfile.TemporaryDirectory() as td:
        p73 = Path(td) / "p73.json"
        p73.write_text(json.dumps({
            "status": "PASS",
            "decision": "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY",
            "checklist_all_confirmed": True,
            "reviewer_is_human": False,
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
            "wordpress_write_executed": False,
        }), encoding="utf-8")
        result = run_gate(_p72(td), p73, _payload(td), Path(td) / "r.json")
        assert result["status"] == "ABORT"


def test_run_gate_writes_output_with_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_gate(_p72(td), _p73(td), _payload(td), out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["gate_passed"] is True
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_post_enabled"] is False
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
