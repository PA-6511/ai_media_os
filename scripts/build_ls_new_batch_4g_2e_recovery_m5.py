#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_historical_m4_"
    "evidence_human_review_policy.json"
)
FIX_APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m5_fix1_"
    "policy_schema_fix_approval.json"
)
M5_APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m5_"
    "historical_evidence_human_review_approval.json"
)
REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_historical_m4_evidence_human_review.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m5_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m5_"
    "historical_evidence_human_review_report.md"
)

SOURCE_PATHS = {
    "parser_runner": ROOT / (
        "scripts/execute_ls_new_batch_4g_2e_recovery_m2.py"
    ),
    "m4_runner": ROOT / (
        "scripts/execute_ls_new_batch_4g_2e_recovery_m4.py"
    ),
    "m4_fix1_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m4_fix1_"
        "volume_canonical_remediation_approval.json"
    ),
    "m4_fix1_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m4_fix1_result.json"
    ),
    "m4_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m4_result.json"
    ),
    "m4_recheck": ROOT / (
        "exchange/rechecks/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_post_parser_fix_result.json"
    ),
    "m4_consumption": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_post_parser_fix_consumption.json"
    ),
    "m4_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m4_execute_now_approval.json"
    ),
    "m3_authorization": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_post_parser_fix_authorization.json"
    ),
    "m2_fix1_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m2_fix1_result.json"
    ),
    "old_m2_result": ROOT / (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m2_result.json"
    ),
    "old_m2_recheck": ROOT / (
        "exchange/rechecks/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_result.json"
    ),
    "old_m2_consumption": ROOT / (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_consumption.json"
    ),
    "old_m2_approval": ROOT / (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m2_execute_now_approval.json"
    ),
    "article": ROOT / (
        "exchange/content/new_release/fresh/"
        "new-release-comic-20260703-001.article.json"
    ),
    "store_link_plan": ROOT / (
        "exchange/plans/new_release/fresh/"
        "new-release-comic-20260703-001."
        "store_link_finalization_plan.json"
    )
}

EXPECTED_PARSER_SHA = (
    "f28ec2df1816e102673831ea9e8dfde0"
    "db2df7df668324925f6b7f1441e306aa"
)
EXPECTED_M4_RUNNER_SHA = (
    "729036b79e18f38bf4f00b257f688726"
    "578673109f5d57023255dd6b329dc4e4"
)
EXPECTED_M4_FIX1_DIGEST = (
    "2290386c3cbb05d54721238cb88ee3af"
    "3221abcf8e7b84b91a11432bed4f561f"
)
EXPECTED_M4_RECHECK_DIGEST = (
    "f3a5c797054c18b50ee83da14507d383"
    "a916277fcf64edd67dfd1ab4ee14ee52"
)
EXPECTED_M4_CONSUMPTION_DIGEST = (
    "f77febc5dcc7a87ab646895c8c159ff1d"
    "91447824a0fb687569981426a2edf9d"
)
EXPECTED_RESPONSE_SHA = (
    "c0c75847c2c048ee468937c2fdf2190f"
    "3ab5586226c9854e11513b2a74a88146"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"required file missing: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def verify_self_digest(
    value: dict[str, Any],
    field: str,
    expected: str | None = None,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"digest missing: {field}",
    )
    require(
        digest(comparable) == stored,
        f"digest invalid: {field}",
    )

    if expected is not None:
        require(
            stored == expected,
            f"digest mismatch: {field}",
        )

    return stored


