from pathlib import Path

from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES
from generic_inference_block_ai.src.gib_alpha_tasks import load_and_validate_task_config

TASKS_PATH = Path(__file__).parent.parent / "config" / "gib_alpha_tasks.json"


def test_task_config_passes_validation() -> None:
    task_config = load_and_validate_task_config(TASKS_PATH)

    assert list(task_config["tasks"].keys()) == REQUIRED_ALLOWED_TASK_TYPES

    for task_type, definition in task_config["tasks"].items():
        assert definition["execution_effect"] == "none"
        assert definition["risk_level"] in ["low", "medium", "high"]
        assert isinstance(definition["input_contract"], list)
        assert isinstance(definition["output_contract"], list)
