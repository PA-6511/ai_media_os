from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
EXCHANGE_DIR = BASE_DIR / "exchange"
DECISION_PACKAGE_DIR = EXCHANGE_DIR / "decision_packages"
APPROVAL_DIR = EXCHANGE_DIR / "approvals"
CONNECTION_DIR = EXCHANGE_DIR / "connections"


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"[CORE] invalid json -> skip: {path.name}")
        return {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_target_key(record: dict[str, Any], fallback: str) -> str:
    for key in ("target", "connection_target", "scope", "agent", "component"):
        value = str(record.get(key, "")).strip()
        if value:
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("target", "connection_target", "scope", "agent", "component"):
            value = str(metadata.get(key, "")).strip()
            if value:
                return value
    return fallback


def _has_approval_file(package_id: str) -> bool:
    if not package_id:
        return False
    return (APPROVAL_DIR / f"{package_id}.approved").exists()


def _is_phase12_approved(pkg: dict[str, Any]) -> bool:
    if not isinstance(pkg, dict):
        return False

    package_id = str(pkg.get("package_id", "")).strip()

    # 互換: 既存運用は approvals/*.approved の存在で承認判定していた。
    if _has_approval_file(package_id):
        return True

    if pkg.get("phase12_approved") is True:
        return True

    phase = str(pkg.get("phase", "")).strip().upper()
    if phase == "PHASE12" and pkg.get("approved") is True:
        return True

    decision = pkg.get("decision")
    if isinstance(decision, dict):
        decision_phase = str(decision.get("phase", "")).strip().upper()
        if decision_phase == "PHASE12" and decision.get("approved") is True:
            return True

    phase12 = pkg.get("phase12")
    if isinstance(phase12, dict) and phase12.get("approved") is True:
        return True

    return False


def limited_connect(
    decision_package: dict[str, Any],
    *,
    package_path: Path,
    ttl_hours: int = 24,
) -> dict[str, Any]:
    package_id = str(decision_package.get("package_id", package_path.stem)).strip() or package_path.stem
    target = _extract_target_key(decision_package, fallback=package_id)
    now = datetime.utcnow().replace(microsecond=0)
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat() + "Z"

    connection_record = {
        "package_id": package_id,
        "source_file": package_path.name,
        "status": "ACTIVE",
        "connected_at": now.isoformat() + "Z",
        "expires_at": expires_at,
        "target": target,
        "scope": ["read:decision_packages"],
        "phase": "PHASE12",
    }

    connection_path = CONNECTION_DIR / f"{package_id}.connected.json"
    _save_json(connection_path, connection_record)
    print(f"[CORE] connected -> {connection_path.name} (expires_at={expires_at})")
    return connection_record


def is_expired(record: dict[str, Any]) -> bool:
    expires_at_text = str(record.get("expires_at", "")).strip()
    if not expires_at_text:
        return False

    normalized = expires_at_text.replace("Z", "+00:00")
    try:
        expires_at = datetime.fromisoformat(normalized)
    except ValueError:
        print("[CORE] invalid expires_at -> treat as not expired")
        return False

    now_utc = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
    return now_utc >= expires_at


def main() -> int:
    DECISION_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    CONNECTION_DIR.mkdir(parents=True, exist_ok=True)

    # ③ 既存接続の期限チェック（EXPIRED化）
    active_connections: dict[str, dict[str, Any]] = {}
    for path in sorted(CONNECTION_DIR.glob("*.connected.json")):
        record = _load_json(path)
        if not record:
            continue

        status = str(record.get("status", "")).strip().upper()
        if not status and str(record.get("mode", "")).strip().upper() == "LIMITED_CONNECT":
            status = "ACTIVE"
        if status != "ACTIVE":
            continue

        if is_expired(record):
            record["status"] = "EXPIRED"
            record["expired_at"] = _utc_now_iso()
            _save_json(path, record)
            print(f"[CORE] expired connection -> {path.name}")
            continue

        # 既存レコード互換: scope がない ACTIVE は最小権限を補完する。
        scope = record.get("scope")
        if not isinstance(scope, list) or not scope:
            record["scope"] = ["read:decision_packages"]
            _save_json(path, record)

        legacy_fallback = str(record.get("package_id", "")).strip() or path.stem
        target_key = _extract_target_key(record, fallback=legacy_fallback)
        active_connections[target_key] = record

    for package_path in sorted(DECISION_PACKAGE_DIR.glob("*.json")):
        decision_package = _load_json(package_path)
        if not decision_package:
            continue

        if not _is_phase12_approved(decision_package):
            print(f"[CORE] not approved by Phase12 -> skip: {package_path.name}")
            continue

        target_key = _extract_target_key(decision_package, fallback=package_path.stem)

        # ④ ACTIVE 接続があれば再接続防止
        if target_key in active_connections:
            print("[CORE] connection already active -> skip")
            continue

        record = limited_connect(decision_package, package_path=package_path)
        active_connections[target_key] = record

    return 0


if __name__ == "__main__":
    raise SystemExit(main())