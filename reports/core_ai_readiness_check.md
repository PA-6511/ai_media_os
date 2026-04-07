# 概要

## 現在地
- コアAI改良は第7弾まで完了し、主要な安全化・監査性・設定外出し・テスト整備が実施済み。
- 現在の実行結果は以下。
  - `python3 -m py_compile $(find . -name "*.py")`: 成功
  - `pytest -q`: 26 passed

## 今回の目的
- retry / logging / config / interfaces / tests の5領域を中心に、運用判断に必要な棚卸しを行う。

## 結論
- **運用開始判定: 条件付きで運用可**

# 実施済み改良

## 状態遷移固定化
- 実装したこと:
  - `pipelines/retry_queue_store.py` に `ALLOWED_RETRY_TRANSITIONS` と `validate_transition` を実装し、許可遷移のみ通過する設計へ統一。
- 確認済み:
  - 不正遷移拒否の動作をテストで固定（`tests/test_retry_queue_store.py`）。
- 未了:
  - 一部の境界遷移（missing起点や全遷移表の網羅）について追加テスト余地あり。
- 現在のリスク:
  - 新しい状態を将来追加した場合、遷移表とテストの同時更新を漏らすと不整合が起きる。

## 監査ログ強化
- 実装したこと:
  - `event_name / event_id / reason / current_state / next_state` を含む構造化監査ログを retry 系イベントへ追加。
  - `monitoring/failure_reporter.py` へ `event_id` と `reason` の橋渡しを追加。
- 確認済み:
  - `tests/test_retry_audit_logs.py` で WARNING / INFO / ERROR の3レベルと主要キー存在を固定。
- 未了:
  - `event_id` 自動生成時の形式検証、reasonサニタイズ境界（長文切り詰め）検証は未実施。
- 現在のリスク:
  - ログフォーマット文字列変更時にダッシュボード/運用手順側が先に壊れる可能性。

## interface/schema 整理
- 実装したこと:
  - `core/interfaces.py` に `CoreInput` / `BlockResult` / `CoreDecision`（TypedDict + Literal）を導入。
  - normalize/build ヘルパーで入力・意思決定を fail-safe に正規化。
- 確認済み:
  - `tests/test_core_interfaces.py` で不正入力時の安全側フォールバックを固定。
- 未了:
  - ブロック追加時の collector 側契約チェック（開発フロー/規約）の文書化が薄い。
- 現在のリスク:
  - 仕様を知らない新規ブロックが不完全 payload を返すと、期待より多く drop される可能性。

## 設定外出し
- 実装したこと:
  - `config/core_runtime.json` + `config/core_runtime_config.py` を追加し、retry/core/logging の主要値を外出し。
  - 壊れ値フォールバック、型変換、clamp を getter に集約。
- 確認済み:
  - `tests/test_core_runtime_config.py` で壊れ設定時のフォールバックと clamp を固定。
- 未了:
  - 運用向け設定変更手順（変更レビュー、反映フロー、ロールバック手順）の文書化が未整備。
- 現在のリスク:
  - JSON の誤編集を起点に想定外の挙動になる可能性（fail-safeで緩和はあるが、意図との差分は残る）。

## retry 系ハードコード整理
- 実装したこと:
  - max retry 既定値 `3` の散在を getter 経由へ統一（`retry_policy`, `publish_article_pipeline`, `main` など）。
- 確認済み:
  - retry 関連分岐を unit テストで固定。
- 未了:
  - retry ポリシーの運用閾値見直しサイクル（定期レビュー基準）未定義。
- 現在のリスク:
  - 業務要件変化時、値調整だけで十分か（分類ロジック修正要否）の判断が属人化しやすい。

## テスト追加
- 実装したこと:
  - 主要テスト群を追加。
  - `tests/test_retry_queue_store.py`
  - `tests/test_core_interfaces.py`
  - `tests/test_core_runtime_config.py`
  - `tests/test_retry_policy.py`
  - `tests/test_publish_article_pipeline.py`
  - `tests/test_main_retry_paths.py`
  - `tests/test_retry_failed_items.py`
  - `tests/test_retry_audit_logs.py`
- 確認済み:
  - `pytest -q` で 26 passed。
- 未了:
  - CI での自動実行・PRゲート化は未整備。
- 現在のリスク:
  - 手元実行前提のため、将来の変更で未検知回帰が入り込む余地がある。

# テスト状況

## py_compile
- 実行: `python3 -m py_compile $(find . -name "*.py")`
- 結果: 成功（構文エラーなし）

## pytest
- 実行: `pytest -q`
- 結果: **26 passed**

## テスト本数
- 現在の管理テスト: 26ケース（pytest集計ベース）

## 主な対象
- retry 状態遷移
- retry/give_up 判定
- publish/retry 分岐
- batch retry ループ集計
- interface normalize/fail-safe
- runtime config fallback/clamp
- 監査ログ項目とレベル

# 現在の強み
- fail-safe:
  - 不正遷移・不正decision・壊れ設定で安全側へ倒す設計が実装済み。
- retry運用安全性:
  - 遷移制御と上限管理、give_up 分岐が一貫。
- 監査追跡性:
  - event_id を中心に追跡可能。
- 設定調整性:
  - 本番コード変更なしで主要閾値を調整可能。

# 未了項目
- 依存管理ファイルの整備（pytest 依存を含む実行要件の明文化）。
- CI 連携（最低限 `py_compile` + `pytest` の自動実行）。
- 運用手順書の最終化（設定変更手順、障害時切り戻し、ログ確認手順）。
- 監査ログ追加観点の補完（event_id自動生成、reasonサニタイズ境界、missing起点の詳細ケース）。
- block 追加時の契約チェック手順（collector / interface 規約）の文書化。

# 要注意リスク
- pytest 依存の明文化不足により、環境差で再現不能になる可能性。
- 本番投入時の運用フロー未文書化により、初動対応が遅れる可能性。
- block 追加時に interface 規約が徹底されず、silent drop が増える可能性。

# 運用開始判定
- 判定: **条件付きで運用可**
- 理由:
  - 安全性（fail-safe）とテスト（26 passed）は十分に強い。
  - retry / logging / config の基盤は運用開始水準。
  - ただし CI・依存管理明文化・運用手順文書化が未完で、運用リスクが残る。

# 次の優先作業

## Top3（運用前に最低限やるならこれ）
1. `requirements.txt` または同等手段でテスト依存（pytest含む）を固定し、セットアップ手順を明文化する。
2. CIで `py_compile` と `pytest -q` を自動実行し、PR時の回帰検知を必須化する。
3. 運用Runbookを1ページ化し、設定変更・監査ログ確認・障害時切り戻し手順を定義する。