def load_module(
    path: Path,
    name: str,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    require(
        spec is not None
        and spec.loader is not None,
        f"module spec failure: {path}",
    )

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def write_exclusive_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_exclusive_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    try:
        policy = load_json(POLICY)
        fix_approval = load_json(
            FIX_APPROVAL
        )

        require(
            policy["phase_id"]
            == "LS-NEW-BATCH-4G-2E-RECOVERY-M5",
            "policy phase mismatch",
        )

        boundary = policy[
            "execution_boundary"
        ]

        require(
            boundary[
                "historical_result_reclassification_allowed"
            ]
            is False,
            "schema fix key missing or not false",
        )
        require(
            boundary["network_connection_allowed"]
            is False,
            "network boundary open",
        )
        require(
            boundary[
                "final_affiliate_link_generation_allowed"
            ]
            is False,
            "link generation boundary open",
        )

        fix_approval_digest = verify_self_digest(
            fix_approval,
            "approval_evidence_digest_sha256",
        )

        require(
            fix_approval["approval_label"]
            == (
                "DMM_M5_POLICY_EXECUTION_BOUNDARY_"
                "SCHEMA_FIX_APPROVED"
            ),
            "fix approval label mismatch",
        )

        source_bindings = {
            label: {
                "path": str(
                    path.relative_to(ROOT)
                ),
                "file_sha256": file_sha256(
                    path
                )
            }
            for label, path
            in SOURCE_PATHS.items()
        }

        source_hashes_before = {
            label: binding["file_sha256"]
            for label, binding
            in source_bindings.items()
        }

        require(
            source_hashes_before[
                "parser_runner"
            ]
            == EXPECTED_PARSER_SHA,
            "parser hash mismatch",
        )
        require(
            source_hashes_before[
                "m4_runner"
            ]
            == EXPECTED_M4_RUNNER_SHA,
            "M4 runner hash mismatch",
        )

        m4_fix1_approval = load_json(
            SOURCE_PATHS[
                "m4_fix1_approval"
            ]
        )
        m4_fix1 = load_json(
            SOURCE_PATHS[
                "m4_fix1_result"
            ]
        )
        m4_result = load_json(
            SOURCE_PATHS["m4_result"]
        )
        m4_recheck = load_json(
            SOURCE_PATHS["m4_recheck"]
        )
        m4_consumption = load_json(
            SOURCE_PATHS[
                "m4_consumption"
            ]
        )

        verify_self_digest(
            m4_fix1,
            "fix_evidence_digest_sha256",
            EXPECTED_M4_FIX1_DIGEST,
        )
        verify_self_digest(
            m4_recheck,
            "post_fix_dmm_recheck_result_digest_sha256",
            EXPECTED_M4_RECHECK_DIGEST,
        )
        verify_self_digest(
            m4_consumption,
            "post_fix_consumption_evidence_digest_sha256",
            EXPECTED_M4_CONSUMPTION_DIGEST,
        )

        historical_bindings = (
            m4_fix1_approval[
                "historical_source_bindings"
            ]["bindings"]
        )

        require(
            file_sha256(
                SOURCE_PATHS["m4_result"]
            )
            == historical_bindings[
                "m4_result"
            ]["file_sha256"],
            "historical M4 result changed",
        )
        require(
            file_sha256(
                SOURCE_PATHS["m4_recheck"]
            )
            == historical_bindings[
                "m4_recheck"
            ]["file_sha256"],
            "historical M4 recheck changed",
        )
        require(
            file_sha256(
                SOURCE_PATHS[
                    "m4_consumption"
                ]
            )
            == historical_bindings[
                "m4_consumption"
            ]["file_sha256"],
            "historical M4 consumption changed",
        )

        require(
            m4_result["successful_match"]
            is False,
            "historical M4 result reclassified",
        )
        require(
            m4_result[
                "failure_reason_codes"
            ]
            == [
                "VOLUME_MISMATCH",
                (
                    "CANONICAL_PRODUCT_"
                    "SERIES_BINDING_FAILED"
                ),
            ],
            "historical failure codes changed",
        )
        require(
            m4_recheck["network"][
                "response_body_sha256"
            ]
            == EXPECTED_RESPONSE_SHA,
            "historical response SHA changed",
        )
        require(
            m4_consumption[
                "authorization_consumed"
            ]
            is True,
            "M4 authorization not consumed",
        )
        require(
            m4_consumption[
                "authorization_reuse_allowed"
            ]
            is False,
            "authorization reuse not blocked",
        )

        parser_module = load_module(
            SOURCE_PATHS["parser_runner"],
            "recovery_m5_fix1_parser",
        )
        m4_module = load_module(
            SOURCE_PATHS["m4_runner"],
            "recovery_m5_fix1_runner",
        )

        require(
            m4_module.EXPECTED_RUNNER_SHA256
            == EXPECTED_PARSER_SHA,
            "M4 parser binding mismatch",
        )

        identity = m4_recheck[
            "extracted_identity"
        ]

        (
            normalized_volume,
            volume_source,
        ) = (
            parser_module
            .extract_expected_volume_from_title_candidates(
                identity[
                    "page_title_candidates"
                ],
                expected_work_title=(
                    "ダークギャザリング"
                ),
                expected_volume_number=20,
            )
        )

        canonical_binding = (
            m4_module
            .canonical_product_url_binds_to_expected_series(
                identity[
                    "canonical_product_url"
                ],
                expected_series_id="861056",
            )
        )

        review_checks = {
            "historical_title_contains_expected_work": (
                "ダークギャザリング"
                in identity[
                    "extracted_work_title"
                ]
            ),
            "historical_title_normalizes_to_volume_20": (
                normalized_volume == "第20巻"
            ),
            "volume_source_is_work_bound": (
                volume_source
                == (
                    "TITLE_OR_STRUCTURED_DATA_"
                    "WORK_BOUND_VOLUME"
                )
            ),
            "author_exact_match": (
                identity[
                    "extracted_author"
                ]
                == "近藤憲一"
            ),
            "publisher_exact_match": (
                identity[
                    "extracted_publisher"
                ]
                == "集英社"
            ),
            "series_id_exact_match": (
                identity[
                    "extracted_series_id"
                ]
                == "861056"
            ),
            "canonical_product_url_exact_match": (
                identity[
                    "canonical_product_url"
                ]
                == (
                    "https://book.dmm.com/"
                    "product/861056/"
                    "b950yshes32617/"
                )
            ),
            "canonical_url_binds_to_series_861056": (
                canonical_binding
            ),
            "m4_fix1_volume_evaluation_match": (
                m4_fix1[
                    "offline_historical_evidence_evaluation"
                ][
                    "historical_title_now_normalizes_to"
                ]
                == "第20巻"
            ),
            "m4_fix1_canonical_evaluation_match": (
                m4_fix1[
                    "offline_historical_evidence_evaluation"
                ][
                    "historical_canonical_url_now_binds_to_series"
                ]
                is True
            ),
        }

        require(
            all(review_checks.values()),
            "review checks failed",
        )

        m5_approval_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M5"
            ),
            "approval_id": (
                "dmm-historical-m4-evidence-"
                "human-review-approval-v1"
            ),
            "approval_label": (
                "DMM_HISTORICAL_M4_EVIDENCE_"
                "HUMAN_REVIEW_APPROVED"
            ),
            "approved_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "approved_at_utc": utc_now(),
            "approved_findings": {
                "historical_title_is_volume_20": True,
                "normalized_volume": "第20巻",
                "author_match": True,
                "publisher_match": True,
                "series_id_match": True,
                "canonical_product_url_match": True,
                "canonical_product_url": (
                    "https://book.dmm.com/"
                    "product/861056/"
                    "b950yshes32617/"
                ),
                "product_url_role": (
                    "VERIFIED_DMM_PRODUCT_URL_"
                    "CANDIDATE_ONLY"
                )
            },
            "approved_outcome": {
                "historical_evidence_match_approved": True,
                "ready_for_final_affiliate_link_generation_gate": True,
                "final_affiliate_link_generation_allowed": False,
                "article_dmm_slot_activation_allowed": False,
                "historical_m4_result_reclassification_allowed": False
            },
            "fix_approval_path": str(
                FIX_APPROVAL.relative_to(ROOT)
            ),
            "fix_approval_digest_sha256": (
                fix_approval_digest
            ),
            "source_bindings": (
                source_bindings
            ),
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        m5_approval = copy.deepcopy(
            m5_approval_without_digest
        )
        m5_approval[
            "approval_evidence_digest_sha256"
        ] = digest(
            m5_approval_without_digest
        )

        write_exclusive_json(
            M5_APPROVAL,
            m5_approval,
        )

        review_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_HISTORICAL_M4_EVIDENCE_"
                "HUMAN_REVIEW"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M5"
            ),
            "content_item_id": (
                "new-release-comic-"
                "20260703-001"
            ),
            "review_id": (
                "dmm-historical-m4-evidence-"
                "human-review-v1"
            ),
            "reviewed_by": "HUMAN_OPERATOR",
            "human_explicit_approval": True,
            "reviewed_at_utc": utc_now(),
            "review_verdict": (
                "APPROVED_HISTORICAL_EVIDENCE_"
                "AS_DMM_PRODUCT_MATCH"
            ),
            "reviewed_historical_evidence": {
                "m4_attempt_id": (
                    m4_recheck["attempt_id"]
                ),
                "historical_page_title": (
                    identity[
                        "extracted_work_title"
                    ]
                ),
                "normalized_volume": (
                    normalized_volume
                ),
                "volume_source": (
                    volume_source
                ),
                "author": (
                    identity[
                        "extracted_author"
                    ]
                ),
                "publisher": (
                    identity[
                        "extracted_publisher"
                    ]
                ),
                "series_id": (
                    identity[
                        "extracted_series_id"
                    ]
                ),
                "canonical_product_url": (
                    identity[
                        "canonical_product_url"
                    ]
                ),
                "response_body_sha256": (
                    m4_recheck["network"][
                        "response_body_sha256"
                    ]
                )
            },
            "review_checks": review_checks,
            "review_conclusion": {
                "dmm_product_url_candidate_verified": True,
                "verified_product_url_candidate": (
                    "https://book.dmm.com/"
                    "product/861056/"
                    "b950yshes32617/"
                ),
                "verified_product_url_candidate_role": (
                    "VERIFIED_DMM_PRODUCT_URL_"
                    "CANDIDATE_ONLY"
                ),
                "ready_for_final_affiliate_link_generation_gate": True,
                "final_affiliate_link_generated": False,
                "article_dmm_slot_activation_allowed": False
            },
            "historical_evidence_treatment": {
                "m4_result_modified": False,
                "m4_result_reclassified": False,
                "m4_recheck_modified": False,
                "m4_consumption_modified": False,
                "m4_execute_approval_modified": False,
                "m3_authorization_modified": False,
                "old_m2_evidence_modified": False
            },
            "source_bindings": source_bindings,
            "new_authorization_created": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO"
        }

        review = copy.deepcopy(
            review_without_digest
        )
        review[
            "human_review_evidence_digest_sha256"
        ] = digest(review_without_digest)

        write_exclusive_json(
            REVIEW,
            review,
        )

        for label, path in (
            SOURCE_PATHS.items()
        ):
            require(
                file_sha256(path)
                == source_hashes_before[
                    label
                ],
                f"source artifact changed: {label}",
            )

        result = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M5"
            ),
            "status": (
                "PASS_DMM_HISTORICAL_M4_"
                "EVIDENCE_HUMAN_REVIEW_"
                "APPROVED_NO_NETWORK_"
                "NO_RECLASSIFICATION"
            ),
            "decision": (
                "DMM_VERIFIED_PRODUCT_URL_"
                "CANDIDATE_APPROVED_READY_FOR_"
                "FINAL_AFFILIATE_LINK_"
                "GENERATION_GATE"
            ),
            "approval_label": (
                "DMM_HISTORICAL_M4_EVIDENCE_"
                "HUMAN_REVIEW_APPROVED"
            ),
            "review_path": str(
                REVIEW.relative_to(ROOT)
            ),
            "review_file_sha256": (
                file_sha256(REVIEW)
            ),
            "review_digest_sha256": (
                review[
                    "human_review_evidence_digest_sha256"
                ]
            ),
            "review_verdict": (
                review["review_verdict"]
            ),
            "normalized_volume": "第20巻",
            "verified_product_url_candidate": (
                "https://book.dmm.com/"
                "product/861056/"
                "b950yshes32617/"
            ),
            "verified_product_url_candidate_role": (
                "VERIFIED_DMM_PRODUCT_URL_"
                "CANDIDATE_ONLY"
            ),
            "historical_m4_result_modified": False,
            "historical_m4_result_reclassified": False,
            "historical_m4_response_sha256_preserved": True,
            "m4_authorization_consumption_preserved": True,
            "same_authorization_retry_allowed": False,
            "new_authorization_created": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "dmm_recheck_performed": False,
            "final_affiliate_link_generated": False,
            "final_affiliate_link_validated": False,
            "article_dmm_slot_activation_allowed": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_HISTORICAL_EVIDENCE_"
                "REVIEWED_AWAITING_FINAL_"
                "AFFILIATE_LINK_GENERATION_"
                "AUTHORIZATION_GATE"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_m6": True,
            "ready_for_final_affiliate_link_generation_gate": True,
            "ready_for_final_affiliate_link_generation": False,
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "completed_at_utc": utc_now()
        }

        write_exclusive_json(
            RESULT,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M5

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Review verdict: `{result["review_verdict"]}`
- Normalized volume: `第20巻`
- Verified product URL candidate: `{result["verified_product_url_candidate"]}`
- M4 result modified: `false`
- M4 result reclassified: `false`
- Network accessed: `false`
- DMM recheck performed: `false`
- Final affiliate link generated: `false`
- Article modified: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
- Ready for M6 gate: `true`
"""

        write_exclusive_text(
            REPORT,
            report,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M5"
                    ),
                    "status": (
                        "FAIL_M5_FIX1_REBUILD_"
                        "VALIDATION"
                    ),
                    "error": str(exc),
                    "network_connection_performed": False,
                    "historical_result_reclassified": False,
                    "final_affiliate_link_generated": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
