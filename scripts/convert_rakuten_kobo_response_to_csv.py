from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rakuten_kobo_csv import write_response_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a saved Rakuten Kobo API response to V2 CSV without network access."
    )
    parser.add_argument("response_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--verified-at", required=True)
    args = parser.parse_args(argv)

    response = json.loads(args.response_json.read_text(encoding="utf-8"))
    if not isinstance(response, dict):
        raise ValueError("Rakuten Kobo response root must be an object")
    rows = write_response_csv(
        response,
        output_path=args.output_csv,
        batch_id=args.batch_id,
        verified_at=args.verified_at,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "row_count": len(rows),
                "output_csv": str(args.output_csv),
                "external_network_performed": False,
                "wordpress_write_performed": False,
                "database_write_performed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
