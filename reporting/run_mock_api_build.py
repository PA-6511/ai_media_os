from __future__ import annotations

import sys

from reporting.mock_api_builder import build_mock_api_home
from reporting.mock_api_writer import write_mock_api_home_json


def main() -> int:
    try:
        payload = build_mock_api_home()
        output_path = write_mock_api_home_json(payload)
        print(f"mock api home generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"mock api home build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())