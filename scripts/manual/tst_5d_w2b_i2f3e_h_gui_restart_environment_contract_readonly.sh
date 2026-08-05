#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-H"
REPO_ROOT="/home/deploy/ai_media_os"

BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"

G_R1_REL="${BASE_REL}/i2f3e-g-r1-gui-stop-restart-route-resolution-readonly-20260725T143015Z-510846"
G_R1_ROOT="${REPO_ROOT}/${G_R1_REL}"

EXPECTED_G_R1_RESULT_SHA="31691e1bec7352e29f422ff3ea460b7e2451c977b730e28ec7dde611a1c47736"
EXPECTED_G_R1_PACKET_MANIFEST_SHA="4ca71f34df8ca6c8eced060eacaeb0d28d6b672a373550c886ac0439e0652b92"
EXPECTED_G_R1_SEMANTIC_SHA="d07d3d540ec2b6086236520b1a17e422ef6fe2b1b946e46b7388029ccdf9cda8"
EXPECTED_G_R1_EVIDENCE_MANIFEST_SHA="1a0c5216932643e08b80d6271be90275c77f2686e910fc2b829e623645ed7002"
EXPECTED_PROCESS_IDENTITY_SHA="3dcadb53adeadac94cb1062d2a4e24c2a00d63a51c87991046b96cd7f0f6ba2a"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

TARGET_SCRIPT="${REPO_ROOT}/scripts/new_release_multistore_app.py"
TARGET_HOST="127.0.0.1"
TARGET_PORT="8765"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_REL="${BASE_REL}/i2f3e-h-gui-restart-environment-contract-readonly-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"
PACKET_ROOT="${EVIDENCE_ROOT}/packet-snapshot"
INPUT_ROOT="${EVIDENCE_ROOT}/input-snapshots"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "RUN_AS_ROOT_FORBIDDEN=true" >&2
  exit 1
fi

mkdir "$EVIDENCE_ROOT"
mkdir "$PACKET_ROOT"
mkdir "$INPUT_ROOT"

on_error() {
  local rc=$?
  set +e
  if [[ -d "$EVIDENCE_ROOT" && -w "$EVIDENCE_ROOT" ]]; then
    {
      printf 'FAILURE_PHASE=%s\n' "$PHASE"
      printf 'FAILURE_EXIT_CODE=%s\n' "$rc"
      printf 'FAILURE_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
      printf 'ENVIRONMENT_SECRET_VALUES_SAVED=false\n'
      printf 'CREDENTIAL_FILE_CONTENT_READ=false\n'
      printf 'PROCESS_SIGNAL_SENT=false\n'
      printf 'WRITER_STOP_PERFORMED=false\n'
      printf 'GUI_STOPPED_OR_RESTARTED=false\n'
      printf 'PRODUCTION_DB_OPENED=false\n'
      printf 'SQL_EXECUTED=false\n'
      printf 'WRITER_FREEZE_EXECUTION=HOLD\n'
      printf 'PRODUCTION_RELEASE_DECISION=HOLD\n'
      printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
    } > "$EVIDENCE_ROOT/failure.txt" 2>/dev/null || true
  fi
  printf 'SCRIPT_EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap on_error ERR

cd "$REPO_ROOT"

test -f "$G_R1_ROOT/result.json"
test -f "$G_R1_ROOT/evidence-manifest.txt"
test -f "$G_R1_ROOT/packet-snapshot/packet-manifest.json"
test -f "$G_R1_ROOT/packet-snapshot/packet-semantic-validation.json"
test -f "$G_R1_ROOT/packet-snapshot/gui-stop-restart-route-resolution.json"
test -f "$G_R1_ROOT/packet-snapshot/process-identity-contract.json"
test -f "$G_R1_ROOT/packet-snapshot/exact-stop-contract.json"
test -f "$G_R1_ROOT/packet-snapshot/exact-restart-contract.json"
test -f "$G_R1_ROOT/packet-snapshot/environment-redaction-report.json"
test -f "$TARGET_SCRIPT"

echo "${EXPECTED_G_R1_RESULT_SHA}  ${G_R1_ROOT}/result.json" | sha256sum -c -
echo "${EXPECTED_G_R1_PACKET_MANIFEST_SHA}  ${G_R1_ROOT}/packet-snapshot/packet-manifest.json" | sha256sum -c -
echo "${EXPECTED_G_R1_SEMANTIC_SHA}  ${G_R1_ROOT}/packet-snapshot/packet-semantic-validation.json" | sha256sum -c -
echo "${EXPECTED_G_R1_EVIDENCE_MANIFEST_SHA}  ${G_R1_ROOT}/evidence-manifest.txt" | sha256sum -c -

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/result.json" \
  "$INPUT_ROOT/3e-g-r1-result.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/evidence-manifest.txt" \
  "$INPUT_ROOT/3e-g-r1-evidence-manifest.txt"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/process-identity-contract.json" \
  "$INPUT_ROOT/3e-g-r1-process-identity-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/exact-stop-contract.json" \
  "$INPUT_ROOT/3e-g-r1-exact-stop-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/exact-restart-contract.json" \
  "$INPUT_ROOT/3e-g-r1-exact-restart-contract.json"

cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "$G_R1_ROOT/packet-snapshot/environment-redaction-report.json" \
  "$INPUT_ROOT/3e-g-r1-environment-redaction-report.json"

cat > "$PACKET_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
G_R1_EXECUTION_EVIDENCE_REVIEW=APPROVE
3E_G_R1_GUI_STOP_RESTART_ROUTE_RESOLUTION=PASS_WITH_RESTART_CONDITION
EXACT_STOP_ROUTE_REVIEW=PASS_PENDING_EXECUTION_APPROVAL
APPROVE_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READONLY

許可範囲：
1. 3E-G-R1 Evidenceを読み取り専用入力として使用する。
2. environment-redaction-report.jsonに記録された秘密変数について、
   変数名と存在有無だけを使用し、値は読み取り、表示、保存しない。
3. scripts/new_release_multistore_app.pyおよび起動時にimportされる
   Repository内Pythonモジュールを静的解析し、os.environ、os.getenv、
   dotenv、設定ローダー、credential.env参照、DB設定参照を特定する。
4. 各環境変数名をSTARTUP_REQUIRED、RUNTIME_REQUIRED、EXTERNAL_ACTION_ONLY、
   OPTIONAL、INHERITED_NOT_USED、UNRESOLVEDへ分類する。
5. /etc/ai-media-os/credential.envその他候補ファイルはmetadataだけを確認し、内容と値は読み取らない。
6. 現行GUIプロセスのEnvironmentは、許可リストの非秘密値と秘密変数名の存在だけを再確認する。
7. Repository内のREADME、manual script、起動Evidence、shell wrapper、systemd unit候補を静的検索する。
8. shell historyを調査する場合は対象行を限定して秘密をマスキングする。
9. exact restart contractを実行せずに準備する。
10. Environment供給元が安全に再現できる場合のみEXACT_RESTART_STATUSをRESOLVED_PENDING_HUMAN_REVIEWとする。
11. 起動に不要な秘密変数を継承しないminimal environment contractを作成する。
12. 新しい一意なshadow/evidence領域へ保存する。

禁止事項：
Environment秘密値の表示・保存、credential.env内容読み取り、process signal送信、
GUI停止・再起動、writer停止、systemctl stop/start/restart、service作成・変更、
cron変更、timer変更、Production DB接続、SQL実行、backup、restore、migration、
manifest変更、source/test変更、git add、git commit、deployment、外部通信、
Slack Worker起動、production approval、production release承認は禁止する。

追加条件：
1. Environment変数の必要性がUNRESOLVEDの場合、exact restartは解決済みにしない。
2. 現行プロセスの秘密値を新Evidenceへ複製しない。
3. credential.envはmetadata確認だけとし、内容を開かない。
4. exact restart contractが解決しても実行しない。
5. 3E-H成功後の次ゲートは人間レビューとし、Writer freezeへ自動遷移しない。

WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

python3 - \
  "$REPO_ROOT" \
  "$G_R1_ROOT" \
  "$G_R1_REL" \
  "$EVIDENCE_ROOT" \
  "$EVIDENCE_REL" \
  "$PACKET_ROOT" \
  "$TARGET_SCRIPT" \
  "$TARGET_HOST" \
  "$TARGET_PORT" \
  "$EXPECTED_PROCESS_IDENTITY_SHA" \
  "$EXPECTED_DB_SHA" \
  "$EXPECTED_MANIFEST_SHA" \
  "$EXPECTED_WORKFLOW_SHA" \
  "$EXPECTED_MIGRATION_SHA" \
  "$EXPECTED_SLACK_RUNTIME_SHA" \
  "$EXPECTED_PROMOTED_TEST_SHA" <<'PY'
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import os
import pwd
import grp
import re
import shlex
import stat
import sys
from collections import deque
from pathlib import Path
from typing import Any

(
    repo_root_s,
    g_r1_root_s,
    g_r1_rel,
    evidence_root_s,
    evidence_rel,
    packet_root_s,
    target_script_s,
    target_host,
    target_port,
    expected_identity_sha,
    expected_db_sha,
    expected_manifest_sha,
    expected_workflow_sha,
    expected_migration_sha,
    expected_slack_runtime_sha,
    expected_promoted_test_sha,
) = sys.argv[1:]

repo_root = Path(repo_root_s).resolve()
g_r1_root = Path(g_r1_root_s).resolve()
evidence_root = Path(evidence_root_s).resolve()
packet_root = Path(packet_root_s).resolve()
target_script = Path(target_script_s).resolve()

phase = "TST-5D-W2B-I2F-3E-H"
now_utc = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", "exchange", "backups",
    "data", "node_modules", ".pytest_cache", ".mypy_cache",
}

