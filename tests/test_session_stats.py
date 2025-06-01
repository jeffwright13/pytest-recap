import pytest
from pytest_recap.models import TestSessionStats


class DummyTestResult:
    def __init__(self, outcome):
        self.outcome = outcome


@pytest.mark.parametrize(
    "outcomes,warnings_count,expected_counts",
    [
        (["passed", "failed", "passed", "skipped"], 2, {"passed": 2, "failed": 1, "skipped": 1, "warnings": 2}),
        ([], 0, {"warnings": 0}),
        (["error", "error", "xfailed"], 1, {"error": 2, "xfailed": 1, "warnings": 1}),
    ],
    ids=[
        "multiple_outcomes",
        "empty",
        "errors_and_xfailed",
    ],
)
def test_session_stats_counts(outcomes, warnings_count, expected_counts):
    results = [DummyTestResult(outcome) for outcome in outcomes]
    stats = TestSessionStats(results, warnings_count)
    for key, count in expected_counts.items():
        assert stats.count(key) == count
    # Check total
    assert stats.total == len(outcomes)
    # Check as_dict
    assert stats.as_dict() == expected_counts


def test_session_stats_unknown_outcome():
    results = []
    stats = TestSessionStats(results, warnings_count=3)
    assert stats.count("notreal") == 0
    assert stats.count("warnings") == 3


def test_session_stats_str():
    results = [DummyTestResult("passed"), DummyTestResult("failed")]
    stats = TestSessionStats(results, warnings_count=1)
    s = str(stats)
    assert "TestSessionStats" in s and "passed" in s and "failed" in s and "warnings" in s
