# GIB-alpha0 Runbook

## 概要

Generic Inference Block AI α版 (GIB-alpha0) の設計・実行手順書です。

## 現在の状態

| 項目 | 値 |
|------|-----|
| 版 | alpha0 |
| 状態 | DESIGN_ONLY |
| 本番判定 | NO_GO |
| 実行モード | DRY_RUN_ONLY |
| 実 LLM | 未接続 (stub_no_model_loaded) |

## 禁止事項（α版）

- credential.env への接触
- WordPress への書き込み
- 外部 API の実行（ネットワーク通信）
- systemd の操作
- GO/NO-GO 最終判断の代行
- 実 LLM 呼び出し（GIB-β で実装予定）

## 対応タスクタイプ（7種）

1. `phase_log_summary` — フェーズ実行ログの要約
2. `validator_result_explain` — バリデータ結果の説明
3. `product_summary` — 商品サマリー生成（dry-run）
4. `social_post_draft` — SNS 投稿案生成（dry-run）
5. `article_outline` — 記事アウトライン生成（dry-run）
6. `compliance_classify` — コンプライアンス分類
7. `security_log_explain` — セキュリティログ説明

## 実行手順

### テスト（全スイート）

```bash
cd /home/deploy/ai_media_os
PYTHONPATH=. python3 -m pytest generic_inference_block_ai/tests/ -v
```

### バリデーションレポート生成

```bash
cd /home/deploy/ai_media_os
PYTHONPATH=. python3 generic_inference_block_ai/run_gib_alpha_validator.py
```

### デモ実行（dry-run のみ）

```bash
cd /home/deploy/ai_media_os
PYTHONPATH=. python3 generic_inference_block_ai/run_gib_alpha_demo_no_execution.py
```

## 次ステップ（GIB-β）

- Gemma 4 QAT / Ollama / llama.cpp への接続
- `model_runtime_enabled: true` に昇格（設計審査後）
- `real_llm_call_allowed: true` に昇格（本番承認後）
