from __future__ import annotations

from pathlib import Path
from typing import Any

from .block_contract import BlockManifest
from .human_review_evidence_writer import write_human_review_artifacts
from .policy_versioning import build_policy_version_info, write_policy_history
from .proposal_validator import validate_proposal
from .quality_metrics import compute_quality_metrics
from .review_decision_logic import build_recommended_decision
from .review_package_builder import write_review_package
from .connection_dryrun_validator import validate_connection_dryrun
from .core_ai_handshake_package import build_core_ai_handshake_package, write_core_ai_handshake_package
from .review_artifacts_validator import (
    validate_review_artifacts_from_result,
    write_review_artifacts_summary,
)
from .signoff_audit_trail import build_signoff_audit_record, write_signoff_audit_log
from .result_schema import build_block_result
from .safety_guard import evaluate_actions, load_policy, validate_runtime_configuration
from .task_constraint_filter import filter_task_candidates
from .task_candidate_scorer import score_task_candidates


class GenericBlockRunner:
    def __init__(self, manifest_path: Path, policy_path: Path) -> None:
        self.base_path = manifest_path.resolve().parent
        self.manifest = BlockManifest.from_json_file(manifest_path)
        self.policy = load_policy(policy_path)

    def run(
        self,
        requested_actions: list[dict[str, Any]] | None = None,
        *,
        source_task_id: str | None = None,
        persist_human_review_artifacts: bool = True,
        signoff_actor: str = "generic_block_ai",
    ) -> dict[str, Any]:
        actions = requested_actions or []
        configuration_errors = validate_runtime_configuration(self.manifest, self.policy)
        task_id = source_task_id or "block_runner_run"

        if configuration_errors:
            result = build_block_result(
                status="error",
                decision="human_review",
                summary="configuration rejected by safety guard",
                risk_level=self.manifest.risk_level,
                needs_approval=True,
                mode=self.manifest.mode,
                actual_execution=False,
                actions=[],
                blocked_actions=[],
                needs_review_actions=[],
                reason_codes=[
                    {
                        "action_type": "runtime_configuration",
                        "classification": "block",
                        "reason": "configuration_rejected",
                    }
                ],
                review_required_fields=["manifest", "policy"],
                warnings=[],
                errors=configuration_errors,
                block_id=self.manifest.block_id,
                version=self.manifest.version,
            )
            if persist_human_review_artifacts:
                review_package = write_review_package(
                    base_path=self.base_path,
                    block_result=result,
                    source_task_id=task_id,
                )
                proposal_validation = validate_proposal(review_package["package"])
                result["review_package"] = {
                    "path": review_package["path"],
                    "external_write_executed": False,
                    "validation_result": proposal_validation.result,
                    "validation_failed_checks": proposal_validation.failed_checks,
                    "validation_warnings": proposal_validation.warnings,
                }

                artifacts = write_human_review_artifacts(
                    base_path=self.base_path,
                    block_result=result,
                    source_task_id=task_id,
                )
                result["review_artifacts"] = {
                    "review_queue_path": artifacts["review_queue_path"],
                    "evidence_path": artifacts["evidence_path"],
                    "external_write_executed": False,
                }
                validation_report = validate_review_artifacts_from_result(result)
                result["review_artifacts_validation"] = validation_report
                summary_paths = write_review_artifacts_summary(
                    base_path=self.base_path,
                    source_task_id=task_id,
                    validation_result=validation_report,
                )
                result["review_artifacts_summary"] = summary_paths

            review_package_info = result.get("review_package", {})
            result["quality_metrics"] = compute_quality_metrics(
                result,
                proposal_validation_result=review_package_info.get("validation_result", "NOT_RUN"),
                proposal_failed_checks=review_package_info.get("validation_failed_checks", []),
                proposal_warnings=review_package_info.get("validation_warnings", []),
                policy_quality_metrics=self.policy.get("quality_metrics"),
            )
            result["review_decision"] = build_recommended_decision(
                result,
                result["quality_metrics"],
                policy_review_decision=self.policy.get("review_decision"),
            )

            policy_versioning = build_policy_version_info(self.policy)
            if persist_human_review_artifacts:
                policy_versioning = write_policy_history(
                    base_path=self.base_path,
                    policy=self.policy,
                    source_task_id=task_id,
                )
            else:
                policy_versioning["history_path"] = None
                policy_versioning["external_write_executed"] = False
            result["policy_versioning"] = policy_versioning

            if persist_human_review_artifacts:
                signoff = write_signoff_audit_log(
                    base_path=self.base_path,
                    block_result=result,
                    source_task_id=task_id,
                    signoff_actor=signoff_actor,
                )
                result["signoff_audit"] = {
                    "path": signoff["path"],
                    "external_write_executed": False,
                    "record": signoff["record"],
                }
            else:
                result["signoff_audit"] = {
                    "path": None,
                    "external_write_executed": False,
                    "record": build_signoff_audit_record(
                        block_result=result,
                        source_task_id=task_id,
                        signoff_actor=signoff_actor,
                    ),
                }

            if persist_human_review_artifacts:
                handshake_output = write_core_ai_handshake_package(
                    base_path=self.base_path,
                    block_result=result,
                    source_task_id=task_id,
                )
                handshake_package = handshake_output["package"]
                handshake_path = handshake_output["path"]
            else:
                handshake_package = build_core_ai_handshake_package(
                    result, source_task_id=task_id
                )
                handshake_path = None
            connection_validation = validate_connection_dryrun(handshake_package)
            result["core_ai_handshake"] = {
                "path": handshake_path,
                "connection_status": handshake_package["connection_status"],
                "validation_result": connection_validation.result,
                "validation_failed_checks": connection_validation.failed_checks,
                "validation_warnings": connection_validation.warnings,
                "external_write_executed": False,
            }
            return result

        guard_decision = evaluate_actions(self.manifest, actions, self.policy)
        task_candidates = score_task_candidates(actions, guard_decision)
        filtered_task_candidates, rejected_task_candidates = filter_task_candidates(
            task_candidates,
            manifest=self.manifest,
            policy=self.policy,
        )

        decision = "human_review" if self.manifest.requires_human_approval else "decision"
        status = "success"
        errors: list[str] = []
        warnings = list(guard_decision.warnings)

        if guard_decision.blocked_actions:
            status = "blocked"
            if decision == "decision":
                decision = "recheck"

        if guard_decision.needs_review_actions:
            decision = "human_review"

        if self.manifest.auto_execute_allowed:
            warnings.append("auto_execute_allowed is ignored in Phase G-1")

        summary = (
            f"planned={len(actions)}, allowed={len(guard_decision.allowed_actions)}, "
            f"blocked={len(guard_decision.blocked_actions)}, "
            f"needs_review={len(guard_decision.needs_review_actions)}, "
            f"candidates={len(task_candidates)}, "
            f"filtered={len(filtered_task_candidates)}, "
            f"rejected={len(rejected_task_candidates)}"
        )

        result = build_block_result(
            status=status,
            decision=decision,
            summary=summary,
            risk_level=self.manifest.risk_level,
            needs_approval=self.manifest.requires_human_approval,
            mode=self.manifest.mode,
            actual_execution=False,
            actions=guard_decision.allowed_actions,
            blocked_actions=guard_decision.blocked_actions,
            needs_review_actions=guard_decision.needs_review_actions,
            task_candidates=filtered_task_candidates,
            rejected_task_candidates=rejected_task_candidates,
            reason_codes=guard_decision.reason_codes,
            review_required_fields=["type", "target", "justification"],
            warnings=warnings,
            errors=errors,
            block_id=self.manifest.block_id,
            version=self.manifest.version,
        )

        if persist_human_review_artifacts and result["decision"] == "human_review":
            review_package = write_review_package(
                base_path=self.base_path,
                block_result=result,
                source_task_id=task_id,
            )
            proposal_validation = validate_proposal(review_package["package"])
            result["review_package"] = {
                "path": review_package["path"],
                "external_write_executed": False,
                "validation_result": proposal_validation.result,
                "validation_failed_checks": proposal_validation.failed_checks,
                "validation_warnings": proposal_validation.warnings,
            }

            artifacts = write_human_review_artifacts(
                base_path=self.base_path,
                block_result=result,
                source_task_id=task_id,
            )
            result["review_artifacts"] = {
                "review_queue_path": artifacts["review_queue_path"],
                "evidence_path": artifacts["evidence_path"],
                "external_write_executed": False,
            }
            validation_report = validate_review_artifacts_from_result(result)
            result["review_artifacts_validation"] = validation_report
            summary_paths = write_review_artifacts_summary(
                base_path=self.base_path,
                source_task_id=task_id,
                validation_result=validation_report,
            )
            result["review_artifacts_summary"] = summary_paths

        review_package_info = result.get("review_package", {})
        result["quality_metrics"] = compute_quality_metrics(
            result,
            proposal_validation_result=review_package_info.get("validation_result", "NOT_RUN"),
            proposal_failed_checks=review_package_info.get("validation_failed_checks", []),
            proposal_warnings=review_package_info.get("validation_warnings", []),
            policy_quality_metrics=self.policy.get("quality_metrics"),
        )
        result["review_decision"] = build_recommended_decision(
            result,
            result["quality_metrics"],
            policy_review_decision=self.policy.get("review_decision"),
        )

        policy_versioning = build_policy_version_info(self.policy)
        if persist_human_review_artifacts:
            policy_versioning = write_policy_history(
                base_path=self.base_path,
                policy=self.policy,
                source_task_id=task_id,
            )
        else:
            policy_versioning["history_path"] = None
            policy_versioning["external_write_executed"] = False
        result["policy_versioning"] = policy_versioning

        if persist_human_review_artifacts:
            signoff = write_signoff_audit_log(
                base_path=self.base_path,
                block_result=result,
                source_task_id=task_id,
                signoff_actor=signoff_actor,
            )
            result["signoff_audit"] = {
                "path": signoff["path"],
                "external_write_executed": False,
                "record": signoff["record"],
            }
        else:
            result["signoff_audit"] = {
                "path": None,
                "external_write_executed": False,
                "record": build_signoff_audit_record(
                    block_result=result,
                    source_task_id=task_id,
                    signoff_actor=signoff_actor,
                ),
            }

        if persist_human_review_artifacts:
            handshake_output = write_core_ai_handshake_package(
                base_path=self.base_path,
                block_result=result,
                source_task_id=task_id,
            )
            handshake_package = handshake_output["package"]
            handshake_path = handshake_output["path"]
        else:
            handshake_package = build_core_ai_handshake_package(
                result, source_task_id=task_id
            )
            handshake_path = None
        connection_validation = validate_connection_dryrun(handshake_package)
        result["core_ai_handshake"] = {
            "path": handshake_path,
            "connection_status": handshake_package["connection_status"],
            "validation_result": connection_validation.result,
            "validation_failed_checks": connection_validation.failed_checks,
            "validation_warnings": connection_validation.warnings,
            "external_write_executed": False,
        }

        return result
