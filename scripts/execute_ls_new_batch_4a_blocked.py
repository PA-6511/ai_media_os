#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


def main() -> int:
    result = {
        "phase_id": "LS-NEW-BATCH-4A",
        "status": "BLOCKED_REVIEW_NOT_COMPLETED",
        "reason": (
            "Human review is NOT_REVIEWED, approval label and "
            "approval token are absent, credentials are blocked, "
            "and WordPress execution authority has not been granted."
        ),
        "human_review_state": "NOT_REVIEWED",
        "human_approval_issued": False,
        "approval_label_present": False,
        "approval_token_present": False,
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "CATEGORY_RESOLUTION_AND_REVIEW_PREP_ONLY"
        )
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
