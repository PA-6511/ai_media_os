import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from auto_builder_block_ai.src.codex_preprocessor import preprocess_codex_context


def test_codex_preprocessor_contains_required_sections_and_redacts():
    summary = preprocess_codex_context(
        raw_log="failure in auto_builder_block_ai/src/low_token_dev_mode.py\npassword=super-secret-value",
        diff_summary="Updated auto_builder_block_ai/src/low_token_dev_mode.py and auto_builder_block_ai/tests/test_low_token_dev_mode_policy.py",
        failing_tests=["auto_builder_block_ai/tests/test_low_token_dev_mode_policy.py::test_policy_stays_in_no_go_dry_run_mode"],
    )

    for heading in ["SUMMARY:", "LIKELY_CAUSE:", "FILES_TO_CHECK:", "NEXT_ACTION:", "SAFETY_NOTES:"]:
        assert heading in summary
    assert "super-secret-value" not in summary
    assert "auto_builder_block_ai/src/low_token_dev_mode.py" in summary