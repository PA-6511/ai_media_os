import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from auto_builder_block_ai.scripts.generate_level5_status_report import generate_level5_status_report


def test_level5_status_report_outputs_required_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "auto_builder_level5_status_report.json"
        report = generate_level5_status_report(output_path)

        assert report["level5_status"] == "AUTO_BUILDER_LEVEL5_READY_DRY_RUN_ONLY"
        assert report["production_status"] == "NO_GO"
        assert report["execution_mode"] == "DRY_RUN_ONLY"
        assert report["next_step"] == "USE_FOR_LOW_TOKEN_PHASE_DEVELOPMENT_ONLY"

        persisted = json.loads(output_path.read_text(encoding="utf-8"))
        assert persisted == report