#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


def main() -> int:
    result = {
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-C"
        ),
        "status": (
            "BLOCKED_CATEGORY_MAPPING_FIXATION_"
            "NOT_AUTHORIZED_IN_HUMAN_REVIEW_PHASE"
        ),
        "reason": (
            "This phase records the human category "
            "selection only. It does not authorize "
            "mapping fixation, payload injection, "
            "WordPress access, or WordPress writes."
        ),
        "selected_category_id": 10,
        "selected_category_name": "最新巻",
        "human_selection_recorded": True,
        "automatic_category_selection_performed": False,
        "automatic_category_mapping_performed": False,
        "category_mapping_fixed": False,
        "credential_file_read": False,
        "network_connection_performed": False,
        "http_request_performed": False,
        "wordpress_category_created": False,
        "wordpress_write_performed": False,
        "production_payload_modified": False,
        "production_category_id_payload_injected": False,
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