SECRET_NAME_RE = re.compile(
    r"(TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE|API_KEY|ACCESS_KEY|"
    r"COOKIE|AUTHORIZATION|SESSION|BEARER|SIGNING|CLIENT_SECRET)",
    re.IGNORECASE,
)

EXTERNAL_NAME_RE = re.compile(
    r"(WP_|WORDPRESS|SLACK|AMAZON|RAKUTEN|DMM|CREATOR|AFFILIATE|"
    r"API_|ACCESS_TOKEN|WEBHOOK|OAUTH|PAAPI|EXTERNAL)",
    re.IGNORECASE,
)

EXTERNAL_FUNCTION_RE = re.compile(
    r"(publish|post|send|slack|wordpress|wp_|amazon|rakuten|dmm|"
    r"affiliate|api|network|external|upload|notify|webhook)",
    re.IGNORECASE,
)

ENV_FILE_NAME_RE = re.compile(
    r"(?:^|[/\\])(?:[^/\\\s\"']*\.env|credential\.env)$",
    re.IGNORECASE,
)

def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON_OBJECT_REQUIRED:{path}")
    return value

def resolve_existing(path: Path) -> Path:
    return path.resolve(strict=False)

def protected_sha_inventory() -> dict[str, Any]:
    items = [
        ("production_database", repo_root / "data/database/ebook_affiliate.db", expected_db_sha),
        ("production_manifest", repo_root / "config/slack_worker_release_source_manifest.json", expected_manifest_sha),
        ("workflow_source", repo_root / "app/db/repositories/workflow_state_repository.py", expected_workflow_sha),
        ("migration_source", repo_root / "migrations/versions/00241611109d_add_unique_wordpress_post_id.py", expected_migration_sha),
        ("slack_runtime_source", repo_root / "scripts/run_slack_approval_socket.py", expected_slack_runtime_sha),
        ("promoted_test", repo_root / "tests/test_slack_approval_socket_hold_remediation_offline.py", expected_promoted_test_sha),
    ]
    result = []
    for label, path, expected in items:
        require(path.is_file(), f"PROTECTED_FILE_MISSING:{path}")
        actual = sha256(path)
        require(actual == expected, f"PROTECTED_SHA_MISMATCH:{label}:{actual}")
        metadata = path.stat()
        result.append({
            "label": label,
            "path": str(path),
            "sha256": actual,
            "size_bytes": metadata.st_size,
            "inode": metadata.st_ino,
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        })
    return {
        "schema_version": "1.0",
        "phase": phase,
        "captured_at_utc": now_utc(),
        "files": result,
        "production_database_opened": False,
        "sql_executed": False,
    }

def proc_cmdline(pid: int) -> list[str]:
    raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()
    return [
        part.decode("utf-8", errors="replace")
        for part in raw.split(b"\0")
        if part
    ]

