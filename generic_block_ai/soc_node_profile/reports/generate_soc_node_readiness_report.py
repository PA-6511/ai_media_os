from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def generate_report(base_dir: Path) -> dict:
    manifest_path = base_dir / "soc_block_manifest.json"
    resource_policy_path = base_dir / "policy" / "soc_node_resource_limits.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resource_policy = json.loads(resource_policy_path.read_text(encoding="utf-8"))

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "SoC-0",
        "status": manifest.get("status", "DESIGN_ONLY"),
        "production_status": manifest.get("production_status", "NO_GO"),
        "execution": manifest.get("execution", "DRY_RUN"),
        "recommended_task_size": resource_policy.get("recommended_task_size", "SMALL"),
        "ready_for_production": False,
        "notes": [
            "DESIGN_ONLY scaffold",
            "DRY_RUN_ONLY execution policy",
            "human review required",
        ],
    }
    return report


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    report_dir = base_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report = generate_report(base_dir)
    output_path = report_dir / "soc_node_readiness_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
