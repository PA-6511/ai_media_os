import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from auto_builder_block_ai.src.level5_dev_pack_generator import generate_level5_dev_pack


def test_level5_dev_pack_generator_writes_expected_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_level5_dev_pack(
            phase_name="sample_l5_phase",
            objective="sample low token development pack",
            target_files=["auto_builder_block_ai/src/low_token_dev_mode.py"],
            validation_commands=["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q auto_builder_block_ai/tests"],
            report_dir=Path(tmpdir),
        )

        assert result["status"] == "READY"
        artifacts = result["generated_artifacts"]
        assert len(artifacts) == 4
        for artifact in artifacts:
            assert Path(artifact).exists()

        dev_pack = json.loads(Path(artifacts[0]).read_text(encoding="utf-8"))
        assert dev_pack["production_status"] == "NO_GO"
        assert dev_pack["execution_mode"] == "DRY_RUN_ONLY"
        assert dev_pack["external_calls_allowed"] is False
        assert dev_pack["credential_access_allowed"] is False
        assert dev_pack["wordpress_write_allowed"] is False
        assert dev_pack["systemd_changes_allowed"] is False