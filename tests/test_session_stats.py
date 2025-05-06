import pytest
from pytest_recap.models import TestSessionStats


class DummyTestResult:
    def __init__(self, outcome):
        self.outcome = outcome


@pytest.mark.parametrize(
    "outcomes,expected_counts",
    [
        (["passed", "failed", "passed", "skipped"], {"passed": 2, "failed": 1, "skipped": 1}),
        ([], {}),
        (["error", "error", "xfailed"], {"error": 2, "xfailed": 1}),
    ],
)
def test_session_stats_counts(outcomes, expected_counts):
    results = [DummyTestResult(outcome) for outcome in outcomes]
    stats = TestSessionStats(results)
    for outcome, count in expected_counts.items():
        assert stats.count(outcome) == count
    # Check total
    assert stats.total == len(outcomes)
    # Check as_dict
    assert stats.as_dict() == {k: v for k, v in expected_counts.items()}


def test_session_stats_unknown_outcome():
    results = []
    stats = TestSessionStats(results)
    assert stats.count("notreal") == 0


def test_session_stats_str():
    results = [DummyTestResult("passed"), DummyTestResult("failed")]
    stats = TestSessionStats(results)
    s = str(stats)
    assert "TestSessionStats" in s and "passed" in s and "failed" in s
