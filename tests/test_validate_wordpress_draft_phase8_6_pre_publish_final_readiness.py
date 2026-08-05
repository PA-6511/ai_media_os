import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_phase8_6_pre_publish_final_readiness import run_validation

ROOT = Path(__file__).resolve().parents[1]
VALID_CONFIG = ROOT / "config/wordpress_draft_phase8_6_pre_publish_final_readiness.json"


def _load_valid() -> dict:
    return json.loads(VALID_CONFIG.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _base_p81() -> dict:
    return {"status": "PASS"}


def _base_p82() -> dict:
    return {
        "status": "PASS",
        "decision": "APPROVE",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
    }


def _base_p83() -> dict:
    return {"status": "PASS"}


def _base_p84() -> dict:
    return {"status": "PASS"}


def _base_p85() -> dict:
    return {"status": "PASS"}


def _base_p76() -> dict:
    return {
        "status": "PASS",
        "phase7_overall_status": "PASS",
        "wordpress_draft_id": 110,
        "created_post_status": "draft",
    }


def run_case(payload, p81=None, p82=None, p83=None, p84=None, p85=None, p76=None):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cfg = td / "cfg.json"
        out = td / "result.json"
        p81_path = td / "p81.json"
        p82_path = td / "p82.json"
        p83_path = td / "p83.json"
        p84_path = td / "p84.json"
        p85_path = td / "p85.json"
        p76_path = td / "p76.json"

        _write_json(cfg, payload)
        _write_json(p81_path, p81 or _base_p81())
        _write_json(p82_path, p82 or _base_p82())
        _write_json(p83_path, p83 or _base_p83())
        _write_json(p84_path, p84 or _base_p84())
        _write_json(p85_path, p85 or _base_p85())
        _write_json(p76_path, p76 or _base_p76())

        import scripts.validate_wordpress_draft_phase8_6_pre_publish_final_readiness as mod

        old_p81 = mod.PHASE8_1
        old_p82 = mod.PHASE8_2
        old_p83 = mod.PHASE8_3
        old_p84 = mod.PHASE8_4
        old_p85 = mod.PHASE8_5
        old_p76 = mod.PHASE7_6
        mod.PHASE8_1 = p81_path
        mod.PHASE8_2 = p82_path
        mod.PHASE8_3 = p83_path
        mod.PHASE8_4 = p84_path
        mod.PHASE8_5 = p85_path
        mod.PHASE7_6 = p76_path
        try:
            result = run_validation(cfg, out)
        finally:
            mod.PHASE8_1 = old_p81
            mod.PHASE8_2 = old_p82
            mod.PHASE8_3 = old_p83
            mod.PHASE8_4 = old_p84
            mod.PHASE8_5 = old_p85
            mod.PHASE7_6 = old_p76

        saved = json.loads(out.read_text(encoding="utf-8"))
        return result, saved


def test_valid_config_passes():
    result, saved = run_case(_load_valid())
    assert result["status"] == "PASS"
    assert saved["readiness_design_ready"] is True
    assert saved["target_draft_id"] == 110
    assert saved["target_draft_status"] == "draft"
    assert saved["wordpress_publish_execution"] == "NO_GO"
    assert saved["wordpress_write_executed"] is False


def test_phase85_not_pass_aborts():
    p85 = _base_p85()
    p85["status"] = "ABORT"
    result, _ = run_case(_load_valid(), p85=p85)
    assert result["status"] == "ABORT"


def test_phase82_not_approve_aborts():
    p82 = _base_p82()
    p82["decision"] = "REQUEST_FIX"
    result, _ = run_case(_load_valid(), p82=p82)
    assert result["status"] == "ABORT"


def test_publish_execution_not_no_go_aborts():
    payload = _load_valid()
    payload["wordpress_publish_execution"] = "GO"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_readiness_requirements_short_aborts():
    payload = _load_valid()
    payload["readiness_requirements"] = payload["readiness_requirements"][:3]
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_validation_writes_output_and_no_go_flags():
    result, saved = run_case(_load_valid())
    assert result["status"] == "PASS"
    assert saved["production_status"] == "NO_GO"
    assert saved["wordpress_publish_execution"] == "NO_GO"
    assert saved["wordpress_post_enabled"] is False
    assert saved["real_write_enabled"] is False
    assert saved["wordpress_write_executed"] is False
    assert saved["auto_post"] is False
    assert saved["auto_update"] is False
    assert saved["auto_delete"] is False
    assert saved["auto_export"] is False
