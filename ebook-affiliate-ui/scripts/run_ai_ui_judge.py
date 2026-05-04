"""
run_ai_ui_judge.py
Phase0.5 - AI UI judge dry-run実行スクリプト
- campaign_items.json を読み込む
- AI判断を実行する (judge_ai_flags)
- manual_override 優先で ui_flags を解決する (resolve_ui_flags)
- campaign_items.json へ保存する
- 結果をコンソールに出力する（dry-run確認用）
安全条件: 自動投稿・自動削除・自動更新・本番公開は行わない
"""
import json
import sys
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from ai_ui_judge import judge_ai_flags, resolve_ui_flags

DATA_PATH = Path(__file__).parent.parent / "data" / "campaign_items.json"


def main() -> None:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[DRY-RUN] 読み込み完了: {len(items)}件")

    items = judge_ai_flags(items)
    items = resolve_ui_flags(items)

    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print("OK: AI UI judge completed")
    print()
    print(f"{'ID':<15} {'source':<18} {'urgent':<8} {'blink':<8} ai_reason")
    print("-" * 80)
    for item in items:
        flags = item["ui_flags"]
        ai = item.get("ai_flags", {})
        print(
            f"{item['id']:<15} {flags.get('source', ''):<18} "
            f"{str(flags.get('urgent')):<8} {str(flags.get('blink')):<8} "
            f"{ai.get('reason', '')}"
        )


if __name__ == "__main__":
    main()
