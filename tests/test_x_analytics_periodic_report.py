from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory
from app.db.models.x_analytics import XAnalyticsImportRun, XAnalyticsMetricSnapshot
from app.db.models.sale_roundup import (
    SaleCampaign,
    SaleCopyVariant,
    SaleExperiment,
    SaleMetricSnapshot,
    SaleOffer,
)

from reporting.x_analytics_periodic_report import (
    collect_business_metrics,
    build_periodic_report,
    resolve_periodic_windows,
    write_periodic_report,
)


UTC = timezone.utc


def test_rolling_weekly_year_boundary_and_previous_period() -> None:
    windows = resolve_periodic_windows(
        "weekly",
        period_mode="rolling",
        timezone_name="UTC",
        reference_at=datetime(2027, 1, 1, 6, 30, tzinfo=UTC),
    )
    assert windows.current_start == datetime(2026, 12, 25, 6, 30, tzinfo=UTC)
    assert windows.current_end == datetime(2027, 1, 1, 6, 30, tzinfo=UTC)
    assert windows.previous_start == datetime(2026, 12, 18, 6, 30, tzinfo=UTC)
    assert windows.previous_end == windows.current_start


def test_rolling_monthly_clamps_month_end_and_is_reproducible() -> None:
    reference = datetime(2026, 3, 31, 21, 15, tzinfo=UTC)
    first = resolve_periodic_windows(
        "monthly",
        period_mode="rolling",
        timezone_name="UTC",
        reference_at=reference,
    )
    second = resolve_periodic_windows(
        "monthly",
        period_mode="rolling",
        timezone_name="UTC",
        reference_at=reference,
    )
    assert first == second
    assert first.current_start == datetime(2026, 2, 28, 21, 15, tzinfo=UTC)
    assert first.previous_start == datetime(2026, 1, 28, 21, 15, tzinfo=UTC)


def test_calendar_month_year_boundary_and_timezone() -> None:
    windows = resolve_periodic_windows(
        "monthly",
        period_mode="calendar",
        period_key="202601",
        timezone_name="Asia/Tokyo",
        reference_at=datetime(2026, 1, 15, tzinfo=UTC),
    )
    assert windows.current_start.isoformat() == "2026-01-01T00:00:00+09:00"
    assert windows.previous_start.isoformat() == "2025-12-01T00:00:00+09:00"
    assert windows.previous_end == windows.current_start


