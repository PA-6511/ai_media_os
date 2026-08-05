# Implementation Restart Phase 2 Plan

## Objective
- Improve `generic_block_ai` task generation precision under strict safety guardrails.
- Keep all runtime behavior in `dry_run` and `OBSERVE`.
- Prevent regression into repetitive evidence-loop operations.

## Scope
- In scope:
  - task generation quality improvements
  - ranking/prioritization logic for candidate tasks
  - deterministic review metadata for human review
  - validator-aligned summary outputs
- Out of scope:
  - external writes (GitHub/WordPress/API)
  - production execution enablement
  - VPS unlock

## Phase 2 Work Items
1. IR2-T1 Task Candidate Scoring
- Add deterministic scoring fields for generated tasks:
  - impact_score
  - risk_score
  - confidence_score
  - priority_score
- Acceptance:
  - same input returns same ordered output
  - unit tests for score boundaries and ordering

2. IR2-T2 Constraint-Aware Filtering
- Add explicit pre-filter checks before task proposal:
  - forbidden actions exclusion
  - capability mismatch exclusion
  - missing mandatory context exclusion
- Acceptance:
  - filtered tasks include structured rejection reasons
  - tests cover each filter branch

3. IR2-T3 Review-Ready Task Package
- Emit task proposal package with required fields:
  - scope
  - non_goals
  - risk_assessment
  - guardrail_checks
  - rollback_conditions
  - approval_required
- Acceptance:
  - validator-compatible payload
  - missing required field fails tests

4. IR2-T4 Quality Metrics Report
- Add local summary report for proposal quality:
  - accepted_candidates
  - rejected_candidates
  - top_rejection_reasons
  - average_scores
- Acceptance:
  - JSON/MD reports generated locally
  - no external side effects

5. IR2-T5 Regression and Safety Net
- Extend tests to lock:
  - dry_run invariant
  - OBSERVE invariant
  - NO_GO invariant
  - external_write_executed=false invariant
- Acceptance:
  - full suite green
  - at least one negative test per invariant

## Guardrails (Must Hold)
- production_status: NO_GO
- manual_release_go_authorization: NOT_GRANTED
- actual_process_start_go_authorization: NOT_GRANTED
- execution_start: NO_GO
- external operations: NOT_EXECUTED

## Validation Commands
- `python3 -m pytest -q generic_block_ai/tests`
- `python3 -m json.tool generic_block_ai/reports/implementation_restart_phase2_plan.json`

## Exit Criteria
- IR2-T1 to IR2-T5 implemented and validated.
- Proposal quality metrics available in local reports.
- No external write operations executed.
