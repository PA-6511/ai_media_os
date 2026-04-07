# GUI Review Handoff

generated_at: 2026-03-15T00:48:50.069592+00:00

## 目的

GUI 実装担当とレビュー担当が、最小時間で確認対象と優先順位を把握するためのハンドオフです。

## 主要 entrypoints

- bootstrap: data/reports/ops_bootstrap_latest.json
- gui_schema: data/reports/ops_gui_schema_latest.json
- home_payload: data/reports/ops_home_payload_latest.json

## preview 確認先

- preview_html: data/reports/ops_gui_preview_latest.html
- preview_html_updated_at: 2026-03-15T00:25:57.303272+00:00

## mock API 確認先

- mock_api: data/reports/mock_api_home_latest.json
- mock_api_health_endpoint: http://127.0.0.1:8765/health
- mock_api_updated_at: 2026-03-15T00:25:57.222271+00:00

## integrity 状況

- integrity_overall: WARNING
- pass_count: 14
- warning_count: 1
- fail_count: 0

## review_points

- integrity の warning/fail を確認: warning=1, fail=0
- anomaly/alert の状態を確認: anomaly=WARNING, alerts=4
- read_order の先頭3件を辿る: data/reports/ops_bootstrap_latest.json, data/reports/ops_gui_schema_latest.json, data/reports/mock_api_home_latest.json

## next_steps

- python3 -m reporting.run_ops_gui_integrity_build を再実行し、missing_refs と FAIL を解消
- ops_alert_center_latest.json を確認し、警告要因をレビュー観点に反映
- python3 -m gui.run_mock_server で mock API を起動し、/health 応答を確認
- ops_gui_preview_latest.html を開き、entrypoints の画面遷移を目視確認

## status

- handoff_loaded: True
- integrity_loaded: True
- health_loaded: True
- artifact_timestamps_loaded: True
- fail_safe: true
