#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


def main() -> int:
    result = {
        "phase_id": "LS-NEW-BATCH-4B",
        "status": (
            "BLOCKED_EXAMPLE_CATEGORY_AND_"
            "NO_EXECUTION_APPROVAL"
        ),
        "reason": (
            "Human review was recorded, but category resolution "
            "is EXAMPLE_ONLY, production-usable category IDs are "
            "absent, execution approval was not issued, and no "
            "approval token exists."
        ),
        "human_review_approval_recorded": True,
        "category_ids_production_usable": False,
        "execution_approval_issued": False,
        "approval_token_present": False,
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": "HUMAN_REVIEW_RECORD_ONLY"
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
