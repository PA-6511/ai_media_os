#!/usr/bin/env python3

from __future__ import annotations

import json
import sys


result = {
    "phase_id": "LS-NEW-BATCH-4G-2E-RECOVERY-G",
    "status": (
        "BLOCKED_HUMAN_REVIEW_CONTENT_GENERATION_"
        "PAYLOAD_BINDING_AND_WORDPRESS_EXECUTION_"
        "NOT_AUTHORIZED"
    ),
    "approval_revision": 2,
    "approval_reissued": True,
    "superseded_approval_preserved": True,
    "content_item_id": (
        "new-release-comic-20260703-001"
    ),
    "work_title": "ダークギャザリング",
    "volume_label": "第20巻",
    "article_input_registered": True,
    "human_review_complete": False,
    "article_content_generated": False,
    "fresh_payload_created": False,
    "fresh_payload_read": False,
    "fresh_payload_copied": False,
    "payload_binding_complete": False,
    "production_category_id_payload_injected": False,
    "network_connection_performed": False,
    "http_request_performed": False,
    "wordpress_access_performed": False,
    "wordpress_write_performed": False,
    "wordpress_draft_created": False,
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
