# SFB Dashboard Operations Checklist

## 1. 基本情報

- run_id:
- operator:
- reviewer:
- checked_at_utc:

## 2. 実行

- [ ] SFB-13 diff 再生成を実行
- [ ] SFB-14 dashboard 再生成を実行
- [ ] SFB-15 readiness チェックを実行

## 3. 生成物確認

- [ ] sfb_13 JSON 生成済み
- [ ] sfb_13 MD 生成済み
- [ ] sfb_14 JSON 生成済み
- [ ] sfb_14 MD 生成済み
- [ ] sfb_15 readiness JSON 生成済み

## 4. WARN確認

- [ ] sfb_14 warn_list を確認
- [ ] undefined_phase_mapping を確認
- [ ] sfb_15 warn_list を確認

## 5. artifact_missing確認

- [ ] artifact_missing = 0
- [ ] missing_artifact_ids が空

## 6. 安全確認

- [ ] production_status = NO_GO
- [ ] mode = DRY_RUN
- [ ] external_api_called = false
- [ ] external_network_called = false
- [ ] wordpress_write_executed = false
- [ ] approval_token_consumed = false

## 7. 差分確認

- [ ] added_candidates を確認
- [ ] removed_candidates を確認
- [ ] updated_candidates を確認
- [ ] duplicate_candidates を確認
- [ ] asin_presence_change を確認
- [ ] confidence_change を確認
- [ ] review_bucket_change を確認
- [ ] adopt_candidate_count_change を確認

## 8. 判定

- [ ] READY
- [ ] STOP_AND_FIX

備考:
