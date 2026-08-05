# M23 人間目視レビュー・チェックリスト

確認対象は、次の安全プレビュー2ファイルだけです。

- デスクトップ:
  `exchange/previews/new_release/fresh/new-release-comic-20260703-001.wordpress_layout_desktop_safe_preview.html`
- スマートフォン:
  `exchange/previews/new_release/fresh/new-release-comic-20260703-001.wordpress_layout_mobile_safe_preview.html`

元のレンダリング済みHTMLや更新Payloadには完全なストア導線情報が含まれるため、通常の目視確認には使用しないでください。

## デスクトップ

- [ ] 書影が左側に配置されている
- [ ] 右側の先頭にPR表記がある
- [ ] Amazon、楽天Kobo、DMMの順で縦並びになっている
- [ ] 作品詳細がストアボタン群の下にある
- [ ] 書影と右側領域の比率が不自然ではない
- [ ] 右側に過剰な空白がない
- [ ] 作品詳細のラベルと値が読みやすい
- [ ] 文字が不自然に細切れ改行されていない

## スマートフォン

- [ ] 書影が先頭にある
- [ ] 作品詳細が書影の次にある
- [ ] PR表記が各ストアボタンより前にある
- [ ] Amazon、楽天Kobo、DMMの順になっている
- [ ] 横スクロールが発生していない
- [ ] 詳細欄のラベルと値が読みやすい
- [ ] 余白が広すぎず狭すぎない

## 機械検証済み境界

- [x] 更新フィールドは `content` と `comment_status` のみ
- [x] `comment_status=closed`
- [x] 外部リンクは安全プレビュー内で無効
- [x] 外部画像通信は埋込みプレースホルダーに置換
- [x] 完全なストアURLを安全プレビューへ出力していない
- [x] アフィリエイト識別子を安全プレビューへ出力していない
- [x] WordPress更新認可は未発行
- [x] WordPressアクセス・更新は未実行
