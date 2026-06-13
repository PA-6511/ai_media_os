import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from auto_builder_block_ai.src.copilot_prompt_generator import generate_copilot_prompt


def test_copilot_prompt_contains_required_sections():
    prompt = generate_copilot_prompt(
        phase_name="AUTO_BUILDER_LEVEL5_L5_1_TO_L5_5",
        objective="Implement the Level5 dry-run control plane.",
        target_files=["auto_builder_block_ai/src/low_token_dev_mode.py"],
        forbidden_actions=["Do not touch production routes."],
        validation_commands=["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q auto_builder_block_ai/tests"],
    )

    for heading in ["TASK:", "SCOPE:", "ALLOWED_FILES:", "DO_NOT:", "VALIDATION:", "OUTPUT:"]:
        assert heading in prompt
    assert "auto_builder_block_ai/src/low_token_dev_mode.py" in prompt
    assert "Do not read credentials." in prompt
    assert "Do not call external APIs." in prompt