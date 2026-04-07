# AI Media OS Daily Checklist

generated_at: 2026-03-14T02:36:25.169535+00:00

anomaly: WARNING
alerts: total=1 warning=1 critical=0
health_score: 70 (C)
retry_queued: 0
latest_daily_report: /home/deploy/ai_media_os/data/reports/daily_report_20260313.json
latest_dashboard: /home/deploy/ai_media_os/data/reports/dashboard_latest.html
latest_archive: /home/deploy/ai_media_os/data/archives/ops_archive_20260314_105443.zip
next_action: anomaly 警告あり。daily_report と anomaly ログ確認推奨

release_decision: release
release_reasons:
- 判定条件を満たしたため release
- anomaly overall は WARNING だが軽微警告として release 許可
recommended_action: 軽微警告あり。リリース可、監視継続

## Check Items

- anomaly が OK: NO
- retry queue が 0: YES
- daily report が存在: YES
- dashboard が存在: YES
- archive が存在: YES
