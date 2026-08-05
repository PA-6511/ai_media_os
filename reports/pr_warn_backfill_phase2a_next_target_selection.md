# PR WARN Backfill Phase 2A：Next Target Selection

## 結果
- status: PASS_NEXT_TARGET_SELECTED_NO_EXECUTION
- decision: SELECT_NEXT_TARGET
- completed_post_id: 101
- selected_next_post_id: 92
- selected_next_title: 呪術廻戦は何巻まで出てる？最新巻・関連情報まとめ
- candidate_count_detected: 5
- WordPress read: false
- WordPress write: false
- LIVE実行: false
- snapshot_created: false
- approval_created: false
- payload_created: false
- update_count: 0
- next_required_phase: Phase 2B-NEXT-TARGET-READ-ONLY-SNAPSHOT

## 固定
- post_id=101 の true approval は再利用不可
- post_id=101 への追加更新は不可
- 次対象へ進む場合は新しい snapshot / approval / preflight が必要
