#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


def main() -> int:
    result = {
        "phase_id": "LS-NEW-BATCH-4C",
        "status": (
            "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION"
        ),
        "reason": (
            "The example category ID was removed. A verified "
            "production WordPress category ID, category-review "
            "evidence, execution approval, and approval token "
            "are all absent."
        ),
        "example_category_ids_removed": True,
        "production_category_ids_present": False,
        "production_category_ids_usable": False,
        "execution_approval_issued": False,
        "approval_token_present": False,
        "credential_read_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_category_lookup_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_publish_allowed": False,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CATEGORY_RESOLUTION_PENDING"
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
