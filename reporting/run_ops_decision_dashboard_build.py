from __future__ import annotations

import sys

from reporting.ops_decision_dashboard_builder import (
    build_ops_decision_dashboard_html,
    load_latest_release_readiness,
)
from reporting.ops_decision_dashboard_writer import write_ops_decision_dashboard


def main() -> int:
    try:
        summary = load_latest_release_readiness()
        html = build_ops_decision_dashboard_html(summary)
        output_path = write_ops_decision_dashboard(html)
        print(f"ops decision dashboard generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops decision dashboard build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
