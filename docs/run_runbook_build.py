from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs.runbook_builder import build_runbook_markdown
from docs.runbook_writer import DEFAULT_RUNBOOK_PATH, write_runbook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用 Runbook を自動生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RUNBOOK_PATH,
        help=f"出力先 markdown (デフォルト: {DEFAULT_RUNBOOK_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        markdown = build_runbook_markdown()
        path = write_runbook(markdown, output_path=args.output)
        print(f"runbook written: {path}")
        print("sections:")
        print("- 日常点検")
        print("- 運用サイクル実行")
        print("- 異常検知確認")
        print("- retry queue 確認")
        print("- 日次レポート確認")
        print("- 月次レポート確認")
        print("- アーカイブ確認")
        print("- 復旧一次確認")
        return 0
    except Exception as exc:
        print(f"runbook build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
