# Ranking DRY_RUN Preview

- status: PASS
- mode: DRY_RUN
- production_status: NO_GO
- policy_path: /home/deploy/ai_media_os/config/ranking_policy.json
- input_source: /home/deploy/ai_media_os/generic_block_template/fixtures/ranking_sample_items.json
- input_status: PASS

## Weights
- new_release_weight: 0.35
- sale_weight: 0.3
- author_weight: 0.2
- publisher_weight: 0.15

## Ranking Preview
- rank=1 item_id=sample-1 title=新刊セール注目作A score=0.815
- rank=2 item_id=sample-3 title=話題作C score=0.66
- rank=3 item_id=sample-2 title=定番人気作B score=0.53
