from __future__ import annotations

import sys

from reporting.ops_gui_bundle_builder import build_ops_gui_bundle_manifest
from reporting.ops_gui_bundle_writer import write_ops_gui_bundle_manifest_json


def main() -> int:
    try:
        payload = build_ops_gui_bundle_manifest()
        output_path = write_ops_gui_bundle_manifest_json(payload)
        print(f"ops gui bundle manifest generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops gui bundle manifest build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())