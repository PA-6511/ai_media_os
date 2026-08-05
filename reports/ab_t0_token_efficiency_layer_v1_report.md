# AB-T0: Auto Builder Token Efficiency Layer v1 Report

## 1. AB-T0 Goal
- Introduce a minimal token-efficiency operation layer for Auto Program Builder Block AI.
- Standardize low-token design workflows before closing Phase 1.5.

## 2. Why This Was Introduced
- Reduce AI context payload size and Copilot usage cost.
- Avoid long log and diff pastes that do not improve decision quality.
- Keep design-only, evidence-first progress without live execution.

## 3. In Scope
- Policy definition for AI context limits.
- Safety baseline lock for NO_GO and NO_EXECUTION.
- Validator and unit test coverage for policy integrity.
- Result/evidence artifacts for AB-T0 phase closure.

## 4. Out Of Scope
- No Phase 8 ebook-affiliate execution changes.
- No production write, WordPress write, or external API execution.
- No credential output or secret read/print operations.
- No live or pre-live execution operations.

## 5. Copilot/AI Input Limits
- Max files per AI context: 5.
- Max lines per file excerpt: 120.
- Full repository dump is forbidden.
- Unrelated historical phase reports are forbidden as context input.

## 6. File Scout Policy
- Start from phase card + file manifest + repository snapshot digest.
- Restrict initial reads to high-signal files only.
- Pull extra files only with explicit, narrow reason.

## 7. Context Compressor Policy
- Use compact evidence cards instead of full artifacts.
- Keep only phase-critical fields, status, and blockers.
- Prefer per-file digest over raw content replay.

## 8. Diff Digest Policy
- Full git diff paste is prohibited.
- Use changed-file list + intent summary + risk notes.
- Include only relevant hunks for validation discussions.

## 9. Error-Only Log Policy
- Full pytest and compile logs are prohibited.
- Share failure-only excerpt and failing assertion lines.
- Keep remediation loop based on minimal error slices.

## 10. Evidence / Report Template Reuse Policy
- Reuse stable report/result template structures.
- Do not regenerate complete historical reports.
- Generate only new phase-local report and result evidence.

## 11. Safety Rule Pack
- Safety Rule Pack ID: SAFETY_RULE_PACK_AB_V1.
- Locked flags:
  - production_write_allowed=false
  - wordpress_write_allowed=false
  - external_api_call_allowed=false
  - credential_output_allowed=false
  - live_execution_allowed=false
  - dry_run_only=true
  - evidence_only=true
  - next_phase_forward_execution=false
  - secret_reading_allowed=false
  - secret_printing_allowed=false

## 12. How To Apply In Future Phases
- Attach policy JSON as mandatory input contract.
- Run validator + targeted unit test before phase close.
- Publish only digest-style context artifacts for AI handoff.

## 13. Validation Result
- Policy JSON schema/field requirements: PASS.
- Safety lock constraints: PASS.
- Token-limit constraints: PASS.
- Validator script and unit tests: PASS (targeted execution).

## 14. Final Decision
AB-T0: PASS_DESIGN_ONLY_NO_EXECUTION
