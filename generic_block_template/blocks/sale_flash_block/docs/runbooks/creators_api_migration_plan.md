# Creators API Migration Plan (SFB)

## Current State

- stage: API_NOT_ELIGIBLE_MANUAL_INTAKE
- creators_api_migration_allowed: false
- intake mode: DRY_RUN
- production_status: NO_GO

## Guardrails

- require_creators_api_eligible: true
- require_human_approval: true
- require_single_controlled_run: true
- require_final_freeze_restore: true

## Planned Stages

1. ASIN enrichment only via Creators API.
2. Title verification only via Creators API.
3. Image, author, and publisher metadata via Creators API.
4. Price and discount fields via Creators API.
5. Shift sale judgment core to Creators API backed signals.

## Exit Conditions For SFB-1

- Eligibility is explicitly confirmed.
- Human approval is recorded.
- Single controlled run succeeds with no external side effects.
- Freeze and restore check is completed.