def matching_gui_pids() -> list[int]:
    matches = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            argv = proc_cmdline(pid)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if (
            str(target_script) in argv
            and "--host" in argv
            and target_host in argv
            and "--port" in argv
            and target_port in argv
        ):
            matches.append(pid)
    return sorted(matches)

def environment_names_only(pid: int) -> dict[str, Any]:
    raw = (Path("/proc") / str(pid) / "environ").read_bytes()
    names = []
    for entry in raw.split(b"\0"):
        if not entry or b"=" not in entry:
            continue
        name_b, _value_b = entry.split(b"=", 1)
        name = name_b.decode("utf-8", errors="replace")
        names.append(name)
    names = sorted(set(names))
    secret_names = sorted(name for name in names if SECRET_NAME_RE.search(name))
    non_secret_names = sorted(name for name in names if name not in secret_names)
    return {
        "all_variable_name_count": len(names),
        "secret_variable_names": secret_names,
        "secret_variable_name_count": len(secret_names),
        "non_secret_variable_names": non_secret_names,
        "raw_environment_saved": False,
        "environment_values_read_for_output": False,
        "environment_values_saved": False,
        "secret_values_saved": False,
    }

def module_name_for_path(path: Path) -> str:
    relative = path.relative_to(repo_root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

def build_module_index() -> tuple[dict[str, Path], dict[Path, str]]:
    by_module: dict[str, Path] = {}
    by_path: dict[Path, str] = {}
    for path in repo_root.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.relative_to(repo_root).parts):
            continue
        if not path.is_file():
            continue
        module = module_name_for_path(path)
        by_module[module] = path
        by_path[path.resolve()] = module
    return by_module, by_path

def resolve_import(
    current_module: str,
    node: ast.Import | ast.ImportFrom,
    module_index: dict[str, Path],
) -> list[Path]:
    candidates: list[str] = []

    if isinstance(node, ast.Import):
        candidates.extend(alias.name for alias in node.names)
    else:
        level = node.level
        base = node.module or ""
        current_parts = current_module.split(".")
        if level:
            package_parts = current_parts[:-1]
            keep = max(0, len(package_parts) - (level - 1))
            prefix = package_parts[:keep]
            absolute_base = ".".join([*prefix, base] if base else prefix)
        else:
            absolute_base = base

        if absolute_base:
            candidates.append(absolute_base)
        for alias in node.names:
            if alias.name == "*":
                continue
            if absolute_base:
                candidates.append(f"{absolute_base}.{alias.name}")
            else:
                candidates.append(alias.name)

    paths: list[Path] = []
    for candidate in candidates:
        candidate_parts = candidate.split(".")
        while candidate_parts:
            name = ".".join(candidate_parts)
            path = module_index.get(name)
            if path is not None:
                paths.append(path.resolve())
                break
            candidate_parts.pop()
    return paths

def iter_function_contexts(tree: ast.AST) -> dict[ast.AST, str | None]:
    contexts: dict[ast.AST, str | None] = {}
    stack: list[str] = []

    class Visitor(ast.NodeVisitor):
        def generic_visit(self, node: ast.AST) -> None:
            contexts[node] = ".".join(stack) if stack else None
            super().generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            contexts[node] = ".".join(stack) if stack else None
            stack.append(node.name)
            for child in ast.iter_child_nodes(node):
                self.visit(child)
            stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_FunctionDef(node)  # type: ignore[arg-type]

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            contexts[node] = ".".join(stack) if stack else None
            stack.append(node.name)
            for child in ast.iter_child_nodes(node):
                self.visit(child)
            stack.pop()

    Visitor().visit(tree)
    return contexts

def constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

def env_access_from_node(node: ast.AST) -> tuple[str | None, str, bool] | None:
    # os.environ["NAME"]
    if isinstance(node, ast.Subscript):
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
            and value.attr == "environ"
        ):
            key = constant_string(node.slice)
            return key, "os.environ_subscript", False

    # os.environ.get("NAME", default), os.getenv("NAME", default)
    if isinstance(node, ast.Call):
        func = node.func
        key = constant_string(node.args[0]) if node.args else None
        has_default = len(node.args) >= 2 or any(
            keyword.arg == "default" for keyword in node.keywords
        )

        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Attribute)
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "os"
            and func.value.attr == "environ"
            and func.attr == "get"
        ):
            return key, "os.environ_get", has_default

        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
            and func.attr == "getenv"
        ):
            return key, "os.getenv", has_default

        if isinstance(func, ast.Name) and func.id == "getenv":
            return key, "getenv_imported", has_default

    return None

