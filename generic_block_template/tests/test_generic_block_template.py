from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_template_check_passes():
    checker = _load_module("checker", SCRIPTS / "check_generic_block_template.py")
    result = checker.check_template(ROOT)
    assert result["status"] == "PASS"


def test_sale_flash_block_design_policy_is_locked_to_no_go():
    policy_path = ROOT / "config/sale_flash_block_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert policy["block_id"] == "sale_flash_block"
    assert policy["lifecycle_phase"] == "DESIGN_POLICY_ONLY"
    assert policy["execution_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["wordpress_allowed"] is False
    assert policy["publish_allowed"] is False


def test_controlled_run_sample_only():
    runner = _load_module("runner", SCRIPTS / "run_generic_controlled_once.py")
    ok = runner.run_once("sample_block")
    ng = runner.run_once("another_block")

    assert ok["status"] == "PASS"
    assert ok["mode"] == "DRY_RUN"
    assert ok["production_status"] == "NO_GO"

    assert ng["status"] == "FAIL"
    assert ng["production_status"] == "NO_GO"


def test_scaffold_generation_creates_files():
    gen = _load_module("scaffold", SCRIPTS / "generate_new_block_from_template.py")
    with tempfile.TemporaryDirectory() as td:
        result = gen.scaffold_block("demo_block", Path(td))
        assert result["status"] == "PASS"
        block_dir = Path(result["target_dir"])
        assert (block_dir / "README.md").exists()
        assert (block_dir / "run.py").exists()


def test_ranking_dry_run_block_preview_is_sorted_and_no_go():
    ranking = _load_module("ranking_block", ROOT / "blocks/ranking_dry_run_block/run.py")
    result = ranking.run_block()
    shared_policy = json.loads((ROOT.parents[0] / "config/ranking_policy.json").read_text(encoding="utf-8"))
    fixture_path = ROOT / "fixtures/ranking_sample_items.json"

    assert result["status"] == "PASS"
    assert result["mode"] == "DRY_RUN"
    assert result["production_status"] == "NO_GO"
    assert result["execution_enabled"] is False
    assert result["external_api_called"] is False
    assert result["external_network_called"] is False
    assert result["policy_path"].endswith("config/ranking_policy.json")
    assert result["input_source"] == str(fixture_path)
    assert result["input_status"] == "PASS"
    assert result["input_item_count"] == 3
    assert result["weights"] == shared_policy["weights"]

    preview = result["ranking_preview"]
    assert len(preview) == 3
    assert preview[0]["ranking_score"] >= preview[1]["ranking_score"] >= preview[2]["ranking_score"]
    assert [item["rank"] for item in preview] == [1, 2, 3]

    json_evidence = ROOT / "logs/ranking_dry_run_preview.json"
    md_evidence = ROOT / "logs/ranking_dry_run_preview.md"
    root_json_evidence = ROOT.parents[0] / "logs/ranking_dry_run_preview.json"
    root_md_evidence = ROOT.parents[0] / "logs/ranking_dry_run_preview.md"
    assert json_evidence.exists()
    assert md_evidence.exists()
    assert root_json_evidence.exists()
    assert root_md_evidence.exists()

    evidence_payload = json.loads(json_evidence.read_text(encoding="utf-8"))
    assert evidence_payload["production_status"] == "NO_GO"
    assert evidence_payload["weights"] == shared_policy["weights"]
    assert evidence_payload["input_source"] == str(fixture_path)
    assert "Ranking DRY_RUN Preview" in md_evidence.read_text(encoding="utf-8")


def test_ranking_dry_run_block_warns_on_empty_fixture():
    ranking = _load_module("ranking_block_warn", ROOT / "blocks/ranking_dry_run_block/run.py")
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td) / "empty.json"
        fixture.write_text("[]\n", encoding="utf-8")
        result = ranking.run_block(fixture)

    assert result["status"] == "WARN"
    assert result["input_status"] == "WARN"
    assert result["input_item_count"] == 0
    assert result["ranking_preview"] == []
    assert result["production_status"] == "NO_GO"


