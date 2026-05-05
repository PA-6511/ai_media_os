# 電子書籍アフィリエイト UI Flags Phase4.111.2A

## 8件先行投入モード設計（シーモア申請中）

## 1. 目的

本設計は、cmoa 2件が申請中の間に、rakuten_kobo / kindle / dmm_books の8件のみ先行投入して検証を進めるための一時ルールを固定する。

本フェーズは「安全に先行検証すること」を目的とし、PRODUCTION exit 0 達成と本番反映は目標にしない。

## 2. 適用範囲

対象:
- data/real_url_input_template.json
- data/campaign_items.json
- scripts/check_affiliate_links.py（集計表示のみ。ゲート基準は変更しない）

非対象:
- WordPress本番反映
- cmoa 2件の本URL化

## 3. 対象・保留

先行投入対象（8件）:
- rakuten_kobo: kobo-001, kobo-002, kobo-007
- kindle: kobo-003, kobo-006, kobo-010
- dmm_books: kobo-004, kobo-008

保留（2件）:
- cmoa: kobo-005, kobo-009

## 4. 8件先行投入ルール

- real_url 必須は先行8件のみ
- cmoa 2件は real_url 空欄を許容
- campaign_items.json への反映は8件のみ
- 先行8件は affiliate_url / campaign_url を同値で実URL化
- cmoa 2件の affiliate_url / campaign_url は変更しない
- check_affiliate_links.py の PRODUCTION exit 0 は未要求
- DRY_RUNで8件のURL形式と許可ドメイン一致を確認
- 本番反映状態は BLOCKED 維持

## 5. cmoaカードの扱い

本フェーズでは既存DRY_RUN挙動を維持する。

- cmoaカードは後続の承認完了フェーズで本URL化する
- 8件先行投入フェーズでは cmoa を完了扱いにしない

## 6. 期待状態（8件先行投入後）

- store_not_allowed: 0
- domain_not_allowed: 0
- 8件の実URL: 許可ドメイン内でOK
- cmoa 2件: 未投入要因として残る
- PRODUCTION: BLOCK
- 本番反映: BLOCKED

## 7. 判定の前提

check_affiliate_links.py は affiliate_url / campaign_url の両方を検証する。
そのため、cmoa 2件が未投入のままでは PRODUCTION は BLOCK のままで正しい。

## 8. Phase4.111.3 合格条件の一時変更

通常の「全10件・empty 0件」条件を一時的に以下へ置換する。

- 合格判定対象は先行8件の投入品質
- cmoa 2件未投入を許容
- PRODUCTION exit 0 を必須にしない
- 本番反映は引き続き BLOCKED

## 9. 後続フェーズ

- Phase4.111.3A: 8件先行投入データ検証（DRY_RUN）
- Phase4.111.3B: cmoa承認待ち継続管理
- Phase4.111.4: cmoa 2件投入後に10件完全モードへ復帰
