# PR WARN 1週間観測テンプレート

## 日次記録フォーマット

```text
観測日:
対象期間:
対象draft件数:

PR WARN率:
FAIL件数:
ERROR件数:
duplicate件数:

daily_result: OK / NG
メモ:
```

## 日次OK条件

```text
PR WARN率を記録できている
FAIL = 0
ERROR = 0
duplicate = 0
Phase2 health = OK
```

## 週次Go条件

```text
PR WARN率が週初より低下
FAIL / ERROR / duplicate が全日 0
運用負荷が増えていない
```

## 判定

| 条件 | 結果 |
| --- | --- |
| 全条件OK | 次に URL WARN 改善へ進む |
| PR WARN低下なし | PR表記ルールを微修正して再観測 |
| 重大系発生 | 改善フェーズ停止、原因調査 |

## 固定運用

```text
1施策 = PR WARNのみ
1観測 = 1週間
半自動公開 = 保留継続
```
