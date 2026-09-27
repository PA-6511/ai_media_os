from app.services.slack_periodic_report_service import (
    SlackPeriodicReportError,
    build_periodic_report_slack_payload,
)


def _core_result():
    return {
        "status": "OK",
        "business_analysis": {
            "status": "OK",
            "current_metrics": {
                "registered_items": {
                    "value": 100,
                    "reason": None,
                },
                "registered_item_cover_rate_current": {
                    "value": 0.9,
                    "reason": None,
                },
                "registered_items_wordpress_draft_current": {
                    "value": 5,
                    "reason": None,
                },
                "registered_items_wordpress_published_current": {
                    "value": 80,
                    "reason": None,
                },
                "sale_campaigns_imported": {
                    "value": 2,
                    "reason": None,
                },
                "sale_offers_imported": {
                    "value": 20,
                    "reason": None,
                },
                "attributed_clicks": {
                    "value": None,
                    "reason": "no_attributed_data",
                },
                "attributed_orders": {
                    "value": None,
                    "reason": "no_attributed_data",
                },
                "attributed_cvr": {
                    "value": None,
                    "reason": "attributed_clicks_or_orders_unavailable",
                },
                "attributed_order_revenue_jpy": {
                    "value": None,
                    "reason": "no_attributed_data",
                },
            },
            "unavailable_metrics": [
                "attributed_clicks",
                "attributed_orders",
            ],
            "notable_changes": [
                {
                    "metric": "registered_items",
                    "previous": 80,
                    "current": 100,
                    "delta": 20,
                    "percent_change": 0.25,
                }
            ],
        },
    }


def test_weekly_payload_contains_business_summary():
    payload = build_periodic_report_slack_payload(
        report_type="weekly",
        core_result=_core_result(),
    )

    assert "週次" in payload.text
    rendered = str(payload.blocks)

    assert "100" in rendered
    assert "90.0%" in rendered
    assert "N/A (no_attributed_data)" in rendered
    assert "registered_items" in rendered
    assert "未取得KPI" in rendered


def test_monthly_payload_changes_label():
    payload = build_periodic_report_slack_payload(
        report_type="monthly",
        core_result=_core_result(),
    )

    assert "月次" in payload.text


def test_non_ok_core_is_rejected():
    try:
        build_periodic_report_slack_payload(
            report_type="weekly",
            core_result={"status": "NOT_FOUND"},
        )
    except SlackPeriodicReportError:
        return

    raise AssertionError("expected SlackPeriodicReportError")
