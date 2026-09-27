from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from analytics.x_core_advisory.contract import build_advisory_snapshot
from analytics.x_core_advisory.store import XCoreAdvisoryStore
from core.core_ai.module import Module
from core.x_analytics_advisory_reader import XAnalyticsAdvisoryReader
from tests.test_x_core_advisory_contract import phase2_report, write_report


class FakeReader:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_latest(self, report_type):
        self.calls.append(report_type)
        return self.payload


def test_core_ai_reads_advisory_through_existing_evaluate_path() -> None:
    reader = FakeReader(
        {
            "status": "OK",
            "reason": None,
            "snapshot": {
                "snapshot_id": "xadv-test",
                "report_type": "weekly",
                "recommended_actions": [
                    {
                        "rule_id": "RULE_LOW",
                        "summary": "Review low priority evidence",
                        "target_period": {"start": "a", "end": "b"},
                        "sample_size": 3,
                        "constraints": ["advisory_only"],
                        "advisory_only": True,
                        "execution_allowed": False,
                    },
                    {
                        "rule_id": "RULE_HIGH",
                        "summary": "Review high priority evidence",
                        "target_period": {"start": "a", "end": "b"},
                        "sample_size": 5,
                        "constraints": ["advisory_only"],
                        "advisory_only": True,
                        "execution_allowed": False,
                    },
                ],
            },
        }
    )
    result = Module().evaluate_x_analytics_advisory(
        reader=reader, report_type="weekly"
    )
    assert reader.calls == ["weekly"]
    assert result["status"] == "OK"
    assert result["proposal_count"] == 2
    assert result["selected_proposal"]["advisory_only"] is True
    assert result["selected_proposal"]["execution_allowed"] is False
    assert "command" not in result["selected_proposal"]


def test_core_ai_does_not_evaluate_missing_snapshot() -> None:
    reader = FakeReader({"status": "MISSING", "reason": "not_generated"})
    result = Module().evaluate_x_analytics_advisory(reader=reader)
    assert result["selected_proposal"] is None
    assert result["advisory_only"] is True
    assert result["business_analysis"]["status"] == "UNAVAILABLE"
    assert (
        result["business_analysis"]["reason"]
        == "business_metrics_not_available"
    )


def test_real_export_reader_core_consumer_path_is_read_only(
    tmp_path: Path,
) -> None:
    source = phase2_report()
    source_path = write_report(tmp_path, source)
    generated = datetime(2026, 9, 8, tzinfo=timezone.utc)
    snapshot = build_advisory_snapshot(
        source,
        report_type="x_kpi_summary",
        source_path=source_path,
        generated_at=generated,
    )
    export_root = tmp_path / "export"
    XCoreAdvisoryStore(export_root).publish(snapshot)
    before = {
        path.relative_to(export_root).as_posix(): path.read_bytes()
        for path in export_root.rglob("*")
        if path.is_file()
    }
    result = Module().evaluate_x_analytics_advisory(
        reader=XAnalyticsAdvisoryReader(export_root)
    )
    after = {
        path.relative_to(export_root).as_posix(): path.read_bytes()
        for path in export_root.rglob("*")
        if path.is_file()
    }
    assert result["status"] in {"OK", "STALE"}
    assert result["selected_proposal"]["execution_allowed"] is False
    assert before == after


def test_core_ai_exposes_business_analysis_without_execution() -> None:
    reader = FakeReader(
        {
            "status": "OK",
            "reason": None,
            "snapshot": {
                "snapshot_id": "xadv-business",
                "report_type": "weekly",
                "period": {
                    "start": "2026-09-01T00:00:00+00:00",
                    "end": "2026-09-08T00:00:00+00:00",
                    "timezone": "UTC",
                    "semantics":
                        "half_open_start_inclusive_end_exclusive",
                },
                "business_metrics": {
                    "registered_items": {
                        "value": 12,
                        "reason": None,
                        "basis": "fixture_registered",
                    },
                    "registered_item_cover_rate_current": {
                        "value": 0.8,
                        "reason": None,
                        "basis": "fixture_cover",
                    },
                    "attributed_clicks": {
                        "value": None,
                        "reason": "no_attributed_data",
                        "basis": "fixture_attribution",
                    },
                    "attributed_order_revenue_jpy": {
                        "value": None,
                        "reason": "no_attributed_data",
                        "basis": "fixture_attribution",
                    },
                },
                "comparison": {
                    "business_metrics": {
                        "registered_items": {
                            "value": 2,
                            "reason": None,
                            "current": 12,
                            "previous": 10,
                            "percent_change": 0.2,
                            "percent_change_reason": None,
                        },
                        "registered_item_cover_rate_current": {
                            "value": 0.3,
                            "reason": None,
                            "current": 0.8,
                            "previous": 0.5,
                            "percent_change": 0.6,
                            "percent_change_reason": None,
                        },
                        "attributed_clicks": {
                            "value": None,
                            "reason":
                                "current_value_unavailable",
                        },
                        "attributed_order_revenue_jpy": {
                            "value": None,
                            "reason":
                                "current_value_unavailable",
                        },
                    },
                },
                "recommended_actions": [
                    {
                        "rule_id": "RULE_BUSINESS",
                        "summary": "Review evidence",
                        "target_period": {
                            "start": "a",
                            "end": "b",
                        },
                        "sample_size": 1,
                        "constraints": [
                            "advisory_only",
                        ],
                        "advisory_only": True,
                        "execution_allowed": False,
                    }
                ],
            },
        }
    )

    result = Module().evaluate_x_analytics_advisory(
        reader=reader,
        report_type="weekly",
    )

    analysis = result[
        "business_analysis"
    ]

    assert analysis["status"] == "OK"

    assert (
        analysis[
            "current_metrics"
        ][
            "registered_items"
        ][
            "value"
        ]
        == 12
    )

    assert analysis["unavailable_metrics"] == [
        "attributed_clicks",
        "attributed_order_revenue_jpy",
    ]

    assert (
        analysis[
            "notable_changes"
        ][0][
            "metric"
        ]
        == "registered_item_cover_rate_current"
    )

    assert (
        analysis[
            "notable_changes"
        ][0][
            "percent_change"
        ]
        == 0.6
    )

    assert result[
        "selected_proposal"
    ][
        "execution_allowed"
    ] is False

    assert (
        "command"
        not in result[
            "selected_proposal"
        ]
    )
