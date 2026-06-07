# PR WARN Cycle 3 Observation

## Scope

- Observe only reports generated on or after 2026-06-08.
- Do not mix older reports when evaluating this cycle.
- This cycle measures only the PR notice insertion change in with_links enrichment.

## Command

```bash
cd /home/deploy/ai_media_os

python3 tools/analyze_draft_check_reports.py \
  --min-date 20260608 \
  --output reports/warn_analysis_pr_warn_cycle3.json

cat reports/warn_analysis_pr_warn_cycle3.json
```

## Decision Rule

- PR WARN rate < 30%: consider moving to URL WARN analysis.
- PR WARN rate 30% to 35%: keep observing for one more week.
- PR WARN rate > 35%: perform additional cause classification.
- If FAIL / ERROR / duplicate occurs: stop improvement and investigate the cause.

## Not In Scope

- URL WARN implementation
- CTA WARN implementation
- featured_image 対応
- semi-automated publish
- max_items changes
- bulk fixes for existing WordPress drafts
