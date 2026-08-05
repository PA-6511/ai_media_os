# Implementation Restart Phase 1 Summary

## Context
- Loop-style evidence generation is closed by policy.
- Focus is shifted from repetitive report chaining to implementation delivery.
- Safety posture remains unchanged: `NO_GO`, `NOT_GRANTED`, `dry_run`, `OBSERVE`, no external reflection.

## Baseline Snapshot
- Target area: `generic_block_ai/app`, `generic_block_ai/config`, `generic_block_ai/tests`
- Current automated baseline: `python3 -m pytest -q generic_block_ai/tests`
- Result: `44 passed`

## Phase 1 Goals
1. Convert current guard-only skeleton into implementation-ready execution pipeline (still dry-run).
2. Add structured review outputs that support human approval decisions.
3. Prepare external integration interfaces as adapters, but keep runtime execution blocked.

## Implementation Tasks (Prioritized)
1. Action Classification Layer
   - Files: `generic_block_ai/app/safety_guard.py`, `generic_block_ai/tests/test_safety_guard.py`
   - Deliverable: classify actions into `allow`, `block`, `needs_review` with explicit reasons.
   - Guardrail: any action in forbidden list remains blocked.
   - Acceptance: new tests cover all three classes.

2. Decision Context Enrichment
   - Files: `generic_block_ai/app/block_runner.py`, `generic_block_ai/app/result_schema.py`, `generic_block_ai/tests/test_result_schema.py`
   - Deliverable: include deterministic decision context (`reason_codes`, `review_required_fields`) in result payload.
   - Guardrail: `actual_execution` must remain `false`.
   - Acceptance: schema validation tests for context fields pass.

3. Review Package Builder (Dry-run)
   - Files: `generic_block_ai/app/main.py` (new option), new module `generic_block_ai/app/review_package_builder.py`, tests.
   - Deliverable: output a review package JSON from requested actions and guard evaluation.
   - Guardrail: file output only to local workspace path, no network calls.
   - Acceptance: CLI test confirms package generation and schema validity.

4. Integration Adapter Interfaces (No Runtime Call)
   - Files: new `generic_block_ai/app/integrations/` package, adapter stubs for WordPress/GitHub.
   - Deliverable: typed adapter interfaces and dry-run simulators returning mock results.
   - Guardrail: adapters do not perform HTTP or git mutation operations in Phase 1.
   - Acceptance: tests verify stubs are non-mutating and deterministic.

5. Safety Gate Regression Suite Expansion
   - Files: `generic_block_ai/tests/` (new regression tests)
   - Deliverable: regressions for `NO_GO`, `NOT_GRANTED`, `OBSERVE`, `dry_run`, `reports-only` assumptions.
   - Guardrail: any policy relaxation must fail tests by default.
   - Acceptance: full suite green, with at least one negative test per guardrail.

## Review Output Contract (Phase 1)
- Required fields in proposal output:
  - `scope`
  - `non_goals`
  - `risk_assessment`
  - `guardrail_checks`
  - `rollback_conditions`
  - `approval_required`
- Missing required fields must fail validation.

## Non-Goals (Phase 1)
- No production publish.
- No WordPress draft posting to real endpoint.
- No GitHub write operations (commit/PR/issue/workflow mutation).
- No VPS execution unlock.

## Exit Criteria
- All Phase 1 tasks implemented with tests.
- Proposal output contains full review contract and passes validator checks.
- Safety guard regressions remain green under default policy.
