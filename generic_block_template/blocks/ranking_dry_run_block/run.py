from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
RANKING_POLICY_PATH = ROOT / "config/ranking_policy.json"
FIXTURE_PATH = TEMPLATE_ROOT / "fixtures/ranking_sample_items.json"
LOG_DIR = TEMPLATE_ROOT / "logs"
ROOT_LOG_DIR = ROOT / "logs"
JSON_LOG_PATH = LOG_DIR / "ranking_dry_run_preview.json"
MD_LOG_PATH = LOG_DIR / "ranking_dry_run_preview.md"


DEFAULT_WEIGHTS = {
    "new_release_weight": 0.35,
    "sale_weight": 0.30,
    "author_weight": 0.20,
    "publisher_weight": 0.15,
}


def load_ranking_weights(policy_path: Path = RANKING_POLICY_PATH) -> Dict[str, float]:
    if not policy_path.exists():
        return dict(DEFAULT_WEIGHTS)

    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    weights = payload.get("weights", {})

    return {
        "new_release_weight": float(weights.get("new_release_weight", DEFAULT_WEIGHTS["new_release_weight"])),
        "sale_weight": float(weights.get("sale_weight", DEFAULT_WEIGHTS["sale_weight"])),
        "author_weight": float(weights.get("author_weight", DEFAULT_WEIGHTS["author_weight"])),
        "publisher_weight": float(weights.get("publisher_weight", DEFAULT_WEIGHTS["publisher_weight"])),
    }


def load_ranking_items(fixture_path: Path = FIXTURE_PATH) -> tuple[str, List[Dict[str, Any]], str]:
    if not fixture_path.exists():
        return "FAIL", [], f"fixture not found: {fixture_path}"

    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return "FAIL", [], f"invalid fixture json: {exc}"

    if not isinstance(payload, list):
        return "FAIL", [], "fixture must be a list"

    if not payload:
        return "WARN", [], "fixture is empty"

    required_keys = {
        "item_id",
        "title",
        "new_release_score",
        "sale_score",
        "author_score",
        "publisher_score",
    }

    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            return "FAIL", [], f"fixture item at index {index} must be an object"

        missing = sorted(required_keys - set(item.keys()))
        if missing:
            return "FAIL", [], f"fixture item at index {index} missing keys: {', '.join(missing)}"

        normalized.append(dict(item))

    return "PASS", normalized, "fixture loaded"


def _score_item(item: Dict[str, Any], weights: Dict[str, float]) -> float:
    return round(
        float(item.get("new_release_score", 0.0)) * weights["new_release_weight"]
        + float(item.get("sale_score", 0.0)) * weights["sale_weight"]
        + float(item.get("author_score", 0.0)) * weights["author_weight"]
        + float(item.get("publisher_score", 0.0)) * weights["publisher_weight"],
        4,
    )


def build_ranking_preview(items: List[Dict[str, Any]], weights: Dict[str, float] | None = None) -> List[Dict[str, Any]]:
    active_weights = weights or load_ranking_weights()
    ranked: List[Dict[str, Any]] = []
    for item in items:
        scored = dict(item)
        scored["ranking_score"] = _score_item(scored, active_weights)
        ranked.append(scored)

    ranked.sort(key=lambda entry: entry["ranking_score"], reverse=True)

    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    return ranked


def write_preview_evidence(payload: Dict[str, Any], log_dir: Path = LOG_DIR) -> Dict[str, str]:
    lines = [
        "# Ranking DRY_RUN Preview",
        "",
        f"- status: {payload.get('status', 'FAIL')}",
        f"- mode: {payload.get('mode', 'UNKNOWN')}",
        f"- production_status: {payload.get('production_status', 'UNKNOWN')}",
        f"- policy_path: {payload.get('policy_path', '')}",
        f"- input_source: {payload.get('input_source', '')}",
        f"- input_status: {payload.get('input_status', '')}",
        "",
        "## Weights",
    ]
    for key, value in payload.get("weights", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Ranking Preview"])
    for item in payload.get("ranking_preview", []):
        lines.append(
            f"- rank={item.get('rank')} item_id={item.get('item_id')} title={item.get('title')} score={item.get('ranking_score')}"
        )

    outputs = {
        "template_json": str(log_dir / JSON_LOG_PATH.name),
        "template_md": str(log_dir / MD_LOG_PATH.name),
        "root_json": str(ROOT_LOG_DIR / JSON_LOG_PATH.name),
        "root_md": str(ROOT_LOG_DIR / MD_LOG_PATH.name),
    }

    for current_dir in (log_dir, ROOT_LOG_DIR):
        current_dir.mkdir(parents=True, exist_ok=True)
        (current_dir / JSON_LOG_PATH.name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (current_dir / MD_LOG_PATH.name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return outputs


def run_block(fixture_path: Path = FIXTURE_PATH) -> dict:
    weights = load_ranking_weights()
    input_status, items, input_reason = load_ranking_items(fixture_path)
    ranking_preview = build_ranking_preview(items, weights) if items else []

    status = input_status
    reason = input_reason
    if input_status == "PASS":
        reason = "ranking preview generated from fixture input"

    payload = {
        "block_id": "ranking_dry_run_block",
        "status": status,
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "reason": reason,
        "policy_path": str(RANKING_POLICY_PATH),
        "input_source": str(fixture_path),
        "input_status": input_status,
        "input_item_count": len(items),
        "weights": weights,
        "ranking_preview": ranking_preview,
        "execution_enabled": False,
        "external_api_called": False,
        "external_network_called": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["evidence_paths"] = write_preview_evidence(payload)
    return payload


def main() -> int:
    payload = run_block()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
