# AI Media OS Release Readiness

generated_at: 2026-03-15T12:32:43.104552+00:00
decision: release

## Core Signals

- anomaly_overall: WARNING
- health_score: 70
- health_grade: C
- retry_queued: 0
- integrity_overall: PASS
- latest_daily_report: /home/deploy/ai_media_os/data/reports/daily_report_20260314.json
- latest_archive: /home/deploy/ai_media_os/data/archives/ops_archive_20260314_132424.zip

## Reasons

- 判定条件を満たしたため release
- 連動指標: alerts=0 warning=0 critical=0 / integrity PASS=12 WARNING=0 FAIL=0
- anomaly overall は WARNING だが health/retry/integrity 条件を満たす

## Recommended Action

- リリース可。軽微警告を運用監視に登録し、次回 ops cycle で再確認

## Checklist / Integrity Details

- checklist_anomaly_overall: WARNING
- checklist_retry_queued_count: 0
- checklist_daily_report_exists: True
- checklist_dashboard_exists: True
- checklist_archive_exists: False
- integrity_pass_count: 12
- integrity_warning_count: 0
- integrity_fail_count: 0
