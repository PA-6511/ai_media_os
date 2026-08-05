# Generic Block Ops Dashboard v1

- status: PASS
- generated_at: 2026-06-13T06:30:02.664691+00:00
- production_status: NO_GO
- filter_status: PASS
- scaffold_generation_history_count: 1
- scaffold_generation_history_raw_count: 25
- scaffold_generation_history_excluded_count: 24
- controlled_run_status: PASS
- controlled_run_target: sample_block
- ranking_preview_status: PASS
- ranking_input_source: /home/deploy/ai_media_os/generic_block_template/fixtures/ranking_sample_items.json
- ranking_input_item_count: 3
- ranking_preview_top_item: 新刊セール注目作A

## Generated Blocks
- ranking_dry_run_block
- sale_flash_block
- sample_block

## Raw Generated Blocks
- dashboard_seed_block
- ranking_dashboard_probe
- ranking_dry_run_block
- sale_flash_block
- sample_block

## Excluded Blocks
- dashboard_seed_block
- ranking_dashboard_probe

## Excluded Scaffold History
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmpzs1oa_n9/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmppcrojieq/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmp2l32_kaw/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmpwa6bs1tp/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmp0majd2dc/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmpdye30xqr/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmpuc5y4sou/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy
- block_name=demo_block target_dir=/tmp/tmp8c6app1z/demo_block reasons=temporary_target_dir
- block_name=dashboard_seed_block target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/dashboard_seed_block reasons=matched_filter_policy
- block_name=ranking_dashboard_probe target_dir=/home/deploy/ai_media_os/generic_block_template/blocks/ranking_dashboard_probe reasons=matched_filter_policy

## Block Status Summary
| block_name | visible | scaffolded | controlled_run_status | ranking_preview_status | production_status | no_go_reason |
| --- | --- | --- | --- | --- | --- | --- |
| dashboard_seed_block | False | True | NOT_RUN | NOT_RUN | NO_GO | filtered_by_policy |
| ranking_dashboard_probe | False | True | NOT_RUN | NOT_RUN | NO_GO | filtered_by_policy |
| ranking_dry_run_block | True | True | NOT_RUN | PASS | NO_GO | ranking_preview_dry_run_only |
| sale_flash_block | True | True | NOT_RUN | NOT_RUN | NO_GO | template_no_go_default |
| sample_block | True | True | PASS | NOT_RUN | NO_GO | controlled_run_dry_run_only |

## NO_GO Items
- type=generated_block name=ranking_dry_run_block production_status=NO_GO
- type=generated_block name=sale_flash_block production_status=NO_GO
- type=generated_block name=sample_block production_status=NO_GO
- type=controlled_run name=sample_block production_status=NO_GO
- type=ranking_preview name=ranking_dry_run_block production_status=NO_GO
