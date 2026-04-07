from __future__ import annotations

import sys

from reporting.ops_manifest_builder import build_ops_manifest
from reporting.ops_manifest_writer import write_ops_manifest_json


def main() -> int:
    try:
        manifest = build_ops_manifest()
        output_path = write_ops_manifest_json(manifest)
        print(f"ops manifest generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops manifest build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())