from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.x_analytics import XAnalyticsImportRun, XAnalyticsMetricSnapshot
from core.x_analytics_advisory_reader import XAnalyticsAdvisoryReader


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv/bin/python"


def test_periodic_runner_regenerates_same_period_and_updates_core_latest(
    tmp_path: Path,
) -> None:
    database = tmp_path / "periodic.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
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
                row_count=1,
                status="SUCCEEDED",
            )
        )
        session.add(
            XAnalyticsMetricSnapshot(
                id="snapshot",
                observation_key="c" * 64,
                source="fixture",
                account_identifier="account:test",
                post_id="1",
                posted_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
                post_type="release",
                metric_scope="lifetime",
                observed_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
                impressions=100,
                link_status="UNMATCHED",
                first_import_run_id="run",
                last_import_run_id="run",
            )
        )
        session.commit()
    engine.dispose()
    reports = tmp_path / "reports"
    advisory = tmp_path / "advisory"
    environment = {
        **os.environ,
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": f"sqlite:///{database}",
        "PYTHONPATH": str(ROOT),
        "AI_MEDIA_OS_TESTING": "1",
    }
    command = [
        str(PYTHON),
        "scripts/run_x_analytics_periodic_export.py",
        "weekly",
        "--period",
        "2026W36",
        "--report-dir",
        str(reports),
        "--export-root",
        str(advisory),
    ]
    first = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True
    )
    second = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["report_id"] == second_payload["report_id"]
    assert Path(second_payload["json_path"]).is_file()
    assert Path(second_payload["markdown_path"]).is_file()
    latest = XAnalyticsAdvisoryReader(advisory).get_latest_weekly()
    assert latest["status"] in {"OK", "STALE"}
    assert isinstance(
        latest["snapshot"]["business_metrics"],
        dict,
    )
    assert (
        latest["snapshot"]["business_metrics"][
            "registered_items"
        ]["value"]
        == 0
    )


def test_periodic_runner_accepts_reproducible_rolling_reference(
    tmp_path: Path,
) -> None:
    database = tmp_path / "rolling.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    engine.dispose()
    reports = tmp_path / "reports"
    advisory = tmp_path / "advisory"
    environment = {
        **os.environ,
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": f"sqlite:///{database}",
        "PYTHONPATH": str(ROOT),
        "AI_MEDIA_OS_TESTING": "1",
    }
    result = subprocess.run(
        [
            str(PYTHON),
            "scripts/run_x_analytics_periodic_export.py",
            "monthly",
            "--period-mode",
            "rolling",
            "--reference-at",
            "2026-03-31T21:15:00Z",
            "--timezone",
            "UTC",
            "--source",
            "x_api_v2",
            "--report-dir",
            str(reports),
            "--export-root",
            str(advisory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    report = json.loads(Path(payload["json_path"]).read_text(encoding="utf-8"))
    assert report["period_strategy"]["mode"] == "rolling"
    assert report["period_strategy"]["reference_at"] == "2026-03-31T21:15:00+00:00"
    assert report["aggregation"]["start"] == "2026-02-28T21:15:00+00:00"
    assert report["comparison"]["period"]["start"] == "2026-01-28T21:15:00+00:00"
    assert report["overall"]["kpis"]["reach"]["value"] is None
    assert report["overall"]["kpis"]["reach"]["reason"]
    assert report["aggregation"]["source_filter"] == "x_api_v2"


def test_disabled_marker_blocks_export_but_not_report_generation(
    tmp_path: Path,
) -> None:
    database = tmp_path / "disabled.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    engine.dispose()
    reports = tmp_path / "reports"
    advisory = tmp_path / "advisory"
    advisory.mkdir()
    (advisory / "DISABLED").write_text("disabled\n", encoding="utf-8")
    environment = {
        **os.environ,
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": f"sqlite:///{database}",
        "PYTHONPATH": str(ROOT),
        "AI_MEDIA_OS_TESTING": "1",
    }
    result = subprocess.run(
        [
            str(PYTHON),
            "scripts/run_x_analytics_periodic_export.py",
            "weekly",
            "--period",
            "2026W36",
            "--report-dir",
            str(reports),
            "--export-root",
            str(advisory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "disabled" in result.stderr
    assert list(reports.glob("*.json"))
    assert list(reports.glob("*.md"))