# Sale Article Payloads

## Summary
- status: PASS
- phase: SFB-3
- article_payload_count: 2
- skipped_candidate_count: 0
- input_quality_gate_status: PASS

## Safety Gates
- production_status: NO_GO
- external_api_called: False
- external_network_called: False
- wordpress_write_executed: False
- creators_api_called: False
- amazon_scraping_called: False

## Article Payloads
| payload_id | title | review_bucket | priority_score | link_type | human_review_required |
| --- | --- | --- | --- | --- | --- |
| sfb3-payload-001 | Crimson Library | ready_high_priority | 94 | amazon_product_link_candidate | True |
| sfb3-payload-002 | Glass Moon | needs_asin_confirmation | 59 | amazon_search_link_candidate | True |

## Skipped Candidates
- none

## Next Phase
- next_recommended_phase: SFB-4: Article payload quality report / human review handoff
