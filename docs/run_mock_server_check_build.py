from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docs.mock_server_check_builder import build_mock_server_check_markdown
from docs.mock_server_check_writer import DEFAULT_OUTPUT_PATH, write_mock_server_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mock server 確認手順 Markdown を生成する"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"出力先 Markdown ファイル (デフォルト: {DEFAULT_OUTPUT_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        markdown = build_mock_server_check_markdown()
        path = write_mock_server_check(markdown, output_path=args.output)
        print(f"mock_server_check written: {path}")
        print("sections:")
        print("- よくある誤操作（やってはいけないこと）")
        print("- 方法 1: Foreground 起動")
        print("- 方法 2: Background 起動")
        print("- 確認観点チェックリスト")
        print("- ポート競合が起きた場合")
        print("- トラブルシュート")
        print("- 関連ファイル")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"mock_server_check build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
