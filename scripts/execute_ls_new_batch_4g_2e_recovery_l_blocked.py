#!/usr/bin/env python3

import json
import sys


result = {
    "phase_id": "LS-NEW-BATCH-4G-2E-RECOVERY-L",
    "status": (
        "BLOCKED_ARTICLE_MODIFICATION_PAYLOAD_CATEGORY_"
        "NETWORK_AND_WORDPRESS_EXECUTION_NOT_AUTHORIZED_IN_L"
    ),
    "review_evidence_creation_allowed": True,
    "generated_article_modification_allowed": False,
    "consumption_evidence_modification_allowed": False,
    "fresh_payload_creation_allowed": False,
    "production_category_id_payload_injection_allowed": False,
    "network_connection_allowed": False,
    "wordpress_write_allowed": False,
    "wordpress_publish_allowed": False,
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

raise SystemExit(3)
