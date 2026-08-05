#!/usr/bin/env python3
"""Build a non-deployable Slack worker release rebinding candidate under /tmp.

This control-plane tool never updates the current release manifest or any
downstream policy.  It reconstructs the local Python dependency closure,
separates review units, and models the downstream SHA rebinding order.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config/slack_worker_release_rebinding_policy.json"
PRODUCTION_MANIFEST_PATH = (
    REPO_ROOT / "config/slack_worker_release_source_manifest.json"
)
DEFAULT_OUTPUT_DIRECTORY = Path(
    "/tmp/slack-worker-release-rebinding-candidate"
)
TMP_ROOT = Path("/tmp").resolve()


class CandidateBlocked(RuntimeError):
    """Raised when a fail-closed candidate precondition is not satisfied."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_read_regular(path: Path) -> bytes:
    """Read a single regular, single-link file descriptor without following it."""

    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise CandidateBlocked(f"SAFE_OPEN_FAILED:{path}:{exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CandidateBlocked(f"SOURCE_NOT_REGULAR:{path}")
        if before.st_nlink != 1:
            raise CandidateBlocked(f"SOURCE_LINK_COUNT_INVALID:{path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after:
            raise CandidateBlocked(f"SOURCE_REPLACED_DURING_READ:{path}")
        value = b"".join(chunks)
        if len(value) != before.st_size:
            raise CandidateBlocked(f"SOURCE_SIZE_CHANGED_DURING_READ:{path}")
        return value
    finally:
        os.close(descriptor)


def sha256_path(path: Path) -> str:
    return sha256_bytes(safe_read_regular(path))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CandidateBlocked(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            safe_read_regular(path).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateBlocked(f"JSON_INVALID:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise CandidateBlocked(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def validate_relative_source_path(repo_root: Path, relative: str) -> Path:
    if not relative or "\\" in relative:
        raise CandidateBlocked(f"SOURCE_PATH_INVALID:{relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute():
        raise CandidateBlocked(f"SOURCE_PATH_ABSOLUTE:{relative}")
    if ".." in pure.parts or any(part in {"", "."} for part in pure.parts):
        raise CandidateBlocked(f"SOURCE_PATH_TRAVERSAL:{relative}")
    candidate = repo_root.joinpath(*pure.parts)
    if not candidate.exists():
        raise CandidateBlocked(f"SOURCE_MISSING:{relative}")
    if candidate.is_symlink():
        raise CandidateBlocked(f"SOURCE_SYMLINK:{relative}")
    resolved_root = repo_root.resolve()
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CandidateBlocked(f"SOURCE_OUTSIDE_ROOT:{relative}") from exc
    cursor = candidate.parent
    while cursor != resolved_root:
        if cursor.is_symlink():
            raise CandidateBlocked(f"SOURCE_SYMLINK_ANCESTRY:{relative}")
        cursor = cursor.parent
    safe_read_regular(candidate)
    return candidate


def validate_source_paths(repo_root: Path, paths: Iterable[str]) -> list[str]:
    ordered = list(paths)
    if len(ordered) != len(set(ordered)):
        raise CandidateBlocked("DUPLICATE_SOURCE_PATH")
    for relative in ordered:
        validate_relative_source_path(repo_root, relative)
    return sorted(ordered)


def module_for_path(repo_root: Path, path: Path) -> str:
    relative = path.relative_to(repo_root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def resolve_module(repo_root: Path, module: str) -> Path | None:
    if not module:
        return None
    relative = Path(*module.split("."))
    module_file = repo_root / relative.with_suffix(".py")
    if module_file.is_file():
        return module_file
    package_file = repo_root / relative / "__init__.py"
    if package_file.is_file():
        return package_file
    return None


class ImportCollector(ast.NodeVisitor):
    def __init__(self, module: str, package_module: str) -> None:
        self.module = module
        self.package_module = package_module
        self.imports: list[dict[str, Any]] = []
        self.unresolved_dynamic: list[dict[str, Any]] = []
        self.subprocess_calls: list[dict[str, Any]] = []
        self._type_only = 0
        self._optional = 0
        self._function_depth = 0

    def _kind(self) -> str:
        if self._type_only:
            return "TYPE_CHECK_ONLY"
        if self._optional:
            return "OPTIONAL_IMPORT"
        if self._function_depth:
            return "LAZY_RUNTIME_IMPORT"
        return "DIRECT_RUNTIME_IMPORT"

    def _record(self, module: str, node: ast.AST) -> None:
        if module:
            self.imports.append(
                {
                    "module": module,
                    "kind": self._kind(),
                    "line": getattr(node, "lineno", None),
                }
            )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._record(alias.name, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            package = self.package_module.split(".") if self.package_module else []
            keep = len(package) - (node.level - 1)
            base_parts = package[: max(keep, 0)]
            if node.module:
                base_parts.extend(node.module.split("."))
            base = ".".join(base_parts)
        else:
            base = node.module or ""
        self._record(base, node)
        for alias in node.names:
            if alias.name != "*":
                self._record(".".join(part for part in (base, alias.name) if part), node)

    @staticmethod
    def _is_type_checking(test: ast.AST) -> bool:
        return (
            isinstance(test, ast.Name)
            and test.id == "TYPE_CHECKING"
        ) or (
            isinstance(test, ast.Attribute)
            and isinstance(test.value, ast.Name)
            and test.value.id == "typing"
            and test.attr == "TYPE_CHECKING"
        )

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        if self._is_type_checking(node.test):
            self._type_only += 1
            for child in node.body:
                self.visit(child)
            self._type_only -= 1
        else:
            for child in node.body:
                self.visit(child)
        for child in node.orelse:
            self.visit(child)

    def visit_Try(self, node: ast.Try) -> None:
        import_optional = any(
            handler.type is None
            or (
                isinstance(handler.type, ast.Name)
                and handler.type.id in {"ImportError", "ModuleNotFoundError"}
            )
            for handler in node.handlers
        )
        if import_optional:
            self._optional += 1
        for child in node.body:
            self.visit(child)
        if import_optional:
            self._optional -= 1
        for handler in node.handlers:
            self.visit(handler)
        for child in node.orelse + node.finalbody:
            self.visit(child)

    def _visit_function(self, node: ast.AST) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Call(self, node: ast.Call) -> None:
        target = ""
        if isinstance(node.func, ast.Name):
            target = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            target = f"{node.func.value.id}.{node.func.attr}"
        if target in {"importlib.import_module", "__import__"}:
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(
                node.args[0].value, str
            ):
                self._record(node.args[0].value, node)
            else:
                self.unresolved_dynamic.append(
                    {
                        "module": self.module,
                        "line": getattr(node, "lineno", None),
                        "call": target,
                    }
                )
        if target in {
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "os.system",
            "os.popen",
        }:
            self.subprocess_calls.append(
                {
                    "module": self.module,
                    "line": getattr(node, "lineno", None),
                    "call": target,
                }
            )
        self.generic_visit(node)


def analyze_module_imports(repo_root: Path, path: Path) -> dict[str, Any]:
    source = safe_read_regular(path)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise CandidateBlocked(f"SOURCE_AST_INVALID:{path}:{exc}") from exc
    module = module_for_path(repo_root, path)
    package_module = module if path.name == "__init__.py" else module.rpartition(".")[0]
    collector = ImportCollector(module, package_module)
    collector.visit(tree)
    return {
        "module": module,
        "imports": collector.imports,
        "unresolved_dynamic_dependencies": collector.unresolved_dynamic,
        "subprocess_calls": collector.subprocess_calls,
    }


def build_dependency_closure(
    repo_root: Path,
    entrypoints: Iterable[str],
) -> dict[str, Any]:
    queue = validate_source_paths(repo_root, entrypoints)
    visited: set[str] = set()
    records: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    external: dict[str, set[str]] = {}
    unresolved: list[dict[str, Any]] = []
    subprocess_calls: list[dict[str, Any]] = []
    while queue:
        relative = queue.pop(0)
        if relative in visited:
            continue
        visited.add(relative)
        path = validate_relative_source_path(repo_root, relative)
        analysis = analyze_module_imports(repo_root, path)
        records.append(
            {
                "path": relative,
                "module": analysis["module"],
                "sha256": sha256_path(path),
            }
        )
        unresolved.extend(analysis["unresolved_dynamic_dependencies"])
        subprocess_calls.extend(analysis["subprocess_calls"])
        for imported in analysis["imports"]:
            resolved = resolve_module(repo_root, imported["module"])
            if resolved is None:
                parts = imported["module"].split(".")
                parent_is_local = any(
                    resolve_module(repo_root, ".".join(parts[:index])) is not None
                    for index in range(len(parts) - 1, 0, -1)
                )
                if parent_is_local:
                    # ``from local.package import ClassName`` records the
                    # imported symbol as a possible submodule.  A resolvable
                    # parent proves that an unresolved suffix is a symbol,
                    # not a missing external dependency.
                    continue
                top = imported["module"].split(".", 1)[0]
                if top in {"app", "scripts"}:
                    unresolved.append(
                        {
                            "module": analysis["module"],
                            "line": imported["line"],
                            "call": "UNRESOLVED_LOCAL_IMPORT",
                            "dependency": imported["module"],
                        }
                    )
                    continue
                external.setdefault(top, set()).add(imported["kind"])
                continue
            target = resolved.relative_to(repo_root).as_posix()
            edge = {
                "from": relative,
                "to": target,
                "module": imported["module"],
                "kind": imported["kind"],
                "line": imported["line"],
            }
            if edge not in edges:
                edges.append(edge)
            if imported["kind"] != "TYPE_CHECK_ONLY" and target not in visited:
                queue.append(target)
        queue.sort()
    result = {
        "schema_version": "slack_worker_runtime_dependency_closure_v1",
        "analysis": "PYTHON_AST_WITH_EXISTING_RUNTIME_IMPORT_SMOKE_CONTRACT",
        "entrypoints": sorted(set(entrypoints)),
        "entrypoint_evidence": (
            load_json(POLICY_PATH).get("runtime_entrypoint_evidence", [])
            if repo_root.resolve() == REPO_ROOT.resolve()
            else []
        ),
        "source_count": len(records),
        "sources": sorted(records, key=lambda item: item["path"]),
        "import_edges": sorted(
            edges,
            key=lambda item: (
                item["from"], item["to"], item["kind"], item["line"] or 0
            ),
        ),
        "external_imports": [
            {"module": name, "kinds": sorted(kinds)}
            for name, kinds in sorted(external.items())
        ],
        "subprocess_calls": sorted(
            subprocess_calls,
            key=lambda item: (item["module"], item["line"] or 0),
        ),
        "unresolved_dynamic_dependencies": sorted(
            unresolved,
            key=lambda item: (item["module"], item["line"] or 0),
        ),
        "existing_runtime_import_smoke": {
            "policy_path": "config/slack_worker_runtime_import_smoke_component_policy.json",
            "result": "USED_AS_EXISTING_DECLARED_MODULE_BASELINE_NOT_EXECUTED",
        },
    }
    result["dependency_closure_sha256"] = sha256_bytes(canonical_bytes(result))
    return result


def require_resolved_dependencies(closure: dict[str, Any]) -> None:
    if closure["unresolved_dynamic_dependencies"]:
        raise CandidateBlocked("UNRESOLVED_DYNAMIC_DEPENDENCY")


def json_leaves(value: object, prefix: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from json_leaves(child, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from json_leaves(child, f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


def artifact_schema(value: dict[str, Any]) -> str:
    schema = value.get("schema_version")
    if schema is not None:
        return str(schema)
    if value.get("phase") is not None:
        return f"PHASE_ARTIFACT:{value['phase']}"
    return "UNVERSIONED_JSON_OBJECT"


def discover_downstream_chain(
    repo_root: Path,
    policy: dict[str, Any],
    current_manifest_sha: str,
    current_release_id: str,
) -> list[dict[str, Any]]:
    control_policy_relative = POLICY_PATH.relative_to(repo_root).as_posix()
    parsed: dict[str, dict[str, Any]] = {}
    for path in sorted((repo_root / "config").glob("slack_worker*.json")):
        relative = path.relative_to(repo_root).as_posix()
        if relative == control_policy_relative:
            continue
        parsed[relative] = load_json(path)
    for relative in policy["immutable_direct_evidence"]:
        parsed[relative] = load_json(repo_root / relative)

    direct_policy = {
        item["path"]: item["binding_kind"]
        for item in policy["direct_policy_binders"]
    }
    immutable = set(policy["immutable_direct_evidence"])
    current_shas = {
        relative: sha256_path(repo_root / relative)
        for relative in parsed
    }
    nodes: dict[str, dict[str, Any]] = {}
    for relative, kind in direct_policy.items():
        if relative not in parsed:
            raise CandidateBlocked(f"DIRECT_BINDER_MISSING:{relative}")
        fields = [
            field
            for field, value in json_leaves(parsed[relative])
            if current_manifest_sha == value
            or current_release_id in value
        ]
        nodes[relative] = {
            "path": relative,
            "depth": 1,
            "artifact_type": "MUTABLE_PRODUCTION_POLICY",
            "binding_kind": kind,
            "binding_fields": sorted(fields),
            "current_artifact_sha256": current_shas[relative],
            "schema": artifact_schema(parsed[relative]),
            "mutable": True,
            "approval_requirement": "SLACK_WORKER_RELEASE_REBINDING_REVIEW_REQUIRED",
            "production_execution_impact": "MAY_CHANGE_FUTURE_RELEASE_OR_AUTHORIZATION_VALIDATION",
        }
    for relative in immutable:
        fields = [
            field
            for field, value in json_leaves(parsed[relative])
            if value == current_manifest_sha
        ]
        nodes[relative] = {
            "path": relative,
            "depth": 1,
            "artifact_type": "IMMUTABLE_HISTORICAL_EVIDENCE",
            "binding_kind": "EXACT_MANIFEST_FILE_SHA256",
            "binding_fields": sorted(fields),
            "current_artifact_sha256": current_shas[relative],
            "schema": artifact_schema(parsed[relative]),
            "mutable": False,
            "approval_requirement": "MUST_NOT_BE_REWRITTEN",
            "production_execution_impact": "HISTORICAL_EVIDENCE_ONLY",
        }

    frontier = {nodes[path]["current_artifact_sha256"] for path in nodes}
    depth = 1
    while frontier:
        discovered: list[str] = []
        for relative, value in parsed.items():
            if relative in nodes:
                continue
            fields = [
                field
                for field, leaf in json_leaves(value)
                if leaf in frontier
            ]
            if not fields:
                continue
            nodes[relative] = {
                "path": relative,
                "depth": depth + 1,
                "artifact_type": "MUTABLE_PRODUCTION_POLICY",
                "binding_kind": "UPSTREAM_ARTIFACT_SHA256",
                "binding_fields": sorted(fields),
                "current_artifact_sha256": current_shas[relative],
                "schema": artifact_schema(value),
                "mutable": True,
                "approval_requirement": "SLACK_WORKER_RELEASE_REBINDING_REVIEW_REQUIRED",
                "production_execution_impact": "MAY_CHANGE_FUTURE_RELEASE_OR_AUTHORIZATION_VALIDATION",
            }
            discovered.append(relative)
        if not discovered:
            break
        frontier = {current_shas[path] for path in discovered}
        depth += 1

    sha_owner = {
        node["current_artifact_sha256"]: relative
        for relative, node in nodes.items()
    }
    for relative, node in nodes.items():
        identity_fields = {
            field
            for field, value in json_leaves(parsed[relative])
            if current_release_id in value
        }
        node["binding_fields"] = sorted(
            set(node["binding_fields"]) | identity_fields
        )
        upstream = sorted(
            {
                sha_owner[leaf]
                for _, leaf in json_leaves(parsed[relative])
                if leaf in sha_owner and sha_owner[leaf] != relative
            }
        )
        if node["depth"] == 1:
            upstream.insert(0, policy["current_manifest"]["path"])
        node["upstream_dependencies"] = sorted(set(upstream))
        node["downstream_dependencies"] = []
        node["required_update_order"] = node["depth"]
        node["atomic_write_requirement"] = node["mutable"]
        node["rollback_source"] = {
            "path": relative,
            "sha256": node["current_artifact_sha256"],
        }
    for relative, node in nodes.items():
        for upstream in node["upstream_dependencies"]:
            if upstream in nodes:
                nodes[upstream]["downstream_dependencies"].append(relative)
    for node in nodes.values():
        node["downstream_dependencies"] = sorted(
            set(node["downstream_dependencies"])
        )
    return sorted(nodes.values(), key=lambda item: (item["depth"], item["path"]))


def finalize_rebinding_graph(chain: list[dict[str, Any]]) -> str:
    """Assign a deterministic topological order and hash the stable graph."""

    paths = {item["path"] for item in chain}
    indegree = {path: 0 for path in paths}
    outgoing = {path: set() for path in paths}
    for item in chain:
        for upstream in item["upstream_dependencies"]:
            if upstream in paths and item["path"] not in outgoing[upstream]:
                outgoing[upstream].add(item["path"])
                indegree[item["path"]] += 1
    queue = sorted(path for path, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while queue:
        path = queue.pop(0)
        order.append(path)
        for downstream in sorted(outgoing[path]):
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                queue.append(downstream)
                queue.sort()
    if len(order) != len(paths):
        raise CandidateBlocked("DOWNSTREAM_REBINDING_GRAPH_CYCLE")
    order_by_path = {path: index + 1 for index, path in enumerate(order)}
    for item in chain:
        item["required_update_order"] = order_by_path[item["path"]]
    graph_contract = {
        "schema_version": "slack_worker_rebinding_graph_contract_v1",
        "artifacts": [
            {
                key: item[key]
                for key in (
                    "path",
                    "depth",
                    "mutable",
                    "binding_kind",
                    "binding_fields",
                    "current_artifact_sha256",
                    "upstream_dependencies",
                    "downstream_dependencies",
                    "required_update_order",
                    "atomic_write_requirement",
                    "rollback_source",
                )
            }
            for item in sorted(chain, key=lambda value: value["path"])
        ],
    }
    return sha256_bytes(canonical_bytes(graph_contract))


def deep_replace(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {key: deep_replace(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [deep_replace(child, replacements) for child in value]
    if isinstance(value, str):
        result = value
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result
    return value


def review_unit_records(
    policy: dict[str, Any], source_sha: dict[str, str]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for unit in policy["review_units"]:
        value = dict(unit)
        value["source_sha256"] = {
            path: source_sha[path]
            for path in sorted(unit["sources"])
        }
        value["review_unit_sha256"] = sha256_bytes(canonical_bytes(value))
        records.append(value)
    return records


def source_review_mapping(review_units: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for unit in review_units:
        for path in unit["sources"]:
            result[path] = {
                "review_unit": unit["unit"],
                "change_category": unit["change_category"],
                "review_status": unit["approval_status"],
            }
    return result


def build_candidate_documents(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    policy = load_json(POLICY_PATH)
    current_manifest = load_json(PRODUCTION_MANIFEST_PATH)
    current_manifest_sha = sha256_path(PRODUCTION_MANIFEST_PATH)
    if current_manifest_sha != policy["current_manifest"]["sha256"]:
        raise CandidateBlocked("CURRENT_MANIFEST_POLICY_BINDING_MISMATCH")
    closure = build_dependency_closure(repo_root, policy["runtime_entrypoints"])
    require_resolved_dependencies(closure)
    unresolved = closure["unresolved_dynamic_dependencies"]

    current_entries = {
        item["path"]: item
        for item in current_manifest["source_files"]
    }
    closure_paths = {item["path"] for item in closure["sources"]}
    candidate_paths = validate_source_paths(
        repo_root, set(current_entries) | closure_paths
    )
    source_sha: dict[str, str] = {}
    source_size: dict[str, int] = {}
    source_mode: dict[str, str] = {}
    for relative in candidate_paths:
        path = validate_relative_source_path(repo_root, relative)
        payload = safe_read_regular(path)
        source_sha[relative] = sha256_bytes(payload)
        source_size[relative] = len(payload)
        source_mode[relative] = f"{stat.S_IMODE(path.stat().st_mode):04o}"

    units = review_unit_records(policy, source_sha)
    review_by_source = source_review_mapping(units)
    sources: list[dict[str, Any]] = []
    source_audit: list[dict[str, Any]] = []
    for relative in candidate_paths:
        baseline = current_entries.get(relative)
        matched = bool(
            baseline
            and baseline["sha256"] == source_sha[relative]
            and baseline["size"] == source_size[relative]
        )
        change = "ADDED" if baseline is None else ("UNCHANGED" if matched else "MODIFIED")
        review = review_by_source.get(
            relative,
            {
                "review_unit": None,
                "change_category": "BASELINE_UNCHANGED",
                "review_status": "BASELINE_MATCHED_NO_NEW_REVIEW",
            },
        )
        classification = (
            "REQUIRED_SAFETY_SOURCE"
            if relative in {
                "app/db/access_guard.py",
                "app/db/config.py",
                "app/db/session.py",
            }
            else "REQUIRED_RUNTIME_SOURCE"
        )
        sources.append(
            {
                "path": relative,
                "sha256": source_sha[relative],
                "size": source_size[relative],
                "mode": source_mode[relative],
                "source_classification": classification,
                **review,
            }
        )
        source_audit.append(
            {
                "path": relative,
                "manifest_sha256": baseline["sha256"] if baseline else None,
                "current_sha256": source_sha[relative],
                "matched": matched,
                "runtime_closure_member": relative in closure_paths,
                "inclusion_reason": classification,
                "change_category": review["change_category"],
                "review_status": review["review_status"],
                "candidate_decision": "RETAIN" if baseline else "ADD_REQUIRED_SOURCE",
                "change": change,
            }
        )

    chain = discover_downstream_chain(
        repo_root,
        policy,
        current_manifest_sha,
        current_manifest["release_id_candidate"],
    )
    graph_contract_sha = finalize_rebinding_graph(chain)

    candidate_content: dict[str, Any] = {
        "schema_version": "slack_worker_release_manifest_candidate_v1",
        "phase": policy["phase"],
        "release_status": "CANDIDATE_NOT_APPROVED",
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "production_approval_created": False,
        "formal_release_id_issued": False,
        "current_manifest": {
            "path": policy["current_manifest"]["path"],
            "sha256": current_manifest_sha,
            "release_id": current_manifest["release_id_candidate"],
        },
        "control_policy_sha256": sha256_path(POLICY_PATH),
        "validator_contract": {
            "contract_status": "HARDENED_DB_SAFE_TST_5B",
            "expected_candidate_validation_result": (
                "PASS_CANDIDATE_NOT_APPROVED"
            ),
            "files": [
                {
                    "path": relative,
                    "sha256": sha256_path(repo_root / relative),
                }
                for relative in (
                    "scripts/lib/secure_release_file_reader.py",
                    "scripts/validate_slack_worker_release_bundle_contract.py",
                    "scripts/validate_slack_worker_release_manifest_candidate.py",
                    "scripts/build_slack_worker_release_manifest_candidate.py",
                )
            ],
        },
        "downstream_rebinding_plan_binding": {
            "schema_version": "slack_worker_rebinding_graph_contract_v1",
            "rebinding_graph_contract_sha256": graph_contract_sha,
            "total_rebinding_chain_count": len(chain),
            "downstream_candidate_count": sum(
                item["mutable"] for item in chain
            ),
            "immutable_evidence_excluded": sum(
                not item["mutable"] for item in chain
            ),
        },
        "dependency_closure_sha256": closure["dependency_closure_sha256"],
        "source_file_count": len(sources),
        "source_files": sources,
        "review_units": units,
        "review_incomplete_source_count": sum(
            item["review_status"] == "NOT_APPROVED" for item in sources
        ),
        "unresolved_dynamic_dependencies": unresolved,
        "wheel_baseline": {
            "source_manifest_sha256": current_manifest_sha,
            "requirements_hash_lock": current_manifest["requirements_hash_lock"],
            "wheel_count": current_manifest["wheel_count"],
            "wheels": current_manifest["wheels"],
        },
        "source_audit": source_audit,
        "dependency_scope_classification": {
            "REQUIRED_RUNTIME_SOURCE": [
                item["path"]
                for item in sources
                if item["source_classification"] == "REQUIRED_RUNTIME_SOURCE"
            ],
            "REQUIRED_SAFETY_SOURCE": [
                item["path"]
                for item in sources
                if item["source_classification"] == "REQUIRED_SAFETY_SOURCE"
            ],
            "OPTIONAL_RUNTIME_SOURCE": [],
            "TEST_ONLY_SOURCE": [],
            "EVIDENCE_ONLY_SOURCE": [],
            "NOT_IN_RELEASE_SCOPE": [],
            "UNRESOLVED_DYNAMIC_DEPENDENCY": unresolved,
        },
        "governance": {
            "human_review_required": True,
            "production_review_created": False,
            "production_manifest_modified": False,
            "production_downstream_artifacts_modified": False,
            "slack_network_used": False,
            "sensitive_content_read": False,
            "production_database_accessed": False,
        },
    }
    content_sha = sha256_bytes(canonical_bytes(candidate_content))
    candidate = {
        "candidate_id": f"slack-worker-CANDIDATE-NOT-APPROVED-{content_sha[:12]}",
        "candidate_manifest_content_sha256": content_sha,
        **candidate_content,
    }
    candidate_payload = pretty_bytes(candidate)
    candidate_file_sha = sha256_bytes(candidate_payload)

    parsed_chain = {
        item["path"]: load_json(repo_root / item["path"])
        for item in chain
    }
    candidate_sha_by_path: dict[str, str] = {}
    for item in chain:
        if not item["mutable"]:
            item["candidate_action"] = "PRESERVE_IMMUTABLE_HISTORICAL_EVIDENCE"
            item["resulting_candidate_artifact_sha256"] = None
            continue
        replacements = {
            current_manifest_sha: candidate_file_sha,
            current_manifest["release_id_candidate"]: candidate["candidate_id"],
        }
        for upstream in item["upstream_dependencies"]:
            if upstream in candidate_sha_by_path:
                replacements[sha256_path(repo_root / upstream)] = candidate_sha_by_path[
                    upstream
                ]
        simulated = deep_replace(parsed_chain[item["path"]], replacements)
        simulated_sha = sha256_bytes(canonical_bytes(simulated))
        candidate_sha_by_path[item["path"]] = simulated_sha
        current_leaves = dict(json_leaves(parsed_chain[item["path"]]))
        candidate_leaves = dict(json_leaves(simulated))
        item["binding_updates"] = [
            {
                "field_path": field,
                "current_binding": current_leaves[field],
                "candidate_binding": candidate_leaves[field],
            }
            for field in item["binding_fields"]
        ]
        item["candidate_action"] = "PLAN_ONLY_DO_NOT_WRITE_PRODUCTION_ARTIFACT"
        item["candidate_manifest_binding"] = candidate_file_sha
        item["resulting_candidate_artifact_sha256"] = simulated_sha

    mutable_chain = [item for item in chain if item["mutable"]]
    downstream_plan: dict[str, Any] = {
        "schema_version": "slack_worker_downstream_rebinding_plan_candidate_v1",
        "phase": policy["phase"],
        "release_status": "CANDIDATE_NOT_APPROVED",
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "production_approval_created": False,
        "current_manifest_sha256": current_manifest_sha,
        "candidate_manifest_sha256": candidate_file_sha,
        "current_release_id": current_manifest["release_id_candidate"],
        "candidate_id_not_formal_release_id": candidate["candidate_id"],
        "direct_policy_binder_count": len(policy["direct_policy_binders"]),
        "direct_immutable_evidence_count": len(policy["immutable_direct_evidence"]),
        "direct_binder_count": sum(item["depth"] == 1 for item in chain),
        "indirect_binder_count": sum(item["depth"] > 1 for item in chain),
        "total_rebinding_chain_count": len(chain),
        "downstream_candidate_count": len(mutable_chain),
        "circular_dependency_detected": False,
        "rebinding_graph_contract_sha256": graph_contract_sha,
        "simulation_serialization": "CANONICAL_JSON_SORTED_KEYS_UTF8",
        "artifacts": chain,
        "governance": {
            "production_artifacts_modified": False,
            "approval_status": "NOT_APPROVED",
            "atomic_write_required_for_future_approved_rebinding": True,
        },
    }
    downstream_plan["downstream_rebinding_plan_sha256"] = sha256_bytes(
        canonical_bytes(downstream_plan)
    )
    return {
        "policy": policy,
        "current_manifest": current_manifest,
        "dependency_closure": closure,
        "candidate_manifest": candidate,
        "candidate_manifest_bytes": candidate_payload,
        "candidate_manifest_sha256": candidate_file_sha,
        "downstream_rebinding_plan": downstream_plan,
    }


def validate_output_directory(output: Path) -> Path:
    absolute = output.absolute()
    if absolute == PRODUCTION_MANIFEST_PATH.absolute():
        raise CandidateBlocked("PRODUCTION_MANIFEST_OUTPUT_REJECTED")
    try:
        absolute.relative_to(TMP_ROOT)
    except ValueError as exc:
        raise CandidateBlocked("OUTPUT_MUST_BE_BELOW_TMP") from exc
    if absolute == TMP_ROOT:
        raise CandidateBlocked("DIRECT_TMP_OUTPUT_REJECTED")
    cursor = absolute
    while cursor != TMP_ROOT:
        if cursor.is_symlink():
            raise CandidateBlocked("OUTPUT_SYMLINK_REJECTED")
        cursor = cursor.parent
    if absolute.exists() or os.path.lexists(os.fspath(absolute)):
        raise CandidateBlocked("OUTPUT_EXISTS_OVERWRITE_REJECTED")
    return absolute


def write_exclusive(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(os.fspath(path), flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def generate(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> dict[str, Any]:
    output = validate_output_directory(output_directory)
    documents = build_candidate_documents()
    output.mkdir(mode=0o700)
    closure_path = output / "dependency-closure.json"
    candidate_path = output / "candidate-manifest.json"
    downstream_path = output / "downstream-rebinding-plan.json"
    write_exclusive(
        closure_path,
        pretty_bytes(documents["dependency_closure"]),
    )
    write_exclusive(candidate_path, documents["candidate_manifest_bytes"])
    write_exclusive(
        downstream_path,
        pretty_bytes(documents["downstream_rebinding_plan"]),
    )
    directory_descriptor = os.open(os.fspath(output), os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
    return {
        "result": "PASS_DRY_RUN_CANDIDATE_NOT_APPROVED",
        "output_directory": str(output),
        "dependency_closure_path": str(closure_path),
        "candidate_manifest_path": str(candidate_path),
        "candidate_manifest_sha256": documents["candidate_manifest_sha256"],
        "downstream_rebinding_plan_path": str(downstream_path),
        "downstream_rebinding_plan_sha256": documents[
            "downstream_rebinding_plan"
        ]["downstream_rebinding_plan_sha256"],
        "production_manifest_modified": False,
        "production_downstream_artifacts_modified": False,
        "deployment_allowed": False,
        "runtime_execution_allowed": False,
        "slack_network_used": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = generate(args.output_dir)
    except CandidateBlocked as exc:
        print(f"SLACK_WORKER_RELEASE_REBINDING_CANDIDATE: BLOCKED ({exc})")
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
