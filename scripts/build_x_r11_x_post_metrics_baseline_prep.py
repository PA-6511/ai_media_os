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
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "X-POST-METRICS-BASELINE-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_CORRECTIVE_EVIDENCE_DIGEST = (
    "478a6fb4f766b139da0d30f50884be72"
    "a39a339fe9be9bc7d335075c316007d2"
)

EXPECTED_OLD_APPROVAL_GATE_DIGEST = (
    "ac8fbb29f3d1b0c365c5f6ac22fe54c0"
    "0c956ab308ff4bd7b28a8be3d3f35b08"
)

REVISION = (
    "CORRECTIVE_DIRECT_AFFILIATE_V1"
)

LINK_ROUTE = "DIRECT_AFFILIATE"
STORE = "RAKUTEN_KOBO"

X_POST_ID = "2078417820015333645"

X_POST_URL = (
    "https://x.com/mz_GK7_DM2/"
    "status/2078417820015333645"
)

X_ACCOUNT_HANDLE = "@mz_GK7_DM2"

AFFILIATE_URL = (
    "https://a.r10.to/hPKo3p"
)

CORRECTIVE_TEXT_SHA = (
    "125481ce9a0a1ad8972c2f855e9d2bb5"
    "5f4e3215152ba6ba0fa626e489a81d67"
)

POSTED_AT_UTC = (
    "2026-07-18T09:53:18.084Z"
)

POSTED_AT_JST = (
    "2026-07-18T18:53:18.084+09:00"
)

CAPTURE_24H_DUE_UTC = (
    "2026-07-19T09:53:18.084Z"
)

CAPTURE_24H_DUE_JST = (
    "2026-07-19T18:53:18.084+09:00"
)

CAPTURE_7D_DUE_UTC = (
    "2026-07-25T09:53:18.084Z"
)

CAPTURE_7D_DUE_JST = (
    "2026-07-25T18:53:18.084+09:00"
)

VALID_WINDOWS = {
    "24H": {
        "due_at_utc": CAPTURE_24H_DUE_UTC,
        "due_at_jst": CAPTURE_24H_DUE_JST,
    },
    "7D": {
        "due_at_utc": CAPTURE_7D_DUE_UTC,
        "due_at_jst": CAPTURE_7D_DUE_JST,
    },
}