def source_static_analysis() -> dict[str, Any]:
    module_index, path_to_module = build_module_index()
    queue: deque[Path] = deque([target_script])
    visited: set[Path] = set()

    file_reports: list[dict[str, Any]] = []
    all_env_usages: list[dict[str, Any]] = []
    all_env_file_refs: set[str] = set()
    loader_patterns: list[dict[str, Any]] = []
    db_references: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []

    while queue:
        path = queue.popleft().resolve()
        if path in visited:
            continue
        visited.add(path)

        if repo_root not in path.parents and path != repo_root:
            continue
        if not path.is_file():
            continue
        if any(part in EXCLUDED_PARTS for part in path.relative_to(repo_root).parts):
            continue

        module = path_to_module.get(path, module_name_for_path(path))
        text = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            parse_errors.append({
                "path": str(path.relative_to(repo_root)),
                "error": str(exc),
            })
            continue

        contexts = iter_function_contexts(tree)
        imported_local_paths: set[Path] = set()
        env_usages: list[dict[str, Any]] = []
        local_loader_patterns: list[dict[str, Any]] = []
        local_db_refs: list[dict[str, Any]] = []
        local_env_file_refs: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for imported_path in resolve_import(module, node, module_index):
                    imported_local_paths.add(imported_path)

            access = env_access_from_node(node)
            if access is not None:
                name, access_type, has_default = access
                usage = {
                    "variable_name": name,
                    "dynamic_name": name is None,
                    "access_type": access_type,
                    "has_default": has_default,
                    "path": str(path.relative_to(repo_root)),
                    "line_number": getattr(node, "lineno", None),
                    "function_context": contexts.get(node),
                    "module_scope": contexts.get(node) is None,
                }
                env_usages.append(usage)
                all_env_usages.append(usage)

            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in {
                    "load_dotenv", "dotenv_values", "find_dotenv",
                    "config", "read_dotenv", "load_env",
                }:
                    item = {
                        "path": str(path.relative_to(repo_root)),
                        "line_number": getattr(node, "lineno", None),
                        "function_name": func_name,
                        "function_context": contexts.get(node),
                    }
                    local_loader_patterns.append(item)
                    loader_patterns.append(item)

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value

                if (
                    value.endswith(".env")
                    or "credential.env" in value
                    or ENV_FILE_NAME_RE.search(value)
                ):
                    local_env_file_refs.add(value)
                    all_env_file_refs.add(value)

                lower = value.lower()
                if (
                    "ebook_affiliate.db" in lower
                    or "sqlite:///" in lower
                    or "database/" in lower
                    or "db_path" in lower
                ):
                    item = {
                        "path": str(path.relative_to(repo_root)),
                        "line_number": getattr(node, "lineno", None),
                        "string_reference": value[:500],
                    }
                    local_db_refs.append(item)
                    db_references.append(item)

            if isinstance(node, ast.Name) and node.id in {
                "BaseSettings", "SettingsConfigDict", "Config",
            }:
                item = {
                    "path": str(path.relative_to(repo_root)),
                    "line_number": getattr(node, "lineno", None),
                    "symbol": node.id,
                    "function_context": contexts.get(node),
                }
                local_loader_patterns.append(item)
                loader_patterns.append(item)

        for imported_path in sorted(imported_local_paths):
            if imported_path not in visited:
                queue.append(imported_path)

        file_reports.append({
            "path": str(path.relative_to(repo_root)),
            "module": module,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "imported_local_modules": sorted(
                str(item.relative_to(repo_root))
                for item in imported_local_paths
            ),
            "environment_usages": env_usages,
            "environment_file_references": sorted(local_env_file_refs),
            "loader_patterns": local_loader_patterns,
            "database_references": local_db_refs,
        })

    file_reports.sort(key=lambda item: item["path"])
    all_env_usages.sort(
        key=lambda item: (
            item["path"],
            item["line_number"] or 0,
            item["variable_name"] or "",
        )
    )

    return {
        "schema_version": "1.0",
        "phase": phase,
        "entry_script": str(target_script.relative_to(repo_root)),
        "visited_python_file_count": len(file_reports),
        "visited_python_files": file_reports,
        "environment_usages": all_env_usages,
        "environment_file_references": sorted(all_env_file_refs),
        "loader_patterns": loader_patterns,
        "database_references": db_references,
        "parse_errors": parse_errors,
        "source_modified": False,
        "imports_executed": False,
        "analysis_method": "PYTHON_AST_STATIC_ONLY",
    }

def classify_usage(
    name: str,
    usages: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if not usages:
        return "INHERITED_NOT_USED", [
            "Variable name is present in the live process or prior redaction report "
            "but is not statically referenced in the imported repository module closure."
        ]

    if any(usage["dynamic_name"] for usage in usages):
        return "UNRESOLVED", ["Dynamic environment variable name usage detected."]

    external_context_only = all(
        EXTERNAL_FUNCTION_RE.search(usage["function_context"] or "")
        or EXTERNAL_NAME_RE.search(name)
        for usage in usages
    )

    if external_context_only:
        reasons.append(
            "All static references are associated with external-action function/name heuristics."
        )
        return "EXTERNAL_ACTION_ONLY", reasons

    if all(usage["access_type"] != "os.environ_subscript" for usage in usages):
        reasons.append("All accesses are getenv/get calls rather than required subscripts.")
        if all(usage["has_default"] for usage in usages):
            reasons.append("Every access provides a default value.")
        return "OPTIONAL", reasons

    if any(
        usage["access_type"] == "os.environ_subscript"
        and usage["module_scope"]
        for usage in usages
    ):
        reasons.append("Required os.environ subscript is evaluated at module scope.")
        return "STARTUP_REQUIRED", reasons

    if any(usage["access_type"] == "os.environ_subscript" for usage in usages):
        reasons.append("Required os.environ subscript is evaluated during runtime.")
        return "RUNTIME_REQUIRED", reasons

    return "UNRESOLVED", ["Static usage exists but classification rules did not resolve it."]

def metadata_only(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {
            "path": str(path),
            "exists": False,
            "content_read": False,
        }
    except PermissionError:
        return {
            "path": str(path),
            "exists": "UNKNOWN_PERMISSION_DENIED",
            "content_read": False,
        }

    is_symlink = stat.S_ISLNK(metadata.st_mode)
    return {
        "path": str(path),
        "exists": True,
        "is_regular_file": stat.S_ISREG(metadata.st_mode),
        "is_directory": stat.S_ISDIR(metadata.st_mode),
        "is_symlink": is_symlink,
        "symlink_target": os.readlink(path) if is_symlink else None,
        "owner": pwd.getpwuid(metadata.st_uid).pw_name
        if metadata.st_uid in {entry.pw_uid for entry in pwd.getpwall()}
        else str(metadata.st_uid),
        "group": grp.getgrgid(metadata.st_gid).gr_name
        if metadata.st_gid in {entry.gr_gid for entry in grp.getgrall()}
        else str(metadata.st_gid),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "size_bytes": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "content_read": False,
    }

def candidate_environment_paths(
    static_analysis: dict[str, Any],
) -> list[Path]:
    candidates: set[Path] = {
        Path("/etc/ai-media-os/credential.env"),
        repo_root / ".env",
        repo_root / ".env.production",
        repo_root / "config/credential.env",
        repo_root / "config/.env",
    }

    for reference in static_analysis["environment_file_references"]:
        reference_path = Path(reference)
        if reference_path.is_absolute():
            candidates.add(reference_path)
        else:
            candidates.add(repo_root / reference_path)

    return sorted(candidates, key=lambda item: str(item))

def repository_launch_search() -> dict[str, Any]:
    allowed_suffixes = {
        ".py", ".sh", ".md", ".txt", ".json", ".yaml", ".yml",
        ".service", ".timer", ".ini", ".toml", ".conf",
    }
    patterns = [
        re.compile(r"new_release_multistore_app\.py"),
        re.compile(r"\b8765\b"),
        re.compile(r"\bcredential\.env\b"),
        re.compile(r"\bEnvironmentFile\b"),
        re.compile(r"\bnohup\b"),
        re.compile(r"\benv\s+-i\b"),
    ]

    secret_assignment_re = re.compile(
        r"(?i)(token|password|passwd|secret|credential|private[_-]?key|"
        r"api[_-]?key|access[_-]?key|cookie|authorization|bearer)"
        r"(\s*[:=]\s*)([^\s]+)"
    )
    url_credential_re = re.compile(
        r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@"
    )
    shell_assignment_re = re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)"
    )

    def redact(line: str) -> str:
        line = secret_assignment_re.sub(
            lambda match: f"{match.group(1)}{match.group(2)}<REDACTED>",
            line,
        )
        line = url_credential_re.sub(
            lambda match: f"{match.group(1)}<REDACTED>:<REDACTED>@",
            line,
        )

        def redact_assignment(match: re.Match[str]) -> str:
            name = match.group(1)
            if SECRET_NAME_RE.search(name):
                return f"{name}=<REDACTED>"
            return match.group(0)

        line = shell_assignment_re.sub(redact_assignment, line)
        return line[:3000]

    matches: list[dict[str, Any]] = []
    files_scanned = 0
    truncated = False

    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() not in allowed_suffixes and path.name not in {
            "README", "Makefile",
        }:
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        files_scanned += 1
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not any(pattern.search(line) for pattern in patterns):
                continue
            matches.append({
                "path": str(relative),
                "line_number": line_number,
                "line": redact(line.strip()),
            })
            if len(matches) >= 400:
                truncated = True
                break
        if truncated:
            break

    return {
        "schema_version": "1.0",
        "phase": phase,
        "files_scanned": files_scanned,
        "match_count": len(matches),
        "truncated": truncated,
        "matches": matches,
        "shell_history_inspected": False,
        "history_secret_values_saved": False,
        "source_modified": False,
    }

