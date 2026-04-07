from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from monitoring.log_helper import get_failure_logger


SLACK_TIMEOUT_SEC = 8


def _get_webhook_url() -> str:
    return os.getenv("SLACK_WEBHOOK_URL", "").strip()


def send_slack_message(text: str) -> bool:
    """Slack Incoming Webhook へテキスト通知する。"""
    webhook_url = _get_webhook_url()
    logger = get_failure_logger()

    if not webhook_url:
        logger.warning("slack webhook not set. skip notification")
        return False

    payload = {"text": text}
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=raw,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with request.urlopen(req, timeout=SLACK_TIMEOUT_SEC) as resp:
            _ = resp.read()
        return True
    except error.URLError as exc:
        logger.warning("slack notify failed: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("slack notify unexpected error: %s", exc)
        return False


def send_slack_block(title: str, lines: list[str]) -> bool:
    """タイトルと複数行の本文をSlackへ送る。"""
    text = "\n".join([title, *lines])
    return send_slack_message(text)
