# 電子書籍アフィリエイト UI Flags Phase4.33 実URL投入用サンプルデータ設計

## 目的

本ドキュメントは、実アフィリエイトURL投入前に、サンプルデータ構造と検証ルールを固定するための設計書である。
本フェーズは DRY_RUN のみとし、本番反映は行わない。

## 安全前提

- 実アフィリエイトURLは投入しない
- Git commit / Git push は本フェーズでは必須ではない
- WordPress 本番更新は実施しない
- 本番反映判定は BLOCKED のまま維持する

## campaign_items.json への追加形式

対象ファイル: ebook-affiliate-ui/data/campaign_items.json

各 item の推奨構造:

- item_id: 必須
- title: 必須
- affiliate_url: 正式キー（新規追加）
- campaign_url: 互換キー（既存運用互換のため残置）
- store: 任意だが推奨（kobo, rakuten, amazon など）

サンプル例:

```json
{
  "item_id": "kobo-001",
  "title": "サンプル書籍",
  "store": "kobo",
  "affiliate_url": "https://example.invalid/affiliate/kobo-001",
  "campaign_url": "https://example.invalid/campaign/kobo-001"
}
```

## campaign_url 互換方針

- 読み取り優先順位は affiliate_url -> campaign_url
- affiliate_url が存在する場合は campaign_url を無視する
- 移行期間中は campaign_url のみでも表示可能とする
- 最終的には affiliate_url へ統一し、campaign_url 廃止を目指す

## HTML の href="#" 除去方針

- 静的HTMLに固定 href="#" を残さない
- 初期状態は data-item-id を保持し、href は描画時に JS で設定する
- URL未設定時は href を無効URLにせず、クリック不可のUI状態にする

## JS 反映方針（CTAへの反映）

- JSで item_id ごとに affiliate_url を解決し、CTAへ反映する
- URL決定ロジック:
1. affiliate_url が有効なら採用
2. なければ campaign_url が有効なら採用
3. どちらも無効なら CTA を disabled にする

CTA無効化ルール:
- aria-disabled="true" を付与
- disabled クラスを付与
- click ハンドラで遷移を中断
- 計測イベントには url_missing を記録

## URL未設定時の挙動

- URL未設定 item を表示する場合でも、遷移はさせない
- ユーザー向け表示は "準備中" などの非誘導文言にする
- check_affiliate_links.py の判定は引き続き BLOCK

## 許可ドメイン検証の拡張方針

check_affiliate_links.py に追加する検証案:

- URLをパースしてホスト名を抽出
- 許可ドメイン一覧との完全一致またはサブドメイン一致を確認
- 許可外ドメインは invalid としてカウント
- invalid が 1 件でもあれば RESULT: BLOCK

初期許可ドメイン案:
- books.rakuten.co.jp
- hb.afl.rakuten.co.jp
- www.amazon.co.jp
- amzn.to

## サンプルURL方針（本物URLを使わない）

- DRY_RUN専用URLを使用する
- example.invalid など実在しないドメインを利用し、誤遷移を防止する
- サンプルURLは本番投入対象として扱わない
- サンプルURL検出時は "DRY_RUN_ONLY" として明示し、リリース判定を BLOCK

## 判定ルール

DRY_RUN設計の PASS:
- データ構造方針が文書化されている
- 互換方針が文書化されている
- href="#" 除去方針が文書化されている
- CTA無効化方針が文書化されている
- ドメイン検証拡張方針が文書化されている

本番反映の PASS（将来フェーズ）:
- html href=# count : 0
- json invalid count: 0
- 許可ドメイン一致
- DRY_RUN専用URL混入なし
- check_affiliate_links.py 終了コード 0

本番反映は、上記が全て満たされるまで BLOCKED とする。

## ロールバック前提

- campaign_items.json 変更は必ず単独コミットに分離する
- URL投入フェーズで問題発生時は該当コミットのみrevert可能な粒度を維持する
- UI描画ロジック変更とデータ投入変更を別コミットに分離する

## 次フェーズ入力

次フェーズでは以下を実施する。

- campaign_items.json の一部 item に DRY_RUNサンプルURLを投入
- JSのURL解決とCTA無効化を実装
- check_affiliate_links.py に許可ドメイン検証を追加
- 結果が BLOCK であることを確認し、安全に停止する