def test_ranking_dry_run_block_fails_on_broken_fixture():
    ranking = _load_module("ranking_block_fail", ROOT / "blocks/ranking_dry_run_block/run.py")
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td) / "broken.json"
        fixture.write_text("{broken json", encoding="utf-8")
        result = ranking.run_block(fixture)

    assert result["status"] == "FAIL"
    assert result["input_status"] == "FAIL"
    assert result["input_item_count"] == 0
    assert result["ranking_preview"] == []
    assert result["production_status"] == "NO_GO"


def test_report_generation_writes_outputs():
    reporter = _load_module("reporter", SCRIPTS / "generate_generic_block_report.py")
    report = reporter.generate_report()
    assert report["status"] in {"PASS", "WARN"}
    assert report["ranking_preview_status"] == "PASS"
    assert report["ranking_input_item_count"] == 3
    assert report["ranking_input_source"].endswith("fixtures/ranking_sample_items.json")
    assert report["ranking_preview_top_item"]["item_id"] == "sample-1"

    json_report = ROOT / "logs/generic_block_report.json"
    md_report = ROOT / "logs/generic_block_report.md"
    assert json_report.exists()
    assert md_report.exists()

    payload = json.loads(json_report.read_text(encoding="utf-8"))
    assert payload["production_status"] == "NO_GO"
    assert payload["ranking_preview_status"] == "PASS"
    assert payload["ranking_input_item_count"] == 3
    assert payload["ranking_preview_top_item"]["item_id"] == "sample-1"

    md_text = md_report.read_text(encoding="utf-8")
    assert "## Ranking Preview" in md_text
    assert "ranking_preview_status: PASS" in md_text
    assert "ranking_preview_top_item: 新刊セール注目作A" in md_text


def test_ops_dashboard_generation_writes_outputs():
    generator = _load_module("scaffold_history_seed", SCRIPTS / "generate_new_block_from_template.py")
    dashboard_module = _load_module("ops_dashboard", SCRIPTS / "generate_generic_block_ops_dashboard.py")
    runner = _load_module("runner_seed", SCRIPTS / "run_generic_controlled_once.py")
    ranking = _load_module("ranking_seed", ROOT / "blocks/ranking_dry_run_block/run.py")

    generator.scaffold_block("dashboard_seed_block")
    generator.scaffold_block("ranking_dashboard_probe")
    runner.run_once("sample_block")
    ranking.run_block()
    dashboard = dashboard_module.generate_dashboard()

    assert dashboard["status"] == "PASS"
    assert dashboard["production_status"] == "NO_GO"
    assert dashboard["filter_status"] == "PASS"
    assert dashboard["scaffold_generation_history_raw_count"] >= dashboard["scaffold_generation_history_filtered_count"]
    assert dashboard["scaffold_generation_history_excluded_count"] >= 1
    assert dashboard["controlled_run_status"] == "PASS"
    assert dashboard["controlled_run_target"] == "sample_block"
    assert dashboard["ranking_preview_status"] == "PASS"
    assert dashboard["ranking_input_item_count"] == 3
    assert "sample_block" in dashboard["generated_blocks"]
    assert "ranking_dry_run_block" in dashboard["generated_blocks"]
    assert "dashboard_seed_block" in dashboard["generated_blocks_raw"]
    assert "ranking_dashboard_probe" in dashboard["generated_blocks_raw"]
    assert "dashboard_seed_block" not in dashboard["generated_blocks_filtered"]
    assert "ranking_dashboard_probe" not in dashboard["generated_blocks_filtered"]
    assert "dashboard_seed_block" in dashboard["excluded_blocks"]
    assert "ranking_dashboard_probe" in dashboard["excluded_blocks"]
    assert dashboard["scaffold_generation_history_raw_count"] >= 1
    assert dashboard["ranking_preview_top_item"]["item_id"] == "sample-1"
    assert any(item["production_status"] == "NO_GO" for item in dashboard["no_go_items"])

    summary_by_name = {item["block_name"]: item for item in dashboard["block_status_summary"]}
    assert summary_by_name["sample_block"]["visible"] is True
    assert summary_by_name["sample_block"]["scaffolded"] is True
    assert summary_by_name["sample_block"]["controlled_run_status"] == "PASS"
    assert summary_by_name["sample_block"]["ranking_preview_status"] == "NOT_RUN"
    assert summary_by_name["sample_block"]["production_status"] == "NO_GO"

    assert summary_by_name["ranking_dry_run_block"]["visible"] is True
    assert summary_by_name["ranking_dry_run_block"]["controlled_run_status"] == "NOT_RUN"
    assert summary_by_name["ranking_dry_run_block"]["ranking_preview_status"] == "PASS"
    assert summary_by_name["ranking_dry_run_block"]["production_status"] == "NO_GO"

    assert summary_by_name["dashboard_seed_block"]["visible"] is False
    assert summary_by_name["dashboard_seed_block"]["no_go_reason"] == "filtered_by_policy"
    assert summary_by_name["ranking_dashboard_probe"]["visible"] is False
    assert summary_by_name["ranking_dashboard_probe"]["no_go_reason"] == "filtered_by_policy"

    excluded_history = dashboard["evidence"]["scaffold_generation_history_excluded"]
    assert any("temporary_target_dir" in item.get("excluded_reasons", []) for item in excluded_history)
    filtered_history = dashboard["evidence"]["scaffold_generation_history"]
    assert all(not str(item.get("target_dir", "")).startswith("/tmp/") for item in filtered_history)

    json_path = ROOT / "logs/generic_block_ops_dashboard.json"
    md_path = ROOT / "logs/generic_block_ops_dashboard.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["production_status"] == "NO_GO"
    assert payload["filter_status"] == "PASS"
    assert payload["controlled_run_status"] == "PASS"
    assert payload["ranking_preview_status"] == "PASS"
    assert payload["scaffold_generation_history_excluded_count"] >= 1
    assert "dashboard_seed_block" not in payload["generated_blocks_filtered"]
    assert "ranking_dashboard_probe" in payload["excluded_blocks"]
    payload_summary = {item["block_name"]: item for item in payload["block_status_summary"]}
    assert payload_summary["sample_block"]["controlled_run_status"] == "PASS"
    assert payload_summary["ranking_dry_run_block"]["ranking_preview_status"] == "PASS"
    assert payload_summary["dashboard_seed_block"]["visible"] is False

    md_text = md_path.read_text(encoding="utf-8")
    assert "## Generated Blocks" in md_text
    assert "## Raw Generated Blocks" in md_text
    assert "## Excluded Blocks" in md_text
    assert "## Excluded Scaffold History" in md_text
    assert "## Block Status Summary" in md_text
    assert "| block_name | visible | scaffolded | controlled_run_status | ranking_preview_status | production_status | no_go_reason |" in md_text
    assert "| sample_block | True | True | PASS | NOT_RUN | NO_GO | controlled_run_dry_run_only |" in md_text
    assert "## NO_GO Items" in md_text


