#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_policy.json"
)
REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_request.example.json"
)
CONTRACT_PATH = (
    ROOT / "config/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_contract.json"
)
PACKAGE_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_k0_result.json"
)
REPORT_PATH = (
    ROOT / "reports/"
    "ls_new_batch_4g_2e_recovery_k0_"
    "template_reconciliation_report.md"
)
CONSUMPTION_PATH = (
    ROOT / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
)
RESERVED_OUTPUT_PATH = (
    ROOT / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"required file missing: {path}")

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


class SnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.classes: set[str] = set()
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._link: dict[str, Any] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        class_value = values.get("class") or ""

        self.classes.update(
            item
            for item in class_value.split()
            if item
        )

        if tag == "a":
            self._link = {
                "href": values.get("href") or "",
                "rel": values.get("rel") or "",
                "class": class_value,
                "text_parts": [],
            }

    def handle_data(self, data: str) -> None:
        compact = " ".join(data.split())

        if not compact:
            return

        self.text_parts.append(compact)

        if self._link is not None:
            self._link["text_parts"].append(compact)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link is not None:
            link = dict(self._link)
            link["text"] = " ".join(
                link.pop("text_parts")
            )
            self.links.append(link)
            self._link = None


def validate_policy(policy: dict[str, Any]) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K0",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "APPROVED_TEMPLATE_RECONCILIATION_"
            "CONTRACT_FIXATION_ONLY"
        ),
        "operation mode mismatch",
    )

    rules = policy["reconciliation_rules"]

    require(
        rules["reconciled_disclosure_text"]
        == (
            "【PR】本記事にはアフィリエイト広告を含みます。"
            "価格・配信状況は各ストアで確認してください。"
        ),
        "reconciled disclosure mismatch",
    )
    require(
        rules["post185_product_data_inheritance_allowed"]
        is False,
        "legacy product inheritance must be false",
    )
    require(
        rules["post185_url_inheritance_allowed"]
        is False,
        "legacy URL inheritance must be false",
    )

    structure = policy["resolved_structure"]

    require(
        structure["information_card_fields"]
        == [
            "作品名",
            "価格",
            "作者",
            "出版社",
            "発売日",
        ],
        "information card fields mismatch",
    )
    require(
        structure["store_button_order"]
        == [
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        ],
        "store order mismatch",
    )

    link_boundary = policy["link_boundary"]

    for field in [
        "final_affiliate_link_generation_allowed",
        "final_affiliate_link_rendering_allowed",
        "snapshot_href_reuse_allowed",
        "dmm_latest_alias_recheck_completed",
        "dmm_url_rendering_allowed",
        "dmm_final_link_use_allowed",
    ]:
        require(
            link_boundary[field] is False,
            f"{field} must remain false",
        )

    boundary = policy["execution_boundary"]

    require(
        boundary[
            "template_reconciliation_contract_fixation_allowed"
        ]
        is True,
        "contract fixation must be allowed",
    )

    for field, value in boundary.items():
        if field in {
            "template_reconciliation_contract_fixation_allowed",
            "production_status",
            "safety_state",
        }:
            continue

        require(
            value is False,
            f"{field} must remain false",
        )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "disclosure_reconciliation_verified",
        "information_card_fields_verified",
        "store_order_verified",
        "legacy_inheritance_blocked",
        "dmm_rendering_blocked",
        "final_affiliate_link_rendering_blocked",
        "execution_boundary_closed",
    ]


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    SnapshotParser,
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K0",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    for field in [
        "template_reconciliation_requested",
        "disclosure_reconciliation_requested",
        "information_card_structure_inheritance_requested",
        "store_navigation_structure_reservation_requested",
        "legacy_product_data_exclusion_requested",
        "legacy_url_exclusion_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "dmm_url_rendering_requested",
        "final_affiliate_link_rendering_requested",
        "article_content_generation_requested",
        "content_output_creation_requested",
        "authorization_consumption_requested",
        "consumption_evidence_creation_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "network_connection_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "execution_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    source_result = load_json(
        resolve_path(request["source_result_path"])
    )
    authorization_path = resolve_path(
        request["source_authorization_path"]
    )
    authorization = load_json(authorization_path)
    template_contract_path = resolve_path(
        request["template_contract_path"]
    )
    template_contract = load_json(
        template_contract_path
    )
    standard_policy_path = resolve_path(
        request["standard_policy_path"]
    )
    standard_policy = load_json(
        standard_policy_path
    )
    renderer_path = resolve_path(
        request["legacy_renderer_path"]
    )
    snapshot_path = resolve_path(
        request["final_snapshot_path"]
    )
    approval = load_json(
        resolve_path(
            request["reconciliation_approval_path"]
        )
    )

    require(
        digest(source_result)
        == request["source_result_digest_sha256"],
        "source result digest mismatch",
    )
    require(
        source_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_OFFLINE_CONTENT_"
            "GENERATION_AUTHORIZATION_RECORDED_"
            "NO_CONTENT_NO_PAYLOAD_NO_NETWORK"
        ),
        "source status mismatch",
    )
    require(
        source_result.get("authorization_consumed")
        is False,
        "source authorization already consumed",
    )

    require(
        file_sha256(authorization_path)
        == request[
            "source_authorization_file_sha256"
        ],
        "authorization file changed",
    )

    authorization_without_digest = copy.deepcopy(
        authorization
    )
    stored_authorization_digest = (
        authorization_without_digest.pop(
            "authorization_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_authorization_digest, str)
        and digest(authorization_without_digest)
        == stored_authorization_digest,
        "authorization digest invalid",
    )
    require(
        stored_authorization_digest
        == request[
            "source_authorization_artifact_digest_sha256"
        ],
        "authorization digest reference mismatch",
    )
    require(
        authorization["authorization_consumed"]
        is False,
        "authorization must remain unconsumed",
    )
    require(
        authorization["authorized_next_phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "authorization phase mismatch",
    )

    for path, hash_field in [
        (
            template_contract_path,
            "template_contract_file_sha256",
        ),
        (
            standard_policy_path,
            "standard_policy_file_sha256",
        ),
        (
            renderer_path,
            "legacy_renderer_file_sha256",
        ),
        (
            snapshot_path,
            "final_snapshot_file_sha256",
        ),
    ]:
        require(
            path.exists(),
            f"source artifact missing: {path}",
        )
        require(
            file_sha256(path) == request[hash_field],
            f"source artifact hash mismatch: {path}",
        )

    require(
        template_contract.get("contract_id")
        == "POST185_STANDARD_TEMPLATE_V1_FIXED",
        "template contract ID mismatch",
    )
    require(
        template_contract.get("template_id")
        == "POST185_STANDARD_TEMPLATE_V1",
        "template ID mismatch",
    )
    require(
        standard_policy.get("status")
        == "NEW_RELEASE_ARTICLE_STANDARD_TEMPLATE_FIXED",
        "standard policy status mismatch",
    )
    require(
        standard_policy["layout_policy"][
            "info_card"
        ]
        is True,
        "standard info card requirement missing",
    )
    require(
        standard_policy["info_card_policy"]["fields"]
        == [
            "作品名",
            "価格",
            "作者",
            "出版社",
            "発売日",
        ],
        "standard info card fields mismatch",
    )

    snapshot_text = snapshot_path.read_text(
        encoding="utf-8",
        errors="strict",
    )
    parser = SnapshotParser()
    parser.feed(snapshot_text)

    required_classes = {
        "ls-book-cover",
        "ls-store-card",
        "ls-store-buttons",
        "ls-store-btn",
        "ls-store-amazon",
        "ls-store-kobo",
        "ls-store-dmm",
    }

    require(
        required_classes.issubset(parser.classes),
        "snapshot required classes missing",
    )

    store_buttons = [
        link
        for link in parser.links
        if "ls-store-btn"
        in link.get("class", "").split()
    ]

    order: list[str] = []

    for link in store_buttons:
        classes = set(
            link.get("class", "").split()
        )

        if "ls-store-amazon" in classes:
            order.append("amazon")
        elif "ls-store-kobo" in classes:
            order.append("rakuten_kobo")
        elif "ls-store-dmm" in classes:
            order.append("dmm_books")

        rel_tokens = set(
            link.get("rel", "").split()
        )

        require(
            {
                "nofollow",
                "sponsored",
                "noopener",
            }.issubset(rel_tokens),
            "snapshot store rel attributes invalid",
        )

    require(
        order
        == [
            "amazon",
            "rakuten_kobo",
            "dmm_books",
        ],
        "snapshot store order mismatch",
    )

    all_text = " ".join(parser.text_parts)

    require(
        "※本ページはプロモーションを含みます。"
        in all_text,
        "legacy disclosure source missing",
    )

    for token in [
        "作品名",
        "価格",
        "作者",
        "出版社",
        "発売日",
    ]:
        require(
            token in all_text,
            f"snapshot information field missing: {token}",
        )

    approval_without_digest = copy.deepcopy(
        approval
    )
    stored_approval_digest = (
        approval_without_digest.pop(
            "approval_evidence_digest_sha256",
            None,
        )
    )

    require(
        isinstance(stored_approval_digest, str)
        and digest(approval_without_digest)
        == stored_approval_digest,
        "reconciliation approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "reconciliation_approval_digest_sha256"
        ],
        "reconciliation approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == "FRESH_ARTICLE_TEMPLATE_RECONCILIATION_APPROVED",
        "reconciliation approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "human approval missing",
    )
    require(
        approval.get("authorization_consumption_allowed")
        is False,
        "approval must not allow authorization consumption",
    )

    require(
        not CONSUMPTION_PATH.exists(),
        "consumption evidence already exists",
    )
    require(
        not RESERVED_OUTPUT_PATH.exists(),
        "reserved content output already exists",
    )

    return (
        source_result,
        authorization,
        template_contract,
        standard_policy,
        approval,
        parser,
        [
            "request_identity_verified",
            "source_result_verified",
            "authorization_file_verified",
            "authorization_digest_verified",
            "authorization_unconsumed",
            "template_contract_verified",
            "standard_policy_verified",
            "renderer_hash_verified",
            "final_snapshot_hash_verified",
            "final_snapshot_structure_verified",
            "information_card_structure_verified",
            "store_button_order_verified",
            "store_link_rel_verified",
            "legacy_disclosure_detected",
            "human_reconciliation_approval_verified",
            "content_generation_not_requested",
            "authorization_consumption_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
        ],
    )


def ensure_contract(
    stable: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if CONTRACT_PATH.exists():
        existing = load_json(CONTRACT_PATH)
        comparable = copy.deepcopy(existing)
        stored_digest = comparable.pop(
            "template_reconciliation_contract_digest_sha256",
            None,
        )
        fixed_at = comparable.pop(
            "contract_fixed_at_utc",
            None,
        )

        require(
            isinstance(fixed_at, str) and fixed_at,
            "existing contract timestamp invalid",
        )
        require(
            comparable == stable,
            "existing reconciliation contract mismatch",
        )

        without_digest = copy.deepcopy(existing)
        without_digest.pop(
            "template_reconciliation_contract_digest_sha256",
            None,
        )

        require(
            isinstance(stored_digest, str)
            and digest(without_digest)
            == stored_digest,
            "existing reconciliation contract digest invalid",
        )

        return existing, False

    without_digest = copy.deepcopy(stable)
    without_digest["contract_fixed_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    contract = copy.deepcopy(without_digest)
    contract[
        "template_reconciliation_contract_digest_sha256"
    ] = digest(without_digest)

    write_json(CONTRACT_PATH, contract)
    return contract, True


def main() -> int:
    try:
        policy = load_json(POLICY_PATH)
        request = load_json(REQUEST_PATH)

        policy_checks = validate_policy(policy)

        (
            source_result,
            authorization,
            template_contract,
            standard_policy,
            approval,
            parser,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        source_authorization_path = resolve_path(
            request["source_authorization_path"]
        )
        authorization_hash_before = file_sha256(
            source_authorization_path
        )

        stable_contract = {
            "schema_version": "1.0.0",
            "document_role": (
                "FRESH_NEW_RELEASE_ARTICLE_"
                "TEMPLATE_RECONCILIATION_CONTRACT"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K0"
            ),
            "contract_id": (
                "FRESH_NEW_RELEASE_COMIC_"
                "TEMPLATE_RECONCILIATION_V1"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1"
            ),
            "template_artifact_resolved": True,
            "source_roles": {
                "template_contract": (
                    "IDENTITY_AND_REQUIRED_COMPONENTS"
                ),
                "standard_policy": (
                    "CURRENT_LAYOUT_AND_SAFETY_REQUIREMENTS"
                ),
                "legacy_renderer": (
                    "ROOT_TEMPLATE_ID_AND_BASIC_RENDERING_REFERENCE"
                ),
                "final_post185_snapshot": (
                    "FINAL_INFORMATION_CARD_AND_STORE_"
                    "NAVIGATION_STRUCTURE_REFERENCE_ONLY"
                )
            },
            "source_artifacts": {
                "template_contract_path": (
                    request["template_contract_path"]
                ),
                "template_contract_file_sha256": (
                    request[
                        "template_contract_file_sha256"
                    ]
                ),
                "standard_policy_path": (
                    request["standard_policy_path"]
                ),
                "standard_policy_file_sha256": (
                    request[
                        "standard_policy_file_sha256"
                    ]
                ),
                "legacy_renderer_path": (
                    request["legacy_renderer_path"]
                ),
                "legacy_renderer_file_sha256": (
                    request[
                        "legacy_renderer_file_sha256"
                    ]
                ),
                "final_snapshot_path": (
                    request["final_snapshot_path"]
                ),
                "final_snapshot_file_sha256": (
                    request[
                        "final_snapshot_file_sha256"
                    ]
                )
            },
            "resolved_structure": {
                "template_root_id": (
                    "POST185_STANDARD_TEMPLATE_V1"
                ),
                "cover_required": True,
                "cover_source_must_come_from_current_article_input": True,
                "cover_anchor_allowed_before_final_link_fixation": False,
                "information_card_required": True,
                "information_card_fields": [
                    "作品名",
                    "価格",
                    "作者",
                    "出版社",
                    "発売日",
                ],
                "store_navigation_structure_reserved": True,
                "store_button_order": [
                    "amazon",
                    "rakuten_kobo",
                    "dmm_books",
                ],
                "store_navigation_html_rendering_allowed": False
            },
            "advertising_disclosure": {
                "required": True,
                "exact_text": (
                    "【PR】本記事にはアフィリエイト広告を含みます。"
                    "価格・配信状況は各ストアで確認してください。"
                ),
                "must_precede_store_navigation": True,
                "legacy_snapshot_disclosure_reused": False
            },
            "legacy_exclusion": {
                "post185_product_data_inheritance_allowed": False,
                "post185_url_inheritance_allowed": False,
                "post185_image_url_inheritance_allowed": False,
                "snapshot_href_reuse_allowed": False,
                "forbidden_product_tokens": [
                    "月曜日のたわわ",
                    "比村奇石",
                    "講談社",
                    "税込792円",
                    "B0H6DQLPPB",
                    "4071859",
                ]
            },
            "link_rendering": {
                "registered_store_links_are_verification_sources_only": True,
                "registered_store_links_are_final_affiliate_links": False,
                "final_affiliate_link_generation_allowed": False,
                "final_affiliate_link_rendering_allowed": False,
                "amazon_button_slot_reserved": True,
                "rakuten_kobo_button_slot_reserved": True,
                "dmm_books_button_slot_reserved": True,
                "dmm_latest_alias_recheck_completed": False,
                "dmm_url_rendering_allowed": False,
                "dmm_final_link_use_allowed": False
            },
            "category_boundary": {
                "categories_field_allowed": False,
                "production_category_id_payload_injection_allowed": False
            },
            "source_authorization": {
                "path": (
                    request["source_authorization_path"]
                ),
                "file_sha256": (
                    request[
                        "source_authorization_file_sha256"
                    ]
                ),
                "authorization_digest_sha256": (
                    request[
                        "source_authorization_artifact_digest_sha256"
                    ]
                ),
                "authorized_next_phase_id": (
                    "LS-NEW-BATCH-4G-2E-RECOVERY-K"
                ),
                "authorization_consumed": False,
                "authorization_modified": False
            },
            "article_content_generated": False,
            "content_output_created": False,
            "authorization_consumed": False,
            "consumption_evidence_created": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "TEMPLATE_RECONCILIATION_FIXED_"
                "AUTHORIZATION_UNCONSUMED"
            )
        }

        contract, created = ensure_contract(
            stable_contract
        )

        require(
            file_sha256(source_authorization_path)
            == authorization_hash_before,
            "source authorization modified during K0",
        )
        require(
            not CONSUMPTION_PATH.exists(),
            "consumption evidence created during K0",
        )
        require(
            not RESERVED_OUTPUT_PATH.exists(),
            "content output created during K0",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K0"
            ),
            "policy_id": policy["policy_id"],
            "reconciliation_contract_path": (
                display_path(CONTRACT_PATH)
            ),
            "reconciliation_contract_digest_sha256": (
                contract[
                    "template_reconciliation_contract_digest_sha256"
                ]
            ),
            "contract_created_in_this_run": created,
            "template_artifact_resolved": True,
            "authorization_consumed": False,
            "source_authorization_modified": False,
            "content_output_exists": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "verified_checks": (
                policy_checks + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "template_reconciliation_package_digest_sha256"
        ] = digest(package_without_digest)

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K0"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_TEMPLATE_RECONCILIATION_"
                "FIXED_NO_CONTENT_NO_AUTH_CONSUMPTION_NO_NETWORK"
            ),
            "decision": (
                "POST185_FINAL_STRUCTURE_AND_CURRENT_DISCLOSURE_"
                "CONTRACT_RECONCILED_READY_FOR_RECOVERY_K_PREFLIGHT"
            ),
            "approval_label": (
                "FRESH_ARTICLE_TEMPLATE_"
                "RECONCILIATION_APPROVED"
            ),
            "reconciliation_contract_id": (
                contract["contract_id"]
            ),
            "reconciliation_contract_path": (
                package[
                    "reconciliation_contract_path"
                ]
            ),
            "reconciliation_contract_digest_sha256": (
                package[
                    "reconciliation_contract_digest_sha256"
                ]
            ),
            "template_reconciliation_package_digest_sha256": (
                package[
                    "template_reconciliation_package_digest_sha256"
                ]
            ),
            "contract_created_in_this_run": created,
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1"
            ),
            "template_artifact_resolved": True,
            "final_snapshot_path": (
                request["final_snapshot_path"]
            ),
            "final_snapshot_file_sha256": (
                request[
                    "final_snapshot_file_sha256"
                ]
            ),
            "reconciled_disclosure_text": (
                contract[
                    "advertising_disclosure"
                ]["exact_text"]
            ),
            "information_card_fields": (
                contract[
                    "resolved_structure"
                ]["information_card_fields"]
            ),
            "store_button_order": (
                contract[
                    "resolved_structure"
                ]["store_button_order"]
            ),
            "legacy_product_data_inheritance_allowed": False,
            "legacy_url_inheritance_allowed": False,
            "final_affiliate_link_rendering_allowed": False,
            "dmm_url_rendering_allowed": False,
            "source_authorization_modified": False,
            "authorization_consumed": False,
            "consumption_evidence_created": False,
            "content_output_exists": False,
            "article_content_generated": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "TEMPLATE_RECONCILIATION_FIXED_"
                "AUTHORIZATION_UNCONSUMED"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_k": True,
            "ready_for_recovery_k_preflight": True,
            "ready_for_one_shot_offline_article_content_generation": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "reconciliation_contract_verified",
                    "reconciliation_contract_digest_verified",
                    "template_artifact_resolved",
                    "current_disclosure_fixed",
                    "legacy_product_data_excluded",
                    "legacy_urls_excluded",
                    "dmm_url_rendering_blocked",
                    "final_affiliate_links_blocked",
                    "authorization_preserved",
                    "authorization_unconsumed",
                    "consumption_evidence_absent",
                    "content_output_absent",
                    "article_content_not_generated",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "execution_gate_closed",
                ]
            ),
        }

        write_json(PACKAGE_PATH, package)
        write_json(RESULT_PATH, result)

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-K0 Template Reconciliation

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Template resolved: `true`
- Authorization consumed: `false`

## Reconciled Structure

- Final snapshot: `{result["final_snapshot_path"]}`
- Information card: `作品名・価格・作者・出版社・発売日`
- Store order: `Amazon → 楽天Kobo → DMMブックス`
- Final affiliate-link rendering: `false`
- DMM URL rendering: `false`

## Advertising Disclosure

`{result["reconciled_disclosure_text"]}`

## Current Phase Boundary

- Legacy product data inherited: `false`
- Legacy URLs inherited: `false`
- Content output exists: `false`
- Article content generated: `false`
- Authorization consumed: `false`
- Network accessed: `false`
- WordPress written: `false`
- Execution allowed: `false`
"""

        write_text(REPORT_PATH, report)

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except ValidationError as exc:
        failure = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K0"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "template_artifact_resolved": False,
            "article_content_generated": False,
            "authorization_consumed": False,
            "consumption_evidence_created": False,
            "content_output_created": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
        }

        write_json(RESULT_PATH, failure)

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
