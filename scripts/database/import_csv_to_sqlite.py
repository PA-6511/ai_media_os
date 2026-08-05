from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.db.config import DATABASE_BACKEND
from app.db.session import SessionLocal
from app.services.csv_import_service import CsvImportService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import ebook CSV data into the operational database."
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="CSV file to import",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Commit changes. Default is DRY_RUN.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if DATABASE_BACKEND != "sqlite":
        raise RuntimeError(
            "SQL-B1 currently permits SQLite only. "
            f"Current backend: {DATABASE_BACKEND}"
        )

    with SessionLocal() as session:
        service = CsvImportService(session)
        summary = service.import_file(
            args.input_csv,
            dry_run=not args.execute,
        )

    payload = {
        "status": "PASS",
        "mode": "EXECUTE" if args.execute else "DRY_RUN",
        "database_backend": DATABASE_BACKEND,
        **asdict(summary),
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
