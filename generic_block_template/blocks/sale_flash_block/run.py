from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path


BLOCK_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BLOCK_DIR / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _overall(statuses: list[str]) -> str:
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "WARN" for status in statuses):
        return "WARN"
    return "PASS"


def run_block() -> dict:
    normalize = _load_module("normalize_sale_candidates", SCRIPTS_DIR / "normalize_sale_candidates.py")
    queue = _load_module("generate_sale_review_queue", SCRIPTS_DIR / "generate_sale_review_queue.py")
    quality_gate = _load_module("apply_sale_review_quality_gate", SCRIPTS_DIR / "apply_sale_review_quality_gate.py")
    readiness = _load_module("check_sale_intake_readiness", SCRIPTS_DIR / "check_sale_intake_readiness.py")
    article_payloads = _load_module("generate_sale_article_payloads", SCRIPTS_DIR / "generate_sale_article_payloads.py")
    human_review_handoff = _load_module("generate_sale_human_review_handoff", SCRIPTS_DIR / "generate_sale_human_review_handoff.py")
    wordpress_draft_handoff = _load_module("generate_wordpress_draft_handoff", SCRIPTS_DIR / "generate_wordpress_draft_handoff.py")
    wordpress_draft_validation = _load_module("validate_wordpress_draft_payloads", SCRIPTS_DIR / "validate_wordpress_draft_payloads.py")
    baseline_lock = _load_module("generate_sale_flash_block_baseline_lock_report", SCRIPTS_DIR / "generate_sale_flash_block_baseline_lock_report.py")
    final_human_approval = _load_module("generate_final_human_approval_package", SCRIPTS_DIR / "generate_final_human_approval_package.py")
    wordpress_dry_run_evidence = _load_module("generate_wordpress_dry_run_execution_evidence", SCRIPTS_DIR / "generate_wordpress_dry_run_execution_evidence.py")
    dry_run_execution_baseline_lock = _load_module("generate_sale_flash_block_dry_run_execution_baseline_lock_report", SCRIPTS_DIR / "generate_sale_flash_block_dry_run_execution_baseline_lock_report.py")
    final_signoff_archive = _load_module("generate_final_signoff_archive", SCRIPTS_DIR / "generate_final_signoff_archive.py")
    governance_boundary_review = _load_module("generate_governance_boundary_review", SCRIPTS_DIR / "generate_governance_boundary_review.py")
    pre_production_baseline_lock = _load_module("generate_pre_production_baseline_lock_report", SCRIPTS_DIR / "generate_pre_production_baseline_lock_report.py")
    report = _load_module("generate_sale_flash_block_report", SCRIPTS_DIR / "generate_sale_flash_block_report.py")

    normalized_result = normalize.normalize_candidates()
    queue_result = queue.generate_review_queue()
    quality_gate_result = quality_gate.apply_quality_gate()
    readiness_result = readiness.check_readiness()
    article_payload_result = article_payloads.generate_article_payloads()
    human_review_handoff_result = human_review_handoff.generate_handoff()
    wordpress_draft_handoff_result = wordpress_draft_handoff.generate_wordpress_draft_handoff()
    sfb6 = wordpress_draft_validation.validate_wordpress_draft_payloads()
    sfb6b = baseline_lock.generate_baseline_lock_report()
    sfb7 = final_human_approval.generate_final_human_approval_package()
    sfb8 = wordpress_dry_run_evidence.generate_wordpress_dry_run_execution_evidence()
    sfb8b = dry_run_execution_baseline_lock.generate_dry_run_execution_baseline_lock_report()
    sfb9 = final_signoff_archive.generate_final_signoff_archive()
    sfb10 = governance_boundary_review.generate_governance_boundary_review()
    sfb10b = pre_production_baseline_lock.generate_pre_production_baseline_lock_report()
    report_result = report.generate_report()

    status = _overall(
        [
            normalized_result.get("status", "FAIL"),
            queue_result.get("status", "FAIL"),
            quality_gate_result.get("status", "FAIL"),
            readiness_result.get("status", "FAIL"),
            article_payload_result.get("status", "FAIL"),
            human_review_handoff_result.get("status", "FAIL"),
            wordpress_draft_handoff_result.get("status", "FAIL"),
            sfb6.get("status", "FAIL"),
            sfb6b.get("status", "FAIL"),
            sfb7.get("status", "FAIL"),
            sfb8.get("status", "FAIL"),
            sfb8b.get("status", "FAIL"),
            sfb9.get("status", "FAIL"),
            sfb10.get("status", "FAIL"),
            sfb10b.get("status", "FAIL"),
            report_result.get("status", "FAIL"),
        ]
    )

    return {
        "block_id": "sale_flash_block",
        "status": status,
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "creators_api_called": False,
        "amazon_scraping_called": False,
        "reason": "local fixture intake pipeline only; no external connectivity",
        "steps": {
            "normalize": normalized_result.get("status", "FAIL"),
            "review_queue": queue_result.get("status", "FAIL"),
            "quality_gate": quality_gate_result.get("status", "FAIL"),
            "readiness": readiness_result.get("status", "FAIL"),
            "article_payloads": article_payload_result.get("status", "FAIL"),
            "human_review_handoff": human_review_handoff_result.get("status", "FAIL"),
            "wordpress_draft_handoff": wordpress_draft_handoff_result.get("status", "FAIL"),
            "sfb6_wordpress_draft_validation": sfb6.get("status", "FAIL"),
            "sfb6b_baseline_lock_report": sfb6b.get("status", "FAIL"),
            "sfb7_final_human_approval_package": sfb7.get("status", "FAIL"),
            "sfb8_wordpress_dry_run_execution_evidence": sfb8.get("status", "FAIL"),
            "sfb8b_dry_run_execution_baseline_lock_report": sfb8b.get("status", "FAIL"),
            "sfb9_final_signoff_archive": sfb9.get("status", "FAIL"),
            "sfb10_governance_boundary_review": sfb10.get("status", "FAIL"),
            "sfb10b_pre_production_baseline_lock_report": sfb10b.get("status", "FAIL"),
            "report": report_result.get("status", "FAIL"),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    import json

    result = run_block()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
