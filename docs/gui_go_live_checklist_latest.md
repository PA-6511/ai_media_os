# AI Media OS GUI Go-Live Checklist

generated_at: 2026-03-14T16:24:24.340171+00:00

## GUI成果物存在確認

- [x] bootstrap generated: /home/deploy/ai_media_os/data/reports/ops_bootstrap_latest.json
- [x] gui schema generated: /home/deploy/ai_media_os/data/reports/ops_gui_schema_latest.json
- [x] gui preview generated: /home/deploy/ai_media_os/data/reports/ops_gui_preview_latest.html
- [x] handoff package generated: /home/deploy/ai_media_os/data/reports/ops_gui_handoff_latest.json

## Mock API 準備状況

- [x] mock api json ready: /home/deploy/ai_media_os/data/reports/mock_api_home_latest.json
- read_order_count: 14
- first_read_assets:
  - data/reports/ops_bootstrap_latest.json
  - data/reports/ops_gui_schema_latest.json
  - data/reports/mock_api_home_latest.json
  - data/reports/ops_home_payload_latest.json
  - data/reports/ops_sidebar_latest.json

## 運用判断

- anomaly_overall: WARNING
- health: 70 (C)
- gui_health_ok: False
- alert_count: 4
- release_readiness: release
- gui_decision: review
- severity: warning
- reason: anomaly overall is WARNING and alerts=4
- recommended_action: リリース可。軽微警告を運用監視に登録し、次回 ops cycle で再確認

## Check Items

- anomaly が OK または WARNING: YES
- release readiness が release / review / hold のいずれか: YES
- mock API 用 JSON が生成済み: YES
- GUI preview が生成済み: YES
- handoff package が生成済み: YES

## Next Action

- リリース可。軽微警告を運用監視に登録し、次回 ops cycle で再確認
- anomaly 状態を確認し、GUI 公開前に warning/critical の内容をレビュー