class XPostMetricsBaselineError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XPostMetricsBaselineError(
            message
        )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise XPostMetricsBaselineError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    require(
        value.get(digest_field)
        == expected_digest,
        f"{label} recorded digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} canonical digest mismatch",
    )


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = (
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
        raise XPostMetricsBaselineError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            data,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_corrective_evidence(
    value: dict[str, Any],
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_manual_posting_corrective_"
            "evidence_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        label="corrective posting evidence",
    )

    require(
        value.get("status")
        == (
            "PASS_X_MANUAL_POSTING_CORRECTIVE_"
            "EVIDENCE_REGISTERED"
        ),
        "corrective evidence status mismatch",
    )

    require(
        value.get("registration_state")
        == (
            "DIRECT_AFFILIATE_POST_RECORDED_"
            "OLD_APPROVAL_SUPERSEDED_"
            "NO_RETROACTIVE_APPROVAL"
        ),
        "corrective evidence state mismatch",
    )

    require(
        value.get("revision")
        == REVISION,
        "corrective revision mismatch",
    )

    require(
        value.get("link_route")
        == LINK_ROUTE,
        "link route mismatch",
    )

    require(
        value.get("store")
        == STORE,
        "store mismatch",
    )

    post = value.get("x_post")

    require(
        isinstance(post, dict),
        "X post evidence is missing",
    )

    require(
        post.get("post_visible")
        is True,
        "X post is not visible",
    )

    require(
        post.get("post_url")
        == X_POST_URL,
        "X post URL mismatch",
    )

    require(
        post.get("post_id")
        == X_POST_ID,
        "X post ID mismatch",
    )

    require(
        post.get("x_account_handle")
        == X_ACCOUNT_HANDLE,
        "X account handle mismatch",
    )

    require(
        post.get("posted_at_utc")
        == POSTED_AT_UTC,
        "X post UTC timestamp mismatch",
    )

    require(
        post.get("posted_at_jst")
        == POSTED_AT_JST,
        "X post JST timestamp mismatch",
    )

    require(
        post.get("affiliate_url")
        == AFFILIATE_URL,
        "affiliate URL mismatch",
    )

    require(
        post.get(
            "affiliate_product_card_visible"
        )
        is True,
        "affiliate product card was not visible",
    )

    transcription = value.get(
        "corrective_transcription"
    )

    require(
        isinstance(transcription, dict),
        "corrective transcription is missing",
    )

    require(
        transcription.get("text_sha256")
        == CORRECTIVE_TEXT_SHA,
        "corrective text SHA mismatch",
    )

    paid = value.get(
        "paid_partnership_evidence"
    )

    require(
        isinstance(paid, dict),
        "paid partnership evidence is missing",
    )

    require(
        paid.get("setting_attested_on")
        is True,
        "paid partnership setting was not attested",
    )

    old_approval = value.get(
        "old_manual_posting_approval"
    )

    require(
        isinstance(old_approval, dict),
        "old approval disposition is missing",
    )

    require(
        old_approval.get("approval_consumed")
        is False,
        "old approval was consumed",
    )

    require(
        old_approval.get("superseded")
        is True,
        "old approval was not superseded",
    )

    require(
        old_approval.get("reuse_allowed")
        is False,
        "old approval remains reusable",
    )

    require(
        value.get(
            "post_execution_evidence_registered"
        )
        is True,
        "post evidence was not registered",
    )

    require(
        value.get("database_write")
        is False,
        "corrective phase wrote to database",
    )

    require(
        value.get("x_api_call")
        is False,
        "corrective phase called X API",
    )

    require(
        value.get(
            "x_post_executed_by_this_phase"
        )
        is False,
        "corrective phase executed an X post",
    )

    require(
        value.get("production_status")
        == "NO_GO",
        "corrective production status mismatch",
    )


def validate_registration_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_MANUAL_X_POSTING_"
            "CORRECTIVE_EVIDENCE_REGISTRATION"
        ),
        "registration lock type mismatch",
    )

    require(
        value.get("x_post_id")
        == X_POST_ID,
        "registration lock post ID mismatch",
    )

    require(
        value.get("x_post_url")
        == X_POST_URL,
        "registration lock post URL mismatch",
    )

    require(
        value.get("revision")
        == REVISION,
        "registration lock revision mismatch",
    )

    require(
        value.get(
            "corrective_evidence_digest_sha256"
        )
        == EXPECTED_CORRECTIVE_EVIDENCE_DIGEST,
        "registration lock digest mismatch",
    )

    require(
        value.get("registration_completed")
        is True,
        "corrective registration is incomplete",
    )

    require(
        value.get("reregistration_allowed")
        is False,
        "registration lock permits rerun",
    )

    require(
        value.get("additional_x_post_allowed")
        is False,
        "registration lock permits another post",
    )


def validate_supersession_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_MANUAL_X_POSTING_"
            "APPROVAL_SUPERSESSION"
        ),
        "supersession lock type mismatch",
    )

    require(
        value.get(
            "old_approval_gate_digest_sha256"
        )
        == EXPECTED_OLD_APPROVAL_GATE_DIGEST,
        "superseded approval digest mismatch",
    )

    require(
        value.get("old_approval_consumed")
        is False,
        "superseded approval was consumed",
    )

    require(
        value.get("old_approval_superseded")
        is True,
        "old approval was not superseded",
    )

    require(
        value.get(
            "old_approval_reuse_allowed"
        )
        is False,
        "superseded approval remains reusable",
    )

    require(
        value.get("retroactive_approval")
        is False,
        "retroactive approval was recorded",
    )

    require(
        value.get("registered_x_post_id")
        == X_POST_ID,
        "supersession lock post ID mismatch",
    )

    require(
        value.get("corrective_revision")
        == REVISION,
        "supersession revision mismatch",
    )

    require(
        value.get(
            "corrective_evidence_digest_sha256"
        )
        == EXPECTED_CORRECTIVE_EVIDENCE_DIGEST,
        "supersession evidence digest mismatch",
    )


