# Ebook Affiliate Block Trial Readiness Gap Report

Last updated: 2026-06-15 (UTC)
Scope: Gap assessment only. No execution unlock, no production write.

## Assessment Result

- Overall: GAP_FOUND
- Trial readiness state: NOT_READY_FOR_ONE_ITEM_TRIAL
- Risk level: Medium (readiness gap), High (if executed without mapping/gate)

## Inputs Used

- blocks/ebook_affiliate_block/block.py
- blocks/ebook_affiliate_block/collector.py
- blocks/ebook_affiliate_block/analyzer.py
- blocks/ebook_affiliate_block/proposal_generator.py
- blocks/ebook_affiliate_block/block_manifest.json
- tests/test_ebook_affiliate_block_connection.py
- exchange/logs/phase8_38_first_one_item_trial_preflight_report.json
- exchange/examples/phase8_38_first_one_item_trial_preflight_request.example.json
- docs/runbooks/phase8_37_first_trial_operation_runbook_final.md

## One-Item Trial Preconditions vs Current Block Output

Required by preflight/runbook:
- target_item_selected
- target_item_schema_valid
- target_item_duplicate_check_passed
- affiliate_disclosure_present
- pr_label_present
- cta_policy_checked
- category_tag_policy_checked

Current proposal output keys (observed):
- top-level: action, metadata, priority, reason, source, target, title
- metadata: genre, opportunity_type, work_title

Gap matrix:
- target_item_selected: GAP (selection mechanism not implemented)
- target_item_schema_valid: GAP (trial schema contract not defined in block output)
- target_item_duplicate_check_passed: GAP (no duplicate detection field/process in block)
- affiliate_disclosure_present: GAP (field not generated)
- pr_label_present: GAP (field not generated)
- cta_policy_checked: GAP (field/check result not generated)
- category_tag_policy_checked: GAP (field/check result not generated)

## Additional Findings

- External fetch attempt exists in collector (requests.get to example.com); fallback works, but network call is attempted before fallback.
- Requests dependency warning observed at runtime: urllib3/chardet compatibility warning.
- Existing test coverage validates manifest/handshake/authority behavior, but does not validate one-item trial preflight fields.

## Safe Interpretation

- Current block is valid as idea/proposal generator in dry-run context.
- Current block is not directly consumable as one-item trial post candidate without a mapping/gate layer.
- SFB-15B HOLD and trial NO_GO/DRY_RUN invariants remain unaffected by this report.

## Missing Components For One-Item Trial Connection

- Candidate schema adapter from block proposal to trial target item contract.
- Duplicate check stage and evidence field emission.
- Affiliate disclosure field generation/validation.
- PR label field generation/validation.
- CTA policy check and result field emission.
- Category/tag policy check and result field emission.
- Preflight-compatible evidence record output for the above checks.

## Recommended Next Step (Readiness-Only)

- Implement a non-executing adapter/check layer between ebook_affiliate_block outputs and phase8_38 preflight input contract.
- Keep NO_GO and DRY_RUN fixed while adding only validation/evidence generation.
- Add focused tests for required trial fields and duplicate/policy checks.

## Go/No-Go For Next Stage

- Move to production write: NO
- Move to one-item trial execution: NO
- Move to readiness-only gap implementation: YES