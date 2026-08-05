import json
import tempfile
from pathlib import Path

from core.exchange_validator import validate_package
from scripts.run_exchange_connection_dry_run import run_dry_run

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _patch_proposal() -> dict:
    return {
        "package_type": "patch_proposal",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "proposal_id": "realdata-patch-001",
        "title": "realdata patch",
        "description": "safe patch",
    }


def _test_report_pass() -> dict:
    return {
        "package_type": "test_report",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "tests": {
            "schema_check": "PASS",
            "link_check": "PASS",
            "wp_post": "PASS",
            "secret_access_check": "PASS",
            "dangerous_operation_check": "PASS",
        },
    }


def test_realdata_normal_example_passes_validator():
    path = ROOT / "exchange/incoming/decision_package.realdata.normal.example.json"
    result = validate_package("decision_package", path)
    assert result["status"] == "PASS", result


def test_realdata_warn_example_warns_validator():
    path = ROOT / "exchange/incoming/decision_package.realdata.warn.example.json"
    result = validate_package("decision_package", path)
    assert result["status"] == "WARN", result


def test_realdata_abort_example_aborts_validator():
    path = ROOT / "exchange/incoming/decision_package.realdata.abort.example.json"
    result = validate_package("decision_package", path)
    assert result["status"] == "ABORT", result


def test_realdata_normal_package_runs_through_dry_run_flow_and_records_source_builder():
    decision = _load(ROOT / "exchange/incoming/decision_package.realdata.normal.example.json")

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        decision_path = tmpdir / "decision_package.json"
        patch_path = tmpdir / "patch_proposal.json"
        report_path = tmpdir / "test_report.json"
        output_path = tmpdir / "validation_result.json"

        _write(decision_path, decision)
        _write(patch_path, _patch_proposal())
        _write(report_path, _test_report_pass())

        result = run_dry_run(
            package_files={
                "decision_package": decision_path,
                "patch_proposal": patch_path,
                "test_report": report_path,
            },
            output_path=output_path,
        )

        assert result["overall_status"] == "PASS", result
        assert result["source_builder"]["type"] == "LOCAL_SELF_BUILDER"
        assert result["source_builder"]["location"] == "local"
        assert result["source_builder"]["execution_allowed"] is False


def test_realdata_warn_package_runs_through_dry_run_flow_as_warn():
    decision = _load(ROOT / "exchange/incoming/decision_package.realdata.warn.example.json")

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        decision_path = tmpdir / "decision_package.json"
        patch_path = tmpdir / "patch_proposal.json"
        report_path = tmpdir / "test_report.json"
        output_path = tmpdir / "validation_result.json"

        _write(decision_path, decision)
        _write(patch_path, _patch_proposal())
        _write(report_path, _test_report_pass())

        result = run_dry_run(
            package_files={
                "decision_package": decision_path,
                "patch_proposal": patch_path,
                "test_report": report_path,
            },
            output_path=output_path,
        )

        assert result["overall_status"] == "WARN", result
        assert result["human_review_required"] is True


def test_realdata_abort_package_stops_dry_run_flow_with_abort():
    decision = _load(ROOT / "exchange/incoming/decision_package.realdata.abort.example.json")

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        decision_path = tmpdir / "decision_package.json"
        patch_path = tmpdir / "patch_proposal.json"
        report_path = tmpdir / "test_report.json"
        output_path = tmpdir / "validation_result.json"

        _write(decision_path, decision)
        _write(patch_path, _patch_proposal())
        _write(report_path, _test_report_pass())

        result = run_dry_run(
            package_files={
                "decision_package": decision_path,
                "patch_proposal": patch_path,
                "test_report": report_path,
            },
            output_path=output_path,
        )

        assert result["overall_status"] == "ABORT", result
        assert result["next_step"] == "ABORT_STOP"
