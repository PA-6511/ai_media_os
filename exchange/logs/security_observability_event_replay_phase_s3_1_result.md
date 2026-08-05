# Security Observability Event Replay Phase S-3.1 Result

- phase_id: PHASE_S3_1
- phase_name: dry_run_observability_event_replay
- replay_result: FAIL
- execution: DRY_RUN
- production_status: NO_GO
- human_approval_required: True
- detector_only: True
- recommendation_only: True
- executor_action_allowed: False
- event_count: 5
- matched_expected_count: 5
- mismatched_expected_count: 0
- freeze_recommendation_detected: True
- human_review_recommendation_detected: True
- state_change_executed: False
- freeze_executed: False
- revoke_executed: False
- isolation_executed: False
- process_kill_executed: False
- scheduler_stop_executed: False
- wordpress_write_executed: False
- external_api_call_executed: False
- timestamp: 2026-05-28T13:35:35.893420+00:00
- next_step: prepare_cross_phase_security_audit_view

## event_results
- scheduler_retry_loop_sample: actual=WARN expected=WARN freeze_recommendation=True human_review_recommendation=True
- wordpress_publish_intent_sample: actual=FAIL expected=FAIL freeze_recommendation=True human_review_recommendation=True
- unknown_external_api_intent_sample: actual=WARN expected=WARN freeze_recommendation=False human_review_recommendation=True
- env_secret_echo_intent_sample: actual=FAIL expected=FAIL freeze_recommendation=True human_review_recommendation=True
- process_duplicate_runner_sample: actual=FAIL expected=FAIL freeze_recommendation=True human_review_recommendation=True

## warnings
- warning event detected in replay

## fail_reasons
- failure event detected in replay

## abort_reasons
- none
