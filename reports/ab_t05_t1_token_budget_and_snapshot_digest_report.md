# AB-T0.5 / AB-T1 Token Budget and Snapshot Digest Report

## 1. AB-T0.5 / AB-T1 Purpose
- AB-T0.5 defines strict token budget controls for AI context usage.
- AB-T1 adds a lightweight repository snapshot digest for low-token handoff.

## 2. Why Add This On Top Of AB-T0
- AB-T0 established baseline limits; AB-T0.5 tightens per-turn budget governance.
- AB-T1 enables compact state sharing before Phase 1N-FIX evidence cleanup.

## 3. Scope
- Token budget governor policy in config.
- Lightweight repository snapshot digest in config.
- Validator and tests for both artifacts.
- Report and result evidence for design-only closure.

## 4. Out Of Scope
- No Phase 8 body changes.
- No live execution or pre-live execution.
- No production write, WordPress write, or external API call.
- No credential read or credential output.
- No broad refactor.

## 5. Token Budget Governor Limits
- max_files_per_ai_context=5
- max_lines_per_file_excerpt=120
- max_ai_context_items_per_turn=8
- max_git_diff_lines_for_ai=0
- full_repository_dump_allowed=false
- git_diff_full_paste_allowed=false
- pytest_full_log_paste_allowed=false
- py_compile_full_log_paste_allowed=false
- json_tool_full_log_paste_allowed=false
- evidence_index_full_paste_allowed=false
- report_full_regeneration_allowed=false

## 6. Repository Snapshot Digest LIGHTWEIGHT
- Current state is compacted to phase status and next action only.
- Safety and token efficiency are stored as concise booleans/limits.
- Digest is limited to Phase 1N-FIX preparation context.

## 7. Copilot/AI Input Rules
- Only allowed context artifacts:
  - phase_closure_card
  - repository_snapshot_digest
  - file_manifest
  - diff_digest
  - error_only_log
  - safety_rule_pack
- Forbidden context artifacts include full dumps/logs and credential/secret sources.

## 8. How To Apply To Phase 1N-FIX
- Use repository_snapshot_digest.json as baseline context card.
- Use error-only validation outputs only.
- Restrict edits to evidence/report/snapshot cleanup paths.

## 9. Safety Rule Pack Continuity
- safety_rule_pack_id remains SAFETY_RULE_PACK_AB_V1.
- NO_GO, NO_EXECUTION, dry_run_only, and evidence_only remain locked.

## 10. Validation Results
- token budget policy validation: PASS
- snapshot digest validation: PASS
- py_compile validator: PASS
- pytest target tests: PASS

## 11. Not Implemented In This Step
- AB-T1.5 Evidence / Report Template Reuse full implementation.
- Future recommended work: add AB-T1.5 as a separate design-only phase item.

## 12. Final Status
AB-T0.5: PASS_DESIGN_ONLY_NO_EXECUTION
AB-T1: PASS_LIGHTWEIGHT_DESIGN_ONLY_NO_EXECUTION
