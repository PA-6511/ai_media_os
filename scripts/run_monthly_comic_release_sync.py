from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.monthly_comic_release_sync import (
    DEFAULT_SOURCE_URL,
    MonthlyComicReleaseSyncError,
    run_monthly_sync,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monthly comic release collection, diff, import, and enrichment.")
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"), help="Target month in YYYY-MM format.")
    parser.add_argument("--execute", action="store_true", help="Commit SQLite changes and make store API requests. Default is DRY_RUN.")
    parser.add_argument("--phase", choices=("plan", "apply", "enrich", "all"), default="all")
    parser.add_argument("--input-csv", type=Path, help="Optional verified source CSV fallback. Required columns: source_item_id,title,release_date,source_url.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL, help="Calendar URL template; {month} is replaced with YYYY-MM.")
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--page-workers", type=int, default=3, help="Concurrent calendar page GETs (1-4; default 3).")
    parser.add_argument("--detail-limit", type=int, default=1000, help="Maximum public Rakuten product pages used for metadata enrichment (0-2000).")
    parser.add_argument("--detail-workers", type=int, default=3, help="Concurrent product-detail GETs (1-4; default 3).")
    parser.add_argument("--sample-size", type=int, help="Limit import candidates (use 100 for the first production test).")
    parser.add_argument("--no-backup", action="store_true", help="Skip the automatic SQLite backup before --execute.")
    parser.add_argument("--kobo-limit", type=int, default=100)
    parser.add_argument("--dmm-limit", type=int, default=100)
    parser.add_argument("--kindle-limit", type=int, default=100)
    parser.add_argument("--cover-limit", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.sample_size is not None and not 1 <= args.sample_size <= 1000:
        raise SystemExit("--sample-size must be between 1 and 1000")
    if not 0 <= args.detail_limit <= 2000:
        raise SystemExit("--detail-limit must be between 0 and 2000")
    if not 1 <= args.detail_workers <= 4:
        raise SystemExit("--detail-workers must be between 1 and 4")
    for name in ("kobo_limit", "dmm_limit", "kindle_limit", "cover_limit"):
        if not 0 <= getattr(args, name) <= 1000:
            raise SystemExit(f"--{name.replace('_', '-')} must be between 0 and 1000")
    try:
        result = run_monthly_sync(
            repository_root=ROOT,
            month=args.month,
            execute=args.execute,
            phase=args.phase,
            input_csv=args.input_csv,
            source_url=args.source_url,
            max_pages=args.max_pages,
            page_workers=args.page_workers,
            detail_limit=args.detail_limit,
            detail_workers=args.detail_workers,
            sample_size=args.sample_size,
            create_backup=not args.no_backup,
            kobo_limit=args.kobo_limit,
            dmm_limit=args.dmm_limit,
            kindle_limit=args.kindle_limit,
            cover_limit=args.cover_limit,
        )
    except MonthlyComicReleaseSyncError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc), "database_write_performed": False}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
