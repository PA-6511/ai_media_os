#!/usr/bin/env python3

import json
import sys


result = {
    "phase_id": "LS-NEW-BATCH-4G-2E-RECOVERY-M1",
    "status": (
        "BLOCKED_ACTUAL_DMM_RECHECK_AUTHORIZATION_"
        "CONSUMPTION_LINK_GENERATION_ARTICLE_"
        "INJECTION_PAYLOAD_AND_WORDPRESS_NOT_AUTHORIZED_IN_M1"
    ),
    "authorization_creation_allowed": True,
    "actual_dmm_recheck_allowed": False,
    "authorization_consumption_allowed": False,
    "network_connection_allowed": False,
    "http_request_allowed": False,
    "final_affiliate_link_generation_allowed": False,
    "article_modification_allowed": False,
    "article_url_injection_allowed": False,
    "fresh_payload_creation_allowed": False,
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
