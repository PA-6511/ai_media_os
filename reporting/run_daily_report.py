from __future__ import annotations

# run_daily_report.py
# 日次レポート生成エントリーポイント。CLI: python3 -m reporting.run_daily_report [--date YYYY-MM-DD]

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from reporting.daily_report_builder import build_daily_report
from reporting.daily_report_writer import write_daily_report


def _format_timestamp(dt: datetime) -> str:
    """ISO 8601 形式でタイムスタンプをフォーマット。"""
    return dt.isoformat(timespec="seconds")


def _print_summary(json_path: Path, txt_path: Path, report: dict) -> None:
    """レポート生成サマリーを表示。"""
    print()
    print("=" * 70)
    print("日次レポート生成完了")
    print("=" * 70)
    print()
    print(f"レポート日:      {report.get('report_date', 'unknown')}")
    print(f"生成時刻:        {report.get('generated_at', '')}")
    print()
    print("=" * 70)
    print("◆ 処理統計")
    print("=" * 70)

    success = report.get("success_count", 0)
    skipped = report.get("skipped_count", 0)
    failed = report.get("failed_count", 0)
    total = success + skipped + failed

    print(f"総処理件数: {total:>5}")
    print(f"  成功:  {success:>5} ({100*success//max(total, 1):>3}%)")
    print(f"  スキップ: {skipped:>5} ({100*skipped//max(total, 1):>3}%)")
    print(f"  失敗:  {failed:>5} ({100*failed//max(total, 1):>3}%)")
    print(f"完了率: {report.get('completion_rate', 0):>6.2f}%")
    print()
    print("=" * 70)
    print("◆ 信号統計")
    print("=" * 70)

    combined = report.get("combined_count", 0)
    price_only = report.get("price_only_count", 0)
    release_only = report.get("release_only_count", 0)
    signal_total = combined + price_only + release_only

    print(f"総シグナル: {signal_total:>5}")
    print(f"  複合: {combined:>5}")
    print(f"  価格: {price_only:>5}")
    print(f"  新刊: {release_only:>5}")
    print()
    print("=" * 70)
    print("◆ Retry Queue")
    print("=" * 70)
    print(f"保留中: {report.get('retry_queued_count', 0):>5}")
    print()
    print("=" * 70)
    print("◆ 出力ファイル")
    print("=" * 70)
    print(f"JSON: {json_path}")
    print(f"TXT:  {txt_path}")
    print()


def generate_daily_report(
    report_date,
    output_dir: Path | None = None,
) -> tuple[dict, Path, Path]:
    """日次レポートを生成し、保存済みファイルパスを返す。

    Args:
        report_date: 対象日 (datetime.date)
        output_dir: 出力ディレクトリ

    Returns:
        (report_dict, json_path, txt_path)
    """
    report = build_daily_report(report_date)
    json_path, txt_path = write_daily_report(report, output_dir=output_dir)
    return report, json_path, txt_path


def main(argv: list[str] | None = None) -> int:
    """メイン処理。

    Args:
        argv: コマンドライン引数 (通常は None で sys.argv を使用)

    Returns:
        終了コード (0=成功, 1=エラー)
    """
    parser = argparse.ArgumentParser(description="日次运用レポートを生成する")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="レポート対象日 (YYYY-MM-DD, デフォルト: 前日)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="出力ディレクトリ (デフォルト: data/reports)",
    )

    args = parser.parse_args(argv)

    try:
        # レポート対象日を決定
        if args.date:
            try:
                report_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                print(f"エラー: --date は YYYY-MM-DD 形式で指定してください: {args.date}")
                return 1
        else:
            # デフォルト: 前日
            report_date = (datetime.now() - timedelta(days=1)).date()

        print()
        print("=" * 70)
        print("日次レポート生成開始")
        print("=" * 70)
        print()
        print(f"レポート対象日: {report_date.isoformat()}")
        print()

        # レポートを生成して保存
        report, json_path, txt_path = generate_daily_report(
            report_date=report_date,
            output_dir=args.output_dir,
        )
        print(f"✓ レポート生成: {len(report)} 項目")
        print(f"✓ JSON 保存: {json_path}")
        print(f"✓ TXT 保存:  {txt_path}")

        # サマリーを表示
        _print_summary(json_path, txt_path, report)

        return 0

    except Exception as e:
        print()
        print(f"エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