def seed_report_data(session: Session, root: Path) -> None:
    current = EbookItem(
        id="current",
        source_name="fixture",
        source_item_id="current",
        title="Current",
        item_type="tankobon",
        wordpress_status="DRAFT",
        image_status="READY",
        cover_status="AUTO_ALLOWED",
        created_at=datetime(2026, 9, 2, tzinfo=UTC),
        updated_at=datetime(2026, 9, 2, tzinfo=UTC),
    )
    previous = EbookItem(
        id="previous",
        source_name="fixture",
        source_item_id="previous",
        title="Previous",
        item_type="tankobon",
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    session.add_all((current, previous))

    current_campaign = SaleCampaign(
        id="campaign-current",
        title="Current Campaign",
        snapshot_hash="c" * 64,
        starts_at="2026-09-01T00:00:00+00:00",
        ends_at="2026-09-30T00:00:00+00:00",
        imported_at="2026-09-03T00:00:00+00:00",
        source_generated_at="2026-09-03T00:00:00+00:00",
    )
    previous_campaign = SaleCampaign(
        id="campaign-previous",
        title="Previous Campaign",
        snapshot_hash="d" * 64,
        starts_at="2026-08-25T00:00:00+00:00",
        ends_at="2026-08-31T23:59:59+00:00",
        imported_at="2026-08-27T00:00:00+00:00",
        source_generated_at="2026-08-27T00:00:00+00:00",
    )

    current_experiment = SaleExperiment(
        id="experiment-current",
        campaign_id="campaign-current",
        snapshot_hash="e" * 64,
        snapshot={
            "items": [
                {
                    "ebook_item_id": "current",
                }
            ]
        },
        payload={},
    )
    previous_experiment = SaleExperiment(
        id="experiment-previous",
        campaign_id="campaign-previous",
        snapshot_hash="f" * 64,
        snapshot={
            "items": [
                {
                    "ebook_item_id": "previous",
                }
            ]
        },
        payload={},
    )

    current_variant = SaleCopyVariant(
        id="variant-current",
        experiment_id="experiment-current",
        components={},
        text="current",
        draft_request={},
    )
    previous_variant = SaleCopyVariant(
        id="variant-previous",
        experiment_id="experiment-previous",
        components={},
        text="previous",
        draft_request={},
    )

    session.add_all(
        (
            current_campaign,
            previous_campaign,
            SaleOffer(
                id="offer-current",
                campaign_id="campaign-current",
                ebook_item_id="current",
                data={},
                block_reasons=[],
            ),
            SaleOffer(
                id="offer-previous",
                campaign_id="campaign-previous",
                ebook_item_id="previous",
                data={},
                block_reasons=[],
            ),
            current_experiment,
            previous_experiment,
            current_variant,
            previous_variant,
            SaleMetricSnapshot(
                post_id="sale-post-current",
                variant_id="variant-current",
                posted_at="2026-09-03T00:00:00+00:00",
                observed_at="2026-09-07T00:00:00+00:00",
                source="fixture",
                attribution_basis="exact_post",
                currency="JPY",
                impressions=1000,
                clicks=20,
                orders=4,
                order_revenue=1200.0,
                referral_fee=120.0,
            ),
            SaleMetricSnapshot(
                post_id="sale-post-previous",
                variant_id="variant-previous",
                posted_at="2026-08-27T00:00:00+00:00",
                observed_at="2026-08-31T00:00:00+00:00",
                source="fixture",
                attribution_basis="exact_post",
                currency="JPY",
                impressions=500,
                clicks=10,
                orders=1,
                order_revenue=500.0,
                referral_fee=50.0,
            ),
        )
    )
    session.add_all(
        (
            WorkflowHistory(
                id="wp-current",
                ebook_item_id="current",
                field_name="wordpress_status",
                before_value="DRAFT",
                after_value="PUBLISHED",
                changed_at=datetime(2026, 9, 3, tzinfo=UTC),
            ),
            WorkflowHistory(
                id="failure-current",
                ebook_item_id="current",
                field_name="last_error",
                before_value=None,
                after_value="temporary error",
                changed_at=datetime(2026, 9, 4, tzinfo=UTC),
            ),
            WorkflowHistory(
                id="wp-previous",
                ebook_item_id="previous",
                field_name="wordpress_status",
                before_value="DRAFT",
                after_value="PUBLISHED",
                changed_at=datetime(2026, 8, 27, tzinfo=UTC),
            ),
        )
    )
    session.add(
        XAnalyticsImportRun(
            id="run",
            import_key="a" * 64,
            csv_sha256="b" * 64,
            source="fixture",
            account_identifier="account:test",
            source_filename="fixture.csv",
            metric_scope="lifetime",
            headers_json="[]",
            row_count=2,
            status="SUCCEEDED",
        )
    )
    for identifier, post_id, posted_at, impressions in (
        ("current-snapshot", "post-current", datetime(2026, 9, 2, tzinfo=UTC), 300),
        ("previous-snapshot", "post-previous", datetime(2026, 8, 26, tzinfo=UTC), 100),
    ):
        session.add(
            XAnalyticsMetricSnapshot(
                id=identifier,
                observation_key=identifier.ljust(64, "0")[:64],
                source="fixture",
                account_identifier="account:test",
                post_id=post_id,
                posted_at=posted_at,
                post_type="tankobon",
                metric_scope="lifetime",
                observed_at=posted_at,
                impressions=impressions,
                link_status="UNMATCHED",
                first_import_run_id="run",
                last_import_run_id="run",
            )
        )
    session.commit()
    evidence = root / "exchange/evidence/ebook_autonomy/x_posts"
    evidence.mkdir(parents=True)
    payload = {
        "status": "POSTED",
        "x_post_id": "x-success-current",
        "posted_at": "2026-09-03T00:00:00+00:00",
    }
    (evidence / "one.json").write_text(json.dumps(payload), encoding="utf-8")
    (evidence / "duplicate.json").write_text(json.dumps(payload), encoding="utf-8")


def test_periodic_report_contains_operational_comparison_and_rankings(
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'report.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_report_data(session, tmp_path)
        report = build_periodic_report(
            session,
            report_type="weekly",
            period_mode="rolling",
            reference_at=datetime(2026, 9, 8, tzinfo=UTC),
            generated_at=datetime(2026, 9, 8, tzinfo=UTC),
            timezone_name="UTC",
            repository_root=tmp_path,
        )
    engine.dispose()

    assert report["period_strategy"]["mode"] == "rolling"
    assert report["aggregation"]["start"] == "2026-09-01T00:00:00+00:00"
    assert report["comparison"]["period"]["start"] == "2026-08-25T00:00:00+00:00"
    assert report["comparison"]["measurement_mode"] == report["aggregation"]["mode"]
    assert report["operational_metrics"]["new_release_registrations"]["value"] == 1
    assert report["operational_metrics"]["wordpress_published"]["value"] == 1
    assert report["operational_metrics"]["x_post_success"]["value"] == 1
    assert report["operational_metrics"]["failure_events"]["value"] == 1
    assert report["operational_metrics"]["current_pending"]["value"] == 1

    business = report["business_metrics"]

    assert business["registered_items"]["value"] == 1
    assert business["sale_campaigns_imported"]["value"] == 1
    assert business["sale_offers_imported"]["value"] == 1

    assert (
        business[
            "registered_items_official_cover_ready_current"
        ]["value"]
        == 1
    )

    assert (
        business[
            "registered_item_cover_rate_current"
        ]["value"]
        == 1.0
    )

    assert (
        business[
            "registered_items_wordpress_draft_current"
        ]["value"]
        == 1
    )

    assert business["attributed_post_count"]["value"] == 1
    assert business["attributed_clicks"]["value"] == 20
    assert business["attributed_orders"]["value"] == 4

    assert (
        business[
            "attributed_order_revenue_jpy"
        ]["value"]
        == 1200.0
    )

    assert (
        business[
            "attributed_referral_fee_jpy"
        ]["value"]
        == 120.0
    )

    assert business["attributed_cvr"]["value"] == 0.2

    comparison = report["comparison"]["business_metrics"]

    assert comparison["attributed_clicks"]["value"] == 10
    assert comparison["attributed_orders"]["value"] == 3
    assert (
        comparison[
            "attributed_order_revenue_jpy"
        ]["value"]
        == 700.0
    )
    assert report["comparison"]["operational_metrics"]["new_release_registrations"]["value"] == 0
    assert report["comparison"]["post_type_kpis"][0]["post_type"] == "tankobon"
    assert [row["post_id"] for row in report["top_posts"]] == ["post-current"]
    assert [row["post_id"] for row in report["bottom_posts"]] == ["post-current"]
    assert report["top_posts"][0]["post_url"] is None
    assert report["top_posts"][0]["post_url_reason"] == "post_id_not_numeric"
    assert report["top_posts"][0]["posted_at"] == "2026-09-02T00:00:00+00:00"
    assert report["top_posts"][0]["observed_at"] == "2026-09-02T00:00:00+00:00"
    assert report["top_posts"][0]["metric"] == report["rankings"]["metric"]
    assert "denominator" in report["top_posts"][0]
    assert report["top_posts"][0]["denominator_reason"] == (
        "not_applicable_for_absolute_metric"
    )
    assert report["top_posts"][0]["eligibility"] == {
        "status": "eligible",
        "reasons": [],
    }
    assert len(report["best_patterns"]) <= 3
    assert len(report["worst_patterns"]) <= 3
    assert report["recommended_actions"][0]["rule_id"]
    assert report["recommended_actions"][0]["execution_allowed"] is False

    _, markdown_path = write_periodic_report(report, output_dir=tmp_path / "out")
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## 投稿別 Best 3" in markdown
    assert "## 投稿別 Worst 3" in markdown
    assert "## パターン別ランキングと改善提案" in markdown



def test_missing_attribution_is_not_reported_as_zero(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'no-attribution.db'}"
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        metrics = collect_business_metrics(
            session,
            start=datetime(
                2026,
                9,
                1,
                tzinfo=UTC,
            ),
            end=datetime(
                2026,
                9,
                8,
                tzinfo=UTC,
            ),
        )

    engine.dispose()

    for key in (
        "attributed_clicks",
        "attributed_orders",
        "attributed_order_revenue_jpy",
        "attributed_referral_fee_jpy",
    ):
        assert metrics[key]["value"] is None
        assert (
            metrics[key]["reason"]
            == "no_attributed_data"
        )

    assert metrics["attributed_cvr"]["value"] is None
    assert (
        metrics["attributed_cvr"]["reason"]
        == "attributed_clicks_or_orders_unavailable"
    )
