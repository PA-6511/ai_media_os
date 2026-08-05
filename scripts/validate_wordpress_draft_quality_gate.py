#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/wordpress_draft_quality_gate.json"
DEFAULT_CANDIDATE = ROOT / "exchange/examples/wordpress_draft_quality_candidate.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_6_quality_gate_validation_result.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_reject_tag(body: str, reject_tags: list[str]) -> bool:
    lower = body.lower()
    for tag in reject_tags:
        if f"<{tag.lower()}" in lower:
            return True
    return False


def _looks_dangerous_scheme(url: str) -> bool:
    lower = url.strip().lower()
    return lower.startswith("http://") or lower.startswith("javascript:") or lower.startswith("data:") or lower.startswith("file:")


def validate_quality_gate(config: dict, candidate: dict) -> dict:
    checked_fields = []
    errors = []
    warnings = []
    safety_errors = []

    required_fields = config.get("required_fields", [])
    for field in required_fields:
        checked_fields.append(field)
        if field not in candidate:
            errors.append(f"required field missing: {field}")

    for field in ["title", "body", "product_name", "pr_notice", "affiliate_links", "cta", "category", "tags"]:
        if field not in checked_fields:
            checked_fields.append(field)
        if field not in candidate:
            errors.append(f"required field missing: {field}")

    body = str(candidate.get("body", ""))
    product_name = str(candidate.get("product_name", ""))
    pr_notice = str(candidate.get("pr_notice", ""))

    body_rules = config.get("body_rules", {})
    min_chars = int(body_rules.get("min_chars", 0))
    max_chars_warning = int(body_rules.get("max_chars_warning", 0))

    if len(body) < min_chars:
        errors.append(f"body is too short: {len(body)} < {min_chars}")

    if max_chars_warning > 0 and len(body) > max_chars_warning:
        warnings.append(f"body is long: {len(body)} > {max_chars_warning}")

    if body_rules.get("must_include_product_name") is True and product_name not in body:
        errors.append("body must include product_name")

    pr_rules = config.get("pr_notice_rules", {})
    phrases = pr_rules.get("accepted_phrases", [])
    if pr_rules.get("required") is True:
        if not pr_notice:
            errors.append("pr_notice is required")
        elif not any(phrase in pr_notice for phrase in phrases):
            errors.append("pr_notice does not include accepted phrase")

    affiliate_rules = config.get("affiliate_link_rules", {})
    links = candidate.get("affiliate_links", [])
    if affiliate_rules.get("required") is True and not isinstance(links, list):
        errors.append("affiliate_links must be a list")
        links = []
    if len(links) < int(affiliate_rules.get("min_link_count", 1)):
        errors.append("affiliate_links must include at least one item")
    for link in links:
        url = str(link.get("url", ""))
        if not url.startswith("https://"):
            safety_errors.append(f"affiliate_links url must start with https: {url}")
        if _looks_dangerous_scheme(url):
            safety_errors.append(f"affiliate_links url uses rejected scheme: {url}")

    cta_rules = config.get("cta_rules", {})
    ctas = candidate.get("cta", [])
    if cta_rules.get("required") is True and not isinstance(ctas, list):
        errors.append("cta must be a list")
        ctas = []
    if len(ctas) < int(cta_rules.get("min_cta_count", 1)):
        errors.append("cta must include at least one item")
    for cta in ctas:
        url = str(cta.get("url", ""))
        if cta_rules.get("require_url") is True and not url:
            errors.append("cta.url is required")
        if url and not url.startswith("https://"):
            safety_errors.append(f"cta url must start with https: {url}")
        if _looks_dangerous_scheme(url):
            safety_errors.append(f"cta url uses rejected scheme: {url}")

    html_rules = config.get("html_safety_rules", {})
    reject_tags = html_rules.get("reject_tags", [])
    if _contains_reject_tag(body, reject_tags):
        safety_errors.append("body contains rejected HTML tag")

    if html_rules.get("reject_inline_event_handlers") is True:
        body_lower = body.lower()
        for token in ["onerror=", "onclick=", "onload="]:
            if token in body_lower:
                safety_errors.append(f"body contains inline event handler: {token}")

    expr_rules = config.get("expression_rules", {})
    for phrase in expr_rules.get("reject_exaggerated_claims", []):
        if phrase in body:
            safety_errors.append(f"body contains rejected exaggerated claim: {phrase}")

    status = "PASS_DRY_RUN_ONLY"
    if safety_errors:
        status = "ABORT"
        errors.extend(safety_errors)
    elif errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"

    return {
        "phase": "Phase 6-6",
        "status": status,
        "production_status": config.get("production_status", "NO_GO"),
        "wordpress_write_executed": bool(config.get("wordpress_write_executed", False)),
        "checked_fields": checked_fields,
        "errors": errors,
        "warnings": warnings,
        "next_step": "phase6_7_slack_approval_dry_run" if status == "PASS_DRY_RUN_ONLY" else "fix_phase6_6_quality_candidate"
    }


def run_validation(config_path: Path | None = None, candidate_path: Path | None = None, output_path: Path | None = None) -> dict:
    config_path = Path(config_path or DEFAULT_CONFIG)
    candidate_path = Path(candidate_path or DEFAULT_CANDIDATE)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    errors = []
    if not config_path.exists():
        errors.append(f"config not found: {config_path}")
    if not candidate_path.exists():
        errors.append(f"candidate not found: {candidate_path}")

    if errors:
        result = {
            "phase": "Phase 6-6",
            "status": "ABORT",
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "checked_fields": [],
            "errors": errors,
            "warnings": [],
            "next_step": "prepare_phase6_6_inputs"
        }
    else:
        result = validate_quality_gate(load_json(config_path), load_json(candidate_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DRY_RUN_ONLY", "WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
