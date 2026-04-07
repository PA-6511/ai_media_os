from __future__ import annotations

import sys

from reporting.mock_server_operational_check_builder import (
    build_mock_server_operational_check,
)
from reporting.mock_server_operational_check_writer import (
    write_mock_server_operational_check_json,
)


def main() -> int:
    try:
        payload = build_mock_server_operational_check()
        output_path = write_mock_server_operational_check_json(payload)

        status = payload.get("status", "FAIL")
        summary = payload.get("summary", {})
        pass_count = summary.get("pass_count", 0)
        total_checks = summary.get("total_checks", 0)
        target_base_url = payload.get("target_base_url") or "n/a"

        print(f"mock server operational check: {status}")
        print(f"output: {output_path}")
        print(f"target: {target_base_url}")
        print(f"checks: {pass_count}/{total_checks} passed")

        for check in payload.get("checks", []):
            name = check.get("name", "unknown")
            ok = bool(check.get("ok", False))
            detail = check.get("detail", "")
            marker = "[OK]" if ok else "[NG]"
            print(f"{marker} {name}: {detail}")

        return 0 if status == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        print(f"mock server operational check failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
