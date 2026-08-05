# SFB-15: Dashboard Operations Runbook Lock

## 1. 目的

SFB dashboard の定常運用手順を固定し、運用時の確認漏れを防止する。
本Runbookは運用固定専用であり、本番write解放は対象外とする。

## 2. 固定前提

- production_status は常に NO_GO
- mode は常に DRY_RUN
- 外部通信は禁止
- WordPress writeは禁止
- approval token / label / human approval の消費は禁止

## 3. dashboard再生成コマンド

実行順:

1. python3 scripts/generate_sfb13_csv_import_diff_report.py
2. python3 scripts/generate_sfb14_dashboard_aggregation.py
3. python3 scripts/check_sfb_dashboard_operations_readiness.py --dry-run

## 4. 確認すべきJSON/MD

- logs/sfb_13_csv_import_diff_report.json
- logs/sfb_13_csv_import_diff_report.md
- logs/sfb_14_dashboard_aggregation.json
- logs/sfb_14_dashboard_aggregation.md
- logs/sfb_15_dashboard_operations_readiness.json

## 5. WARN確認

- sfb_14 dashboard の warn_list を確認
- undefined_phase_mapping の有無を確認
- readiness の warn_list を確認

## 6. artifact_missing確認

- sfb_14 の artifact_missing が 0 であること
- missing_artifact_ids が空であること
- 欠落時は次工程へ進めない

## 7. NO_GO確認

- sfb_13 と sfb_14 と sfb_15 の production_status が NO_GO
- wordpress_write_executed が false
- external_api_called が false
- external_network_called が false
- approval_token_consumed が false

## 8. 差分レポート確認

- added_candidates / removed_candidates / updated_candidates を確認
- duplicate_candidates の変化を確認
- asin_presence_change を確認
- confidence_change を確認
- review_bucket_change を確認
- adopt_candidate_count_change を確認

## 9. 再実行タイミング

- 実データCSV更新直後
- SFB-13 policy更新直後
- SFB-14 mapping更新直後
- WARN発生後の修正反映直後
- 定期点検時（最低1日1回）

## 10. 停止条件

- NO_GO 逸脱
- DRY_RUN 逸脱
- artifact_missing > 0
- 重要WARN未解消
- JSON/MD未生成
- safetyフラグのいずれかが true になった場合

## 11. 最終判定

- READY: 全チェック通過
- STOP_AND_FIX: 停止条件に該当
