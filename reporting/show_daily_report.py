from __future__ import annotations

# show_daily_report.py
# 生成済み日次レポートを表示するユーティリティ。
# - 引数なし: 最新の txt を表示
# - --date YYYYMMDD: 指定日のレポートを表示
# - --format txt/json: 表示フォーマットを切替

import argparse
import re
import sys
from pathlib import Path

from reporting.daily_report_writer import list_available_report_dates


REPORT_NAME_PATTERN = re.compile(r"^daily_report_(\d{8})\.(txt|json)$")
VALID_FORMATS: set[str] = {"txt", "json"}


def list_report_files(report_dir: Path) -> list[Path]:
    """reports ディレクトリ配下の対象ファイルを列挙する。"""
    if not report_dir.exists() or not report_dir.is_dir():
        return []

    files: list[Path] = []
    for path in report_dir.iterdir():
        if path.is_file() and REPORT_NAME_PATTERN.match(path.name):
            files.append(path)
    return sorted(files)


def extract_report_date(filename: str) -> str | None:
    """ファイル名から日付 (YYYYMMDD) を抽出する。"""
    matched = REPORT_NAME_PATTERN.match(filename)
    if not matched:
        return None
    return matched.group(1)


def find_latest_report(report_dir: Path, report_format: str) -> Path | None:
    """指定フォーマットの最新レポートを返す。"""
    normalized_format = report_format.lower()
    if normalized_format not in VALID_FORMATS:
        raise ValueError(
            f"不正な format です: {report_format} (許可: {sorted(VALID_FORMATS)})"
        )

    candidates = sorted(report_dir.glob(f"daily_report_*.{normalized_format}"))
    if not candidates:
        return None

    dated_candidates: list[tuple[str, Path]] = []
    for path in candidates:
        date_str = extract_report_date(path.name)
        if date_str:
            dated_candidates.append((date_str, path))

    if not dated_candidates:
        return None

    dated_candidates.sort(key=lambda x: x[0])
    return dated_candidates[-1][1]


def find_report_by_date(report_dir: Path, date_str: str, report_format: str) -> Path | None:
    """指定日・指定フォーマットのレポートを返す。"""
    normalized_format = report_format.lower()
    if normalized_format not in VALID_FORMATS:
        raise ValueError(
            f"不正な format です: {report_format} (許可: {sorted(VALID_FORMATS)})"
        )

    if not re.fullmatch(r"\d{8}", date_str):
        raise ValueError("--date は YYYYMMDD 形式で指定してください")

    target_path = report_dir / f"daily_report_{date_str}.{normalized_format}"
    if target_path.exists() and target_path.is_file():
        return target_path
    return None


def show_report(path: Path) -> None:
    """レポートファイル内容を標準出力に表示する。"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"レポートファイルが見つかりません: {path}")
    except OSError as exc:
        raise OSError(f"レポートファイルの読み込みに失敗しました: {path} ({exc})")

    print(text, end="" if text.endswith("\n") else "\n")


def _default_report_dir() -> Path:
    """デフォルトの reports ディレクトリを返す。"""
    return Path(__file__).resolve().parents[1] / "data" / "reports"


def main(argv: list[str] | None = None) -> int:
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(description="日次レポートを表示する")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="表示対象日 (YYYYMMDD)。省略時は最新を表示",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="txt",
        choices=sorted(VALID_FORMATS),
        help="表示フォーマット (txt/json)",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="レポートディレクトリ (デフォルト: data/reports)",
    )

    args = parser.parse_args(argv)
    report_dir = args.report_dir or _default_report_dir()
    report_format = args.format.lower()

    try:
        # レポートディレクトリの基本チェック
        all_reports = list_report_files(report_dir)
        if not all_reports:
            print("レポートファイルが見つかりません。先に run_daily_report を実行してください。")
            return 1

        # 指定日あり: ピンポイント検索
        if args.date:
            found = find_report_by_date(report_dir, args.date, report_format)
            if found is None:
                available_dates = list_available_report_dates(report_dir)
                latest = available_dates[-1] if available_dates else "なし"
                print(f"指定日のレポートが見つかりません: {args.date}")
                print(f"利用可能な最新日付: {latest}")
                return 1

            print(f"レポート表示: {found}")
            print()
            show_report(found)
            return 0

        # 指定日なし: 最新を表示
        latest_report = find_latest_report(report_dir, report_format)
        if latest_report is None:
            print("レポートファイルが見つかりません。先に run_daily_report を実行してください。")
            return 1

        print(f"最新レポート: {latest_report}")
        print()
        show_report(latest_report)
        return 0

    except ValueError as exc:
        print(f"エラー: {exc}")
        return 1
    except Exception as exc:
        print(f"エラーが発生しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