g_result = read_json(g_r1_root / "result.json")
g_identity = read_json(g_r1_root / "packet-snapshot/process-identity-contract.json")
g_stop = read_json(g_r1_root / "packet-snapshot/exact-stop-contract.json")
g_restart = read_json(g_r1_root / "packet-snapshot/exact-restart-contract.json")
g_redaction = read_json(g_r1_root / "packet-snapshot/environment-redaction-report.json")

require(
    g_result.get("result")
    == "PASS_W2B_I2F3E_G_R1_GUI_STOP_RESTART_ROUTE_RESOLUTION_READY",
    "G_R1_RESULT_INVALID",
)
require(g_result.get("process_state") == "RUNNING_SINGLE_MATCH", "G_R1_PROCESS_STATE_INVALID")
require(g_result.get("matching_process_count") == 1, "G_R1_MATCH_COUNT_INVALID")
require(
    g_result.get("process_identity_sha256") == expected_identity_sha,
    "G_R1_IDENTITY_SHA_INVALID",
)
require(g_stop.get("method") == "SIGTERM_TO_EXACT_PID", "G_R1_STOP_METHOD_INVALID")
require(
    g_stop.get("status") == "RESOLVED_PENDING_HUMAN_REVIEW",
    "G_R1_STOP_STATUS_INVALID",
)
require(
    g_restart.get("status")
    == "UNRESOLVED_MISSING_REPRODUCIBLE_RUNTIME_COMPONENTS",
    "G_R1_RESTART_STATUS_INVALID",
)
require(g_restart.get("execution_allowed") is False, "G_R1_RESTART_EXECUTION_INVALID")
require(g_redaction.get("secret_values_saved") is False, "G_R1_SECRET_VALUE_FLAG_INVALID")
require(g_redaction.get("raw_environment_saved") is False, "G_R1_RAW_ENV_FLAG_INVALID")

protected_before = protected_sha_inventory()
write_json(packet_root / "protected-sha-before.json", protected_before)

pids = matching_gui_pids()
require(len(pids) == 1, f"GUI_PROCESS_SINGLE_MATCH_REQUIRED:{pids}")
current_pid = pids[0]
require(current_pid == g_result.get("current_pid"), f"GUI_PID_CHANGED:{current_pid}")

current_environment = environment_names_only(current_pid)
prior_secret_names = sorted(set(g_redaction.get("redacted_secret_variable_names", [])))
require(
    set(prior_secret_names).issubset(set(current_environment["secret_variable_names"])),
    "PRIOR_SECRET_VARIABLE_NAME_SET_NOT_PRESENT_IN_CURRENT_PROCESS",
)

static_analysis = source_static_analysis()
write_json(packet_root / "import-closure-static-analysis.json", static_analysis)

all_variable_names = sorted(set(
    prior_secret_names
    + current_environment["secret_variable_names"]
    + [
        usage["variable_name"]
        for usage in static_analysis["environment_usages"]
        if usage["variable_name"] is not None
    ]
))

usages_by_name: dict[str, list[dict[str, Any]]] = {
    name: [] for name in all_variable_names
}
dynamic_usages = []

for usage in static_analysis["environment_usages"]:
    name = usage["variable_name"]
    if name is None:
        dynamic_usages.append(usage)
    else:
        usages_by_name.setdefault(name, []).append(usage)

classifications = []
for name in sorted(usages_by_name):
    classification, reasons = classify_usage(name, usages_by_name[name])
    classifications.append({
        "variable_name": name,
        "secret_name_pattern": bool(SECRET_NAME_RE.search(name)),
        "present_in_current_process": name in current_environment["secret_variable_names"]
        or name in current_environment["non_secret_variable_names"],
        "present_in_prior_redaction_report": name in prior_secret_names,
        "classification": classification,
        "reasons": reasons,
        "static_usages": usages_by_name[name],
        "value_read_for_output": False,
        "value_saved": False,
    })

if dynamic_usages:
    classifications.append({
        "variable_name": "<DYNAMIC_NAME>",
        "secret_name_pattern": False,
        "present_in_current_process": None,
        "present_in_prior_redaction_report": False,
        "classification": "UNRESOLVED",
        "reasons": ["One or more environment accesses use a dynamic variable name."],
        "static_usages": dynamic_usages,
        "value_read_for_output": False,
        "value_saved": False,
    })

