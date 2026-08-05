from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def read_console_line(
    prompt: str,
) -> str:
    """Read one terminal line with UTF-8/CP932 fallback."""

    sys.stdout.write(prompt)
    sys.stdout.flush()

    stream = getattr(
        sys.stdin,
        "buffer",
        None,
    )

    if stream is None:
        try:
            return sys.stdin.readline().strip()
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                "端末入力の文字コードを解釈できませんでした。"
            ) from exc

    raw = stream.readline()

    if raw == b"":
        raise RuntimeError(
            "対話入力が終了しました。"
            "通常のSSH端末から直接実行してください。"
        )

    raw = raw.rstrip(
        b"\\r\\n"
    )

    decoding_errors = []

    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp932",
        "shift_jis",
    ):
        try:
            return raw.decode(
                encoding
            ).strip()
        except UnicodeDecodeError as exc:
            decoding_errors.append(
                f"{encoding}:{exc}"
            )

    preview = raw[:16].hex()

    raise RuntimeError(
        "端末入力の文字コードを解釈できませんでした。"
        f" bytes={preview} "
        f"attempts={decoding_errors}"
    )


def required(prompt: str) -> str:
    while True:
        value = read_console_line(
            f"{prompt}: "
        )

        if value:
            return value

        print(
            "必須項目です。空欄にはできません。"
        )


def optional(prompt: str) -> str:
    return read_console_line(
        f"{prompt}［省略可］: "
    )


