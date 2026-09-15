#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.xnr_roundup_metadata_gate import (  # noqa: E402
    XnrRoundupAuthorization,
    XnrRoundupMetadataGate,
    XnrRoundupMetadataGateError,
    select_roundup_candidates,
)
# DIGEST_FIX1R_SHARED_CONTEXT_PROJECTION_V1
from app.services.xnr_roundup_candidate_projection import (  # noqa: E402
    build_context_candidate_payload,
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise XnrRoundupMetadataGateError(
            "MALFORMED_PUBLIC_SOURCE",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    if not isinstance(value, dict):
        raise XnrRoundupMetadataGateError("MALFORMED_PUBLIC_SOURCE")
    return value


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _emit(payload: dict[str, Any]) -> None:
    print(
        "XNR_METADATA_GATE_RESULT="
        + json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def run(args: argparse.Namespace) -> int:
    def load_selection():
        return select_roundup_candidates(
            build_context_candidate_payload(_read_json(args.public_json)),
            target_date=args.target_date,
            max_items=args.max_items,
        )

    gate = XnrRoundupMetadataGate()
    if args.revalidate:
        authorization = XnrRoundupAuthorization.from_dict(
            _read_json(args.authorization_file)
        )
        selection = load_selection()
        gate.revalidate(selection, authorization)
        _emit(
            {
                "status": "PASS",
                "phase": "PRE_WORDPRESS_REVALIDATION",
                "candidate_ids": list(selection.candidate_ids),
                "item_count": selection.item_count,
                "wordpress_write_authorized": True,
                "public_source_evaluated": True,
            }
        )
        return 0

    selection = load_selection()
    authorization = gate.authorize(selection)
    _atomic_write(args.authorization_file, authorization.to_dict())
    _emit(
        {
            "status": "PASS",
            "phase": "INITIAL_AUTHORIZATION",
            "candidate_ids": list(selection.candidate_ids),
            "item_count": selection.item_count,
            "wordpress_write_authorized": False,
            "public_source_evaluated": True,
        }
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-json", required=True, type=Path)
    parser.add_argument("--date", dest="target_date", required=True)
    parser.add_argument("--max-items", required=True, type=int)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--revalidate", action="store_true")
    args = parser.parse_args()
    if args.max_items < 1 or args.max_items > 200:
        error = XnrRoundupMetadataGateError(
            "INVALID_MAX_ITEMS",
            detail="max-items must be between 1 and 200",
        )
        _emit(error.to_dict())
        return 40
    try:
        return run(args)
    except XnrRoundupMetadataGateError as exc:
        _emit(exc.to_dict())
        return 40
    except Exception as exc:
        error = XnrRoundupMetadataGateError(
            "METADATA_GATE_UNAVAILABLE",
            detail=f"{type(exc).__name__}: {exc}",
        )
        _emit(error.to_dict())
        return 40


if __name__ == "__main__":
    raise SystemExit(main())
