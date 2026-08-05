# SFB-14 Dashboard Aggregation

- status: SFB14_DASHBOARD_AGGREGATION_READY
- phase: SFB-14
- mode: DRY_RUN
- production_status: NO_GO
- artifact_total: 6
- artifact_found: 6
- artifact_missing: 0

## Artifact Summary
- sfb_10b_baseline: found=true status=PASS path=/home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/logs/sale_flash_block_baseline_lock_report.json
- sfb_11_import: found=true status=PASS path=/home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/logs/real_sale_csv_import_report.json
- sfb_11b_dry_run_evidence: found=true status=PASS path=/home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/logs/real_data_import_dry_run_evidence.json
- sfb_11c_import_baseline_lock: found=true status=PASS path=/home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/logs/real_data_import_dry_run_baseline_lock_report.json
- sfb_12_operating_readiness: found=true status=SFB12_REAL_DATA_CSV_OPERATING_RULES_LOCKED_READY path=/home/deploy/ai_media_os/logs/real_data_csv_operating_readiness.json
- sfb_13_diff_report: found=true status=SFB13_CSV_IMPORT_DIFF_REPORT_READY path=/home/deploy/ai_media_os/logs/sfb_13_csv_import_diff_report.json

## Mapping Guard
- undefined_phase_mapping_count: 0

## Safety
- wordpress_write_executed: false
- external_api_called: false
- external_network_called: false
- approval_token_consumed: false
