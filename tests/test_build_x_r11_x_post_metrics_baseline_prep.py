from __future__ import annotations

import pytest

from scripts.build_x_r11_x_post_metrics_baseline_prep import (
    CAPTURE_24H_DUE_JST,
    CAPTURE_7D_DUE_JST,
    XPostMetricsBaselineError,
    build_metrics_template,
    validate_pending_template,
)


def test_24h_template_passes() -> None:
    value = build_metrics_template(
        "24H"
    )

    assert value[
        "capture_due_at_jst"
    ] == CAPTURE_24H_DUE_JST

    validate_pending_template(
        value,
        expected_window="24H",
    )


def test_7d_template_passes() -> None:
    value = build_metrics_template(
        "7D"
    )

    assert value[
        "capture_due_at_jst"
    ] == CAPTURE_7D_DUE_JST

    validate_pending_template(
        value,
        expected_window="7D",
    )


def test_invalid_window_fails() -> None:
    with pytest.raises(
        XPostMetricsBaselineError,
        match="unsupported metrics window",
    ):
        build_metrics_template(
            "30D"
        )


def test_prefilled_x_metric_fails() -> None:
    value = build_metrics_template(
        "24H"
    )

    value[
        "x_metrics"
    ]["impressions"] = 1

    with pytest.raises(
        XPostMetricsBaselineError,
        match="must remain empty",
    ):
        validate_pending_template(
            value,
            expected_window="24H",
        )


def test_prefilled_rakuten_metric_fails() -> None:
    value = build_metrics_template(
        "7D"
    )

    value[
        "rakuten_metrics"
    ]["affiliate_clicks"] = 1

    with pytest.raises(
        XPostMetricsBaselineError,
        match="must remain empty",
    ):
        validate_pending_template(
            value,
            expected_window="7D",
        )


def test_prefilled_manual_evidence_fails() -> None:
    value = build_metrics_template(
        "24H"
    )

    value[
        "manual_evidence"
    ][
        "x_metrics_captured_at_utc"
    ] = "2026-07-19T10:00:00Z"

    with pytest.raises(
        XPostMetricsBaselineError,
        match="remain empty",
    ):
        validate_pending_template(
            value,
            expected_window="24H",
        )
