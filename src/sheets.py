"""src/sheets.py

Google Sheets 投稿キュー操作モジュール。

必須環境変数:
    SPREADSHEET_ID               Google Spreadsheet の ID
    GOOGLE_SERVICE_ACCOUNT_JSON  サービスアカウント JSON（raw JSON / base64 / ファイルパス）

環境変数が未設定の場合は ImportError または ValueError を送出するため、
呼び出し側で適切に except して fallback 処理を行うこと。

主な列名 (ワークシートヘッダーで定義):
    row_id, article_type, status, sale_end_date, error_message, updated_at
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- 定数 ---
SPREADSHEET_ID_ENV = "SPREADSHEET_ID"
SERVICE_ACCOUNT_ENV = "GOOGLE_SERVICE_ACCOUNT_JSON"
WORKSHEET_NAME_ENV = "POST_QUEUE_WORKSHEET"
DEFAULT_WORKSHEET_NAME = "投稿キュー"
ERROR_LOG_WORKSHEET_NAME = "エラーログ"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# シート列名（ワークシートのヘッダー行で定義される）
COL_STATUS = "status"
COL_ERROR_LOG = "error_log"
COL_ERROR_MESSAGE = "error_message"
COL_UPDATED_AT = "updated_at"
ROW_INDEX_KEY = "_row_index"  # fetch_all_rows が付与する内部キー


# --- 認証 ---

def _parse_service_account_json(value: str) -> dict[str, Any]:
    """GOOGLE_SERVICE_ACCOUNT_JSON 環境変数の値を dict に変換する。

    以下の3形式に対応:
      1. ファイルパス
      2. base64 エンコードされた JSON 文字列
      3. JSON 文字列そのまま
    """
    # 1. ファイルパス
    p = Path(value)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))

    # パス形式なのにファイルが無い場合は、JSON decode エラーではなく明示的に知らせる。
    if p.suffix.lower() == ".json" or "/" in value:
        raise ValueError(
            "service_account.json が存在しません。"
            f" パスを確認してください: {value}"
        )

    # 2. base64 decode を試みる
    try:
        # パディングを補って decode
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        return json.loads(decoded)
    except Exception:  # noqa: BLE001
        pass

    # 3. JSON 文字列そのまま
    return json.loads(value)


def _get_credentials():
    """google.oauth2 の Credentials オブジェクトを返す。"""
    try:
        from google.oauth2.service_account import Credentials  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "google-auth が未インストールです。"
            " pip install gspread google-auth を実行してください。"
        ) from exc

    sa_json_raw = os.getenv(SERVICE_ACCOUNT_ENV, "").strip()
    if not sa_json_raw:
        raise ValueError(
            f"環境変数 {SERVICE_ACCOUNT_ENV} が未設定です。"
            " .env に設定してから再実行してください。"
        )
    try:
        sa_info = _parse_service_account_json(sa_json_raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"環境変数 {SERVICE_ACCOUNT_ENV} の値を JSON として解釈できません。"
            " raw JSON / base64 JSON / ファイルパス のいずれかで設定してください。"
        ) from exc
    return Credentials.from_service_account_info(sa_info, scopes=SCOPES)


def _get_gspread_client():
    """認証済みの gspread クライアントを返す。"""
    try:
        import gspread  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "gspread が未インストールです。"
            " pip install gspread google-auth を実行してください。"
        ) from exc

    creds = _get_credentials()
    return gspread.authorize(creds)


# --- 公開 API ---

def get_spreadsheet():
    """認証済みの Spreadsheet オブジェクトを返す。"""
    spreadsheet_id = os.getenv(SPREADSHEET_ID_ENV, "").strip()
    if not spreadsheet_id:
        raise ValueError(
            f"環境変数 {SPREADSHEET_ID_ENV} が未設定です。"
            " .env に設定してから再実行してください。"
        )

    client = _get_gspread_client()
    return client.open_by_key(spreadsheet_id)

def get_sheet(worksheet_name: str | None = None):
    """投稿キューワークシートを返す。

    Returns:
        gspread.Worksheet

    Raises:
        ImportError: gspread / google-auth 未インストール
        ValueError: 環境変数未設定
        gspread.SpreadsheetNotFound: SPREADSHEET_ID 不正
    """
    name = worksheet_name or os.getenv(WORKSHEET_NAME_ENV, DEFAULT_WORKSHEET_NAME)
    spreadsheet = get_spreadsheet()
    return spreadsheet.worksheet(name)


def fetch_all_rows(sheet) -> list[dict[str, Any]]:
    """ワークシートの全行を dict のリストとして返す。

    各 dict にはヘッダー列をキーとした値と、
    1始まりの行インデックス ``_row_index`` が付与される。

    Returns:
        [{"work_id": "manga_0001", "status": "PUBLISHED", ..., "_row_index": 2}, ...]
    """
    records: list[dict[str, Any]] = sheet.get_all_records(default_blank="")
    for i, row in enumerate(records, start=2):  # ヘッダー行=1 なので data は 2 始まり
        row[ROW_INDEX_KEY] = i
    return records


def _find_col_index(sheet, col_name: str) -> int:
    """ヘッダー行から列インデックス（1始まり）を返す。"""
    headers: list[str] = sheet.row_values(1)
    try:
        return headers.index(col_name) + 1
    except ValueError as exc:
        raise ValueError(
            f"シートにカラム '{col_name}' が見つかりません。"
            f" ヘッダー: {headers}"
        ) from exc


def update_status(sheet, row_index: int, new_status: str) -> None:
    """指定行の status カラムを更新する。

    Args:
        sheet:      gspread.Worksheet
        row_index:  1始まりの行番号（_row_index の値）
        new_status: 新しいステータス文字列
    """
    col = _find_col_index(sheet, COL_STATUS)
    sheet.update_cell(row_index, col, new_status)

    # updated_at が存在すれば同時更新
    try:
        at_col = _find_col_index(sheet, COL_UPDATED_AT)
        sheet.update_cell(row_index, at_col, datetime.now(timezone.utc).isoformat())
    except ValueError:
        pass  # updated_at カラムなければスキップ


def update_row_fields(sheet, row_index: int, updates: dict[str, Any]) -> None:
    """指定行の複数カラムを更新する。存在しないカラムは無視しない。"""
    for key, value in updates.items():
        col = _find_col_index(sheet, key)
        sheet.update_cell(row_index, col, value)


def append_error_log(sheet, row_index: int, error_msg: str) -> None:
    """指定行の error_log カラムにエラーメッセージを追記する。

    既存の値があれば改行で連結する。

    Args:
        sheet:      gspread.Worksheet
        row_index:  1始まりの行番号
        error_msg:  追記するエラーメッセージ
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"[{timestamp}] {error_msg}"

    # 1. 旧来の error_log 列があればそこへ追記
    try:
        col = _find_col_index(sheet, COL_ERROR_LOG)
        current = sheet.cell(row_index, col).value or ""
        new_value = f"{current}\n{entry}".strip()
        sheet.update_cell(row_index, col, new_value)
        return
    except ValueError:
        pass

    # 2. error_message 列があればそこへ追記
    try:
        col = _find_col_index(sheet, COL_ERROR_MESSAGE)
        current = sheet.cell(row_index, col).value or ""
        new_value = f"{current}\n{entry}".strip()
        sheet.update_cell(row_index, col, new_value)
    except ValueError:
        pass

    # 3. エラーログシートがあれば append する
    try:
        spreadsheet = sheet.spreadsheet
        log_sheet = spreadsheet.worksheet(ERROR_LOG_WORKSHEET_NAME)
        row_id = ""
        try:
            row_id_col = _find_col_index(sheet, "row_id")
            row_id = sheet.cell(row_index, row_id_col).value or ""
        except ValueError:
            pass
        log_sheet.append_row([timestamp, "ERROR", "append_error_log", row_id, error_msg])
    except Exception:
        pass
