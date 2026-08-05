#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


def main() -> int:
    result = {
        "phase_id": "LS-NEW-BATCH-4G-2C",
        "status": (
            "BLOCKED_AWAITING_EXPLICIT_"
            "CATEGORY_CANDIDATE_SEARCH_APPROVAL"
        ),
        "reason": (
            "The previous one-shot approval is consumed and "
            "cannot be reused. The new category-candidate search "
            "scope is fixed, but its separate human approval has "
            "not been issued."
        ),
        "previous_approval_consumed": True,
        "previous_approval_reusable": False,
        "previous_lock_state": (
            "CONSUMED_COMPLETED_BLOCKED"
        ),
        "previous_lock_deletion_allowed": False,
        "previous_lock_reuse_allowed": False,
        "requested_approval_label": (
            "APPROVED_FOR_ONE_SHOT_READ_ONLY_"
            "CATEGORY_CANDIDATE_SEARCH_ONLY"
        ),
        "approval_label_issued": False,
        "actual_go_decision_issued": False,
        "maximum_http_requests": 1,
        "maximum_attempts": 1,
        "retry_allowed": False,
        "credential_file_read": False,
        "network_connection_performed": False,
        "http_request_performed": False,
        "wordpress_response_read": False,
        "wordpress_write_performed": False,
        "candidate_selected": False,
        "production_payload_modified": False,
        "execution_allowed": False,
        "production_status": "NO_GO"
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
