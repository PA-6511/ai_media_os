# Phase TST-5D-W1 completion report

RESULT: BLOCKED

WORKFLOW_STATE_CONTRACT: The repository flushes but does not commit. WordPress draft services own commit/rollback and require READY + APPROVED + no existing WordPress binding. Direct repository calls have no cross-workflow uniqueness or bound/PUBLISHED replacement guard.
WORDPRESS_POST_ID_TYPE: nullable `String(64)` model/migration field; repository accepts int or digit string and persists a trimmed digit string.
WORDPRESS_POST_ID_NULL_ALLOWED: true
SAME_WORKFLOW_SAME_POST_ID_BEHAVIOR: IDEMPOTENT_NO_MUTATION
DIFFERENT_WORKFLOW_DUPLICATE_POST_ID_BEHAVIOR: CURRENTLY_ACCEPTED_IMPLEMENTATION_GAP
INVALID_POST_ID_BEHAVIOR: bool, zero, negative, empty, whitespace, decimal, and nonnumeric fail closed; null and digit strings are accepted; leading zeros remain; values longer than 64 digits are not rejected in SQLite.

DUPLICATE_POST_ID_TEST_RESULT: BLOCKED_REQUIRED_REJECTION_ABSENT; isolated reproduction persisted `12345` on two workflow rows.
SAME_WORKFLOW_IDEMPOTENCY_RESULT: PASS
INVALID_POST_ID_TEST_RESULT: BLOCKED_EXTREME_LENGTH_NOT_REJECTED; all other enumerated invalid classes PASS.

FLUSH_FAILURE_ROLLBACK_RESULT: PASS
COMMIT_FAILURE_ROLLBACK_RESULT: PASS
PARTIAL_UPDATE_PREVENTION_RESULT: PASS_FOR_TESTED_TRANSACTION_BOUNDARIES
POST_FAILURE_SESSION_RECOVERY_RESULT: PASS

HISTORY_IDEMPOTENCY_RESULT: PASS
READY_APPROVED_STATE_PROTECTION_RESULT: PARTIAL; formal WordPress service preflight PASS, direct repository binding/PUBLISHED replacement protection ABSENT.
SLACK_APPROVAL_MUTATION_BOUNDARY_RESULT: PASS

IMPLEMENTATION_GAPS_FOUND:

- `ebook_items.wordpress_post_id` has a non-unique index and no repository cross-row duplicate check.
- Direct repository calls can replace an existing or PUBLISHED WordPress binding without an approved reconciliation path.
- The repository does not enforce the declared 64-character limit before flush; SQLite accepts a 65-digit value.

TEST_EVIDENCE_GAPS_REMAINING: NONE for the recorded current behavior; implementation gaps prevent HOLD clearance.
PRODUCTION_SOURCE_CHANGE_REQUIRED: true; reviewed repository/model/migration changes and a pre-migration read-only duplicate audit are required.

SUPPLEMENTAL_EVIDENCE_ROOT: `exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w1-workflow-state-hold-clearance/`
SUPPLEMENTAL_EVIDENCE_MANIFEST: `exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w1-workflow-state-hold-clearance/evidence-manifest.json`
SUPPLEMENTAL_EVIDENCE_MANIFEST_SHA256: `4814e55adff17a82c759d31eb654e6b32be1b7e6ee31fdd79a55b15e4cfdcb8c`
EVIDENCE_STATUS: WORKFLOW_STATE_HOLD_CLEARANCE_EVIDENCE_READY
EVIDENCE_INTEGRITY: PASS; 7 regular single-link files, exact manifest set and SHA bindings validated.

TARGETED_TEST_RESULT: PASS
TARGETED_TEST_COUNT: 48
FAULT_INJECTION_REPEAT_RESULTS: PASS; 3 critical tests passed in each of two separate pytest processes.
ADVERSARIAL_TEST_RESULT: PASS
ADVERSARIAL_TEST_COUNT: 19
RELATED_TEST_RESULT: EXPECTED_FAIL_PRE_REBIND_ONLY; 224 passed, 2 known expected failed, 0 unexpected failed.
RELATED_TEST_COUNT: 226

FULL_CANONICAL_SUITE: EXPECTED_FAIL_PRE_REBIND_ONLY
FULL_PASS_COUNT: 10794 (plus 8 passed subtests)
FULL_FAILURE_COUNT: 2
KNOWN_EXPECTED_FAILURE_COUNT: 2
UNEXPECTED_FAILURE_COUNT: 0

The known failures are:

