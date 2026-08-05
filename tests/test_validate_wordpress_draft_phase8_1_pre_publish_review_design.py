import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_phase8_1_pre_publish_review_design import run_validation

ROOT = Path(__file__).resolve().parents[1]
VALID_CONFIG = ROOT / "config/wordpress_draft_phase8_1_pre_publish_review_design.json"
VALID_P76 = ROOT / "exchange/logs/phase7_6_wordpress_draft_creation_overall_completion_report.json"



def _load_valid() -> dict:
    return json.loads(VALID_CONFIG.read_text(encoding="utf-8"))



def _write_case(td: str, data: dict, p76: dict | None = None) -> tuple[Path, Path, Path]:
    cfg = Path(td) / "phase8_1.json"
    out = Path(td) / "result.json"
    p76_path = Path(td) / "phase7_6.json"
    cfg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if p76 is None:
        p76_data = json.loads(VALID_P76.read_text(encoding="utf-8"))
    else:
        p76_data = p76
    p76_path.write_text(json.dumps(p76_data, ensure_ascii=False), encoding="utf-8")
    return cfg, out, p76_path



def test_valid_config_passes():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_validation(VALID_CONFIG, out)
        assert result["status"] == "PASS"
        assert result["design_ready"] is True
        assert result["target_draft_id"] == 110
        assert result["target_draft_status"] == "draft"
        assert result["wordpress_publish_execution"] == "NO_GO"
        assert result["wordpress_write_executed"] is False



def test_wordpress_post_enabled_true_aborts():
    data = _load_valid()
    data["wordpress_post_enabled"] = True
    with tempfile.TemporaryDirectory() as td:
        cfg, out, p76 = _write_case(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"



def test_publish_execution_not_no_go_aborts():
    data = _load_valid()
    data["wordpress_publish_execution"] = "GO"
    with tempfile.TemporaryDirectory() as td:
        cfg, out, p76 = _write_case(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"



def test_review_checklist_short_aborts():
    data = _load_valid()
    data["review_checklist"] = data["review_checklist"][:3]
    with tempfile.TemporaryDirectory() as td:
        cfg, out, p76 = _write_case(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"



def test_target_draft_id_mismatch_aborts():
    data = _load_valid()
    data["target_draft"]["wordpress_draft_id"] = 999
    with tempfile.TemporaryDirectory() as td:
        cfg, out, p76 = _write_case(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"



def test_validation_writes_output_and_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_validation(VALID_CONFIG, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_publish_execution"] == "NO_GO"
        assert saved["wordpress_post_enabled"] is False
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
