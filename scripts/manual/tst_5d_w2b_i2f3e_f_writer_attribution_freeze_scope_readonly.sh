#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PHASE="TST-5D-W2B-I2F-3E-F"
REPO_ROOT="/home/deploy/ai_media_os"
DB_PATH="$REPO_ROOT/data/database/ebook_affiliate.db"
WAL_PATH="$DB_PATH-wal"
SHM_PATH="$DB_PATH-shm"
MANIFEST_PATH="$REPO_ROOT/config/slack_worker_release_source_manifest.json"
WORKFLOW_PATH="$REPO_ROOT/app/db/repositories/workflow_state_repository.py"
MIGRATION_PATH="$REPO_ROOT/migrations/versions/00241611109d_add_unique_wordpress_post_id.py"
SLACK_RUNTIME_PATH="$REPO_ROOT/scripts/run_slack_approval_socket.py"
PROMOTED_TEST_PATH="$REPO_ROOT/tests/test_slack_approval_socket_hold_remediation_offline.py"

EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
EXPECTED_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_WORKFLOW_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_MIGRATION_SHA="e1d29ed34fdbcaedb4a811681d8c28534682f8ce2d1144d044c0cb6dd0f3054a"
EXPECTED_SLACK_RUNTIME_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_PROMOTED_TEST_SHA="86dfc01686ffd53a2c6c7e73192d469db5040bc38f6541031cb6f36e7846ed72"

PREV_EVIDENCE_ROOT="$REPO_ROOT/exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632/i2f3e-e-production-db-preflight-backup-preparation-20260725T133523-508590"
PREV_RESULT="$PREV_EVIDENCE_ROOT/result.json"
PREV_PACKET_MANIFEST="$PREV_EVIDENCE_ROOT/packet-snapshot/production-db-preflight-backup-preparation-packet-manifest.json"
PREV_EVIDENCE_MANIFEST="$PREV_EVIDENCE_ROOT/production-db-preflight-backup-preparation-evidence-manifest.txt"
EXPECTED_PREV_RESULT_SHA="12437e404ee24af88a8bb80be055cd7dba87b55c178a131176673b137b2ffaa7"
EXPECTED_PREV_PACKET_MANIFEST_SHA="c0a352cdfcda2c54e7ac35a8b754a6a47c0b2f8ee3b26891586e844f44721d91"
EXPECTED_PREV_EVIDENCE_MANIFEST_SHA="c903d0855fb8e45fc04ade2d4f55c1acfde61c6089dcdeca5b44caa5b83b96e8"

APPROVED_PIDS=(945 1853 302168)
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
BASE_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
EVIDENCE_ROOT="$REPO_ROOT/$BASE_REL/i2f3e-f-writer-attribution-freeze-scope-readonly-$RUN_ID"
EVIDENCE_ROOT_REL="$BASE_REL/i2f3e-f-writer-attribution-freeze-scope-readonly-$RUN_ID"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3e-f-writer-attribution-freeze-scope-$RUN_ID"
PACKET_ROOT="$EVIDENCE_ROOT/packet-snapshot"
INPUT_ROOT="$EVIDENCE_ROOT/input-snapshots"
CONSOLE_SNAPSHOT="$EVIDENCE_ROOT/console-snapshot.txt"

mkdir "$EVIDENCE_ROOT"
mkdir "$SHADOW_ROOT"
mkdir "$PACKET_ROOT"
mkdir "$INPUT_ROOT"

exec > >(tee "$CONSOLE_SNAPSHOT") 2>&1

