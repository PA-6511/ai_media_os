# WordPress File Plan (Dry Run)

## Candidate files for deployment prep
- Fixed page content (HTML block)
- Cocoon Additional CSS
- Optional child-theme JS file (future)
- JSON data source file (static in initial phase)

## Initial recommended mapping
1. Fixed page
- Paste from: fixed-page-html-draft.html
- Includes container HTML and script hook call

2. Cocoon Additional CSS
- Paste from: cocoon-css-extract.css

3. JS loading
- Initial: inline script block in fixed page
- Next: move to child theme JS and enqueue

4. JSON source
- Initial: static JSON path defined in json-placement-plan.md

## Not included in this phase
- Production file overwrite
- Theme file direct edit on production
- Plugin packaging
