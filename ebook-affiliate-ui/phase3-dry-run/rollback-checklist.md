# Rollback Checklist (Dry Run)

## Trigger conditions
- UI breakage
- JSON load failure
- Critical console errors
- Incorrect highlight behavior

## Rollback steps
1. Unpublish or hide the fixed page
2. Disable JS block for UI flags
3. Restore previous JSON file
4. Revert CSS additions if needed
5. Restore previous page content
6. Verify old page behavior

## Verification after rollback
- [ ] No fatal console errors
- [ ] Legacy page is accessible
- [ ] No broken layout on desktop/mobile
- [ ] JSON endpoint no longer required by page

## Recovery source
- Use saved GitHub main commit as known-good source
- Keep operation log for incident review

## Safety note
- No production changes are executed in this dry-run package itself.