on_error() {
  local rc=$?
  set +e
  printf 'FAILURE_PHASE=%s\n' "$PHASE" > "$EVIDENCE_ROOT/failure.txt"
  printf 'FAILURE_EXIT_CODE=%s\n' "$rc" >> "$EVIDENCE_ROOT/failure.txt"
  printf 'FAILURE_AT_UTC=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$EVIDENCE_ROOT/failure.txt"
  printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_ROOT_REL" >> "$EVIDENCE_ROOT/failure.txt"
  printf 'PRODUCTION_DB_OPENED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'SQL_EXECUTED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'WRITER_STOP_PERFORMED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'PROCESS_SIGNAL_SENT=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'SYSTEMD_CHANGED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'CRON_CHANGED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'BACKUP_CREATED=false\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'PRODUCTION_RELEASE_DECISION=HOLD\n' >> "$EVIDENCE_ROOT/failure.txt"
  printf 'SCRIPT_EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap on_error ERR

sha_of() { sha256sum "$1" | awk '{print $1}'; }
require_file() { test -f "$1" || { echo "MISSING_FILE=$1" >&2; return 1; }; }
require_sha() {
  local path="$1" expected="$2" actual
  require_file "$path"
  actual="$(sha_of "$path")"
  test "$actual" = "$expected" || {
    printf 'SHA_MISMATCH=%s:expected=%s:actual=%s\n' "$path" "$expected" "$actual" >&2
    return 1
  }
  printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

require_sha "$PREV_RESULT" "$EXPECTED_PREV_RESULT_SHA"
require_sha "$PREV_PACKET_MANIFEST" "$EXPECTED_PREV_PACKET_MANIFEST_SHA"
require_sha "$PREV_EVIDENCE_MANIFEST" "$EXPECTED_PREV_EVIDENCE_MANIFEST_SHA"
require_sha "$DB_PATH" "$EXPECTED_DB_SHA"
require_sha "$MANIFEST_PATH" "$EXPECTED_MANIFEST_SHA"
require_sha "$WORKFLOW_PATH" "$EXPECTED_WORKFLOW_SHA"
require_sha "$MIGRATION_PATH" "$EXPECTED_MIGRATION_SHA"
require_sha "$SLACK_RUNTIME_PATH" "$EXPECTED_SLACK_RUNTIME_SHA"
require_sha "$PROMOTED_TEST_PATH" "$EXPECTED_PROMOTED_TEST_SHA"

cp "$PREV_RESULT" "$INPUT_ROOT/3e-e-result.json"
cp "$PREV_PACKET_MANIFEST" "$INPUT_ROOT/3e-e-packet-manifest.json"
cp "$PREV_EVIDENCE_MANIFEST" "$INPUT_ROOT/3e-e-evidence-manifest.txt"
cp "$PROMOTED_TEST_PATH" "$INPUT_ROOT/promoted-test.py"

cat > "$PACKET_ROOT/human-approval-verbatim.txt" <<'APPROVAL'
承認：
PREPARATION_PACKET_REVIEW=APPROVE_WITH_CONDITIONS
3E_E_PRODUCTION_DB_PREFLIGHT_BACKUP_PREPARATION=PASS
APPROVE_3E_F_WRITER_ATTRIBUTION_AND_FREEZE_SCOPE_PREPARATION_READONLY

許可範囲：
1. PID 945、1853、302168について、cmdline、親プロセス、cwd、exe、cgroup、systemd所属を読み取り確認する。
2. root権限による/proc fdの読み取り専用検査を行い、Production DB、WAL、SHMのopen handleを再確認する。
3. PID 1853のuvicornが所属するアプリケーションと、Production DBへの到達可能性を確認する。
4. new_release_multistore_app.pyのDB設定経路と、graceful stop／restart方法を読み取り調査する。
5. cron daemon自体と、登録された個別cron jobを分離して評価し、Production DBへ到達する可能性のあるjobを特定する。
6. cron、GUI、uvicornそれぞれについて、STOP_REQUIRED、WINDOW_CONTROL_ONLY、NOT_RELEVANT、UNRESOLVEDのいずれかへ分類する。
7. 実際の停止対象、停止順序、再開順序、Freeze時間帯を準備Packetとして作成する。
8. 新しい一意なshadow／evidence領域へ結果を保存する。

禁止事項：
process signal送信、writer停止、GUI停止・再起動、systemctl stop/start/restart、cron変更、timer変更、Production DB接続、SQL実行、backup作成、restore、migration、manifest変更、source/test変更、git add、git commit、deployment、外部通信、Slack Worker起動、production approval、production release承認は禁止する。

WRITER_FREEZE_EXECUTION=HOLD
PRODUCTION_RELEASE_DECISION=HOLD
RELEASE_STATUS=CANDIDATE_NOT_APPROVED
APPROVAL

python3 - "$PACKET_ROOT/protected-sha-before.json" <<'PY'
import hashlib, json, os, stat, sys
from pathlib import Path
paths = [
    Path('/home/deploy/ai_media_os/data/database/ebook_affiliate.db'),
    Path('/home/deploy/ai_media_os/config/slack_worker_release_source_manifest.json'),
    Path('/home/deploy/ai_media_os/app/db/repositories/workflow_state_repository.py'),
    Path('/home/deploy/ai_media_os/migrations/versions/00241611109d_add_unique_wordpress_post_id.py'),
    Path('/home/deploy/ai_media_os/scripts/run_slack_approval_socket.py'),
    Path('/home/deploy/ai_media_os/tests/test_slack_approval_socket_hold_remediation_offline.py'),
]
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
items=[]
for p in paths:
    s=p.stat()
    items.append({'path':str(p),'sha256':h(p),'size':s.st_size,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns,'mode':f'{stat.S_IMODE(s.st_mode):04o}'})
Path(sys.argv[1]).write_text(json.dumps({'captured_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'items':items,'production_database_opened':False,'sql_executed':False},sort_keys=True,indent=2)+'\n')
PY

if [ "$(id -u)" -eq 0 ]; then
  SUDO=( )
else
  echo "SUDO_READONLY_AUTHENTICATION_REQUIRED=true"
  sudo -v
  SUDO=(sudo -n)
fi

"${SUDO[@]}" python3 - "$PACKET_ROOT/root-proc-readonly-inspection.json" "$REPO_ROOT" "$DB_PATH" "$WAL_PATH" "$SHM_PATH" "${APPROVED_PIDS[@]}" <<'PY'
from __future__ import annotations
import datetime as dt
import json
import os
import re
import stat
import sys
from pathlib import Path

out = Path(sys.argv[1])
repo = Path(sys.argv[2]).resolve()
target_paths = {str(Path(x).resolve()) for x in sys.argv[3:6]}
approved_pids = [int(x) for x in sys.argv[6:]]
proc = Path('/proc')

signatures = {
    'cron': '/usr/sbin/cron -f -P',
    'uvicorn_8000': 'uvicorn app.main:app --host 0.0.0.0 --port 8000',
    'ebook_gui_8765': 'scripts/new_release_multistore_app.py',
}

skip_dirs = {'.git','.venv','venv','node_modules','__pycache__','exchange','backups','data','logs','.cache'}
skip_name_tokens = {'secret','credential','token','password','private','apikey','api_key','.env','key.pem','id_rsa'}
text_suffixes = {'.py','.sh','.toml','.ini','.cfg','.json','.yaml','.yml','.service','.timer','.conf'}
patterns = {
    'production_db_absolute_path': str(Path(sys.argv[3]).resolve()),
    'production_db_basename': Path(sys.argv[3]).name,
    'repo_absolute_path': str(repo),
    'db_module_reference': 'app.db',
    'session_local_reference': 'SessionLocal',
    'sqlalchemy_engine_reference': 'create_engine',
    'sqlite_reference': 'sqlite',
}

def read_bytes(path: Path, limit: int = 2_000_000) -> bytes:
    with path.open('rb') as f:
        return f.read(limit)

def safe_read_text(path: Path) -> str | None:
    name = path.name.lower()
    if any(tok in name for tok in skip_name_tokens):
        return None
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return read_bytes(path).decode('utf-8', errors='ignore')
    except Exception:
        return None

def scan_tree(root: Path, max_files: int = 1500) -> dict:
    result = {'root': str(root), 'exists': root.exists(), 'scanned_file_count': 0, 'skipped_file_count': 0, 'matches': [], 'completed': False}
    if not root.exists() or not root.is_dir():
        return result
    seen = 0
    try:
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for name in files:
                p = Path(current) / name
                if p.suffix.lower() not in text_suffixes:
                    continue
                if any(tok in name.lower() for tok in skip_name_tokens):
                    result['skipped_file_count'] += 1
                    continue
                seen += 1
                if seen > max_files:
                    result['limit_reached'] = True
                    result['completed'] = False
                    return result
                text = safe_read_text(p)
                if text is None:
                    result['skipped_file_count'] += 1
                    continue
                result['scanned_file_count'] += 1
                labels = [label for label, value in patterns.items() if value in text]
                if labels:
                    result['matches'].append({'path': str(p), 'pattern_labels': labels})
        result['completed'] = True
        return result
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}:{exc}'
        return result

def readlink(path: Path) -> str | None:
    try: return os.readlink(path)
    except Exception: return None

def read_text(path: Path) -> str | None:
    try: return path.read_text(errors='replace')
    except Exception: return None

def cmdline(pid: int) -> str | None:
    try:
        raw=(proc/str(pid)/'cmdline').read_bytes()
        return ' '.join(x.decode(errors='replace') for x in raw.split(b'\0') if x)
    except Exception:
        return None

def process_detail(pid: int) -> dict:
    base=proc/str(pid)
    detail={'pid':pid,'exists':base.exists()}
    if not base.exists(): return detail
    detail['cmdline']=cmdline(pid)
    detail['cwd']=readlink(base/'cwd')
    detail['exe']=readlink(base/'exe')
    detail['root']=readlink(base/'root')
    detail['cgroup']=read_text(base/'cgroup')
    status=read_text(base/'status') or ''
    for key in ('Name','State','PPid','Uid','Gid'):
        m=re.search(rf'^{key}:\s*(.*)$',status,re.M)
        detail[key.lower()]=m.group(1) if m else None
    try:
        ppid=int((detail.get('ppid') or '0').split()[0])
    except Exception: ppid=0
    if ppid:
        detail['parent']={'pid':ppid,'cmdline':cmdline(ppid),'cwd':readlink(proc/str(ppid)/'cwd'),'exe':readlink(proc/str(ppid)/'exe')}
    fd_targets=[]
    fd_dir=base/'fd'
    try:
        for fd in sorted(fd_dir.iterdir(), key=lambda p:int(p.name) if p.name.isdigit() else 999999):
            target=readlink(fd)
            if target is not None:
                fd_targets.append({'fd':fd.name,'target':target})
    except Exception as exc:
        detail['fd_error']=f'{type(exc).__name__}:{exc}'
    detail['stdio']={x['fd']:x['target'] for x in fd_targets if x['fd'] in {'0','1','2'}}
    detail['target_db_handles']=[x for x in fd_targets if x['target'].replace(' (deleted)','') in target_paths]
    cgroup=detail.get('cgroup') or ''
    units=[]
    for line in cgroup.splitlines():
        path=line.rsplit(':',1)[-1]
        for part in path.split('/'):
            if part.endswith(('.service','.scope','.slice')):
                units.append(part)
    detail['systemd_membership']=sorted(set(units))
    try:
        raw=(base/'environ').read_bytes()
        env={}
        for item in raw.split(b'\0'):
            if b'=' not in item: continue
            k,v=item.split(b'=',1)
            key=k.decode(errors='replace')
            if key in {'PWD','VIRTUAL_ENV','PYTHONPATH','INVOCATION_ID','SYSTEMD_EXEC_PID'}:
                env[key]=v.decode(errors='replace')
            elif any(t in key.upper() for t in ('DATABASE','SQLITE','DB_PATH')):
                env[key]='<VALUE_REDACTED>'
        detail['safe_environment']=env
    except Exception as exc:
        detail['environment_error']=f'{type(exc).__name__}:{exc}'
    return detail

all_pids=[]
for p in proc.iterdir():
    if p.name.isdigit(): all_pids.append(int(p.name))
all_pids.sort()

matched={k:[] for k in signatures}
for pid in all_pids:
    c=cmdline(pid)
    if not c: continue
    for key,sig in signatures.items():
        if sig in c:
            matched[key].append(pid)

open_handles=[]
inaccessible=0
for pid in all_pids:
    fd_dir=proc/str(pid)/'fd'
    try:
        entries=list(fd_dir.iterdir())
    except Exception:
        inaccessible+=1
        continue
    for fd in entries:
        target=readlink(fd)
        if target is None: continue
        normalized=target.replace(' (deleted)','')
        if normalized in target_paths:
            open_handles.append({'pid':pid,'fd':fd.name,'target':target,'cmdline':cmdline(pid)})

processes={str(pid):process_detail(pid) for pid in sorted(set(approved_pids + sum(matched.values(),[])))}

source_scans={}
for logical, pids in matched.items():
    scans=[]
    for pid in pids:
        d=processes.get(str(pid),{})
        if logical=='ebook_gui_8765':
            scans.append(scan_tree(repo))
        elif logical=='uvicorn_8000':
            cwd=d.get('cwd')
            if cwd:
                root_view=Path(f'/proc/{pid}/root') / cwd.lstrip('/')
                scans.append(scan_tree(root_view))
        source_scans.setdefault(logical,[]).append({'pid':pid,'scans':scans})

result={
    'phase':'TST-5D-W2B-I2F-3E-F',
    'captured_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
    'root_privileged_readonly_inspection':True,
    'approved_pids':approved_pids,
    'signature_matches':matched,
    'processes':processes,
    'target_paths':sorted(target_paths),
    'root_proc_scan':{'scanned_pid_count':len(all_pids),'inaccessible_or_vanished_proc_count':inaccessible,'open_handle_count':len(open_handles),'open_handles':open_handles},
    'source_scans':source_scans,
    'process_signal_sent':False,
    'writer_stop_performed':False,
    'production_database_opened':False,
    'sql_executed':False,
}
out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
PY

{
  echo "CRON_READONLY_INVENTORY"
  echo "CAPTURED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "CRON_CHANGED=false"
  echo
  echo "===== DEPLOY CRONTAB ====="
  crontab -l 2>&1 || true
  echo
  echo "===== ROOT CRONTAB ====="
  "${SUDO[@]}" crontab -l -u root 2>&1 || true
  echo
  echo "===== WWW-DATA CRONTAB ====="
  "${SUDO[@]}" crontab -l -u www-data 2>&1 || true
  echo
  echo "===== /ETC/CRON FILES ====="
  "${SUDO[@]}" find /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly -maxdepth 1 -type f -printf '%p|%m|%u|%g|%s|%TY-%Tm-%TdT%TH:%TM:%TS%Tz\n' 2>/dev/null | sort
} > "$PACKET_ROOT/cron-readonly-inventory.txt"

{
  echo "SYSTEMD_READONLY_ATTRIBUTION"
  echo "CAPTURED_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "SYSTEMD_CHANGED=false"
  echo
  echo "===== TARGET PID STATUS ====="
  for pid in "${APPROVED_PIDS[@]}"; do
    echo "--- PID $pid ---"
    "${SUDO[@]}" systemctl status "$pid" --no-pager --full 2>&1 || true
  done
  echo
  echo "===== RELEVANT SERVICES ====="
  systemctl list-units --type=service --all --no-pager --no-legend 2>&1 | grep -Ei 'ai.media|ebook|slack|uvicorn|new.release|multistore|wordpress' || true
  echo
  echo "===== RELEVANT TIMERS ====="
  systemctl list-timers --all --no-pager 2>&1 | grep -Ei 'ai.media|ebook|slack|uvicorn|new.release|multistore|wordpress' || true
} > "$PACKET_ROOT/systemd-readonly-attribution.txt"

python3 - "$PACKET_ROOT/root-proc-readonly-inspection.json" "$PACKET_ROOT/cron-readonly-inventory.txt" "$PACKET_ROOT/process-and-cron-attribution.json" "$PACKET_ROOT/freeze-window-plan.json" "$PACKET_ROOT/stop-restart-scope-plan.json" "$REPO_ROOT" <<'PY'
from __future__ import annotations
import datetime as dt
import json
import os
import re
import shlex
import sys
from pathlib import Path

proc_path=Path(sys.argv[1]); cron_path=Path(sys.argv[2]); out=Path(sys.argv[3]); window_out=Path(sys.argv[4]); scope_out=Path(sys.argv[5]); repo=Path(sys.argv[6]).resolve()
root=json.loads(proc_path.read_text())
cron_text=cron_path.read_text(errors='replace')
DB=str(repo/'data/database/ebook_affiliate.db')

valid_classes={'STOP_REQUIRED','WINDOW_CONTROL_ONLY','NOT_RELEVANT','UNRESOLVED'}

def signature_pids(name): return root.get('signature_matches',{}).get(name,[])

def proc(pid): return root.get('processes',{}).get(str(pid),{})

def scan_labels(logical):
    labels=set(); completed=False; roots=[]
    for group in root.get('source_scans',{}).get(logical,[]):
        for scan in group.get('scans',[]):
            roots.append(scan.get('root'))
            completed=completed or bool(scan.get('completed'))
            for m in scan.get('matches',[]): labels.update(m.get('pattern_labels',[]))
    return sorted(labels),completed,roots

classifications=[]

cron_pids=signature_pids('cron')
classifications.append({
    'logical_writer':'cron_daemon',
    'approved_pid':945,
    'current_pids':cron_pids,
    'classification':'WINDOW_CONTROL_ONLY',
    'reason':'The daemon schedules jobs but is not itself classified as the database writer. Freeze control must prevent relevant jobs from starting and verify no cron child is active during the window.',
    'stop_daemon_required':False,
})

gui_pids=signature_pids('ebook_gui_8765')
gui_details=[proc(p) for p in gui_pids]
classifications.append({
    'logical_writer':'ebook_gui_8765',
    'approved_pid':302168,
    'current_pids':gui_pids,
    'classification':'STOP_REQUIRED' if gui_pids else 'UNRESOLVED',
    'reason':'The process is the ai_media_os new-release multistore GUI and is conservatively treated as write-capable for the production database.' if gui_pids else 'Approved GUI PID/signature is no longer present; replacement process attribution is unresolved.',
    'systemd_membership':sorted({u for d in gui_details for u in d.get('systemd_membership',[])}),
    'cwd':sorted({d.get('cwd') for d in gui_details if d.get('cwd')}),
    'stdio':[d.get('stdio',{}) for d in gui_details],
})

uv_pids=signature_pids('uvicorn_8000')
uv_labels,uv_scan_completed,uv_roots=scan_labels('uvicorn_8000')
uv_handles=[]
for p in uv_pids: uv_handles.extend(proc(p).get('target_db_handles',[]))
strong={'production_db_absolute_path','production_db_basename','repo_absolute_path'} & set(uv_labels)
if not uv_pids:
    uv_class='UNRESOLVED'; uv_reason='Approved uvicorn PID/signature is no longer present; replacement process attribution is unresolved.'
elif uv_handles or strong:
    uv_class='STOP_REQUIRED'; uv_reason='Exact production DB/repository reachability evidence or target DB handle was found.'
elif uv_scan_completed:
    uv_class='NOT_RELEVANT'; uv_reason='Root-visible application source scan completed with no exact production DB basename/path or ai_media_os repository reference, and no target DB handle was open.'
else:
    uv_class='UNRESOLVED'; uv_reason='No exact DB handle was found, but source scan did not complete sufficiently to exclude reachability.'
uv_details=[proc(p) for p in uv_pids]
classifications.append({
    'logical_writer':'uvicorn_8000',
    'approved_pid':1853,
    'current_pids':uv_pids,
    'classification':uv_class,
    'reason':uv_reason,
    'source_scan_completed':uv_scan_completed,
    'source_scan_roots':uv_roots,
    'source_pattern_labels':uv_labels,
    'target_db_handles':uv_handles,
    'systemd_membership':sorted({u for d in uv_details for u in d.get('systemd_membership',[])}),
    'cwd':sorted({d.get('cwd') for d in uv_details if d.get('cwd')}),
})

# Parse crontab sections and active job lines.
section='unknown'; jobs=[]
for raw in cron_text.splitlines():
    line=raw.rstrip('\n')
    if line.startswith('===== ') and line.endswith(' ====='):
        section=line.strip('= ').lower().replace(' ','_'); continue
    s=line.strip()
    if not s or s.startswith('#') or s.startswith('CRON_') or s.startswith('CAPTURED_') or s.startswith('no crontab for'):
        continue
    if s.startswith('@'):
        parts=s.split(None,1)
        if len(parts)==2: schedule,command=parts
        else: continue
    else:
        parts=s.split(None,5)
        if len(parts)<6: continue
        schedule=' '.join(parts[:5]); command=parts[5]
    labels=[]
    if str(repo) in command: labels.append('repo_command_path')
    if DB in command or 'ebook_affiliate.db' in command: labels.append('exact_db_reference')
    abs_paths=re.findall(r'(?<![A-Za-z0-9_])(/[A-Za-z0-9_./-]+)',command)
    scanned=[]; inaccessible=[]
    for token in abs_paths:
        p=Path(token)
        if not p.is_file(): continue
        low=p.name.lower()
        if any(x in low for x in ('secret','credential','token','password','.env','private','key')): continue
        try:
            if p.stat().st_size>2_000_000: continue
            text=p.read_text(errors='ignore')
            file_labels=[]
            for label,val in [('production_db_absolute_path',DB),('production_db_basename','ebook_affiliate.db'),('repo_absolute_path',str(repo)),('db_module_reference','app.db'),('session_local_reference','SessionLocal')]:
                if val in text: file_labels.append(label)
            scanned.append({'path':str(p),'pattern_labels':file_labels})
            labels.extend(file_labels)
        except Exception as exc:
            inaccessible.append({'path':str(p),'error':f'{type(exc).__name__}:{exc}'})
    labels=sorted(set(labels))
    if 'exact_db_reference' in labels or 'production_db_absolute_path' in labels or 'production_db_basename' in labels or 'db_module_reference' in labels or 'session_local_reference' in labels:
        cls='WINDOW_CONTROL_ONLY'; reason='Job has direct or source-level database/repository reachability indicators; prevent launch during freeze and verify no active child.'
    elif 'repo_command_path' in labels:
        cls='WINDOW_CONTROL_ONLY'; reason='Job executes inside ai_media_os; control the maintenance window even though no direct DB literal was found.'
    elif inaccessible:
        cls='UNRESOLVED'; reason='Referenced executable/source could not be completely inspected.'
    else:
        cls='NOT_RELEVANT'; reason='No ai_media_os or production DB reachability indicator was found in the command or readable referenced files.'
    jobs.append({'section':section,'schedule':schedule,'command':command,'classification':cls,'reason':reason,'pattern_labels':labels,'referenced_files':scanned,'inaccessible_files':inaccessible})

# Simple cron matching for window selection.
def field_match(expr, value, minimum, maximum):
    def atom(a):
        if a=='*': return True
        if a.startswith('*/'):
            try: return (value-minimum)%int(a[2:])==0
            except: return False
        if '-' in a:
            try:
                lo,hi=map(int,a.split('-',1)); return lo<=value<=hi
            except: return False
        try: return value==int(a)
        except: return False
    return any(atom(x) for x in expr.split(','))

def cron_due(schedule, when):
    parts=schedule.split()
    if len(parts)!=5: return None
    minute,hour,dom,month,dow=parts
    vals=[(minute,when.minute,0,59),(hour,when.hour,0,23),(dom,when.day,1,31),(month,when.month,1,12),(dow,(when.weekday()+1)%7,0,7)]
    return all(field_match(*x) for x in vals)

relevant_jobs=[j for j in jobs if j['classification']=='WINDOW_CONTROL_ONLY']
unresolved_jobs=[j for j in jobs if j['classification']=='UNRESOLVED']
now=dt.datetime.now().astimezone().replace(second=0,microsecond=0)
start=now+dt.timedelta(minutes=(5-now.minute%5)%5 or 5)
chosen=None
if not unresolved_jobs:
    for offset in range(0,24*60,5):
        candidate=start+dt.timedelta(minutes=offset)
        end=candidate+dt.timedelta(minutes=20)
        conflict=False
        t=candidate-dt.timedelta(minutes=10)
        while t<=end+dt.timedelta(minutes=10):
            for job in relevant_jobs:
                due=cron_due(job['schedule'],t)
                if due is None or due:
                    conflict=True; break
            if conflict: break
            t+=dt.timedelta(minutes=1)
        if not conflict:
            chosen=(candidate,end); break

window={
    'schema_version':'1.0','phase':'TST-5D-W2B-I2F-3E-F','generated_at_local':now.isoformat(),
    'duration_minutes':20,'guard_before_minutes':10,'guard_after_minutes':10,
    'relevant_cron_job_count':len(relevant_jobs),'unresolved_cron_job_count':len(unresolved_jobs),
    'status':'CANDIDATE_WINDOW_PREPARED_NOT_APPROVED' if chosen else 'HOLD_NO_SAFE_WINDOW_OR_UNRESOLVED_CRON',
    'candidate_start_local':chosen[0].isoformat() if chosen else None,
    'candidate_end_local':chosen[1].isoformat() if chosen else None,
    'execution_allowed':False,'cron_changed':False,'timer_changed':False,
}

unresolved=sum(1 for x in classifications if x['classification']=='UNRESOLVED') + len(unresolved_jobs)
stop_targets=[x['logical_writer'] for x in classifications if x['classification']=='STOP_REQUIRED']
window_targets=['cron_daemon'] if any(x['logical_writer']=='cron_daemon' for x in classifications) else []
not_relevant=[x['logical_writer'] for x in classifications if x['classification']=='NOT_RELEVANT']

scope={
    'schema_version':'1.0','phase':'TST-5D-W2B-I2F-3E-F','status':'FREEZE_SCOPE_PREPARED_HOLD_FOR_HUMAN_REVIEW',
    'writer_freeze_execution':'HOLD','production_release_decision':'HOLD','release_status':'CANDIDATE_NOT_APPROVED',
    'stop_targets':stop_targets,'window_control_targets':window_targets,'not_relevant_targets':not_relevant,'unresolved_count':unresolved,
    'ordered_stop_sequence':[
        {'order':1,'action':'Enter the approved cron-safe maintenance window and verify no relevant cron child is running.','performed':False},
        {'order':2,'action':'Record final process, cgroup, DB/WAL/SHM stat and root open-handle inventories.','performed':False},
        {'order':3,'action':'Gracefully stop each explicitly approved STOP_REQUIRED process using its reviewed service or SIGTERM method.','targets':stop_targets,'performed':False},
        {'order':4,'action':'Verify STOP_REQUIRED processes are absent and root DB/WAL/SHM open-handle count is zero.','performed':False},
        {'order':5,'action':'Issue a freeze token before any read-only DB preflight.','performed':False},
    ],
    'ordered_restart_sequence':[
        {'order':1,'action':'After all separately approved DB/backup/rehearsal work is complete, verify production DB SHA and filesystem state.','performed':False},
        {'order':2,'action':'Restart STOP_REQUIRED targets in reverse stop order using separately approved exact commands.','targets':list(reversed(stop_targets)),'performed':False},
        {'order':3,'action':'Verify GUI/service health locally without external communication.','performed':False},
        {'order':4,'action':'Exit the maintenance window and record restart evidence.','performed':False},
    ],
    'exact_restart_command_status':'REQUIRES_HUMAN_REVIEW_OF_SYSTEMD_MEMBERSHIP_AND_STDIO',
    'process_signal_sent':False,'writer_stop_performed':False,'gui_stopped_or_restarted':False,'systemd_changed':False,'cron_changed':False,'timer_changed':False,
}

report={
    'schema_version':'1.0','phase':'TST-5D-W2B-I2F-3E-F','captured_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
    'classifications':classifications,'cron_jobs':jobs,
    'classification_counts':{c:sum(1 for x in classifications if x['classification']==c)+sum(1 for j in jobs if j['classification']==c) for c in valid_classes},
    'persistent_process_candidate_count':sum(len(x.get('current_pids',[])) for x in classifications),
    'root_open_handle_count':root['root_proc_scan']['open_handle_count'],
    'root_open_handles':root['root_proc_scan']['open_handles'],
    'root_proc_inaccessible_or_vanished_count':root['root_proc_scan']['inaccessible_or_vanished_proc_count'],
    'writer_freeze_execution':'HOLD','production_database_opened':False,'sql_executed':False,'process_signal_sent':False,'writer_stop_performed':False,
}
out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
window_out.write_text(json.dumps(window,sort_keys=True,indent=2)+'\n')
scope_out.write_text(json.dumps(scope,sort_keys=True,indent=2)+'\n')
PY

python3 - "$PACKET_ROOT/root-proc-readonly-inspection.json" "$PACKET_ROOT/process-and-cron-attribution.json" "$PACKET_ROOT/freeze-window-plan.json" "$PACKET_ROOT/stop-restart-scope-plan.json" "$PACKET_ROOT/packet-semantic-validation.json" <<'PY'
import json, sys
from pathlib import Path
root=json.loads(Path(sys.argv[1]).read_text())
a=json.loads(Path(sys.argv[2]).read_text())
w=json.loads(Path(sys.argv[3]).read_text())
s=json.loads(Path(sys.argv[4]).read_text())
assert root['root_privileged_readonly_inspection'] is True
assert root['production_database_opened'] is False
assert root['sql_executed'] is False
logical={x['logical_writer']:x for x in a['classifications']}
assert set(logical)=={'cron_daemon','uvicorn_8000','ebook_gui_8765'}
assert logical['cron_daemon']['classification']=='WINDOW_CONTROL_ONLY'
assert logical['ebook_gui_8765']['classification'] in {'STOP_REQUIRED','UNRESOLVED'}
assert logical['uvicorn_8000']['classification'] in {'STOP_REQUIRED','NOT_RELEVANT','UNRESOLVED'}
assert all(x['classification'] in {'STOP_REQUIRED','WINDOW_CONTROL_ONLY','NOT_RELEVANT','UNRESOLVED'} for x in a['classifications'])
assert s['writer_freeze_execution']=='HOLD'
assert s['process_signal_sent'] is False
assert s['writer_stop_performed'] is False
assert w['execution_allowed'] is False
report={
 'schema_version':'1.0','result':'PASS_3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PREPARATION_SEMANTIC_VALIDATION',
 'root_privileged_proc_inspection':True,'root_open_handle_count':a['root_open_handle_count'],
 'cron_classification':logical['cron_daemon']['classification'],
 'gui_classification':logical['ebook_gui_8765']['classification'],
 'uvicorn_classification':logical['uvicorn_8000']['classification'],
 'unresolved_count':s['unresolved_count'],'freeze_window_status':w['status'],
 'writer_freeze_execution':'HOLD','production_database_opened':False,'sql_executed':False,'process_signal_sent':False,'writer_stop_performed':False,
 'production_release_decision':'HOLD','release_status':'CANDIDATE_NOT_APPROVED'
}
Path(sys.argv[5]).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
PY

cat > "$PACKET_ROOT/README.md" <<EOF
# 3E-F Writer Attribution and Freeze Scope Preparation

Status: READ-ONLY PREPARATION ONLY — WRITER FREEZE EXECUTION IS NOT APPROVED.

This packet records root-privileged /proc attribution, exact DB/WAL/SHM open-handle inspection,
cron job separation, uvicorn and GUI reachability analysis, classifications, a candidate freeze
window, and stop/restart ordering. No process signal, stop, restart, cron/systemd change, SQLite
connection, SQL, backup, restore, migration, Git operation, deployment, network call, Slack Worker
start, or production approval was performed.
EOF

cat > "$PACKET_ROOT/safety-boundary.json" <<'JSON'
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3E-F",
  "production_database_opened": false,
  "production_database_sql_connection_used": false,
  "sql_executed": false,
  "process_signal_sent": false,
  "writer_stop_performed": false,
  "gui_stopped_or_restarted": false,
  "systemctl_stop_start_restart_executed": false,
  "systemd_changed": false,
  "cron_changed": false,
  "timer_changed": false,
  "backup_created": false,
  "restore_executed": false,
  "migration_executed": false,
  "production_manifest_modified": false,
  "source_modified": false,
  "test_modified": false,
  "git_add_performed": false,
  "git_commit_performed": false,
  "deployment_performed": false,
  "external_network_used": false,
  "slack_worker_started": false,
  "production_approval_created": false,
  "production_release_approved": false,
  "writer_freeze_execution": "HOLD",
  "production_release_decision": "HOLD",
  "release_status": "CANDIDATE_NOT_APPROVED"
}
JSON

git status --short -- "$PROMOTED_TEST_PATH" > "$PACKET_ROOT/promoted-test-git-status.txt"

python3 - "$PACKET_ROOT/protected-sha-after.json" <<'PY'
import hashlib, json, stat, sys
from pathlib import Path
paths = [
    Path('/home/deploy/ai_media_os/data/database/ebook_affiliate.db'),
    Path('/home/deploy/ai_media_os/config/slack_worker_release_source_manifest.json'),
    Path('/home/deploy/ai_media_os/app/db/repositories/workflow_state_repository.py'),
    Path('/home/deploy/ai_media_os/migrations/versions/00241611109d_add_unique_wordpress_post_id.py'),
    Path('/home/deploy/ai_media_os/scripts/run_slack_approval_socket.py'),
    Path('/home/deploy/ai_media_os/tests/test_slack_approval_socket_hold_remediation_offline.py'),
]
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
items=[]
for p in paths:
    s=p.stat(); items.append({'path':str(p),'sha256':h(p),'size':s.st_size,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns,'mode':f'{stat.S_IMODE(s.st_mode):04o}'})
Path(sys.argv[1]).write_text(json.dumps({'captured_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'items':items,'production_database_opened':False,'sql_executed':False},sort_keys=True,indent=2)+'\n')
PY
cmp -s "$PACKET_ROOT/protected-sha-before.json" "$PACKET_ROOT/protected-sha-after.json" || {
  python3 - "$PACKET_ROOT/protected-sha-before.json" "$PACKET_ROOT/protected-sha-after.json" <<'PY'
import json,sys
from pathlib import Path
b=json.loads(Path(sys.argv[1]).read_text()); a=json.loads(Path(sys.argv[2]).read_text())
b.pop('captured_at_utc',None); a.pop('captured_at_utc',None)
if b!=a: raise SystemExit('PROTECTED_SHA_OR_STAT_CHANGED')
PY
}

python3 - "$PACKET_ROOT" "$PACKET_ROOT/packet-manifest.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for p in sorted(root.iterdir(),key=lambda p:p.name):
    if not p.is_file() or p==out: continue
    files.append({'name':p.name,'sha256':h(p),'size_bytes':p.stat().st_size})
obj={'schema_version':'1.0','phase':'TST-5D-W2B-I2F-3E-F','result':'PASS_3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PACKET_GENERATED','status':'READONLY_PREPARATION_ONLY_WRITER_FREEZE_NOT_APPROVED','packet_file_count_excluding_manifest':len(files),'packet_files':files,'writer_freeze_execution':'HOLD','production_release_decision':'HOLD','release_status':'CANDIDATE_NOT_APPROVED'}
out.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
PY

python3 - "$PACKET_ROOT/process-and-cron-attribution.json" "$PACKET_ROOT/packet-semantic-validation.json" "$PACKET_ROOT/freeze-window-plan.json" "$PACKET_ROOT/stop-restart-scope-plan.json" "$EVIDENCE_ROOT/result.json" "$EVIDENCE_ROOT_REL" <<'PY'
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
attr=json.loads(Path(sys.argv[1]).read_text()); val=json.loads(Path(sys.argv[2]).read_text()); window=json.loads(Path(sys.argv[3]).read_text()); scope=json.loads(Path(sys.argv[4]).read_text())
classes={x['logical_writer']:x['classification'] for x in attr['classifications']}
def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
obj={
 'schema_version':'1.0','phase':'TST-5D-W2B-I2F-3E-F','completed_at_utc':datetime.now(timezone.utc).isoformat(),
 'result':'PASS_W2B_I2F3E_F_WRITER_ATTRIBUTION_FREEZE_SCOPE_PREPARATION_READY','evidence_root':sys.argv[6],
 'attribution':{'cron':classes['cron_daemon'],'uvicorn':classes['uvicorn_8000'],'ebook_gui':classes['ebook_gui_8765'],'unresolved_count':scope['unresolved_count'],'root_open_handle_count':attr['root_open_handle_count']},
 'freeze_window':window,'writer_freeze_execution':'HOLD','production_release_decision':'HOLD','release_status':'CANDIDATE_NOT_APPROVED',
 'next_gate':'HUMAN_REVIEW_3E_F_WRITER_ATTRIBUTION_AND_FREEZE_SCOPE_PACKET',
 'execution':{'process_signal_sent':False,'writer_stop_performed':False,'gui_stopped_or_restarted':False,'systemd_changed':False,'cron_changed':False,'timer_changed':False,'production_database_opened':False,'production_database_sql_connection_used':False,'sql_executed':False,'backup_created':False,'restore_executed':False,'migration_executed':False,'production_manifest_modified':False,'source_modified':False,'test_modified':False,'git_add_performed':False,'git_commit_performed':False,'deployment_performed':False,'external_network_used':False,'slack_worker_started':False,'production_approval_created':False,'production_release_approved':False},
 'semantic_validation':val['result']
}
Path(sys.argv[5]).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
PY

find "$PACKET_ROOT" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_ROOT/packet-sha-manifest.txt"
find "$EVIDENCE_ROOT" -type f ! -name 'evidence-manifest.txt' ! -name 'console-snapshot.txt' -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_ROOT/evidence-manifest.txt"

ATTR="$PACKET_ROOT/process-and-cron-attribution.json"
VAL="$PACKET_ROOT/packet-semantic-validation.json"
WINDOW="$PACKET_ROOT/freeze-window-plan.json"
RESULT_JSON="$EVIDENCE_ROOT/result.json"

python3 - "$ATTR" "$VAL" "$WINDOW" "$RESULT_JSON" <<'PY'
import json,sys
from pathlib import Path
a=json.loads(Path(sys.argv[1]).read_text()); v=json.loads(Path(sys.argv[2]).read_text()); w=json.loads(Path(sys.argv[3]).read_text()); r=json.loads(Path(sys.argv[4]).read_text())
classes={x['logical_writer']:x['classification'] for x in a['classifications']}
print(f"RESULT={r['result']}")
print(f"ROOT_DB_WAL_SHM_OPEN_HANDLE_COUNT={a['root_open_handle_count']}")
print(f"CRON_CLASSIFICATION={classes['cron_daemon']}")
print(f"UVICORN_CLASSIFICATION={classes['uvicorn_8000']}")
print(f"EBOOK_GUI_CLASSIFICATION={classes['ebook_gui_8765']}")
print(f"UNRESOLVED_CLASSIFICATION_COUNT={v['unresolved_count']}")
print(f"FREEZE_WINDOW_STATUS={w['status']}")
print(f"FREEZE_WINDOW_START_LOCAL={w.get('candidate_start_local')}")
print(f"FREEZE_WINDOW_END_LOCAL={w.get('candidate_end_local')}")
print("ROOT_PRIVILEGED_PROC_INSPECTION=true")
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
print("NEXT_GATE=HUMAN_REVIEW_3E_F_WRITER_ATTRIBUTION_AND_FREEZE_SCOPE_PACKET")
PY

printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_ROOT_REL"
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'PACKET_FILE_COUNT=%s\n' "$(find "$PACKET_ROOT" -maxdepth 1 -type f | wc -l)"
printf 'RESULT_SHA=%s\n' "$(sha_of "$RESULT_JSON")"
printf 'PACKET_MANIFEST_SHA=%s\n' "$(sha_of "$PACKET_ROOT/packet-manifest.json")"
printf 'PACKET_SEMANTIC_VALIDATION_SHA=%s\n' "$(sha_of "$VAL")"
printf 'EVIDENCE_MANIFEST_SHA=%s\n' "$(sha_of "$EVIDENCE_ROOT/evidence-manifest.txt")"

# Finalize evidence read-only after every evidence artifact and hash has been written.
# console-snapshot.txt remains excluded from the evidence manifest because this live tee
# continues appending until the script exits.
find "$EVIDENCE_ROOT" -type f -exec chmod 0444 {} +
find "$EVIDENCE_ROOT" -type d -exec chmod 0555 {} +

printf 'SCRIPT_EXIT_CODE=0\n'
