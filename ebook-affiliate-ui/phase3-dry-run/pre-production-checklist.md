# Pre-Production Checklist (Dry Run)

## Access / Loading
- [ ] HTML path resolves (no 404)
- [ ] JSON path resolves (no 404/403)
- [ ] CSS is loaded
- [ ] JS is loaded

## Behavior
- [ ] data-item-id and JSON ids match
- [ ] urgent style is visible for urgent items
- [ ] blink style is visible only for selected items
- [ ] blink max 3 is preserved by AI judge output
- [ ] manual_override has priority over AI flags

## Quality
- [ ] No fatal console errors
- [ ] Desktop layout is not broken
- [ ] Mobile layout is not broken
- [ ] Affiliate links are valid
- [ ] PR/ad labels are visible where required

## Ops / Safety
- [ ] Backup is prepared (page, settings, JSON)
- [ ] Rollback checklist is ready
- [ ] Production update is still NOT executed
