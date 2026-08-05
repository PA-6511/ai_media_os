#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="電子書籍1件の書誌情報を安全にプレビュー／補完します。"
    )
    parser.add_argument("--ebook-item-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-ebook-item-id")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=REPOSITORY_ROOT / "exchange" / "logs" / "ebook_metadata_autofill",
    )
    return parser


def _serialize(
    preview: object,
    evidence: dict[str, object],
    evidence_path: Path,
) -> str:
    return json.dumps(
        {
            "ebook_item_id": preview.ebook_item_id,
            "operation": preview.operation,
            "dry_run": preview.dry_run,
            "metadata_status": preview.metadata_status,
            "apply_possible": preview.apply_possible,
            "field_results": [
                asdict(result) for result in preview.field_results
            ],
            "evidence_path": str(evidence_path),
            "external_communication_attempted": evidence[
                "external_communication_attempted"
            ],
            "wordpress_update_attempted": evidence[
                "wordpress_update_attempted"
            ],
            "database_update_attempted": evidence[
                "database_update_attempted"
            ],
            "database_update_succeeded": evidence[
                "database_update_succeeded"
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ebook_item_id = args.ebook_item_id.strip()
    if not ebook_item_id:
        raise SystemExit("--ebook-item-id must not be empty")
    if args.execute and args.confirm_ebook_item_id != ebook_item_id:
        raise SystemExit(
            "--confirm-ebook-item-id must exactly match --ebook-item-id"
        )

    from app.services.ebook_metadata_autofill_service import (
        EbookMetadataAutofillService,
        build_evidence,
        write_evidence,
    )

    changed_by = (
        "human:cli_metadata_autofill"
        if args.execute
        else "system:cli_metadata_autofill_dry_run"
    )
    if args.execute:
        from app.db.session import SessionLocal

        preview = None
        result = None
        service = None
        try:
            with SessionLocal() as session:
                service = EbookMetadataAutofillService(session)
                preview = service.preview(ebook_item_id)
                result = service.apply(
                    ebook_item_id=ebook_item_id,
                    confirmed_fingerprint=preview.fingerprint,
                    changed_by=changed_by,
                )
                session.commit()
        except Exception:
            if preview is not None:
                database_update_attempted = bool(
                    service and service.database_update_attempted
                )
                failed_result = result or replace(
                    preview,
                    operation="APPLY",
                    dry_run=False,
                )
                failed_evidence = build_evidence(
                    failed_result,
                    database_update_attempted=database_update_attempted,
                    database_update_succeeded=False,
                    changed_by=changed_by,
                )
                write_evidence(failed_evidence, args.evidence_dir)
            raise
        if result is None or service is None:  # pragma: no cover
            raise RuntimeError("apply completed without a result")
        evidence = build_evidence(
            result,
            database_update_attempted=service.database_update_attempted,
            database_update_succeeded=True,
            changed_by=changed_by,
        )
    else:
        from app.db.read_only_session import ReadOnlySessionLocal

        with ReadOnlySessionLocal() as session:
            result = EbookMetadataAutofillService(session).preview(
                ebook_item_id
            )
        evidence = build_evidence(
            result,
            database_update_attempted=False,
            database_update_succeeded=False,
            changed_by=changed_by,
        )

    evidence_path = write_evidence(evidence, args.evidence_dir)
    print(_serialize(result, evidence, evidence_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
