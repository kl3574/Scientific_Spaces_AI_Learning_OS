from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from common import REPO_ROOT, SecurityToolError, load_json


DEPENDENCY_FIELDS = {
    "id",
    "ecosystem",
    "package",
    "advisory_id",
    "scope",
    "reason",
    "owner",
    "tracking_url",
    "created_at",
    "expires_at",
    "review_after",
}
SECRET_FIELDS = {
    "id",
    "rule_id",
    "path",
    "irreversible_fingerprint",
    "reason",
    "owner",
    "tracking_url",
    "created_at",
    "expires_at",
    "review_after",
}


def _parse_date(value: object, field: str, suppression_id: str) -> date:
    if not isinstance(value, str):
        raise SecurityToolError(f"{suppression_id}: {field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SecurityToolError(f"{suppression_id}: invalid {field}") from exc


def _validate_common(
    suppression: dict[str, Any], required: set[str], today: date
) -> list[str]:
    suppression_id = str(suppression.get("id") or "<missing-id>")
    findings: list[str] = []
    missing = sorted(required - set(suppression))
    if missing:
        findings.append(f"{suppression_id}: missing fields: {','.join(missing)}")
        return findings
    for field in required - {"created_at", "expires_at", "review_after"}:
        value = suppression.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(f"{suppression_id}: {field} must be non-empty")
    tracking_url = suppression.get("tracking_url")
    if isinstance(tracking_url, str) and not tracking_url.startswith("https://"):
        findings.append(f"{suppression_id}: tracking_url must use https")
    try:
        created = _parse_date(suppression.get("created_at"), "created_at", suppression_id)
        review = _parse_date(suppression.get("review_after"), "review_after", suppression_id)
        expires = _parse_date(suppression.get("expires_at"), "expires_at", suppression_id)
    except SecurityToolError as exc:
        findings.append(str(exc))
        return findings
    if not created <= review <= expires:
        findings.append(f"{suppression_id}: require created_at <= review_after <= expires_at")
    if expires < today:
        findings.append(f"{suppression_id}: suppression expired")
    return findings


def _dependency_key(value: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(value.get("ecosystem", "")),
        str(value.get("package", "")),
        str(value.get("advisory_id", "")),
        str(value.get("scope", "")),
    )


def _secret_key(value: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(value.get("rule_id", "")),
        str(value.get("path", "")),
        str(value.get("irreversible_fingerprint", "")),
    )


def validate(
    policy: dict[str, Any],
    *,
    today: date | None = None,
    dependency_findings: list[dict[str, Any]] | None = None,
    secret_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    findings: list[str] = []
    if policy.get("schema_version") != 1:
        findings.append("unsupported suppression schema_version")
    dependencies = policy.get("dependency_suppressions")
    secrets = policy.get("secret_suppressions")
    if not isinstance(dependencies, list) or not isinstance(secrets, list):
        raise SecurityToolError("suppression lists must be arrays")

    seen_ids: set[str] = set()
    for collection, fields in ((dependencies, DEPENDENCY_FIELDS), (secrets, SECRET_FIELDS)):
        for value in collection:
            if not isinstance(value, dict):
                findings.append("suppression entry must be an object")
                continue
            findings.extend(_validate_common(value, fields, today))
            suppression_id = value.get("id")
            if isinstance(suppression_id, str):
                if suppression_id in seen_ids:
                    findings.append(f"duplicate suppression id: {suppression_id}")
                seen_ids.add(suppression_id)

    dependency_keys = {
        _dependency_key(item) for item in (dependency_findings or [])
    }
    secret_keys = {_secret_key(item) for item in (secret_findings or [])}
    if dependency_findings is not None:
        for suppression in dependencies:
            if isinstance(suppression, dict) and _dependency_key(suppression) not in dependency_keys:
                findings.append(f"{suppression.get('id', '<missing-id>')}: unmatched dependency suppression")
    if secret_findings is not None:
        for suppression in secrets:
            if isinstance(suppression, dict) and _secret_key(suppression) not in secret_keys:
                findings.append(f"{suppression.get('id', '<missing-id>')}: unmatched secret suppression")

    return {
        "status": "PASS" if not findings else "BLOCKED",
        "dependency_suppression_count": len(dependencies),
        "secret_suppression_count": len(secrets),
        "findings": sorted(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate structured security suppressions.")
    parser.add_argument(
        "--policy",
        type=Path,
        default=REPO_ROOT / ".github" / "security" / "suppressions.json",
    )
    parser.add_argument("--dependency-findings", type=Path)
    parser.add_argument("--secret-findings", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        policy = load_json(args.policy)
        dependency_findings = (
            load_json(args.dependency_findings).get("findings", [])
            if args.dependency_findings
            else None
        )
        secret_findings = (
            load_json(args.secret_findings).get("findings", [])
            if args.secret_findings
            else None
        )
        result = validate(
            policy,
            dependency_findings=dependency_findings,
            secret_findings=secret_findings,
        )
    except (SecurityToolError, AttributeError) as exc:
        print(f"suppression_validation=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "suppression_validation={status} dependency={dependency_suppression_count} "
            "secret={secret_suppression_count}".format(**result)
        )
        for finding in result["findings"]:
            print(f"finding={finding}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
