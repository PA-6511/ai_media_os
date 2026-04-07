from __future__ import annotations

from collections import Counter

from pipelines.retry_queue_store import list_queue_items


def main() -> None:
    rows = list_queue_items()
    counter = Counter(str(row.get("retry_status", "unknown")) for row in rows)

    print("retry_queue status counts:")
    print(f"queued: {counter.get('queued', 0)}")
    print(f"retrying: {counter.get('retrying', 0)}")
    print(f"resolved: {counter.get('resolved', 0)}")
    print(f"give_up: {counter.get('give_up', 0)}")

    print("\nqueued items:")
    queued = [row for row in rows if row.get("retry_status") == "queued"]
    if not queued:
        print("- なし")
    else:
        for row in queued:
            print(f"- {row.get('slug')} retry_count={row.get('retry_count')} next_retry_at={row.get('next_retry_at')}")

    print("\ngive_up items:")
    give_up = [row for row in rows if row.get("retry_status") == "give_up"]
    if not give_up:
        print("- なし")
    else:
        for row in give_up:
            print(f"- {row.get('slug')} error={row.get('last_error', '')}")


if __name__ == "__main__":
    main()
