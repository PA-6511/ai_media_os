from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE_ROOT = Path(
    "/home/deploy/ai_media_os/"
    "exchange/evidence/ebook_autonomy/daily_cycle"
)


def _empty(
    *,
    code: str,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "available": False,
        "code": code,
        "detail": detail,
        "source_path": "",
        "schema": "",
        "run_id": "",
        "started_at": "",
        "finished_at": "",
        "status": "UNAVAILABLE",
        "new_release": {},
        "x_publish": {},
        "sale": {},
        "campaign": {},
    }


def load_latest_autonomy_summary(
    evidence_root: Path | None = None,
) -> dict[str, Any]:

    root = (
        evidence_root
        if evidence_root is not None
        else DEFAULT_EVIDENCE_ROOT
    )

    try:
        files = sorted(
            (
                path
                for path in root.glob(
                    "*/summary.json"
                )
                if path.is_file()
            ),
            key=lambda path: (
                path.stat().st_mtime
            ),
            reverse=True,
        )
    except Exception as exc:
        return _empty(
            code="EVIDENCE_SCAN_FAILED",
            detail=type(exc).__name__,
        )

    if not files:
        return _empty(
            code="EVIDENCE_NOT_FOUND"
        )

    target = files[0]

    try:
        payload = json.loads(
            target.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        return _empty(
            code="LATEST_EVIDENCE_INVALID",
            detail=type(exc).__name__,
        )

    if not isinstance(payload, dict):
        return _empty(
            code="LATEST_EVIDENCE_ROOT_INVALID"
        )

    steps: dict[str, dict[str, Any]] = {}

    for raw_step in payload.get("steps") or []:
        if not isinstance(raw_step, dict):
            continue

        component = str(
            raw_step.get("component") or ""
        ).strip()

        if component:
            steps[component] = raw_step

    new_step = steps.get(
        "new_release",
        {},
    )

    # COMMAND_CENTER_X_PUBLISH_V2
    x_publish_step = steps.get(
        "x_publish",
        {},
    )

    sale_step = steps.get(
        "sale",
        {},
    )

    campaign_step = steps.get(
        "campaign",
        {},
    )

    new_metadata = (
        new_step.get("metadata")
        if isinstance(
            new_step.get("metadata"),
            dict,
        )
        else {}
    )

    x_publish_metadata = (
        x_publish_step.get("metadata")
        if isinstance(
            x_publish_step.get("metadata"),
            dict,
        )
        else {}
    )

    sale_metadata = (
        sale_step.get("metadata")
        if isinstance(
            sale_step.get("metadata"),
            dict,
        )
        else {}
    )

    campaign_metadata = (
        campaign_step.get("metadata")
        if isinstance(
            campaign_step.get("metadata"),
            dict,
        )
        else {}
    )

    wordpress = (
        new_metadata.get("wordpress")
        if isinstance(
            new_metadata.get("wordpress"),
            dict,
        )
        else {}
    )

    x_state = (
        new_metadata.get("x")
        if isinstance(
            new_metadata.get("x"),
            dict,
        )
        else {}
    )

    x_publish = (
        x_publish_metadata.get(
            "x_publish"
        )
        if isinstance(
            x_publish_metadata.get(
                "x_publish"
            ),
            dict,
        )
        else {}
    )

    sale = (
        sale_metadata.get("sale")
        if isinstance(
            sale_metadata.get("sale"),
            dict,
        )
        else {}
    )

    campaign = (
        campaign_metadata.get("campaign")
        if isinstance(
            campaign_metadata.get("campaign"),
            dict,
        )
        else {}
    )

    return {
        "available": True,
        "code": "PASS",
        "detail": "",
        "source_path": str(target),
        "schema": str(
            payload.get("schema") or ""
        ),
        "run_id": str(
            payload.get("run_id") or ""
        ),
        "started_at": str(
            payload.get("started_at") or ""
        ),
        "finished_at": str(
            payload.get("finished_at") or ""
        ),
        "status": str(
            payload.get("status")
            or "UNKNOWN"
        ),
        "new_release": {
            "status": str(
                new_step.get("status")
                or "UNKNOWN"
            ),
            "wordpress_post_id":
                wordpress.get("post_id"),
            "wordpress_status": str(
                wordpress.get("status")
                or ""
            ),
            "wordpress_permalink": str(
                wordpress.get("permalink")
                or ""
            ),
            "x_article_url_state": str(
                x_state.get(
                    "article_url_state"
                )
                or ""
            ),
            "x_article_url": str(
                x_state.get("article_url")
                or ""
            ),
            "x_draft_path": str(
                x_state.get("draft_path")
                or ""
            ),
        },
        "x_publish": {
            "step_status": str(
                x_publish_step.get(
                    "status"
                )
                or "UNKNOWN"
            ),
            "status": str(
                x_publish.get(
                    "status"
                )
                or ""
            ),
            "code": str(
                x_publish.get(
                    "code"
                )
                or ""
            ),
            "x_post_id": str(
                x_publish.get(
                    "x_post_id"
                )
                or ""
            ),
            "x_post_url": str(
                x_publish.get(
                    "x_post_url"
                )
                or ""
            ),
            "evidence_path": str(
                x_publish.get(
                    "evidence_path"
                )
                or ""
            ),
            "delivery_state": str(
                x_publish.get(
                    "delivery_state"
                )
                or ""
            ),
            "x_post_executed": str(
                x_publish.get(
                    "x_post_executed"
                )
                or ""
            ),
        },
        "sale": {
            "status": str(
                sale_step.get("status")
                or "UNKNOWN"
            ),
            "candidate_count":
                sale.get("candidate_count"),
            "success_count":
                sale.get("success_count"),
            "failed_count":
                sale.get("failed_count"),
            "skipped_count":
                sale.get("skipped_count"),
            "external_call_count":
                sale.get(
                    "external_call_count"
                ),
            "outcome": str(
                sale.get("outcome")
                or ""
            ),
        },
        "campaign": {
            "status": str(
                campaign_step.get("status")
                or "UNKNOWN"
            ),
            "campaign_id": str(
                campaign.get("campaign_id")
                or ""
            ),
            "selected_count":
                campaign.get(
                    "selected_count"
                ),
            "created_count":
                campaign.get(
                    "created_count"
                ),
            "existing_exact_count":
                campaign.get(
                    "existing_exact_count"
                ),
            "no_fresh_candidates":
                campaign.get(
                    "no_fresh_candidates"
                ),
            "external_get_count":
                campaign.get(
                    "external_get_count"
                ),
        },
    }
