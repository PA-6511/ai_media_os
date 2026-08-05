from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.repositories.import_repository import ImportRepository


@dataclass
class CsvImportSummary:
    input_path: str
    processed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    offer_created: int = 0
    offer_updated: int = 0
    offer_unchanged: int = 0
    failed: int = 0


class CsvImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ImportRepository(session)

    def import_file(
        self,
        input_path: Path,
        *,
        dry_run: bool = True,
        commit: bool = True,
    ) -> CsvImportSummary:
        if not input_path.exists():
            raise FileNotFoundError(input_path)

        summary = CsvImportSummary(input_path=str(input_path))

        with input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise ValueError("CSV header is missing")

            for row_number, row in enumerate(reader, start=2):
                try:
                    result = self.repository.import_row(row)
                    summary.processed += 1
                    summary.created += int(result.created)
                    summary.updated += int(result.updated)
                    summary.unchanged += int(result.unchanged)
                    summary.offer_created += int(result.offer_created)
                    summary.offer_updated += int(result.offer_updated)
                    summary.offer_unchanged += int(
                        result.offer_unchanged
                    )
                except Exception as exc:
                    summary.failed += 1
                    raise ValueError(
                        f"CSV import failed at row {row_number}: {exc}"
                    ) from exc

        if dry_run:
            self.session.rollback()
        elif commit:
            self.session.commit()

        return summary
