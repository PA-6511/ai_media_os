from __future__ import annotations

import sys

from reporting.ops_cards_builder import build_ops_cards
from reporting.ops_cards_writer import write_ops_cards_json


def main() -> int:
    try:
        cards = build_ops_cards()
        output_path = write_ops_cards_json(cards)
        print(f"ops cards generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops cards build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())