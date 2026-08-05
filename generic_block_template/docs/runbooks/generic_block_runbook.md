# Generic Block Runbook v1

## 目的
電子書籍ブロックで確立した安全機構を再利用できる汎用雛形として運用する。

## 固定ルール
- 実API呼び出し: 禁止
- 外部通信: 禁止
- WordPress操作: 禁止
- publish/update/delete/export: 禁止
- 実行モード: DRY_RUN のみ
- 本番運用状態: NO_GO 固定
- 実行対象: sample_block のみ

## 手順
1. テンプレート妥当性チェックを実行
2. controlled run を 1 回だけ実行
3. evidence を logs に保存
4. 総合レポートを生成して PASS/WARN/FAIL を確認

## コマンド
```bash
cd /home/deploy/ai_media_os
python3 generic_block_template/scripts/check_generic_block_template.py
python3 generic_block_template/scripts/run_generic_controlled_once.py
python3 generic_block_template/scripts/generate_generic_block_report.py
```

## NO_GO維持確認
- すべての出力に production_status=NO_GO が含まれること
- sample_block 以外は実行されないこと