def test_baseline_lock_report_generation_writes_outputs():
    generic_report_module = _load_module("generic_report_seed", SCRIPTS / "generate_generic_block_report.py")
    ops_dashboard_module = _load_module("ops_dashboard_seed", SCRIPTS / "generate_generic_block_ops_dashboard.py")
    lock_module = _load_module(
        "baseline_lock",
        SCRIPTS / "generate_generic_block_template_baseline_lock_report.py",
    )

    generic_report_module.generate_report()
    ops_dashboard_module.generate_dashboard()
    lock = lock_module.generate_baseline_lock_report()

    assert lock["status"] == "PASS"
    assert lock["baseline_locked"] is True
    assert lock["production_status"] == "NO_GO"

    checks = lock["checks"]
    assert checks["required_reports_present"] is True
    assert checks["production_status_no_go"] is True
    assert checks["generic_block_report_status"] == "PASS"
    assert checks["ops_dashboard_status"] == "PASS"
    assert checks["ops_dashboard_filter_status"] == "PASS"
    assert checks["ranking_preview_status"] == "PASS"
    assert checks["external_api_called"] is False
    assert checks["external_network_called"] is False

    json_path = ROOT / "logs/generic_block_template_baseline_lock_report.json"
    md_path = ROOT / "logs/generic_block_template_baseline_lock_report.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["baseline_locked"] is True
    assert payload["production_status"] == "NO_GO"

    md_text = md_path.read_text(encoding="utf-8")
    assert "# Generic Block Template Baseline Lock Report" in md_text
    assert "- status: PASS" in md_text
    assert "- production_status: NO_GO" in md_text