def build_metrics_template(
    window: str,
) -> dict[str, Any]:
    require(
        window in VALID_WINDOWS,
        f"unsupported metrics window: {window}",
    )

    timing = VALID_WINDOWS[window]

    return {
        "schema_version": (
            "X_R11_POST_METRICS_MANUAL_V1"
        ),
        "status": (
            "PENDING_MANUAL_METRICS_CAPTURE"
        ),
        "capture_window": window,
        "capture_due_at_utc": (
            timing["due_at_utc"]
        ),
        "capture_due_at_jst": (
            timing["due_at_jst"]
        ),
        "capture_tolerance_minutes": 120,
        "x_post": {
            "post_id": X_POST_ID,
            "post_url": X_POST_URL,
            "x_account_handle": (
                X_ACCOUNT_HANDLE
            ),
            "posted_at_utc": POSTED_AT_UTC,
            "posted_at_jst": POSTED_AT_JST,
            "revision": REVISION,
            "link_route": LINK_ROUTE,
            "store": STORE,
            "affiliate_url": (
                AFFILIATE_URL
            ),
            "text_sha256": (
                CORRECTIVE_TEXT_SHA
            ),
        },
        "x_metrics": {
            "impressions": None,
            "engagements": None,
            "engagement_rate": None,
            "likes": None,
            "reposts": None,
            "replies": None,
            "bookmarks": None,
            "link_clicks": None,
            "profile_visits": None,
            "detail_expands": None,
        },
        "rakuten_metrics": {
            "affiliate_clicks": None,
            "orders": None,
            "cancelled_orders": None,
            "sales_amount_jpy": None,
            "commission_pending_jpy": None,
            "commission_confirmed_jpy": None,
        },
        "derived_metrics": {
            "link_ctr": None,
            "order_conversion_rate": None,
            "commission_per_click_jpy": None,
            "commission_per_impression_jpy": None,
        },
        "manual_evidence": {
            "x_analytics_screenshot_path": None,
            "rakuten_report_screenshot_path": None,
            "x_metrics_captured_at_utc": None,
            "rakuten_metrics_captured_at_utc": None,
            "human_verified": None,
            "notes": None,
        },
        "collection_policy": {
            "manual_read_only_collection": True,
            "x_post_must_remain_unmodified": True,
            "affiliate_url_must_remain_unmodified": True,
            "no_credentials_in_evidence": True,
            "x_api_allowed": False,
            "rakuten_api_allowed": False,
            "browser_automation_allowed": False,
        },
        "metrics_registration_completed": False,
        "x_api_call": False,
        "rakuten_api_call": False,
        "browser_automation": False,
        "credentials_recorded": False,
        "database_write": False,
        "production_status": "NO_GO",
    }


def validate_pending_template(
    value: dict[str, Any],
    *,
    expected_window: str,
) -> None:
    require(
        value.get("status")
        == "PENDING_MANUAL_METRICS_CAPTURE",
        "metrics template status mismatch",
    )

    require(
        value.get("capture_window")
        == expected_window,
        "metrics capture window mismatch",
    )

    timing = VALID_WINDOWS[
        expected_window
    ]

    require(
        value.get("capture_due_at_utc")
        == timing["due_at_utc"],
        "metrics UTC due time mismatch",
    )

    require(
        value.get("capture_due_at_jst")
        == timing["due_at_jst"],
        "metrics JST due time mismatch",
    )

    for section_name in (
        "x_metrics",
        "rakuten_metrics",
        "derived_metrics",
    ):
        section = value.get(section_name)

        require(
            isinstance(section, dict),
            f"metrics section missing: {section_name}",
        )

        for field, item in section.items():
            require(
                item is None,
                (
                    "metrics template must remain "
                    f"empty: {section_name}.{field}"
                ),
            )

    manual = value.get(
        "manual_evidence"
    )

    require(
        isinstance(manual, dict),
        "manual evidence section is missing",
    )

    for field, item in manual.items():
        require(
            item is None,
            (
                "manual evidence template must "
                f"remain empty: {field}"
            ),
        )

    policy = value.get(
        "collection_policy"
    )

    require(
        isinstance(policy, dict),
        "collection policy is missing",
    )

    require(
        policy.get(
            "manual_read_only_collection"
        )
        is True,
        "manual collection is not required",
    )

    require(
        policy.get("x_api_allowed")
        is False,
        "X API is permitted",
    )

    require(
        policy.get("rakuten_api_allowed")
        is False,
        "Rakuten API is permitted",
    )

    require(
        policy.get(
            "browser_automation_allowed"
        )
        is False,
        "browser automation is permitted",
    )

    require(
        value.get(
            "metrics_registration_completed"
        )
        is False,
        "metrics were already registered",
    )


