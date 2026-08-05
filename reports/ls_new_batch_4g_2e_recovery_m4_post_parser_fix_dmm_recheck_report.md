# LS-NEW-BATCH-4G-2E-RECOVERY-M4

## Result

- Status: `PASS_DMM_POST_REMEDIATION_ONE_SHOT_RECHECK_EXECUTED_AUTH_CONSUMED_NO_LINK_GENERATION`
- Decision: `DMM_POST_REMEDIATION_RECHECK_FAILED_CLOSED_SLOT_UNAVAILABLE_RETURN_TO_HUMAN_REVIEW`
- Authorization consumed: `true`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`

## Parser

- Runner SHA-256: `adfe2cbb8478458e8940eb0d67de4aa8e223ba6923353a2f0f0dc4d35e37e35f`
- Null-safe remediation bound: `true`

## Network Evidence

- HTTP response received: `true`
- Redirect count: `0`
- Final HTTP status: `200`
- Final URL: `https://book.dmm.com/product/861056/latest/`
- Response body SHA-256: `c0c75847c2c048ee468937c2fdf2190f3ab5586226c9854e11513b2a74a88146`
- Full response body persisted: `false`

## Verification

- All required identity fields match: `false`
- Canonical product URL: `https://book.dmm.com/product/861056/b950yshes32617/`
- Canonical series binding: `false`
- Successful match: `false`
- DMM slot available: `false`
- Human review required: `true`
- Failure reason codes: `['VOLUME_MISMATCH', 'CANONICAL_PRODUCT_SERIES_BINDING_FAILED']`

## Boundary

- Final affiliate link generated: `false`
- Article modified: `false`
- URL injected: `false`
- Payload created: `false`
- WordPress accessed: `false`
- Production status: `NO_GO`
