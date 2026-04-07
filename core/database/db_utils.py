from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_FILE = DATA_DIR / "media.db"
KEYWORDS_FILE = DATA_DIR / "keywords.json"
INTENT_ANALYSIS_FILE = DATA_DIR / "intent_analysis.json"


def ensure_data_dir() -> Path:
    """dataディレクトリを作成して返す。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def get_db_path() -> Path:
    """media.db の絶対パスを返す。"""
    ensure_data_dir()
    return DB_FILE


def get_keywords_path() -> Path:
    """keywords.json の絶対パスを返す。"""
    ensure_data_dir()
    return KEYWORDS_FILE


def get_intent_analysis_path() -> Path:
    """intent_analysis.json の絶対パスを返す。"""
    ensure_data_dir()
    return INTENT_ANALYSIS_FILE


def connect_db() -> sqlite3.Connection:
    """SQLite接続を返す（row_factory付き）。"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
