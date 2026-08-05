import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from legal_compliance_gate_ai.core.observation_metrics import (
    build_legal_observation_kpis,
    build_windowed_legal_observation_kpis,
    write_kpi_report,
)


def _write_observation(
    path: Path,
    *,
    status: str,
    risk_ids: list[str],
    human_review: bool,
    observed_at_utc: str | None = None,
) -> None:
    detected_risks = [{"risk_id": rid} for rid in risk_ids]
    payload = {
        "event_id": path.stem,
        "observed_at_utc": observed_at_utc,
        "decision_package": {
            "legal_gate": {
                "status": status,
                "detected_risks": detected_risks,
                "human_review_required": human_review,
            }
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_legal_observation_kpis(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir(parents=True, exist_ok=True)

    _write_observation(
        obs / "legal_gate_observation_1.json",
        status="LEGAL_REVIEW_REQUIRED",
        risk_ids=["AFFILIATE_DISCLOSURE_REQUIRED", "API_TERMS_CHECK_REQUIRED"],
        human_review=True,
    )
    _write_observation(
        obs / "legal_gate_observation_2.json",
        status="PASS",
        risk_ids=[],
        human_review=False,
    )
    _write_observation(
        obs / "legal_gate_observation_3.json",
        status="ABORT",
        risk_ids=["SECRETS_EXPOSURE_RISK"],
        human_review=True,
    )

    report = build_legal_observation_kpis(obs)

    assert report["total_observations"] == 3
    kpis = report["kpis"]
    assert kpis["legal_warn_rate"] == 0.666667
    assert kpis["disclosure_missing_rate"] == 0.333333
    assert kpis["api_terms_pending_rate"] == 0.333333
    assert kpis["secret_abort_count"] == 1
    assert kpis["human_legal_review_rate"] == 0.666667


def test_write_kpi_report(tmp_path):
    report = {
        "total_observations": 0,
        "kpis": {
            "legal_warn_rate": 0.0,
            "disclosure_missing_rate": 0.0,
            "api_terms_pending_rate": 0.0,
            "secret_abort_count": 0,
            "human_legal_review_rate": 0.0,
        },
    }

    output = tmp_path / "reports" / "kpi.json"
    write_kpi_report(report, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["kpis"]["secret_abort_count"] == 0


def test_build_windowed_legal_observation_kpis(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir(parents=True, exist_ok=True)

    base_now = datetime(2026, 5, 24, 4, 0, 0, tzinfo=timezone.utc)

    _write_observation(
        obs / "legal_gate_observation_recent.json",
        status="LEGAL_REVIEW_REQUIRED",
        risk_ids=["AFFILIATE_DISCLOSURE_REQUIRED", "API_TERMS_CHECK_REQUIRED"],
        human_review=True,
        observed_at_utc=(base_now - timedelta(days=2)).isoformat(),
    )
    _write_observation(
        obs / "legal_gate_observation_mid.json",
        status="PASS",
        risk_ids=[],
        human_review=False,
        observed_at_utc=(base_now - timedelta(days=20)).isoformat(),
    )
    _write_observation(
        obs / "legal_gate_observation_old.json",
        status="ABORT",
        risk_ids=["SECRETS_EXPOSURE_RISK"],
        human_review=True,
        observed_at_utc=(base_now - timedelta(days=45)).isoformat(),
    )

    report = build_windowed_legal_observation_kpis(obs, now_utc=base_now)

    assert report["window_metrics"]["7d"]["total_observations"] == 1
    assert report["window_metrics"]["30d"]["total_observations"] == 2
    assert report["window_metrics"]["all"]["total_observations"] == 3

    assert report["window_metrics"]["7d"]["kpis"]["legal_warn_rate"] == 1.0
    assert report["window_metrics"]["30d"]["kpis"]["legal_warn_rate"] == 0.5
    assert report["window_metrics"]["all"]["kpis"]["secret_abort_count"] == 1


def test_build_windowed_legal_observation_kpis_handles_zero_and_missing_timestamp(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir(parents=True, exist_ok=True)

    base_now = datetime(2026, 5, 24, 4, 0, 0, tzinfo=timezone.utc)

    _write_observation(
        obs / "legal_gate_observation_no_ts.json",
        status="WARN",
        risk_ids=[],
        human_review=True,
        observed_at_utc=None,
    )

    report = build_windowed_legal_observation_kpis(obs, now_utc=base_now)
    assert report["records_missing_timestamp"] == 1
    assert report["window_metrics"]["7d"]["total_observations"] == 0
    assert report["window_metrics"]["7d"]["kpis"]["legal_warn_rate"] == 0.0
    assert report["window_metrics"]["all"]["total_observations"] == 1

    empty = build_windowed_legal_observation_kpis(tmp_path / "missing_dir", now_utc=base_now)
    assert empty["window_metrics"]["7d"]["total_observations"] == 0
    assert empty["window_metrics"]["30d"]["total_observations"] == 0
    assert empty["window_metrics"]["all"]["kpis"]["secret_abort_count"] == 0
