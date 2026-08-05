# SFB-11B Real-Data CSV Import DRY_RUN Evidence

- generated_at: 2026-06-14T04:38:38.880917+00:00
- status: PASS
- phase: SFB-11B
- input_csv: /home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/data/incoming/sale_flash_candidates.csv
- fixture_csv: /home/deploy/ai_media_os/generic_block_template/blocks/sale_flash_block/fixtures/sample_sale_candidates.csv
- no_go_maintained: True

## Validation
- status: PASS
- accepted_row_count: 2
- invalid_row_count: 0
- duplicate_row_count: 0

## Import
- status: PASS
- imported_row_count: 2
- backup_artifact_count: 2

## Fixture Diff
- changed: True
- added_line_count: 2
- removed_line_count: 5

## Pipeline DRY_RUN
- status: PASS
- production_status: NO_GO
- wordpress_write_executed: False
- external_api_called: False
- external_network_called: False

## Step Summary
- article_payloads: PASS
- human_review_handoff: PASS
- normalize: PASS
- quality_gate: PASS
- readiness: PASS
- report: PASS
- review_queue: PASS
- sfb10_governance_boundary_review: PASS
- sfb10b_pre_production_baseline_lock_report: PASS
- sfb6_wordpress_draft_validation: PASS
- sfb6b_baseline_lock_report: PASS
- sfb7_final_human_approval_package: PASS
- sfb8_wordpress_dry_run_execution_evidence: PASS
- sfb8b_dry_run_execution_baseline_lock_report: PASS
- sfb9_final_signoff_archive: PASS
- wordpress_draft_handoff: PASS

## Fixture Diff Preview
```diff
--- fixture_before
+++ fixture_after
@@ -1,6 +1,3 @@
 source,title,author,isbn,asin,campaign,sale_status,confidence,note
-manual_csv,Blue Harbor Chronicle,Kei Tanaka,9781111111111,B0TEST0001,SUMMER_FLASH,candidate,0.91,fixture row with asin
-publisher_news_candidate,Glass Orbit Stories,Mina Kudo,9782222222222,,PUBLISHER_PUSH,candidate,0.78,missing asin for search candidate
-rakuten_books_candidate,Neon Wind Archive,Ryo Sato,9783333333333,B0TEST0002,STORE_CAMPAIGN,candidate,0.83,fixture row with asin
-manual_csv,,Aoi Shimizu,9784444444444,,EDITOR_PICK,candidate,0.66,missing title should require review
-publisher_news_candidate,Silent Harbor,,9785555555555,,NEWS_DIGEST,candidate,unknown,missing author and invalid confidence
+manual_csv,Crimson Library,Aki Mori,9786000000001,B0REAL00001,SUMMER_FLASH,candidate,0.92,real-data dry run candidate
+publisher_news_candidate,Glass Moon,Yuna Sato,9786000000002,,NEWS_DIGEST,candidate,0.77,asin missing allowed for search candidate
```
