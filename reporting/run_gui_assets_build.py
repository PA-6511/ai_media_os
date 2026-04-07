from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildStep:
    name: str
    module: str


GUI_BUILD_STEPS: list[BuildStep] = [
    BuildStep("release_readiness", "ops.run_release_readiness_check"),
    BuildStep("ops_summary", "reporting.run_ops_summary_build"),
    BuildStep("ops_api_payload", "reporting.run_ops_api_payload_build"),
    BuildStep("status_badge", "reporting.run_status_badge_build"),
    BuildStep("ops_status_light", "reporting.run_ops_status_light_build"),
    BuildStep("ops_portal", "reporting.run_ops_portal_build"),
    BuildStep("ops_home", "reporting.run_ops_home_build"),
    BuildStep("ops_manifest", "reporting.run_ops_manifest_build"),
    BuildStep("ops_timestamps", "reporting.run_ops_timestamps_build"),
    BuildStep("ops_cards", "reporting.run_ops_cards_build"),
    BuildStep("ops_sidebar", "reporting.run_ops_sidebar_build"),
    BuildStep("ops_tabs", "reporting.run_ops_tabs_build"),
    BuildStep("ops_widgets", "reporting.run_ops_widgets_build"),
    BuildStep("ops_layout", "reporting.run_ops_layout_build"),
    BuildStep("ops_header", "reporting.run_ops_header_build"),
    BuildStep("ops_home_payload", "reporting.run_ops_home_payload_build"),
    BuildStep("ops_gui_schema", "reporting.run_ops_gui_schema_build"),
    BuildStep("ops_bootstrap", "reporting.run_ops_bootstrap_build"),
    BuildStep("mock_api", "reporting.run_mock_api_build"),
    BuildStep("ops_gui_preview", "reporting.run_ops_gui_preview_build"),
    BuildStep("ops_alert_center", "reporting.run_ops_alert_center_build"),
    BuildStep("ops_timeline", "reporting.run_ops_timeline_build"),
    BuildStep("ops_recent_events", "reporting.run_ops_recent_events_build"),
    BuildStep("ops_config_summary", "reporting.run_ops_config_summary_build"),
    BuildStep("ops_gui_health", "reporting.run_ops_gui_health_build"),
    BuildStep("ops_decision_summary", "reporting.run_ops_decision_summary_build"),
    BuildStep("ops_gui_bundle", "reporting.run_ops_gui_bundle_build"),
    BuildStep("ops_gui_handoff", "reporting.run_ops_gui_handoff_build"),
]


def _tail(text: str, max_lines: int = 6) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def _run_step(step: BuildStep) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", step.module],
        capture_output=True,
        text=True,
        check=False,
    )

    output_parts = []
    stdout_tail = _tail(result.stdout)
    stderr_tail = _tail(result.stderr)
    if stdout_tail:
        output_parts.append(stdout_tail)
    if stderr_tail:
        output_parts.append(stderr_tail)
    combined = "\n".join(output_parts).strip()
    return result.returncode == 0, combined


def main() -> int:
    total = len(GUI_BUILD_STEPS)
    passed = 0
    failed_steps: list[str] = []

    print("GUI assets build started")
    for index, step in enumerate(GUI_BUILD_STEPS, start=1):
        ok, detail = _run_step(step)
        status = "PASS" if ok else "FAIL"
        print(f"[{index}/{total}] {status} {step.name} ({step.module})")
        if detail:
            print(detail)

        if ok:
            passed += 1
        else:
            failed_steps.append(step.name)

    failed = len(failed_steps)
    print("=" * 72)
    print("GUI assets build summary")
    print(f"total: {total}")
    print(f"passed: {passed}")
    print(f"failed: {failed}")
    if failed_steps:
        print("failed_steps: " + ", ".join(failed_steps))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())