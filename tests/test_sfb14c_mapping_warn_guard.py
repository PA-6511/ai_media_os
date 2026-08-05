import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/generate_sfb14_dashboard_aggregation.py"
BASE_POLICY = ROOT / "config/sfb_14_dashboard_aggregation_policy.json"


def test_sfb14c_undefined_mapping_is_warn_not_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        policy = json.loads(BASE_POLICY.read_text(encoding="utf-8"))

        # Force one undefined mapping while keeping aggregation runnable.
        policy["display_name_mapping"].pop("sfb_10b_baseline", None)
        policy["output_paths"] = {
            "report_json": str(tmp / "sfb14_warn.json"),
            "report_md": str(tmp / "sfb14_warn.md"),
        }

        policy_path = tmp / "policy.json"
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--policy", str(policy_path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr

        report_json = Path(policy["output_paths"]["report_json"])
        payload = json.loads(report_json.read_text(encoding="utf-8"))

        assert payload["status"] == "SFB14_DASHBOARD_AGGREGATION_READY_WITH_WARNINGS"
        assert payload["undefined_phase_mapping_count"] >= 1
        assert any(item["id"] == "sfb_10b_baseline" for item in payload["undefined_phase_mappings"])

        # Non-blocking guard: safety invariants must stay unchanged.
        assert payload["production_status"] == "NO_GO"
        assert payload["mode"] == "DRY_RUN"
        assert payload["external_api_called"] is False
        assert payload["wordpress_write_executed"] is False