classification_counts = {
    category: sum(
        1 for item in classifications if item["classification"] == category
    )
    for category in [
        "STARTUP_REQUIRED",
        "RUNTIME_REQUIRED",
        "EXTERNAL_ACTION_ONLY",
        "OPTIONAL",
        "INHERITED_NOT_USED",
        "UNRESOLVED",
    ]
}

write_json(
    packet_root / "environment-variable-classification.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "current_pid": current_pid,
        "prior_secret_variable_names": prior_secret_names,
        "current_environment_name_inventory": current_environment,
        "classifications": classifications,
        "classification_counts": classification_counts,
        "dynamic_environment_usage_count": len(dynamic_usages),
        "environment_values_read_for_output": False,
        "environment_values_saved": False,
        "secret_values_saved": False,
    },
)

candidate_paths = candidate_environment_paths(static_analysis)
metadata_inventory = [metadata_only(path) for path in candidate_paths]

write_json(
    packet_root / "environment-source-file-metadata.json",
    {
        "schema_version": "1.0",
        "phase": phase,
        "candidate_count": len(metadata_inventory),
        "candidates": metadata_inventory,
        "credential_file_content_read": False,
        "environment_file_content_read": False,
        "metadata_only": True,
    },
)

launch_search = repository_launch_search()
write_json(packet_root / "repository-environment-launch-search.json", launch_search)

blocking_classifications = [
    item for item in classifications
    if item["classification"] in {
        "STARTUP_REQUIRED", "RUNTIME_REQUIRED", "UNRESOLVED",
    }
]

loader_blockers = static_analysis["loader_patterns"]
parse_blockers = static_analysis["parse_errors"]

minimal_environment = {
    "HOME": "/home/deploy",
    "USER": "deploy",
    "LOGNAME": "deploy",
    "PATH": (
        "/home/deploy/ai_media_os/.venv/bin:"
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ),
    "VIRTUAL_ENV": "/home/deploy/ai_media_os/.venv",
    "PWD": "/home/deploy/ai_media_os",
    "PYTHONUNBUFFERED": "1",
}

explicit_environment_source = {
    "type": "STATIC_MINIMAL_ENVIRONMENT_CONTRACT_NO_CREDENTIAL_FILE",
    "contract": minimal_environment,
    "credential_file_loaded": False,
    "credential_file_content_read": False,
    "inherits_parent_environment": False,
    "secret_variables_inherited": [],
    "external_action_secret_variables_omitted": sorted(
        item["variable_name"]
        for item in classifications
        if item["classification"] == "EXTERNAL_ACTION_ONLY"
        and item["variable_name"] != "<DYNAMIC_NAME>"
    ),
    "inherited_unused_secret_variables_omitted": sorted(
        item["variable_name"]
        for item in classifications
        if item["classification"] == "INHERITED_NOT_USED"
        and item["secret_name_pattern"]
    ),
}

environment_contract_resolved = (
    not blocking_classifications
    and not loader_blockers
    and not parse_blockers
)

exact_restart_status = (
    "RESOLVED_PENDING_HUMAN_REVIEW"
    if environment_contract_resolved
    else "UNRESOLVED_ENVIRONMENT_CONTRACT_BLOCKERS"
)

restart_argv = [
    "/home/deploy/ai_media_os/.venv/bin/python",
    "/home/deploy/ai_media_os/scripts/new_release_multistore_app.py",
    "--repo-root",
    "/home/deploy/ai_media_os",
    "--host",
    "127.0.0.1",
    "--port",
    "8765",
]

environment_assignments = " ".join(
    f"{name}={shlex.quote(value)}"
    for name, value in minimal_environment.items()
)

planned_restart_shell = (
    "cd /home/deploy/ai_media_os && "
    "umask 027 && "
    f"nohup env -i {environment_assignments} "
    + shlex.join(restart_argv)
    + " </dev/null >>/home/deploy/ai_media_os/logs/new_release_gui.log "
      "2>&1 & new_pid=$!; "
      "printf 'NEW_GUI_PID=%s\\n' \"$new_pid\""
)

restart_contract = {
    "schema_version": "1.0",
    "phase": phase,
    "status": exact_restart_status,
    "execution_allowed": False,
    "working_directory": "/home/deploy/ai_media_os",
    "python_executable": "/home/deploy/ai_media_os/.venv/bin/python",
    "script_path": "/home/deploy/ai_media_os/scripts/new_release_multistore_app.py",
    "arguments": [
        "--repo-root", "/home/deploy/ai_media_os",
        "--host", "127.0.0.1",
        "--port", "8765",
    ],
    "environment_source": explicit_environment_source,
    "stdin": "/dev/null",
    "stdout": "/home/deploy/ai_media_os/logs/new_release_gui.log",
    "stderr": "/home/deploy/ai_media_os/logs/new_release_gui.log",
    "background_mode": "DETACHED_BACKGROUND",
    "pid_capture": {
        "method": "SHELL_BACKGROUND_PID_AND_PROCESS_IDENTITY_EVIDENCE",
        "source": "$!",
        "future_pid_file": None,
        "pid_file_created_now": False,
        "future_execution_must_capture_new_pid_in_unique_evidence": True,
        "pid_only_trust_forbidden": True,
    },
    "process_identity_generation": {
        "required_fields": [
            "pid", "starttime_ticks", "cmdline_argv", "cwd",
            "exe", "uid", "session_id", "process_group_id",
        ],
        "identity_sha256_required": True,
    },
    "readiness_check": {
        "host": "127.0.0.1",
        "port": 8765,
        "method": "LOCAL_LISTENER_AND_SINGLE_PROCESS_IDENTITY",
        "external_network_required": False,
        "http_request_required": False,
        "future_commands": [
            ["ss", "-ltnp"],
            [
                "ps", "-o",
                "pid,ppid,sid,pgid,lstart,tty,stat,user,comm,args",
                "-p", "<NEW_PID>",
            ],
        ],
    },
    "double_start_prevention": {
        "before_start_require_zero_matching_processes": True,
        "before_start_require_port_free": True,
        "after_start_require_one_matching_process": True,
        "after_start_require_listener_owned_by_new_process": True,
    },
    "planned_shell_command_not_executed": planned_restart_shell,
    "blocking_environment_classifications": blocking_classifications,
    "loader_pattern_blockers": loader_blockers,
    "parse_error_blockers": parse_blockers,
    "writer_freeze_execution": "HOLD",
}

