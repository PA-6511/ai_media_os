from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R13-PRE-POST-SLACK-"
    "APPROVAL-FLOW-PREP"
)

STATUS = (
    "PASS_X_R13_PRE_POST_SLACK_"
    "APPROVAL_FLOW_PREP_READY"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_CLOSEOUT_DIGEST = (
    "cfe0a6bb934d5ced22ce1d46c41c03b6"
    "6bb7edc682aac4bf7c788ef216652574"
)

EXPECTED_REVIEW_DIGEST = (
    "f841e1f7845c4bcb883b1710031b7266"
    "b3c3c01063471fb6873635a4fe7ce90b"
)

EXPECTED_INDEX_SHA = (
    "f9357785b1d7a8390d4da2845f1f219f"
    "263620223c2a1ee4d116bde5c1299d13"
)

EXPECTED_X_R12_ENTRY_NAME = (
    "x_r12_slack_draft_review_"
    "closeout_evidence_pack"
)

EXPECTED_X_R12_ENTRY_PATH = (
    "exchange/diagnostics/x_draft_module/"
    "x_r12_closeout_evidence_index_registration/"
    "20260718T142742Z-136310/"
    "x_r12_closeout_evidence_index_"
    "registration_result.json"
)

EXPECTED_FLOW_ORDER = [
    "LOCAL_DRAFT_GENERATED",
    "LOCAL_DRAFT_VALIDATED",
    "SLACK_ONE_SHOT_DELIVERY_APPROVED",
    "SLACK_MESSAGE_SENT",
    "HUMAN_THREAD_REVIEW",
    "MANUAL_REVIEW_RESULT_REGISTERED",
    "PRE_POST_POSTING_AUTHORIZATION_ISSUED",
    "HUMAN_MANUAL_X_POST",
    "X_POST_URL_REGISTERED",
    "METRICS_CAPTURE",
]

EXPECTED_BINDINGS = {
    "review_request_id",
    "x_account_handle",
    "draft_text_sha256",
    "affiliate_url",
    "store",
    "link_route",
}

FORBIDDEN_SECRET_FRAGMENTS = (
    "hooks.slack.com/services/",
    "xoxb-",
    "xapp-",
)


class Xr13PrepError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise Xr13PrepError(message)


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
    require(
        path.is_file(),
        f"JSON file missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise Xr13PrepError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise Xr13PrepError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_text(
    path: Path,
    value: str,
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = value.encode("utf-8")

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise Xr13PrepError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify_no_secret(
    value: Any,
    label: str,
) -> None:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
    )

    for fragment in FORBIDDEN_SECRET_FRAGMENTS:
        require(
            fragment not in serialized,
            f"secret material found in {label}",
        )


def validate_policy(
    policy: dict[str, Any],
) -> None:
    require(
        policy.get("schema_version")
        == (
            "X_R13_PRE_POST_SLACK_"
            "APPROVAL_FLOW_POLICY_V1"
        ),
        "policy schema mismatch",
    )

    require(
        policy.get("phase") == PHASE,
        "policy phase mismatch",
    )

    require(
        policy.get("status")
        == "PREP_ONLY_NO_DELIVERY_NO_POSTING",
        "policy status mismatch",
    )

    require(
        policy.get("flow_order")
        == EXPECTED_FLOW_ORDER,
        "flow order mismatch",
    )

    source = policy.get("source_baseline")

    require(
        isinstance(source, dict),
        "source baseline missing",
    )

    require(
        source.get(
            "x_r12_closeout_digest_sha256"
        )
        == EXPECTED_CLOSEOUT_DIGEST,
        "X-R12 closeout binding mismatch",
    )

    require(
        source.get(
            "x_r12_review_result_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "X-R12 review binding mismatch",
    )

    require(
        source.get("evidence_index_sha256")
        == EXPECTED_INDEX_SHA,
        "evidence index binding mismatch",
    )

    delivery = policy.get("delivery")

    require(
        isinstance(delivery, dict),
        "delivery policy missing",
    )

    require(
        delivery.get("transport")
        == "SLACK_INCOMING_WEBHOOK",
        "Slack transport mismatch",
    )

    require(
        delivery.get(
            "credential_read_allowed_in_prep"
        )
        is False,
        "Prep permits credential read",
    )

    require(
        delivery.get(
            "slack_api_call_allowed_in_prep"
        )
        is False,
        "Prep permits Slack API call",
    )

    require(
        delivery.get(
            "message_send_allowed_in_prep"
        )
        is False,
        "Prep permits Slack delivery",
    )

    require(
        delivery.get(
            "one_shot_delivery_required"
        )
        is True,
        "one-shot delivery is not required",
    )

    require(
        delivery.get(
            "automatic_retry_allowed"
        )
        is False,
        "delivery permits automatic retry",
    )

    review = policy.get("review")

    require(
        isinstance(review, dict),
        "review policy missing",
    )

    require(
        review.get("exact_tokens")
        == [
            "APPROVE",
            "REVISE",
            "REJECT",
        ],
        "review tokens mismatch",
    )

    require(
        review.get(
            "pre_post_approval_required"
        )
        is True,
        "pre-post approval not required",
    )

    require(
        review.get(
            "retrospective_approval_is_normal_path"
        )
        is False,
        "retrospective approval remains normal path",
    )

    require(
        review.get(
            "reaction_only_approval_allowed"
        )
        is False,
        "reaction-only approval is allowed",
    )

    binding = policy.get(
        "approval_binding"
    )

    require(
        isinstance(binding, dict),
        "approval binding missing",
    )

    require(
        set(binding.get("required_fields", []))
        == EXPECTED_BINDINGS,
        "approval bindings mismatch",
    )

    for key in (
        "invalidate_on_text_change",
        "invalidate_on_url_change",
        "invalidate_on_account_change",
        "invalidate_on_store_change",
        "invalidate_on_link_route_change",
        "posting_authorization_only_after_approve",
        "pre_post_approval",
    ):
        require(
            binding.get(key) is True,
            f"required binding flag false: {key}",
        )

    require(
        binding.get("approved_state")
        == "APPROVED_BEFORE_POSTING",
        "approved state mismatch",
    )

    require(
        binding.get(
            "retroactive_content_review"
        )
        is False,
        "normal flow is marked retrospective",
    )

    posting = policy.get("posting")

    require(
        isinstance(posting, dict),
        "posting policy missing",
    )

    require(
        posting.get("mode")
        == "HUMAN_MANUAL",
        "posting mode mismatch",
    )

    require(
        posting.get(
            "one_manual_x_post_authorized_after_approval"
        )
        is True,
        "one manual post authorization missing",
    )

    for key in (
        "x_api_allowed",
        "browser_automation_allowed",
        "automatic_posting_allowed",
        "additional_x_post_allowed",
    ):
        require(
            posting.get(key) is False,
            f"unsafe posting flag: {key}",
        )

    require(
        posting.get(
            "x_post_url_registration_required"
        )
        is True,
        "post URL registration not required",
    )

    require(
        posting.get("metrics_capture_required")
        is True,
        "metrics capture not required",
    )

    storage = policy.get("storage")

    require(
        isinstance(storage, dict),
        "storage policy missing",
    )

    for key in (
        "database_write_allowed_in_prep",
        "workflow_write_allowed_in_prep",
        "wordpress_write_allowed_in_prep",
    ):
        require(
            storage.get(key) is False,
            f"Prep write enabled: {key}",
        )

    failure = policy.get(
        "failure_policy"
    )

    require(
        isinstance(failure, dict),
        "failure policy missing",
    )

    require(
        failure.get("failure_action")
        == "STOP",
        "failure action mismatch",
    )

    require(
        failure.get(
            "automatic_retry_allowed"
        )
        is False,
        "failure policy permits retry",
    )

    require(
        policy.get("production_status")
        == "NO_GO",
        "production status mismatch",
    )

    verify_no_secret(
        policy,
        "policy",
    )


def validate_closeout(
    closeout: dict[str, Any],
) -> None:
    digest_field = (
        "x_r12_closeout_evidence_index_"
        "registration_digest_sha256"
    )

    require(
        closeout.get(digest_field)
        == EXPECTED_CLOSEOUT_DIGEST,
        "closeout recorded digest mismatch",
    )

    payload = {
        key: value
        for key, value in closeout.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == EXPECTED_CLOSEOUT_DIGEST,
        "closeout canonical digest mismatch",
    )

    require(
        closeout.get("status")
        == (
            "PASS_X_R12_CLOSEOUT_"
            "EVIDENCE_INDEX_REGISTERED"
        ),
        "closeout status mismatch",
    )

    require(
        closeout.get("closeout_state")
        == (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "CLOSED_APPROVED_RETROSPECTIVE"
        ),
        "closeout state mismatch",
    )

    source_review = (
        closeout.get("source_chain", {})
        .get("review_result", {})
    )

    require(
        source_review.get("digest_sha256")
        == EXPECTED_REVIEW_DIGEST,
        "source review digest mismatch",
    )

    terminal = closeout.get(
        "terminal_state"
    )

    require(
        isinstance(terminal, dict),
        "terminal state missing",
    )

    require(
        terminal.get("slack_message_sent")
        is True,
        "Slack delivery was not completed",
    )

    require(
        terminal.get("approval_consumed")
        is True,
        "delivery approval was not consumed",
    )

    require(
        terminal.get("human_review_state")
        == "APPROVED_RETROSPECTIVE",
        "X-R12 review state mismatch",
    )

    require(
        terminal.get("pre_post_approval")
        is False,
        "X-R12 was incorrectly pre-approved",
    )

    require(
        terminal.get(
            "posting_authorization_issued"
        )
        is False,
        "X-R12 posting authorization mismatch",
    )

    require(
        closeout.get("authorized_next_phase")
        == (
            "X-R13-PRE-POST-SLACK-"
            "APPROVAL-FLOW-PREP"
        ),
        "authorized next phase mismatch",
    )

    require(
        closeout.get("production_status")
        == "NO_GO",
        "closeout production status mismatch",
    )

    verify_no_secret(
        closeout,
        "X-R12 closeout",
    )


def validate_evidence_index(
    index: dict[str, Any],
    *,
    actual_sha: str,
) -> None:
    require(
        actual_sha == EXPECTED_INDEX_SHA,
        "evidence index SHA mismatch",
    )

    require(
        isinstance(index.get("schema_version"), str),
        "index schema version missing",
    )

    require(
        isinstance(index.get("entries"), list),
        "index entries missing",
    )

    matching = [
        entry
        for entry in index["entries"]
        if (
            isinstance(entry, dict)
            and entry.get("name")
            == EXPECTED_X_R12_ENTRY_NAME
        )
    ]

    require(
        len(matching) == 1,
        "X-R12 index entry count mismatch",
    )

    entry = matching[0]

    require(
        entry.get("path")
        == EXPECTED_X_R12_ENTRY_PATH,
        "X-R12 index path mismatch",
    )

    require(
        entry.get("status")
        == (
            "PASS_X_R12_CLOSEOUT_"
            "EVIDENCE_INDEX_REGISTERED"
        ),
        "X-R12 index status mismatch",
    )

    verify_no_secret(
        index,
        "evidence index",
    )


def build_prep_payload(
    *,
    policy_path: Path,
    closeout_path: Path,
    evidence_index_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": STATUS,
        "prep_state": (
            "DESIGN_BASELINE_READY_"
            "NO_CANDIDATE_BOUND"
        ),
        "candidate_bound": False,
        "source_baseline": {
            "x_r12_closeout_path": str(
                closeout_path.resolve()
            ),
            "x_r12_closeout_digest_sha256": (
                EXPECTED_CLOSEOUT_DIGEST
            ),
            "x_r12_review_result_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "evidence_index_path": str(
                evidence_index_path.resolve()
            ),
            "evidence_index_sha256": (
                EXPECTED_INDEX_SHA
            ),
            "policy_path": str(
                policy_path.resolve()
            ),
        },
        "target_flow": {
            "approval_timing": "BEFORE_X_POSTING",
            "approved_state": (
                "APPROVED_BEFORE_POSTING"
            ),
            "pre_post_approval": True,
            "retroactive_content_review": False,
            "posting_authorization_after_approve": True,
            "posting_mode": "HUMAN_MANUAL",
            "one_manual_x_post_only": True,
            "x_post_url_registration_required": True,
            "metrics_capture_required": True,
        },
        "change_invalidation": {
            "draft_text_change": True,
            "affiliate_url_change": True,
            "x_account_change": True,
            "store_change": True,
            "link_route_change": True,
        },
        "review_evidence": {
            "slack_thread_exact_token_required": True,
            "manual_screenshot_evidence_required": True,
            "reaction_only_approval_allowed": False,
            "slack_api_read_required": False,
        },
        "safety": {
            "slack_message_sent": False,
            "credential_read": False,
            "slack_api_call": False,
            "x_api_call": False,
            "browser_automation": False,
            "x_post_executed": False,
            "posting_authorization_issued": False,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "automatic_retry_allowed": False,
            "production_status": "NO_GO",
        },
        "report_path": str(
            report_path.resolve()
        ),
        "authorized_next_phase": (
            "X-R13-CANDIDATE-BOUND-"
            "DRAFT-PREP"
        ),
        "production_status": "NO_GO",
    }


def build_report(
    payload: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# X-R13 Pre-Post Slack Approval Flow Prep",
            "",
            f"- Status: `{payload['status']}`",
            f"- State: `{payload['prep_state']}`",
            "- Candidate bound: `false`",
            "",
            "## Standard sequence",
            "",
            "1. Generate and validate a local canonical X draft.",
            "2. Approve and execute one Slack review delivery.",
            "3. Human replies with exact APPROVE, REVISE, or REJECT token.",
            "4. Register screenshot evidence and exact review token.",
            "5. Issue one manual X posting authorization only after APPROVE.",
            "6. Human posts manually to X.",
            "7. Register the resulting X post URL.",
            "8. Capture 24-hour and 7-day metrics.",
            "",
            "## Safety",
            "",
            "- No Slack message was sent.",
            "- No Slack credential was read.",
            "- No X API or browser automation was used.",
            "- No database, workflow, or WordPress write occurred.",
            "- Production status remains `NO_GO`.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--policy",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--x-r12-closeout",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--evidence-index",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--report",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--result-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--generation-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        require(
            sha256_file(args.production_db)
            == EXPECTED_DATABASE_SHA,
            "production database changed",
        )

        policy = load_json(args.policy)

        closeout = load_json(
            args.x_r12_closeout
        )

        evidence_index = load_json(
            args.evidence_index
        )

        validate_policy(policy)
        validate_closeout(closeout)

        validate_evidence_index(
            evidence_index,
            actual_sha=sha256_file(
                args.evidence_index
            ),
        )

        for path in (
            args.report,
            args.result_pack,
            args.generation_lock,
        ):
            require(
                not path.exists(),
                f"output already exists: {path}",
            )

        generated_at = datetime.now(
            timezone.utc
        ).isoformat()

        payload = build_prep_payload(
            policy_path=args.policy,
            closeout_path=(
                args.x_r12_closeout
            ),
            evidence_index_path=(
                args.evidence_index
            ),
            report_path=args.report,
        )

        payload["generated_at"] = (
            generated_at
        )

        result = {
            **payload,
            "x_r13_pre_post_slack_approval_"
            "flow_prep_digest_sha256": (
                canonical_digest(payload)
            ),
        }

        result_digest = result[
            "x_r13_pre_post_slack_approval_"
            "flow_prep_digest_sha256"
        ]

        generation_lock = {
            "lock_type": (
                "X_R13_PRE_POST_SLACK_"
                "APPROVAL_FLOW_PREP_GENERATION"
            ),
            "created_at": generated_at,
            "source_x_r12_closeout_digest_sha256": (
                EXPECTED_CLOSEOUT_DIGEST
            ),
            "prep_result_path": str(
                args.result_pack.resolve()
            ),
            "prep_result_digest_sha256": (
                result_digest
            ),
            "generation_completed": True,
            "reexecution_allowed": False,
            "candidate_bound": False,
            "slack_message_sent": False,
            "posting_authorization_issued": False,
            "x_post_executed": False,
            "database_write": False,
            "production_status": "NO_GO",
        }

        atomic_create_text(
            args.report,
            build_report(result),
        )

        atomic_create_json(
            args.result_pack,
            result,
        )

        atomic_create_json(
            args.generation_lock,
            generation_lock,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_R13_PRE_POST_SLACK_"
                        "APPROVAL_FLOW_PREP"
                    ),
                    "error": str(exc),
                    "slack_message_sent": False,
                    "posting_authorization_issued": False,
                    "x_post_executed": False,
                    "database_write": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "prep_state": (
                    result["prep_state"]
                ),
                "candidate_bound": False,
                "approval_timing": (
                    result["target_flow"][
                        "approval_timing"
                    ]
                ),
                "approved_state": (
                    result["target_flow"][
                        "approved_state"
                    ]
                ),
                "pre_post_approval": True,
                "retroactive_content_review": False,
                "slack_message_sent": False,
                "credential_read": False,
                "posting_authorization_issued": False,
                "x_post_executed": False,
                "database_write": False,
                "production_status": "NO_GO",
                "report_path": str(
                    args.report.resolve()
                ),
                "result_pack_path": str(
                    args.result_pack.resolve()
                ),
                "prep_digest_sha256": (
                    result_digest
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