- `tests/test_validate_slack_worker_release_bundle_contract.py::test_validator_passes`
- `tests/test_validate_slack_worker_release_bundle_contract.py::test_validator_reports_symlink_boundary_pass`

Both report the pre-existing `SOURCE_SHA_MISMATCH: app/db/config.py` condition.

UNIT_WORKFLOW_STATE_DECISION_BEFORE: HOLD
UNIT_WORKFLOW_STATE_DECISION_AFTER: HOLD
AUTOMATIC_APPROVAL_PERFORMED: false
HUMAN_REREVIEW_REQUIRED: true
PRODUCTION_REBINDING_ALLOWED: false

PRODUCTION_MANIFEST_UNCHANGED: true; `ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d`
PRODUCTION_DOWNSTREAM_ARTIFACTS_UNCHANGED: true; prior/current 21-artifact aggregate `f3b796680be17d8043d54a6ccbe4450ab0c330d09c60a4e3d36feb2c158c655e`
PRODUCTION_RUNTIME_SOURCES_UNCHANGED: true; prior/current 17-source aggregate `85efad884e195e8535cc77258d36b7349e1bbf0897c019276fa637a5c2ba362e`; target source remains `ac3fbddee5d3edf3cfd3368d5e3ed1ed40a4ff13d8655ad44847c55d4596bdd7`.
TST_5C_REVIEW_BUNDLE_UNCHANGED: true; review bundle manifest `7143183f25628bb6b7936197800cf6d9ac9d7078ad0f50a32c817aa7051ab4ea`
TST_5D_DECISION_ARTIFACT_UNCHANGED: true; `9cd0833a644b1f3669a8969d754eebb296603febfa89e06c4067fedc0b9154c4`

PRODUCTION_DB_SHA_BEFORE: `1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9`
PRODUCTION_DB_SHA_AFTER: `1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9`
PRODUCTION_DB_SHA_UNCHANGED: true; 233472 bytes
PRODUCTION_WAL_UNCHANGED: true; `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, 0 bytes
PRODUCTION_SHM_UNCHANGED: true; `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb`, 32768 bytes
PRODUCTION_CREDENTIAL_STAT_UNCHANGED: true; regular file, 444 bytes, mode 0600, uid 1001, gid 1001, mtime/ctime 1784537841; content not read.
TERMINAL_ARTICLE_UNCHANGED: true; `de2739c8ae1aa4a50973b983964b05844086a2187b9ef337383ad6fa7123697d`
TST_4A_FIXTURE_UNCHANGED: true; `6e099df4d92eed1069d9cb65d7c62d049d6647416a397149436bf001a2b5696d`
TST_4B_FIXTURE_UNCHANGED: true; `ef0e37e26c345a3e539291b6618e0a46aecd8437a011e410169c8eaa0a6fad45`
TST_4C_FIXTURE_UNCHANGED: true; `f677c6adcc75507bc82ccbed1d52bc54a737b935cc92251c2633e608e0537094`
TST_4D_FIXTURE_UNCHANGED: true; `e38558627ebc4e2b660c7b52ae825b47da621d56af357fe2ca8ba6745f73aaff`

FILES_CHANGED:

- `tests/database/test_tst_5d_w1_workflow_state_hold_clearance.py`
- `tests/test_validate_tst_5d_w1_workflow_state_hold_clearance_evidence.py`
- `scripts/validate_tst_5d_w1_workflow_state_hold_clearance_evidence.py`
- `exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w1-workflow-state-hold-clearance/**` (7 files)
- `reports/tst_5d_w1_workflow_state_hold_clearance_report.md`

DEPLOYMENT_PERFORMED: false
SLACK_RUNTIME_STARTED: false
SLACK_NETWORK_USED: false
WORDPRESS_NETWORK_USED: false
CORRECTIVE_EXECUTION_PERFORMED: false
LV999_IMPORTED: false
GIT_DESTRUCTIVE_OPERATION_EXECUTED: false

FOUND_ISSUES:

- Required cross-workflow WordPress post-ID uniqueness is absent.
- Existing/PUBLISHED bindings can be reassigned through the repository directly.
- Extreme digit-string length is not fail-closed.

NEXT_RECOMMENDED_ACTION:

- Keep `UNIT_WORKFLOW_STATE` on HOLD. Human rereview should authorize a separately scoped remediation: read-only duplicate audit, uniqueness migration, fixed domain-error/rollback behavior, binding replacement guard, length/canonicalization contract, and regression tests. Do not update the production manifest or decision artifact in this phase.
