from __future__ import annotations

import sys

from reporting.status_badge_builder import build_status_badge, build_status_badge_html
from reporting.status_badge_writer import write_status_badge_html, write_status_badge_json


def main() -> int:
    try:
        badge = build_status_badge()
        html = build_status_badge_html(badge)
        json_path = write_status_badge_json(badge)
        html_path = write_status_badge_html(html)
        print(f"status badge generated: {json_path}")
        print(f"status badge fragment generated: {html_path}")
        return 0
    except Exception as exc:
        print(f"status badge build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())