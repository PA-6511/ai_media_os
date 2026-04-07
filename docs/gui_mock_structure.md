# GUI Mock Structure

## 現在のファイル構成
- `ui/index.html`
- `ui/script.js`
- `ui/data/mock-data.js`
- `ui/services/blockService.js`
- `ui/services/logService.js`

## 各ファイルの責務
- `ui/index.html`
  - 画面骨組みとmodule script読込
- `ui/script.js`
  - UI描画とイベント制御
  - service呼び出しの窓口
- `ui/data/mock-data.js`
  - block一覧とaudit logのダミーデータ定義
- `ui/services/blockService.js`
  - block操作用の取得・更新ロジック
  - UIから直接データを触らせない
- `ui/services/logService.js`
  - audit log取得・追記ロジック

## mock と service の分離方針
- UIは `services` の公開関数のみ参照する
- `mock-data.js` はデータ定義に限定する
- データ更新は service 経由に限定する
- UI内にダミーデータ配列を直書きしない

## 後で本実装へ差し替える箇所
- `blockService.js`
  - getBlocks / connect / disconnect / export / delete の内部実装
- `logService.js`
  - getAuditLogs / appendAuditLog の内部実装
- 差し替え時の維持条件
  - 関数名・引数・返却形式（`success`, `message`）は極力維持
  - UI側の呼び出しコードは変更最小化
