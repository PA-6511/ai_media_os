# TST-5D-W2B 候補専用受入テスト

このディレクトリの3テストは、未承認の開発候補
`exchange/candidates/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/`
配下の候補実装（`workflow_state_repository_*_candidate.py` 等）を
module importlib で直接ロードして検証する **候補専用の受入テスト** です。

## 通常CIから分離している理由

- 候補アーティファクトは未承認であり、リポジトリに登録されていない。
- 候補が不在の環境では収集時（import時）に FileNotFoundError となり、
  正式コードのCI（`pytest -q`、`pytest.ini` の `testpaths = tests`）を破壊する。
- テストの内容・検証意図（契約値検証・冪等性・重複拒否・互換性）は
  変更せずそのまま保持している（assert・fixture・期待値は無改変）。

## 実行方法（opt-in）

候補アーティファクトを上記パスへ配置した状態で、リポジトリルートから:

```bash
python -m pytest candidate_tests/tst_5d_w2b -q
```

`pytest.ini` の `testpaths = tests` は引数なし実行にのみ適用されるため、
パスを明示すればこのディレクトリのテストを実行できる。

## 前提条件

- 候補アーティファクトが所定パスに存在すること
  （各テストの `CANDIDATE_ROOT` は `Path(__file__).resolve().parents[2]`
  基準の相対パスであり、本ディレクトリは root 直下から2階層に配置されているため
  移設前とパス解決は同一）。
- 候補不在の状態で実行すると収集時に FileNotFoundError となる（仕様どおり）。
