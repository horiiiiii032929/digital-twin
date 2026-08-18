from collections import Counter
from datetime import date

from scripts.audit_python_dependencies import evaluate_policy, finding_key


def _report(version: str = "1.0.0") -> dict:
    return {
        "dependencies": [
            {
                "name": "Example",
                "version": version,
                "vulns": [{"id": "CVE-TEST-1", "fix_versions": ["2.0.0"]}],
            }
        ]
    }


def _policy(version: str = "1.0.0") -> dict:
    return {
        "policy_id": "test-policy",
        "review_by": "2099-01-01",
        "exceptions": [
            {
                "package": "example",
                "version": version,
                "advisory_id": "CVE-TEST-1",
                "fix_versions": ["2.0.0"],
            }
        ],
    }


def test_exact_reviewed_finding_passes_with_visible_exception() -> None:
    result = evaluate_policy(_report(), _policy(), today=date(2026, 8, 18))

    assert result["status"] == "passed-with-reviewed-exceptions"
    assert result["finding_count"] == 1
    assert result["reviewed_exception_count"] == 1
    assert result["unexpected_findings"] == []
    assert result["stale_exceptions"] == []
    assert result["policy_expired"] is False


def test_version_drift_fails_and_reports_unexpected_and_stale_entries() -> None:
    result = evaluate_policy(
        _report(version="1.0.1"), _policy(), today=date(2026, 8, 18)
    )

    assert result["status"] == "failed"
    assert result["unexpected_findings"][0]["version"] == "1.0.1"
    assert result["stale_exceptions"][0]["version"] == "1.0.0"


def test_duplicate_findings_require_duplicate_review_entries() -> None:
    report = _report()
    report["dependencies"][0]["vulns"] *= 2

    result = evaluate_policy(report, _policy(), today=date(2026, 8, 18))

    assert result["status"] == "failed"
    assert result["unexpected_findings"][0]["occurrences"] == 1


def test_finding_key_normalizes_package_name_and_fix_order() -> None:
    key = finding_key("Example", "1.0.0", "CVE-TEST-1", ["3.0", "2.0"])

    assert Counter([key]) == Counter(
        [("example", "1.0.0", "CVE-TEST-1", ("2.0", "3.0"))]
    )


def test_expired_policy_fails_even_when_findings_match() -> None:
    policy = _policy()
    policy["review_by"] = "2026-08-17"

    result = evaluate_policy(_report(), policy, today=date(2026, 8, 18))

    assert result["status"] == "failed"
    assert result["policy_expired"] is True
