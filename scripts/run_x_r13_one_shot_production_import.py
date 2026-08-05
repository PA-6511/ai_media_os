from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.csv_import_service import CsvImportService
from scripts.build_x_r9_preflight_approval_pack import canonical_digest


class RunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunPaths:
    policy: Path
    gate_pack: Path
    approval_certificate: Path
    database: Path
    execution_claim: Path
    result_pack: Path
    report: Path
    consumption_lock: Path

    @property
    def completion_lock(self) -> Path:
        return self.consumption_lock.with_name(
            self.consumption_lock.stem
            + ".completion.json"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise RunnerError(
            f"required JSON does not exist: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise RunnerError(
            f"JSON root must be an object: {path}"
        )

    return value


def validate_digest(
    value: dict[str, Any],
    field: str,
    label: str,
) -> str:
    recorded = value.get(field)

    if not isinstance(recorded, str) or not recorded:
        raise RunnerError(
            f"{label} digest is missing: {field}"
        )

    payload = {
        key: item
        for key, item in value.items()
        if key != field
    }

    calculated = canonical_digest(payload)

    if calculated != recorded:
        raise RunnerError(
            f"{label} digest mismatch: "
            f"recorded={recorded} "
            f"calculated={calculated}"
        )

    return recorded


def atomic_create(
    path: Path,
    content: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise RunnerError(
            f"output already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, content)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    atomic_create(
        path,
        (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )


def atomic_create_text(
    path: Path,
    value: str,
) -> None:
    atomic_create(
        path,
        value.encode("utf-8"),
    )


def inspect_database(
    database_path: Path,
    *,
    source_name: str,
    source_item_id: str,
    store_item_id: str,
) -> dict[str, Any]:
    connection = sqlite3.connect(
        f"file:{database_path}?mode=ro",
        uri=True,
    )

    try:
        connection.execute(
            "PRAGMA query_only = ON"
        )

        integrity_check = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_failure_count = len(
            connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        )

        source_identity_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM ebook_items
            WHERE source_name = ?
              AND source_item_id = ?
            """,
            (
                source_name,
                source_item_id,
            ),
        ).fetchone()[0]

        store_item_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM store_offers
            WHERE store_item_id = ?
            """,
            (store_item_id,),
        ).fetchone()[0]

        return {
            "integrity_check": integrity_check,
            "foreign_key_failure_count": (
                foreign_key_failure_count
            ),
            "source_identity_count": (
                source_identity_count
            ),
            "store_item_count": store_item_count,
        }

    finally:
        connection.close()


def validate_policy(
    policy: dict[str, Any],
) -> None:
    if (
        policy.get("phase")
        != "X-R13-ONE-SHOT-PRODUCTION-IMPORT-POLICY"
    ):
        raise RunnerError("policy phase mismatch")

    if policy.get("execution_default") != "BLOCKED":
        raise RunnerError(
            "policy execution default must be BLOCKED"
        )

    safety = policy.get("safety")

    if not isinstance(safety, dict):
        raise RunnerError(
            "policy safety contract is missing"
        )

    for key in (
        "automatic_retry_allowed",
        "reexecution_allowed",
        "approval_reuse_allowed",
        "manual_raw_sql_allowed",
        "temporary_database_copy_allowed",
        "x_r11_runner_reexecution_allowed",
        "external_api_call_allowed",
        "credential_read_allowed",
    ):
        if safety.get(key) is not False:
            raise RunnerError(
                f"unsafe policy value: {key}"
            )

    if safety.get("candidate_count_limit") != 1:
        raise RunnerError(
            "policy candidate limit must be one"
        )


def validate_gate(
    gate: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    runtime = policy.get("runtime_contract")

    if not isinstance(runtime, dict):
        raise RunnerError(
            "runtime contract is missing"
        )

    digest_field = runtime.get(
        "gate_digest_field"
    )

    if not isinstance(digest_field, str):
        raise RunnerError(
            "gate digest field is missing"
        )

    gate_digest = validate_digest(
        gate,
        digest_field,
        "production import gate",
    )

    expected_digest = policy.get(
        "source_binding",
        {},
    ).get(
        "production_import_gate_digest_sha256"
    )

    if gate_digest != expected_digest:
        raise RunnerError(
            "gate digest is not policy-bound"
        )

    if (
        gate.get("status")
        != runtime.get("required_gate_status")
    ):
        raise RunnerError("gate status mismatch")

    if (
        gate.get("gate_state")
        != runtime.get("required_gate_state")
    ):
        raise RunnerError("gate state mismatch")

    current_state = gate.get("current_state")

    if not isinstance(current_state, dict):
        raise RunnerError(
            "gate current state is missing"
        )

    if (
        current_state.get(
            "production_import_executed"
        )
        is not False
    ):
        raise RunnerError(
            "gate already records import execution"
        )

    return gate_digest


def validate_approval(
    approval: dict[str, Any],
    policy: dict[str, Any],
    gate_digest: str,
) -> tuple[str, dict[str, str]]:
    runtime = policy["runtime_contract"]

    digest_field = runtime.get(
        "approval_digest_field"
    )

    if not isinstance(digest_field, str):
        raise RunnerError(
            "approval digest field is missing"
        )

    approval_digest = validate_digest(
        approval,
        digest_field,
        "production import execution approval",
    )

    if (
        approval.get("status")
        != runtime.get(
            "required_approval_status"
        )
    ):
        raise RunnerError(
            "approval status mismatch"
        )

    if (
        approval.get("approval_state")
        != runtime.get(
            "required_approval_state"
        )
    ):
        raise RunnerError(
            "approval state mismatch"
        )

    source_binding = approval.get(
        "source_binding"
    )

    if not isinstance(source_binding, dict):
        raise RunnerError(
            "approval source binding is missing"
        )

    if (
        source_binding.get(
            "gate_digest_sha256"
        )
        != gate_digest
    ):
        raise RunnerError(
            "approval is not bound to the gate"
        )

    permissions = approval.get("permissions")

    if not isinstance(permissions, dict):
        raise RunnerError(
            "approval permissions are missing"
        )

    for key in (
        "gate_open_for_this_execution",
        "production_import_execution_allowed",
        "production_database_write_allowed",
        "candidate_binding_allowed",
        "candidate_import_allowed",
        "single_candidate_only",
    ):
        if permissions.get(key) is not True:
            raise RunnerError(
                f"required approval permission "
                f"is false: {key}"
            )

    for key in (
        "approval_reuse_allowed",
        "automatic_retry_allowed",
        "x_r11_runner_reexecution_allowed",
        "manual_raw_sql_runner_allowed",
        "temporary_database_copy_allowed",
        "external_api_call_allowed",
        "credential_read_allowed",
    ):
        if permissions.get(key) is not False:
            raise RunnerError(
                f"unsafe approval permission: {key}"
            )

    state = approval.get("current_state")

    if not isinstance(state, dict):
        raise RunnerError(
            "approval current state is missing"
        )

    if (
        state.get(
            "production_import_approval_issued"
        )
        is not True
    ):
        raise RunnerError(
            "production import approval is not issued"
        )

    if (
        state.get("human_approval_consumed")
        is not False
    ):
        raise RunnerError(
            "approval is already consumed"
        )

    if (
        state.get("production_import_executed")
        is not False
    ):
        raise RunnerError(
            "approval already records execution"
        )

    candidate = approval.get("candidate")

    if not isinstance(candidate, dict):
        raise RunnerError(
            "approval candidate is missing"
        )

    row = candidate.get(
        "canonical_import_row"
    )

    if not isinstance(row, dict):
        raise RunnerError(
            "canonical import row is missing"
        )

    normalized_row = {
        str(key): (
            ""
            if value is None
            else str(value)
        )
        for key, value in row.items()
    }

    return approval_digest, normalized_row


def validate_candidate_row(
    row: dict[str, str],
    policy: dict[str, Any],
) -> None:
    expected = policy.get("candidate")

    if not isinstance(expected, dict):
        raise RunnerError(
            "policy candidate contract is missing"
        )

    required_values = {
        "source_name": (
            expected.get("source_name")
        ),
        "source_item_id": (
            expected.get("store_item_id")
        ),
        "title": expected.get("title"),
        "volume_label": (
            expected.get("volume_label")
        ),
        "item_type": expected.get("item_type"),
        "store_name": (
            expected.get("store_name")
        ),
        "store_item_id": (
            expected.get("store_item_id")
        ),
    }

    for key, expected_value in (
        required_values.items()
    ):
        if row.get(key) != expected_value:
            raise RunnerError(
                f"candidate field mismatch: {key}: "
                f"expected={expected_value!r} "
                f"actual={row.get(key)!r}"
            )

    for key in (
        "author_name",
        "publisher_name",
        "release_date",
        "product_url",
        "affiliate_url",
    ):
        if not row.get(key):
            raise RunnerError(
                f"required candidate field "
                f"is empty: {key}"
            )


def ensure_outputs_absent(
    paths: RunPaths,
) -> None:
    for path in (
        paths.execution_claim,
        paths.result_pack,
        paths.report,
        paths.consumption_lock,
        paths.completion_lock,
    ):
        if path.exists():
            raise RunnerError(
                f"one-shot output already exists: "
                f"{path}"
            )


def check_nonempty_wal(
    database_path: Path,
) -> None:
    wal_path = Path(
        str(database_path) + "-wal"
    )

    if (
        wal_path.exists()
        and wal_path.stat().st_size > 0
    ):
        raise RunnerError(
            f"database has a non-empty WAL "
            f"file: {wal_path}"
        )


def duplicate_preflight(
    database_path: Path,
    row: dict[str, str],
) -> None:
    state = inspect_database(
        database_path,
        source_name=row["source_name"],
        source_item_id=row["source_item_id"],
        store_item_id=row["store_item_id"],
    )

    if state["integrity_check"] != "ok":
        raise RunnerError(
            "database integrity check failed"
        )

    if (
        state["foreign_key_failure_count"]
        != 0
    ):
        raise RunnerError(
            "database foreign-key check failed"
        )

    if (
        state["source_identity_count"]
        != 0
    ):
        raise RunnerError(
            "duplicate source identity detected"
        )

    if state["store_item_count"] != 0:
        raise RunnerError(
            "duplicate store item detected"
        )


def write_candidate_csv(
    path: Path,
    row: dict[str, str],
) -> None:
    fieldnames = [
        "source_name",
        "source_item_id",
        "title",
        "normalized_title",
        "volume_label",
        "author_name",
        "publisher_name",
        "release_date",
        "item_type",
        "store_name",
        "store_item_id",
        "product_url",
        "affiliate_url",
        "price_yen",
        "discount_rate",
        "point_rate",
    ]

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerow(
            {
                key: row.get(key, "")
                for key in fieldnames
            }
        )


def run_import(
    paths: RunPaths,
) -> dict[str, Any]:
    for path in (
        paths.policy,
        paths.gate_pack,
        paths.approval_certificate,
        paths.database,
    ):
        if not path.is_file():
            raise RunnerError(
                f"required input does not exist: "
                f"{path}"
            )

    ensure_outputs_absent(paths)
    check_nonempty_wal(paths.database)

    policy = load_json(paths.policy)

    policy_digest = validate_digest(
        policy,
        "policy_digest_sha256",
        "X-R13 production import policy",
    )

    validate_policy(policy)

    gate = load_json(paths.gate_pack)

    gate_digest = validate_gate(
        gate,
        policy,
    )

    approval = load_json(
        paths.approval_certificate
    )

    approval_digest, row = (
        validate_approval(
            approval,
            policy,
            gate_digest,
        )
    )

    validate_candidate_row(
        row,
        policy,
    )

    expected_database_sha = approval.get(
        "source_binding",
        {},
    ).get(
        "production_database_sha256"
    )

    database_sha_before = sha256_file(
        paths.database
    )

    if (
        database_sha_before
        != expected_database_sha
    ):
        raise RunnerError(
            "production database SHA does not "
            "match the approval binding"
        )

    duplicate_preflight(
        paths.database,
        row,
    )

    approval_id = approval.get("approval_id")

    if (
        not isinstance(approval_id, str)
        or not approval_id
    ):
        raise RunnerError(
            "approval ID is missing"
        )

    claimed_at = datetime.now(
        timezone.utc
    ).isoformat()

    claim_payload = {
        "phase": (
            "X-R13-ONE-SHOT-PRODUCTION-"
            "IMPORT-EXECUTION-CLAIM"
        ),
        "claim_state": "CLAIMED",
        "claimed_at": claimed_at,
        "approval_id": approval_id,
        "policy_digest_sha256": (
            policy_digest
        ),
        "gate_digest_sha256": gate_digest,
        "approval_digest_sha256": (
            approval_digest
        ),
        "database_sha256_before": (
            database_sha_before
        ),
        "candidate": {
            "source_name": (
                row["source_name"]
            ),
            "source_item_id": (
                row["source_item_id"]
            ),
            "store_item_id": (
                row["store_item_id"]
            ),
            "display_title": (
                f"{row['title']} "
                f"{row['volume_label']}"
            ),
        },
        "reexecution_allowed": False,
        "production_status": "NO_GO",
    }

    claim = {
        **claim_payload,
        "claim_digest_sha256": (
            canonical_digest(
                claim_payload
            )
        ),
    }

    atomic_create_json(
        paths.execution_claim,
        claim,
    )

    consumption_payload = {
        "phase": (
            "X-R13-ONE-SHOT-PRODUCTION-"
            "IMPORT-APPROVAL-CONSUMPTION"
        ),
        "approval_id": approval_id,
        "approval_digest_sha256": (
            approval_digest
        ),
        "claim_digest_sha256": (
            claim["claim_digest_sha256"]
        ),
        "approval_consumed": True,
        "approval_reuse_allowed": False,
        "automatic_retry_allowed": False,
        "reexecution_allowed": False,
        "production_import_executed": False,
        "production_status": "NO_GO",
    }

    consumption = {
        **consumption_payload,
        "consumption_digest_sha256": (
            canonical_digest(
                consumption_payload
            )
        ),
    }

    atomic_create_json(
        paths.consumption_lock,
        consumption,
    )

    engine = create_engine(
        f"sqlite+pysqlite:///"
        f"{paths.database}",
        future=True,
    )

    try:
        with tempfile.TemporaryDirectory(
            prefix="x_r13_one_shot_import_"
        ) as temporary_directory:
            csv_path = (
                Path(temporary_directory)
                / "candidate.csv"
            )

            write_candidate_csv(
                csv_path,
                row,
            )

            with Session(engine) as session:
                try:
                    summary = (
                        CsvImportService(
                            session
                        ).import_file(
                            csv_path,
                            dry_run=False,
                        )
                    )
                except Exception:
                    session.rollback()
                    raise

                summary_dict = asdict(
                    summary
                )

    finally:
        engine.dispose()

    expected_summary = {
        "processed": 1,
        "created": 1,
        "updated": 0,
        "offer_created": 1,
        "offer_updated": 0,
        "failed": 0,
    }

    for key, expected_value in (
        expected_summary.items()
    ):
        if (
            summary_dict.get(key)
            != expected_value
        ):
            raise RunnerError(
                f"unexpected import summary: "
                f"{key}: "
                f"expected={expected_value} "
                f"actual={summary_dict.get(key)}"
            )

    post_state = inspect_database(
        paths.database,
        source_name=row["source_name"],
        source_item_id=row["source_item_id"],
        store_item_id=row["store_item_id"],
    )

    if (
        post_state["source_identity_count"]
        != 1
    ):
        raise RunnerError(
            "post-write source identity "
            "count is not one"
        )

    if post_state["store_item_count"] != 1:
        raise RunnerError(
            "post-write store item count "
            "is not one"
        )

    if (
        post_state[
            "foreign_key_failure_count"
        ]
        != 0
    ):
        raise RunnerError(
            "post-write foreign-key "
            "check failed"
        )

    if post_state["integrity_check"] != "ok":
        raise RunnerError(
            "post-write integrity check failed"
        )

    database_sha_after = sha256_file(
        paths.database
    )

    result_payload = {
        "phase": (
            "X-R13-ONE-SHOT-"
            "PRODUCTION-IMPORT"
        ),
        "status": (
            "PASS_X_R13_MEDALIST_15_"
            "ONE_SHOT_PRODUCTION_IMPORT_"
            "EXECUTED"
        ),
        "decision": (
            "READY_X_R13_FOR_POST_IMPORT_"
            "HUMAN_REVIEW"
        ),
        "approval_id": approval_id,
        "policy_digest_sha256": (
            policy_digest
        ),
        "gate_digest_sha256": gate_digest,
        "approval_digest_sha256": (
            approval_digest
        ),
        "claim_digest_sha256": (
            claim["claim_digest_sha256"]
        ),
        "consumption_digest_sha256": (
            consumption[
                "consumption_digest_sha256"
            ]
        ),
        "candidate": {
            "source_name": (
                row["source_name"]
            ),
            "source_item_id": (
                row["source_item_id"]
            ),
            "store_name": (
                row["store_name"]
            ),
            "store_item_id": (
                row["store_item_id"]
            ),
            "display_title": (
                f"{row['title']} "
                f"{row['volume_label']}"
            ),
            "item_type": row["item_type"],
        },
        "summary": summary_dict,
        "database_sha256_before": (
            database_sha_before
        ),
        "database_sha256_after": (
            database_sha_after
        ),
        "post_write_verification": (
            post_state
        ),
        "approval_consumed": True,
        "approval_reuse_allowed": False,
        "reexecution_allowed": False,
        "production_import_executed": True,
        "candidate_bound": True,
        "candidate_imported": True,
        "external_api_call": False,
        "credential_read": False,
        "production_status": "NO_GO",
    }

    result = {
        **result_payload,
        "result_digest_sha256": (
            canonical_digest(
                result_payload
            )
        ),
    }

    atomic_create_json(
        paths.result_pack,
        result,
    )

    report_text = "\n".join(
        [
            "# X-R13 One-shot Production Import Result",
            "",
            f"- Status: `{result['status']}`",
            "- Candidate: `メダリスト 第15巻`",
            "- Processed: `1`",
            "- Created: `1`",
            "- Offer created: `1`",
            "- Foreign-key check: `PASS`",
            "- Integrity check: `PASS`",
            "- Approval consumed: `true`",
            "- Reexecution allowed: `false`",
            "- Production status: `NO_GO`",
            "",
            (
                "- Result digest: "
                f"`{result['result_digest_sha256']}`"
            ),
            "",
        ]
    )

    atomic_create_text(
        paths.report,
        report_text,
    )

    completion_payload = {
        "phase": (
            "X-R13-ONE-SHOT-PRODUCTION-"
            "IMPORT-COMPLETION"
        ),
        "approval_id": approval_id,
        "claim_digest_sha256": (
            claim["claim_digest_sha256"]
        ),
        "consumption_digest_sha256": (
            consumption[
                "consumption_digest_sha256"
            ]
        ),
        "result_digest_sha256": (
            result["result_digest_sha256"]
        ),
        "execution_completed": True,
        "completion_authority": (
            "RESULT_PACK_AND_"
            "CONSUMPTION_LOCK"
        ),
        "approval_consumed": True,
        "approval_reuse_allowed": False,
        "reexecution_allowed": False,
        "candidate_bound": True,
        "candidate_imported": True,
        "production_status": "NO_GO",
    }

    completion = {
        **completion_payload,
        "completion_digest_sha256": (
            canonical_digest(
                completion_payload
            )
        ),
    }

    atomic_create_json(
        paths.completion_lock,
        completion,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execute one gate-bound X-R13 "
            "production import. Execution "
            "remains blocked unless every "
            "immutable approval and database "
            "precondition passes."
        )
    )

    parser.add_argument(
        "--policy",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--gate-pack",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--approval-certificate",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--database",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--execution-claim",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--result-pack",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--report",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--consumption-lock",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    paths = RunPaths(
        policy=args.policy.resolve(),
        gate_pack=args.gate_pack.resolve(),
        approval_certificate=(
            args.approval_certificate.resolve()
        ),
        database=args.database.resolve(),
        execution_claim=(
            args.execution_claim.resolve()
        ),
        result_pack=(
            args.result_pack.resolve()
        ),
        report=args.report.resolve(),
        consumption_lock=(
            args.consumption_lock.resolve()
        ),
    )

    try:
        result = run_import(paths)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": (
                        "HOLD_X_R13_ONE_SHOT_"
                        "IMPORT_FAILED"
                    ),
                    "error_type": (
                        type(exc).__name__
                    ),
                    "error": str(exc),
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result["decision"],
                "candidate": result[
                    "candidate"
                ],
                "summary": result["summary"],
                "result_digest_sha256": (
                    result[
                        "result_digest_sha256"
                    ]
                ),
                "production_status": "NO_GO",
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
