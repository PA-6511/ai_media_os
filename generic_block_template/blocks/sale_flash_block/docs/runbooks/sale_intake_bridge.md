# Sale Intake Bridge (SFB-1)

## Purpose

Run the sale_flash_block intake pipeline in DRY_RUN mode while Creators API access is not yet eligible.

## Scope

- Source input is fixture CSV only.
- External API and network calls are disabled.
- WordPress write/publish/update/delete is disabled.
- production_status remains NO_GO.

## Procedure

1. Normalize candidates from fixture CSV.
2. Generate review queue from normalized candidates.
3. Run readiness check.
4. Generate JSON and Markdown report.

## Commands

```bash
python3 generic_block_template/blocks/sale_flash_block/scripts/normalize_sale_candidates.py
python3 generic_block_template/blocks/sale_flash_block/scripts/generate_sale_review_queue.py
python3 generic_block_template/blocks/sale_flash_block/scripts/check_sale_intake_readiness.py
python3 generic_block_template/blocks/sale_flash_block/scripts/generate_sale_flash_block_report.py
```

## Success Criteria

- normalized_sale_candidates.json status is PASS or WARN.
- sale_review_queue.json status is PASS or WARN.
- sale_intake_readiness.json status is PASS.
- sale_flash_block_report.json status is PASS or WARN.
- All artifacts report production_status as NO_GO.
