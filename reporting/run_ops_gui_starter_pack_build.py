from __future__ import annotations

import argparse
from pathlib import Path

from reporting.ops_gui_starter_pack_writer import write_ops_gui_starter_pack


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build GUI implementation starter pack JSON for onboarding and handoff."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to data/reports.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    output_path = write_ops_gui_starter_pack(output_dir=args.output_dir) if args.output_dir else write_ops_gui_starter_pack()
    print(f"[ops_gui_starter_pack] wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
