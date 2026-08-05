import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_phase7_1_pre_release_checklist import run_validation

ROOT = Path(__file__).resolve().parents[1]
VALID_CONFIG = ROOT / "config/wordpress_draft_phase7_1_pre_release_checklist.json"


def _load_valid() -> dict:
    return json.loads(VALID_CONFIG.read_text(encoding="utf-8"))


def _write(td: str, data: dict) -> tuple[Path, Path]:
    cfg = Path(td) / "checklist.json"
    out = Path(td) / "result.json"
    cfg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return cfg, out


def test_valid_config_passes():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_validation(VALID_CONFIG, out)
        assert result["status"] == "PASS"
        assert result["checklist_ready"] is True
        assert result["design_status"] == "DESIGN_ONLY"
        assert result["wordpress_post_enabled"] is False
        assert result["real_write_enabled"] is False
        assert result["production_status"] == "NO_GO"
        assert result["wordpress_draft_creation"] == "NO_GO"
        assert result["wordpress_write_executed"] is False
        assert result["current_result"] in ("CHECKLIST_INCOMPLETE", "CHECKLIST_BLOCKED")
        assert result["mandatory_item_count"] >= 1


def test_wordpress_post_enabled_true_aborts():
    data = _load_valid()
    data["wordpress_post_enabled"] = True
    with tempfile.TemporaryDirectory() as td:
        cfg, out = _write(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_real_write_enabled_true_aborts():
    data = _load_valid()
    data["real_write_enabled"] = True
    with tempfile.TemporaryDirectory() as td:
        cfg, out = _write(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_missing_required_section_aborts():
    data = _load_valid()
    del data["safety_checks"]
    with tempfile.TemporaryDirectory() as td:
        cfg, out = _write(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_insufficient_safety_checks_aborts():
    data = _load_valid()
    data["safety_checks"] = data["safety_checks"][:2]  # 2件に削減
    with tempfile.TemporaryDirectory() as td:
        cfg, out = _write(td, data)
        result = run_validation(cfg, out)
        assert result["status"] == "ABORT"


def test_run_validation_writes_output_and_no_go_flags():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "result.json"
        result = run_validation(VALID_CONFIG, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
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
