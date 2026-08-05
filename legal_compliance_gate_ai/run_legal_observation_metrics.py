from pathlib import Path

from core.observation_metrics import (
    build_legal_observation_kpis,
    build_windowed_legal_observation_kpis,
    write_kpi_report,
)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    observations_dir = repo_root / "reports" / "legal_compliance_gate_observations"
    output_all = repo_root / "reports" / "legal_compliance_gate_observation_metrics.json"
    output_7d = repo_root / "reports" / "legal_compliance_gate_observation_metrics_7d.json"
    output_30d = repo_root / "reports" / "legal_compliance_gate_observation_metrics_30d.json"
    output_windows = repo_root / "reports" / "legal_compliance_gate_observation_metrics_windows.json"

    all_report = build_legal_observation_kpis(observations_dir)
    windowed_report = build_windowed_legal_observation_kpis(observations_dir)

    write_kpi_report(all_report, output_all)
    write_kpi_report(windowed_report, output_windows)
    write_kpi_report(windowed_report.get("window_metrics", {}).get("7d", {}), output_7d)
    write_kpi_report(windowed_report.get("window_metrics", {}).get("30d", {}), output_30d)

    kpis = all_report.get("kpis", {})
    window_metrics = windowed_report.get("window_metrics", {})
    kpis_7d = window_metrics.get("7d", {}).get("kpis", {})
    kpis_30d = window_metrics.get("30d", {}).get("kpis", {})

    print(f"total_observations: {all_report.get('total_observations', 0)}")
    print(f"legal_warn_rate: {kpis.get('legal_warn_rate', 0.0)}")
    print(f"disclosure_missing_rate: {kpis.get('disclosure_missing_rate', 0.0)}")
    print(f"api_terms_pending_rate: {kpis.get('api_terms_pending_rate', 0.0)}")
    print(f"secret_abort_count: {kpis.get('secret_abort_count', 0)}")
    print(f"human_legal_review_rate: {kpis.get('human_legal_review_rate', 0.0)}")
    print(f"7d_legal_warn_rate: {kpis_7d.get('legal_warn_rate', 0.0)}")
    print(f"30d_legal_warn_rate: {kpis_30d.get('legal_warn_rate', 0.0)}")
    print(f"report_path_all: {output_all}")
    print(f"report_path_7d: {output_7d}")
    print(f"report_path_30d: {output_30d}")
    print(f"report_path_windows: {output_windows}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
