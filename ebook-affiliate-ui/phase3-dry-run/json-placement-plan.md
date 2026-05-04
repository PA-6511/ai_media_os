# JSON Placement Plan (Dry Run)

## Options
1. Static JSON under WordPress public path
- Example: /wp-content/uploads/ebook-affiliate-ui/campaign_items.json
- Pros: simple and fast verification
- Cons: update operation needs process control

2. Static JSON outside theme path
- Example: /var/www/shared/ebook-affiliate-ui/campaign_items.json
- Pros: independent from theme updates
- Cons: routing and permissions become complex

3. REST API endpoint
- Pros: long-term extensibility
- Cons: implementation cost is higher for initial release

## Initial decision
- Use Option 1 (static JSON under WordPress public path).

## Access check commands (dry run)
- curl -I <json-url>
- curl <json-url> | head

## Validation points
- HTTP 200
- Valid JSON
- id values match fixed page data-item-id values