def latest_input_root() -> Path:
    base = (
        ROOT
        / "exchange/manual_input/x_r11_real_source"
    )

    candidates = sorted(
        (
            path
            for path in base.iterdir()
            if path.is_dir()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise RuntimeError(
            "手入力用ディレクトリがありません。"
        )

    return candidates[0].resolve()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-root",
        type=Path,
    )

    args = parser.parse_args()

    input_root = (
        args.input_root.resolve()
        if args.input_root
        else latest_input_root()
    )

    input_csv = (
        input_root
        / "x_r11_manual_real_source_intake.csv"
    )
    pending_csv = (
        input_root
        / "x_r11_manual_real_source_intake.pending.csv"
    )
    policy_path = (
        input_root
        / "x_r11_manual_real_source_intake_policy.json"
    )
    manifest_path = (
        input_root
        / "input_manifest.json"
    )

    for path in (
        input_csv,
        policy_path,
        manifest_path,
    ):
        if not path.is_file():
            raise RuntimeError(
                f"必要ファイルがありません: {path}"
            )

    line_count = len(
        input_csv.read_text(
            encoding="utf-8-sig"
        ).splitlines()
    )

    if line_count != 1:
        raise RuntimeError(
            "入力CSVは空テンプレートではありません。"
            "既存行の上書きは禁止します。"
        )

    pending_csv.unlink(
        missing_ok=True
    )

    header = [
        "intake_id",
        "title",
        "volume_label",
        "release_date",
        "publisher",
        "authors",
        "category",
        "source_discovery_url",
        "publisher_confirmation_url",
        "amazon_url",
        "rakuten_kobo_url",
        "dmm_url",
        "description_mode",
        "human_review_state",
    ]

    print()
    print(
        "実在する新刊1件の情報を入力してください。"
    )
    print(
        "仮URL、example.com、サンプル名、"
        "テスト名は禁止です。"
    )
    print()

    title = required(
        "作品タイトル"
    )
    volume_label = optional(
        "巻数表記（例：第1巻）"
    )
    release_date = required(
        "発売日（YYYY-MM-DD）"
    )
    publisher = required(
        "出版社"
    )
    authors = optional(
        "著者名。複数の場合は | 区切り"
    )

    while True:
        category = required(
            "カテゴリ comic / light_novel / general_book"
        )

        if category in {
            "comic",
            "light_novel",
            "general_book",
        }:
            break

        print(
            "指定可能なのは comic、light_novel、"
            "general_bookです。"
        )

    source_discovery_url = required(
        "発見元URL"
    )
    publisher_confirmation_url = required(
        "出版社公式確認URL"
    )
    amazon_url = optional(
        "Amazon商品URL"
    )
    rakuten_kobo_url = optional(
        "楽天Kobo商品URL"
    )
    dmm_url = optional(
        "DMMブックス商品URL"
    )

    if not any(
        (
            amazon_url,
            rakuten_kobo_url,
            dmm_url,
        )
    ):
        raise RuntimeError(
            "Amazon、楽天Kobo、DMMのうち"
            "最低1件の販売URLが必要です。"
        )

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    row = {
        "intake_id": (
            f"x-r11-real-{stamp}"
        ),
        "title": title,
        "volume_label": volume_label,
        "release_date": release_date,
        "publisher": publisher,
        "authors": authors,
        "category": category,
        "source_discovery_url": (
            source_discovery_url
        ),
        "publisher_confirmation_url": (
            publisher_confirmation_url
        ),
        "amazon_url": amazon_url,
        "rakuten_kobo_url": (
            rakuten_kobo_url
        ),
        "dmm_url": dmm_url,
        "description_mode": "MINIMAL",
        "human_review_state": (
            "NOT_REVIEWED"
        ),
    }

    print()
    print("=== 入力内容確認 ===")

    for field in header:
        print(
            f"{field}={row[field]}"
        )

    print()

    confirmation = required(
        "この内容で検証する場合は YES"
    )

    if confirmation != "YES":
        print(
            "入力を中止しました。"
        )
        return 1

    with pending_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=header,
        )
        writer.writeheader()
        writer.writerow(row)

    validation_stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    validation_root = (
        ROOT
        / (
            "exchange/diagnostics/x_draft_module/"
            "x_r11_manual_real_source_data_entry"
        )
        / validation_stamp
    )

    command = [
        sys.executable,
        str(
            ROOT
            / "scripts/validate_x_r11_manual_real_source_intake.py"
        ),
        "--input-csv",
        str(pending_csv),
        "--policy",
        str(policy_path),
        "--output-root",
        str(validation_root),
    ]

    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )

    if completed.stdout:
        print(completed.stdout)

    if completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
        )

    if completed.returncode != 0:
        pending_csv.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "手入力データの検証に失敗しました。"
        )

    result_path = (
        validation_root
        / "x_r11_manual_real_source_intake_result.json"
    )

    result = json.loads(
        result_path.read_text(
            encoding="utf-8"
        )
    )

    expected_status = (
        "PASS_MANUAL_REAL_SOURCE_INTAKE_"
        "ONE_VALID_CANDIDATE_REVIEW_REQUIRED"
    )

    if result.get("status") != expected_status:
        pending_csv.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "候補は有効条件を満たしていません。"
            f" status={result.get('status')}"
        )

    pending_csv.replace(
        input_csv
    )

    input_sha256 = sha256_file(
        input_csv
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest.update(
        {
            "status": (
                "ONE_VALID_REAL_SOURCE_ROW_ENTERED_"
                "AWAITING_HUMAN_REVIEW"
            ),
            "row_entered": True,
            "row_entered_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "input_csv_current_sha256": (
                input_sha256
            ),
            "validation_result_path": str(
                result_path.resolve()
            ),
            "validation_status": (
                result["status"]
            ),
            "valid_candidate_count": 1,
            "candidate_selected": False,
            "human_review_required": True,
            "database_import_allowed": False,
            "wordpress_draft_creation_allowed": (
                False
            ),
            "approval_request_creation_allowed": (
                False
            ),
            "normal_x_fb_write_allowed": False,
            "production_execution": False,
            "production_status": "NO_GO",
        }
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "X-R11 MANUAL REAL-SOURCE DATA ENTRY: VALIDATED"
    )
    print(
        f"status={result['status']}"
    )
    print(
        f"input_csv={input_csv}"
    )
    print(
        f"input_sha256={input_sha256}"
    )
    print(
        f"validation_result={result_path}"
    )
    print()
    print(
        "database_import_allowed=false"
    )
    print(
        "wordpress_draft_creation_allowed=false"
    )
    print(
        "normal_x_fb_write_allowed=false"
    )
    print(
        "production_status=NO_GO"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
