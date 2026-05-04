"""
cli.py
Phase0.5 - manual_override 対話型CLI
- 一覧表示
- 推す (apply_manual_override)
- 解除 (clear_manual_override)
"""
import sys
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from manual_override import (
    load_items,
    apply_manual_override,
    clear_manual_override,
    is_active_override,
)


def list_items() -> None:
    items = load_items()
    print("\n=== キャンペーン一覧 ===")
    for item in items:
        status = "点滅中/manual" if is_active_override(item) else "AI判断"
        title = item.get("title", "")
        item_id = item.get("id", "")
        sale_end = item.get("sale_end", "")
        print(f"- {item_id}: {title} [{status}] 終了: {sale_end}")


def main() -> None:
    while True:
        print("\n=== manual_override CLI ===")
        print("1: 一覧表示")
        print("2: 推す")
        print("3: 解除")
        print("0: 終了")
        choice = input("選択: ").strip()

        if choice == "1":
            list_items()

        elif choice == "2":
            list_items()
            item_id = input("\n推す item_id: ").strip()
            try:
                hours = int(input("時間 6 / 24 / 48: ").strip())
            except ValueError:
                print("ERROR: 数値を入力してください")
                continue
            reason = input("理由（必須）: ").strip()
            try:
                apply_manual_override(item_id, hours, reason)
                print("OK: manual_override を適用しました")
            except Exception as e:
                print(f"ERROR: {e}")

        elif choice == "3":
            list_items()
            item_id = input("\n解除 item_id: ").strip()
            reason = input("解除理由（空欄でmajual clear）: ").strip() or "manual clear"
            try:
                clear_manual_override(item_id, reason)
                print("OK: manual_override を解除しました")
            except Exception as e:
                print(f"ERROR: {e}")

        elif choice == "0":
            break

        else:
            print("無効な選択です")


if __name__ == "__main__":
    main()
