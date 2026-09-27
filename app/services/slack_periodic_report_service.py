from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class SlackPeriodicReportError(ValueError):
    pass


@dataclass(frozen=True)
class SlackPeriodicReportPayload:
    text: str
    blocks: list[dict[str, Any]]


def _plain(text: str) -> dict[str, Any]:
    return {
        "type": "plain_text",
        "text": text,
        "emoji": True,
    }


def _mrkdwn(text: str) -> dict[str, Any]:
    return {
        "type": "mrkdwn",
        "text": text,
    }


def _metric_value(
    metrics: Mapping[str, Any],
    name: str,
) -> tuple[Any, str | None]:
    raw = metrics.get(name)

    if not isinstance(raw, Mapping):
        return None, "not_available"

    return raw.get("value"), raw.get("reason")


def _display(
    value: Any,
    reason: str | None,
    *,
    percent: bool = False,
    yen: bool = False,
) -> str:
    if value is None:
        return f"N/A ({reason or 'unavailable'})"

    if percent:
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return str(value)

    if yen:
        try:
            return f"¥{float(value):,.0f}"
        except (TypeError, ValueError):
            return str(value)

    if isinstance(value, float):
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def _change_line(change: Mapping[str, Any]) -> str:
    name = str(change.get("metric") or "unknown")
    current = change.get("current")
    previous = change.get("previous")
    delta = change.get("delta")
    pct = change.get("percent_change")

    pct_text = "N/A"
    if isinstance(pct, (int, float)):
        pct_text = f"{pct * 100:+.1f}%"

    return (
        f"• `{name}`: "
        f"{previous} → {current} "
        f"(Δ {delta}, {pct_text})"
    )


def build_periodic_report_slack_payload(
    *,
    report_type: str,
    core_result: Mapping[str, Any],
) -> SlackPeriodicReportPayload:
    normalized_type = str(report_type).strip().lower()

    if normalized_type not in {"weekly", "monthly"}:
        raise SlackPeriodicReportError(
            "report_type must be weekly or monthly"
        )

    if core_result.get("status") != "OK":
        raise SlackPeriodicReportError(
            "Core advisory status is not OK"
        )

    analysis = core_result.get("business_analysis")

    if not isinstance(analysis, Mapping):
        raise SlackPeriodicReportError(
            "business_analysis is unavailable"
        )

    metrics = analysis.get("current_metrics")
    if not isinstance(metrics, Mapping):
        metrics = {}

    changes = analysis.get("notable_changes")
    if not isinstance(changes, Sequence) or isinstance(
        changes,
        (str, bytes),
    ):
        changes = []

    unavailable = analysis.get("unavailable_metrics")
    if not isinstance(unavailable, Sequence) or isinstance(
        unavailable,
        (str, bytes),
    ):
        unavailable = []

    registered, registered_reason = _metric_value(
        metrics,
        "registered_items",
    )
    cover_rate, cover_reason = _metric_value(
        metrics,
        "registered_item_cover_rate_current",
    )
    wp_draft, wp_draft_reason = _metric_value(
        metrics,
        "registered_items_wordpress_draft_current",
    )
    wp_published, wp_published_reason = _metric_value(
        metrics,
        "registered_items_wordpress_published_current",
    )
    campaigns, campaigns_reason = _metric_value(
        metrics,
        "sale_campaigns_imported",
    )
    offers, offers_reason = _metric_value(
        metrics,
        "sale_offers_imported",
    )
    clicks, clicks_reason = _metric_value(
        metrics,
        "attributed_clicks",
    )
    orders, orders_reason = _metric_value(
        metrics,
        "attributed_orders",
    )
    cvr, cvr_reason = _metric_value(
        metrics,
        "attributed_cvr",
    )
    revenue, revenue_reason = _metric_value(
        metrics,
        "attributed_order_revenue_jpy",
    )

    label = "週次" if normalized_type == "weekly" else "月次"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": _plain(
                f"電子書籍アフィリエイト {label}レポート"
            ),
        },
        {
            "type": "section",
            "fields": [
                _mrkdwn(
                    "*登録冊数*\n"
                    + _display(
                        registered,
                        registered_reason,
                    )
                ),
                _mrkdwn(
                    "*書影READY率*\n"
                    + _display(
                        cover_rate,
                        cover_reason,
                        percent=True,
                    )
                ),
                _mrkdwn(
                    "*WP Draft*\n"
                    + _display(
                        wp_draft,
                        wp_draft_reason,
                    )
                ),
                _mrkdwn(
                    "*WP Published*\n"
                    + _display(
                        wp_published,
                        wp_published_reason,
                    )
                ),
                _mrkdwn(
                    "*Sale Campaigns*\n"
                    + _display(
                        campaigns,
                        campaigns_reason,
                    )
                ),
                _mrkdwn(
                    "*Sale Offers*\n"
                    + _display(
                        offers,
                        offers_reason,
                    )
                ),
            ],
        },
        {
            "type": "section",
            "fields": [
                _mrkdwn(
                    "*Attributed Clicks*\n"
                    + _display(
                        clicks,
                        clicks_reason,
                    )
                ),
                _mrkdwn(
                    "*Attributed Orders*\n"
                    + _display(
                        orders,
                        orders_reason,
                    )
                ),
                _mrkdwn(
                    "*Attributed CVR*\n"
                    + _display(
                        cvr,
                        cvr_reason,
                        percent=True,
                    )
                ),
                _mrkdwn(
                    "*Attributed Revenue*\n"
                    + _display(
                        revenue,
                        revenue_reason,
                        yen=True,
                    )
                ),
            ],
        },
    ]

    valid_changes = [
        change
        for change in changes[:5]
        if isinstance(change, Mapping)
    ]

    if valid_changes:
        blocks.append(
            {
                "type": "section",
                "text": _mrkdwn(
                    "*主な前期間差*\n"
                    + "\n".join(
                        _change_line(change)
                        for change in valid_changes
                    )
                ),
            }
        )

    if unavailable:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    _mrkdwn(
                        "*未取得KPI:* "
                        + ", ".join(
                            f"`{str(name)}`"
                            for name in unavailable
                        )
                    )
                ],
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [
                _mrkdwn(
                    "Core advisory / read-only analysis • "
                    "自動公開・自動投稿なし"
                )
            ],
        }
    )

    return SlackPeriodicReportPayload(
        text=f"電子書籍アフィリエイト {label}レポート",
        blocks=blocks,
    )
