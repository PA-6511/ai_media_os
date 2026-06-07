from __future__ import annotations

from typing import Any


def validate_hardware_profile(
    profile: dict[str, Any],
    manifest: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required_fields = [str(field) for field in policy.get("required_profile_fields", [])]
    missing = [field for field in required_fields if field not in profile]
    if missing:
        errors.append(f"missing_required_fields:{','.join(missing)}")

    allowed_device_classes = set(policy.get("allowed_device_classes", []))
    device_class = str(profile.get("device_class", "")).strip()
    if device_class and device_class not in allowed_device_classes:
        errors.append(f"unsupported_device_class:{device_class}")

    manifest_hw = manifest.get("hardware_profile", {})
    min_ram = float(manifest_hw.get("ram_gb_min_required", 0))
    min_storage = float(manifest_hw.get("storage_gb_min_required", 0))

    ram_gb = float(profile.get("ram_gb", 0))
    storage_gb = float(profile.get("storage_gb", 0))

    if ram_gb < min_ram:
        errors.append(f"ram_below_min:{ram_gb}<{min_ram}")

    if storage_gb < min_storage:
        errors.append(f"storage_below_min:{storage_gb}<{min_storage}")

    thermal_status = str(profile.get("thermal_status", "")).upper()
    thermal_fail_status = {str(s).upper() for s in policy.get("thermal_fail_status", [])}
    if thermal_status in thermal_fail_status:
        errors.append(f"thermal_not_acceptable:{thermal_status}")

    battery_min_percent = int(policy.get("battery_min_percent", 0))
    battery_percent = int(profile.get("battery_percent", 0))
    if battery_percent < battery_min_percent:
        warnings.append(f"battery_low:{battery_percent}<{battery_min_percent}")

    status = "PASS" if not errors else "FAIL"

    return {
        "phase": "SoC-1",
        "status": status,
        "design_only": True,
        "no_execution": True,
        "errors": errors,
        "warnings": warnings,
        "recommended_task_size": "SMALL",
    }


def validate_soc1_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    violations: list[str] = []

    if str(manifest.get("status", "")).upper() != "DESIGN_ONLY":
        violations.append("manifest.status must remain DESIGN_ONLY")

    if str(manifest.get("production_status", "")).upper() != "NO_GO":
        violations.append("manifest.production_status must remain NO_GO")

    execution_value = str(manifest.get("execution", "")).upper()
    if execution_value not in {"DRY_RUN", "DRY_RUN_ONLY", "NO_EXECUTION"}:
        violations.append("manifest.execution must remain dry-run/no-execution")

    if str(policy.get("status", "")).upper() != "DESIGN_ONLY":
        violations.append("policy.status must remain DESIGN_ONLY")

    if str(policy.get("production_status", "")).upper() != "NO_GO":
        violations.append("policy.production_status must remain NO_GO")

    if str(policy.get("execution_mode", "")).upper() != "NO_EXECUTION":
        violations.append("policy.execution_mode must remain NO_EXECUTION")

    if bool(policy.get("dry_run_only", False)) is not True:
        violations.append("policy.dry_run_only must remain true")

    return violations
