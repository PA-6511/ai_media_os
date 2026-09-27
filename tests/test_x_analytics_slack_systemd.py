from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEMD = ROOT / "systemd"


def _read(name: str) -> str:
    return (
        SYSTEMD / name
    ).read_text(
        encoding="utf-8"
    )


def test_weekly_report_triggers_weekly_slack_on_success():
    text = _read(
        "ai-media-os-x-analytics-weekly-report.service"
    )

    assert (
        "OnSuccess="
        "ai-media-os-x-analytics-weekly-slack.service"
        in text
    )

    # Existing report sandbox remains network-disabled.
    assert (
        "RestrictAddressFamilies=AF_UNIX"
        in text
    )


def test_monthly_report_triggers_monthly_slack_on_success():
    text = _read(
        "ai-media-os-x-analytics-monthly-report.service"
    )

    assert (
        "OnSuccess="
        "ai-media-os-x-analytics-monthly-slack.service"
        in text
    )

    assert (
        "RestrictAddressFamilies=AF_UNIX"
        in text
    )


def test_weekly_slack_service_contract():
    text = _read(
        "ai-media-os-x-analytics-weekly-slack.service"
    )

    assert (
        "EnvironmentFile=/etc/ai-media-os/slack.env"
        in text
    )

    assert (
        "EnvironmentFile=/etc/ai-media-os/credential.env"
        in text
    )

    assert (
        "send_slack_periodic_report.py weekly --send"
        in text
    )

    assert (
        "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6"
        in text
    )


def test_monthly_slack_service_contract():
    text = _read(
        "ai-media-os-x-analytics-monthly-slack.service"
    )

    assert (
        "EnvironmentFile=/etc/ai-media-os/slack.env"
        in text
    )

    assert (
        "EnvironmentFile=/etc/ai-media-os/credential.env"
        in text
    )

    assert (
        "send_slack_periodic_report.py monthly --send"
        in text
    )

    assert (
        "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6"
        in text
    )


def test_slack_services_do_not_change_report_generation():
    weekly = _read(
        "ai-media-os-x-analytics-weekly-slack.service"
    )

    monthly = _read(
        "ai-media-os-x-analytics-monthly-slack.service"
    )

    for text in (weekly, monthly):
        assert (
            "run_x_analytics_periodic_export.py"
            not in text
        )
        assert "wordpress" not in text.lower()
        assert "x_publish" not in text.lower()