write_json(packet_root / "minimal-environment-contract.json", explicit_environment_source)
write_json(packet_root / "exact-restart-environment-contract.json", restart_contract)

resolution = {
    "schema_version": "1.0",
    "phase": phase,
    "completed_at_utc": now_utc(),
    "input_g_r1_evidence_root": g_r1_rel,
    "current_gui_pid": current_pid,
    "process_identity_sha256": expected_identity_sha,
    "static_analysis": {
        "visited_python_file_count": static_analysis["visited_python_file_count"],
        "environment_usage_count": len(static_analysis["environment_usages"]),
        "environment_file_reference_count": len(
            static_analysis["environment_file_references"]
        ),
        "loader_pattern_count": len(loader_blockers),
        "parse_error_count": len(parse_blockers),
    },
    "environment_classification_counts": classification_counts,
    "environment_contract_resolved": environment_contract_resolved,
    "exact_stop_status": "RESOLVED_PENDING_HUMAN_REVIEW",
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": environment_contract_resolved,
    "credential_file_content_read": False,
    "environment_file_content_read": False,
    "live_environment_values_saved": False,
    "secret_environment_values_saved": False,
    "shell_history_inspected": False,
    "minimal_environment_contract_created": True,
    "restart_execution_allowed": False,
    "execution": {
        "process_signal_sent": False,
        "writer_stop_performed": False,
        "gui_stopped_or_restarted": False,
        "systemctl_stop_start_restart_executed": False,
        "service_created_or_modified": False,
        "cron_changed": False,
        "timer_changed": False,
        "production_database_opened": False,
        "production_database_sql_connection_used": False,
        "sql_executed": False,
        "backup_created": False,
        "restore_executed": False,
        "migration_executed": False,
        "production_manifest_modified": False,
        "source_modified": False,
        "test_modified": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "deployment_performed": False,
        "external_network_used": False,
        "slack_worker_started": False,
        "production_approval_created": False,
        "production_release_approved": False,
    },
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET",
}
write_json(packet_root / "environment-contract-resolution.json", resolution)

protected_after = protected_sha_inventory()
write_json(packet_root / "protected-sha-after.json", protected_after)
require(
    [item["sha256"] for item in protected_before["files"]]
    == [item["sha256"] for item in protected_after["files"]],
    "PROTECTED_SHA_CHANGED",
)

semantic_validation = {
    "schema_version": "1.0",
    "phase": phase,
    "result": "PASS_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READONLY",
    "current_gui_single_match": True,
    "process_identity_sha256": expected_identity_sha,
    "environment_contract_resolved": environment_contract_resolved,
    "exact_stop_status": "RESOLVED_PENDING_HUMAN_REVIEW",
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": environment_contract_resolved,
    "classification_counts": classification_counts,
    "blocking_classification_count": len(blocking_classifications),
    "loader_pattern_blocker_count": len(loader_blockers),
    "parse_error_blocker_count": len(parse_blockers),
    "credential_file_content_read": False,
    "environment_file_content_read": False,
    "live_environment_values_saved": False,
    "secret_environment_values_saved": False,
    "shell_history_inspected": False,
    "protected_sha_unchanged": True,
    "process_signal_sent": False,
    "writer_stop_performed": False,
    "gui_stopped_or_restarted": False,
    "production_database_opened": False,
    "sql_executed": False,
    "external_network_used": False,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
}
write_json(packet_root / "packet-semantic-validation.json", semantic_validation)

