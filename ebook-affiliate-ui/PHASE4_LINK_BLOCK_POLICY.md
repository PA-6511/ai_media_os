# 電子書籍アフィリエイト UI Flags Phase4 リンクBLOCKポリシー

目的:
本番反映前に、未設定リンクの混入を機械的に遮断する。

## BLOCK判定条件

以下のいずれかを1件でも検出した場合は、本番反映を BLOCK とする。

1. HTML内のカードリンクに `href="#"` が残存
2. JSON内のリンクフィールドが未設定
- 対象フィールド: `affiliate_url`（優先）または `campaign_url`
- 未設定の定義: キーなし / `null` / 空文字 / `#`

## 運用ルール

- `href="#"` 残存件数は 0 件でなければならない
- JSONの対象リンクフィールド未設定件数は 0 件でなければならない
- 上記が 0 件でない限り、本番反映は実行しない

## 実行コマンド

`ebook-affiliate-ui/` で実行:

```bash
python3 scripts/check_affiliate_links.py
```

## 期待される終了コード

- `0`: PASS（BLOCK条件なし）
- `1`: FAIL（BLOCK条件あり）

## 現時点の状態（Phase4.16開始時点）

- HTML `href="#"`: 10件
- JSON リンク未設定: 10件
- 判定: BLOCK（本番反映不可）