def build_baseline_prep(
    *,
    production_database_path: Path,
    corrective_evidence_path: Path,
    registration_lock_path: Path,
    supersession_lock_path: Path,
    template_24h_path: Path,
    template_7d_path: Path,
    baseline_pack_path: Path,
    generation_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    corrective_evidence_path = (
        corrective_evidence_path.resolve()
    )

    registration_lock_path = (
        registration_lock_path.resolve()
    )

    supersession_lock_path = (
        supersession_lock_path.resolve()
    )

    template_24h_path = (
        template_24h_path.resolve()
    )

    template_7d_path = (
        template_7d_path.resolve()
    )

    baseline_pack_path = (
        baseline_pack_path.resolve()
    )

    generation_lock_path = (
        generation_lock_path.resolve()
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    corrective_evidence = load_json(
        corrective_evidence_path
    )

    validate_corrective_evidence(
        corrective_evidence
    )

    registration_lock = load_json(
        registration_lock_path
    )

    validate_registration_lock(
        registration_lock
    )

    supersession_lock = load_json(
        supersession_lock_path
    )

    validate_supersession_lock(
        supersession_lock
    )

    for path, label in (
        (
            template_24h_path,
            "24-hour metrics template",
        ),
        (
            template_7d_path,
            "7-day metrics template",
        ),
        (
            baseline_pack_path,
            "metrics baseline pack",
        ),
        (
            generation_lock_path,
            "metrics baseline generation lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    template_24h = build_metrics_template(
        "24H"
    )

    template_7d = build_metrics_template(
        "7D"
    )

    validate_pending_template(
        template_24h,
        expected_window="24H",
    )

    validate_pending_template(
        template_7d,
        expected_window="7D",
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    baseline_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_POST_METRICS_"
            "BASELINE_PREP_READY"
        ),
        "baseline_state": (
            "AWAITING_MANUAL_METRICS_"
            "CAPTURE_24H_AND_7D"
        ),
        "prepared_at": prepared_at,
        "source_corrective_evidence_path": str(
            corrective_evidence_path
        ),
        "source_corrective_evidence_digest_sha256": (
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        "source_registration_lock_path": str(
            registration_lock_path
        ),
        "source_supersession_lock_path": str(
            supersession_lock_path
        ),
        "x_post": {
            "post_id": X_POST_ID,
            "post_url": X_POST_URL,
            "x_account_handle": (
                X_ACCOUNT_HANDLE
            ),
            "posted_at_utc": POSTED_AT_UTC,
            "posted_at_jst": POSTED_AT_JST,
            "revision": REVISION,
            "link_route": LINK_ROUTE,
            "store": STORE,
            "affiliate_url": (
                AFFILIATE_URL
            ),
            "text_sha256": (
                CORRECTIVE_TEXT_SHA
            ),
        },
        "capture_schedule": {
            "capture_24h_due_at_utc": (
                CAPTURE_24H_DUE_UTC
            ),
            "capture_24h_due_at_jst": (
                CAPTURE_24H_DUE_JST
            ),
            "capture_7d_due_at_utc": (
                CAPTURE_7D_DUE_UTC
            ),
            "capture_7d_due_at_jst": (
                CAPTURE_7D_DUE_JST
            ),
            "capture_tolerance_minutes": 120,
        },
        "metrics_templates": {
            "24h": str(template_24h_path),
            "7d": str(template_7d_path),
        },
        "collection_mode": (
            "MANUAL_READ_ONLY"
        ),
        "manual_metrics_capture_allowed": True,
        "metrics_registration_completed": False,
        "additional_x_post_allowed": False,
        "x_post_modification_allowed": False,
        "affiliate_url_modification_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "rakuten_api_call": False,
        "production_status": "NO_GO",
        "safety_state": (
            "METRICS_BASELINE_READY_"
            "MANUAL_CAPTURE_ONLY_"
            "NO_POST_NO_API_NO_DB_WRITE"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-POST-METRICS-24H-"
            "MANUAL-CAPTURE"
        ),
    }

    baseline = {
        **baseline_payload,
        "x_post_metrics_baseline_"
        "prep_digest_sha256": (
            canonical_digest(
                baseline_payload
            )
        ),
    }

    baseline_digest = baseline[
        "x_post_metrics_baseline_"
        "prep_digest_sha256"
    ]

    generation_lock = {
        "lock_type": (
            "X_R11_X_POST_METRICS_"
            "BASELINE_PREP_GENERATION"
        ),
        "created_at": prepared_at,
        "source_corrective_evidence_digest_sha256": (
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        "baseline_pack_path": str(
            baseline_pack_path
        ),
        "baseline_pack_digest_sha256": (
            baseline_digest
        ),
        "template_24h_path": str(
            template_24h_path
        ),
        "template_7d_path": str(
            template_7d_path
        ),
        "generation_completed": True,
        "reexecution_allowed": False,
        "additional_x_post_allowed": False,
    }

    atomic_create_json(
        template_24h_path,
        template_24h,
    )

    atomic_create_json(
        template_7d_path,
        template_7d,
    )

    atomic_create_json(
        baseline_pack_path,
        baseline,
    )

    atomic_create_json(
        generation_lock_path,
        generation_lock,
    )

    return baseline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--corrective-evidence",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--registration-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--supersession-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--template-24h",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--template-7d",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--baseline-pack",
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
        result = build_baseline_prep(
            production_database_path=(
                args.production_db
            ),
            corrective_evidence_path=(
                args.corrective_evidence
            ),
            registration_lock_path=(
                args.registration_lock
            ),
            supersession_lock_path=(
                args.supersession_lock
            ),
            template_24h_path=(
                args.template_24h
            ),
            template_7d_path=(
                args.template_7d
            ),
            baseline_pack_path=(
                args.baseline_pack
            ),
            generation_lock_path=(
                args.generation_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_POST_METRICS_"
                        "BASELINE_PREP"
                    ),
                    "error": str(exc),
                    "automatic_rerun_allowed": False,
                    "metrics_registration_completed": False,
                    "additional_x_post_allowed": False,
                    "database_write": False,
                    "x_api_call": False,
                    "rakuten_api_call": False,
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
                "baseline_state": (
                    result["baseline_state"]
                ),
                "x_post_id": (
                    result["x_post"]["post_id"]
                ),
                "x_post_url": (
                    result["x_post"]["post_url"]
                ),
                "revision": (
                    result["x_post"]["revision"]
                ),
                "capture_24h_due_at_jst": (
                    result[
                        "capture_schedule"
                    ][
                        "capture_24h_due_at_jst"
                    ]
                ),
                "capture_7d_due_at_jst": (
                    result[
                        "capture_schedule"
                    ][
                        "capture_7d_due_at_jst"
                    ]
                ),
                "collection_mode": (
                    result["collection_mode"]
                ),
                "manual_metrics_capture_allowed": True,
                "metrics_registration_completed": False,
                "additional_x_post_allowed": False,
                "database_write": False,
                "x_api_call": False,
                "rakuten_api_call": False,
                "production_status": "NO_GO",
                "baseline_pack_path": str(
                    args.baseline_pack.resolve()
                ),
                "baseline_digest_sha256": (
                    result[
                        "x_post_metrics_baseline_"
                        "prep_digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