packet_files_before_manifest = sorted(
    path for path in packet_root.iterdir() if path.is_file()
)
manifest_entries = [
    {
        "name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }
    for path in packet_files_before_manifest
]

packet_manifest = {
    "schema_version": "1.0",
    "phase": phase,
    "created_at_utc": now_utc(),
    "status": "READONLY_ENVIRONMENT_CONTRACT_PACKET_WRITER_FREEZE_NOT_APPROVED",
    "result": "PASS_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET_GENERATED",
    "packet_file_count_excluding_manifest": len(manifest_entries),
    "packet_files": manifest_entries,
    "environment_contract_resolved": environment_contract_resolved,
    "exact_stop_status": "RESOLVED_PENDING_HUMAN_REVIEW",
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": environment_contract_resolved,
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET",
}
write_json(packet_root / "packet-manifest.json", packet_manifest)

result = {
    "schema_version": "1.0",
    "phase": phase,
    "completed_at_utc": now_utc(),
    "result": "PASS_W2B_I2F3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_RESOLUTION_READY",
    "evidence_root": evidence_rel,
    "input_g_r1_evidence_root": g_r1_rel,
    "current_gui_pid": current_pid,
    "process_identity_sha256": expected_identity_sha,
    "visited_python_file_count": static_analysis["visited_python_file_count"],
    "environment_classification_counts": classification_counts,
    "blocking_environment_classification_count": len(blocking_classifications),
    "loader_pattern_blocker_count": len(loader_blockers),
    "parse_error_blocker_count": len(parse_blockers),
    "environment_contract_resolved": environment_contract_resolved,
    "exact_stop_status": "RESOLVED_PENDING_HUMAN_REVIEW",
    "exact_restart_status": exact_restart_status,
    "both_exact_routes_resolved": environment_contract_resolved,
    "credential_file_content_read": False,
    "environment_file_content_read": False,
    "raw_live_environment_saved": False,
    "secret_environment_values_saved": False,
    "shell_history_inspected": False,
    "packet_file_count": len(manifest_entries) + 1,
    "packet_manifest_sha256": sha256(packet_root / "packet-manifest.json"),
    "packet_semantic_validation_sha256": sha256(
        packet_root / "packet-semantic-validation.json"
    ),
    "execution": resolution["execution"],
    "writer_freeze_execution": "HOLD",
    "production_release_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_gate": "HUMAN_REVIEW_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET",
}
write_json(evidence_root / "result.json", result)

manifest_path = evidence_root / "evidence-manifest.txt"
manifest_lines = []
for artifact in sorted(
    evidence_root.rglob("*"),
    key=lambda item: item.relative_to(evidence_root).as_posix(),
):
    if artifact.is_file() and artifact != manifest_path:
        manifest_lines.append(
            f"{sha256(artifact)}  {artifact.relative_to(evidence_root).as_posix()}"
        )
manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

for line in manifest_path.read_text(encoding="utf-8").splitlines():
    expected, relative_path = line.split("  ", 1)
    artifact = evidence_root / relative_path
    require(artifact.is_file(), f"EVIDENCE_MANIFEST_FILE_MISSING:{relative_path}")
    require(
        sha256(artifact) == expected,
        f"EVIDENCE_MANIFEST_SHA_MISMATCH:{relative_path}",
    )

files = sorted(path for path in evidence_root.rglob("*") if path.is_file())
directories = sorted(
    (path for path in evidence_root.rglob("*") if path.is_dir()),
    key=lambda path: len(path.relative_to(evidence_root).parts),
    reverse=True,
)

repo_stat = repo_root.stat()
for artifact in [*files, *directories, evidence_root]:
    metadata = artifact.lstat()
    require(not stat.S_ISLNK(metadata.st_mode), f"EVIDENCE_SYMLINK_FORBIDDEN:{artifact}")
    require(metadata.st_uid == repo_stat.st_uid, f"EVIDENCE_UID_INVALID:{artifact}")
    require(metadata.st_gid == repo_stat.st_gid, f"EVIDENCE_GID_INVALID:{artifact}")

for artifact in files:
    os.chmod(artifact, 0o444)
for directory in directories:
    os.chmod(directory, 0o555)
os.chmod(evidence_root, 0o555)

for artifact in files:
    require(
        stat.S_IMODE(artifact.stat().st_mode) == 0o444,
        f"FILE_SEAL_FAILED:{artifact}",
    )
for directory in [*directories, evidence_root]:
    require(
        stat.S_IMODE(directory.stat().st_mode) == 0o555,
        f"DIRECTORY_SEAL_FAILED:{directory}",
    )

print(f"RESULT={result['result']}")
print(f"EVIDENCE_ROOT={evidence_rel}")
print(f"CURRENT_GUI_PID={current_pid}")
print(f"PROCESS_IDENTITY_SHA={expected_identity_sha}")
print(f"VISITED_PYTHON_FILE_COUNT={static_analysis['visited_python_file_count']}")
print(f"ENVIRONMENT_USAGE_COUNT={len(static_analysis['environment_usages'])}")
print(f"ENVIRONMENT_FILE_REFERENCE_COUNT={len(static_analysis['environment_file_references'])}")
print(f"STARTUP_REQUIRED_COUNT={classification_counts['STARTUP_REQUIRED']}")
print(f"RUNTIME_REQUIRED_COUNT={classification_counts['RUNTIME_REQUIRED']}")
print(f"EXTERNAL_ACTION_ONLY_COUNT={classification_counts['EXTERNAL_ACTION_ONLY']}")
print(f"OPTIONAL_COUNT={classification_counts['OPTIONAL']}")
print(f"INHERITED_NOT_USED_COUNT={classification_counts['INHERITED_NOT_USED']}")
print(f"UNRESOLVED_COUNT={classification_counts['UNRESOLVED']}")
print(f"LOADER_PATTERN_BLOCKER_COUNT={len(loader_blockers)}")
print(f"PARSE_ERROR_BLOCKER_COUNT={len(parse_blockers)}")
print(f"ENVIRONMENT_CONTRACT_RESOLVED={'true' if environment_contract_resolved else 'false'}")
print("EXACT_STOP_STATUS=RESOLVED_PENDING_HUMAN_REVIEW")
print(f"EXACT_RESTART_STATUS={exact_restart_status}")
print(f"BOTH_EXACT_ROUTES_RESOLVED={'true' if environment_contract_resolved else 'false'}")
print("ENVIRONMENT_SOURCE_TYPE=STATIC_MINIMAL_ENVIRONMENT_CONTRACT_NO_CREDENTIAL_FILE")
print("CREDENTIAL_FILE_CONTENT_READ=false")
print("ENVIRONMENT_FILE_CONTENT_READ=false")
print("RAW_LIVE_ENVIRONMENT_SAVED=false")
print("SECRET_ENVIRONMENT_VALUES_SAVED=false")
print("SHELL_HISTORY_INSPECTED=false")
print(f"PACKET_FILE_COUNT={result['packet_file_count']}")
print(f"PACKET_MANIFEST_SHA={result['packet_manifest_sha256']}")
print(f"PACKET_SEMANTIC_VALIDATION_SHA={result['packet_semantic_validation_sha256']}")
print(f"RESULT_SHA={sha256(evidence_root / 'result.json')}")
print(f"EVIDENCE_MANIFEST_SHA={sha256(evidence_root / 'evidence-manifest.txt')}")
print("PROCESS_SIGNAL_SENT=false")
print("WRITER_STOP_PERFORMED=false")
print("GUI_STOPPED_OR_RESTARTED=false")
print("SYSTEMD_CHANGED=false")
print("CRON_CHANGED=false")
print("TIMER_CHANGED=false")
print("PRODUCTION_DB_OPENED=false")
print("PRODUCTION_DB_SQL_CONNECTION_USED=false")
print("SQL_EXECUTED=false")
print("BACKUP_CREATED=false")
print("RESTORE_EXECUTED=false")
print("MIGRATION_EXECUTED=false")
print("PRODUCTION_MANIFEST_MODIFIED=false")
print("SOURCE_MODIFIED=false")
print("TEST_MODIFIED=false")
print("GIT_ADD_PERFORMED=false")
print("GIT_COMMIT_PERFORMED=false")
print("DEPLOYMENT_PERFORMED=false")
print("EXTERNAL_NETWORK_USED=false")
print("SLACK_WORKER_STARTED=false")
print("PRODUCTION_APPROVAL_CREATED=false")
print("PRODUCTION_RELEASE_APPROVED=false")
print("WRITER_FREEZE_EXECUTION=HOLD")
print("PRODUCTION_RELEASE_DECISION=HOLD")
print("RELEASE_STATUS=CANDIDATE_NOT_APPROVED")
print("NEXT_GATE=HUMAN_REVIEW_3E_H_GUI_RESTART_ENVIRONMENT_CONTRACT_PACKET")
PY

trap - ERR
printf 'SCRIPT_EXIT_CODE=0\n'
