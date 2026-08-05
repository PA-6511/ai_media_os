import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _iter_observation_files(observations_dir: Path):
    if not observations_dir.exists():
        return []
    return sorted(observations_dir.glob("legal_gate_observation_*.json"))


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_observation_record(path: Path) -> dict[str, Any] | None:
    data = _load_json(path)
    if not isinstance(data, dict):
        return None

    decision_package = data.get("decision_package", {})
    if not isinstance(decision_package, dict):
        return None

    legal_gate = decision_package.get("legal_gate", {})
    if not isinstance(legal_gate, dict):
        return None

    observed_at = _parse_utc_timestamp(data.get("observed_at_utc"))
    return {
        "path": str(path),
        "observed_at_utc": observed_at,
        "legal_gate": legal_gate,
    }


def _build_kpis_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    legal_warn_count = 0
    disclosure_missing_count = 0
    api_terms_pending_count = 0
    secret_abort_count = 0
    human_legal_review_count = 0

    risk_id_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for record in records:
        legal_gate = record.get("legal_gate", {})
        if not isinstance(legal_gate, dict):
            continue

        total += 1

        legal_status = str(legal_gate.get("status", "UNKNOWN"))
        status_counts[legal_status] = status_counts.get(legal_status, 0) + 1

        if legal_status in {"WARN", "LEGAL_REVIEW_REQUIRED", "FAIL", "ABORT"}:
            legal_warn_count += 1

        if legal_status == "ABORT":
            secret_abort_count += 1

        if bool(legal_gate.get("human_review_required", False)):
            human_legal_review_count += 1

        detected_risks = legal_gate.get("detected_risks", [])
        if not isinstance(detected_risks, list):
            detected_risks = []

        risk_ids = set()
        for risk in detected_risks:
            if not isinstance(risk, dict):
                continue
            risk_id = str(risk.get("risk_id", "")).strip()
            if not risk_id:
                continue
            risk_ids.add(risk_id)
            risk_id_counts[risk_id] = risk_id_counts.get(risk_id, 0) + 1

        if "AFFILIATE_DISCLOSURE_REQUIRED" in risk_ids:
            disclosure_missing_count += 1
        if "API_TERMS_CHECK_REQUIRED" in risk_ids:
            api_terms_pending_count += 1

    return {
        "total_observations": total,
        "kpis": {
            "legal_warn_rate": _safe_rate(legal_warn_count, total),
            "disclosure_missing_rate": _safe_rate(disclosure_missing_count, total),
            "api_terms_pending_rate": _safe_rate(api_terms_pending_count, total),
            "secret_abort_count": secret_abort_count,
            "human_legal_review_rate": _safe_rate(human_legal_review_count, total),
        },
        "status_counts": status_counts,
        "risk_id_counts": risk_id_counts,
    }


def build_legal_observation_kpis(observations_dir: Path) -> dict[str, Any]:
    files = _iter_observation_files(observations_dir)
    records: list[dict[str, Any]] = []
    for path in files:
        record = _extract_observation_record(path)
        if record is not None:
            records.append(record)

    aggregated = _build_kpis_from_records(records)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "kpi_scope": "legal_compliance_gate_observation",
        "observations_dir": str(observations_dir),
        **aggregated,
    }


def build_windowed_legal_observation_kpis(
    observations_dir: Path,
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    files = _iter_observation_files(observations_dir)
    records: list[dict[str, Any]] = []
    for path in files:
        record = _extract_observation_record(path)
        if record is not None:
            records.append(record)

    base_now = now_utc.astimezone(timezone.utc) if now_utc else datetime.now(timezone.utc)

    all_metrics = _build_kpis_from_records(records)

    records_with_ts = [r for r in records if isinstance(r.get("observed_at_utc"), datetime)]
    records_7d = [
        r
        for r in records_with_ts
        if r["observed_at_utc"] >= base_now - timedelta(days=7)
    ]
    records_30d = [
        r
        for r in records_with_ts
        if r["observed_at_utc"] >= base_now - timedelta(days=30)
    ]

    return {
        "generated_at_utc": base_now.isoformat(),
        "kpi_scope": "legal_compliance_gate_observation_windowed",
        "observations_dir": str(observations_dir),
        "records_with_timestamp": len(records_with_ts),
        "records_missing_timestamp": max(0, len(records) - len(records_with_ts)),
        "window_metrics": {
            "7d": _build_kpis_from_records(records_7d),
            "30d": _build_kpis_from_records(records_30d),
            "all": all_metrics,
        },
    }


def write_kpi_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
