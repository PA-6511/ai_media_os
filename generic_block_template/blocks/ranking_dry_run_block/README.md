# ranking_dry_run_block

Generated from generic_block_template v1.

- DRY_RUN only
- external API/network disabled
- production_status is NO_GO
- local sample data only
- ranking preview only

## Purpose

R-1前段として、ランキング計算の重み付けプレビューをローカルデータだけで確認するための雛形です。

## Included

- `new_release_weight`
- `sale_weight`
- `author_weight`
- `publisher_weight`
- サンプル3件のスコア計算
- rank 付き preview 出力

## Safety

- 実APIなし
- 外部通信なし
- publish/update/delete/export なし
- controlled run 未配線
- production_status は常に NO_GO
