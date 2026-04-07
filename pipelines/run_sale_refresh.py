from __future__ import annotations

import os

from main import run_pipeline


def main() -> None:
    """sale_article のみ優先再生成する簡易CLI。"""
    max_items_env = (os.getenv("MAX_ITEMS", "")).strip().lower()
    max_items = None if max_items_env in {"", "none", "all", "*"} else int(max_items_env)

    save_per_item_files = (os.getenv("SAVE_PER_ITEM_FILES", "1")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    result = run_pipeline(
        max_items=max_items,
        save_per_item_files=save_per_item_files,
        only_sale_articles=True,
    )

    print("sale refresh finished")
    print(f"success_count: {result.get('success_count', 0)}")
    print(f"skipped_count: {result.get('skipped_count', 0)}")
    print(f"failed_count: {result.get('failed_count', 0)}")


if __name__ == "__main__":
    main()
