from datetime import datetime, timedelta, timezone

import pytest
from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult, TestSession


def test_testoutcome_from_str_and_to_str():
    assert TestOutcome.from_str("passed") == TestOutcome.PASSED
    assert TestOutcome.from_str("FAILED") == TestOutcome.FAILED
    assert TestOutcome.PASSED.to_str() == "passed"
    assert TestOutcome.FAILED.to_str() == "failed"
    assert TestOutcome.to_list() == [o.value.lower() for o in TestOutcome]
    with pytest.raises(ValueError):
        TestOutcome.from_str("not_a_real_outcome")


def test_testoutcome_is_failed():
    assert TestOutcome.FAILED.is_failed() is True
    assert TestOutcome.ERROR.is_failed() is True
    assert TestOutcome.PASSED.is_failed() is False
    assert TestOutcome.SKIPPED.is_failed() is False


def test_testoutcome_from_str_none_and_empty():
    assert TestOutcome.from_str(None) == TestOutcome.SKIPPED
    assert TestOutcome.from_str("") == TestOutcome.SKIPPED
    with pytest.raises(ValueError):
        TestOutcome.from_str("   ")


def test_testresult_init_and_to_dict():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=2)
    result = TestResult(
        nodeid="test_foo.py::test_foo",
        outcome=TestOutcome.PASSED,
        start_time=start,
        stop_time=stop,
        duration=None,
        caplog="",
        capstderr="",
        capstdout="",
        longreprtext="",
        has_warning=False,
    )
    d = result.to_dict()
    assert d["nodeid"] == "test_foo.py::test_foo"
    assert d["outcome"] == "passed"
    assert datetime.fromisoformat(d["start_time"]) == start
    assert datetime.fromisoformat(d["stop_time"]) == stop
    assert d["duration"] == 2.0


def test_testresult_from_dict():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=2)
    d = {
        "nodeid": "test_bar.py::test_bar",
        "outcome": "failed",
        "start_time": start.isoformat(),
        "stop_time": stop.isoformat(),
        "duration": 2.0,
        "caplog": "",
        "capstderr": "",
        "capstdout": "",
        "longreprtext": "",
        "has_warning": False,
    }
    result = TestResult.from_dict(d)
    assert result.nodeid == "test_bar.py::test_bar"
    assert result.outcome == TestOutcome.FAILED
    assert result.duration == 2.0
    assert result.start_time == start
    assert result.stop_time == stop


@pytest.mark.parametrize("duration", [0, -1])
def test_testresult_negative_and_zero_duration(duration):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=duration)
    result = TestResult(
        nodeid="test_neg.py::test_neg",
        outcome=TestOutcome.PASSED,
        start_time=start,
        stop_time=stop,
        duration=duration,
    )
    d = result.to_dict()
    assert d["duration"] == duration


@pytest.mark.parametrize("extra_field", ["foo", "bar"])
def test_testresult_from_dict_with_extra_fields(extra_field):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=2)
    d = {
        "nodeid": "test_extra.py::test_extra",
        "outcome": "passed",
        "start_time": start.isoformat(),
        "stop_time": stop.isoformat(),
        "duration": 2.0,
        extra_field: 42,
    }
    result = TestResult.from_dict(d)
    assert result.nodeid == "test_extra.py::test_extra"


def test_reruntestgroup_add_and_final_outcome():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tr1 = TestResult(
        "foo",
        TestOutcome.RERUN,
        start,
        stop_time=start + timedelta(seconds=1),
        duration=1,
    )
    tr2 = TestResult(
        "foo",
        TestOutcome.FAILED,
        start + timedelta(seconds=1),
        stop_time=start + timedelta(seconds=2),
        duration=1,
    )
    group = RerunTestGroup(nodeid="foo")
    group.add_test(tr1)
    group.add_test(tr2)
    assert group.final_outcome == TestOutcome.FAILED
    d = group.to_dict()
    assert d["nodeid"] == "foo"
    assert len(d["tests"]) == 2
    group2 = RerunTestGroup.from_dict(d)
    assert group2.nodeid == "foo"
    assert group2.tests[1].outcome == TestOutcome.FAILED
    assert group2.tests[0].start_time == start


def test_reruntestgroup_empty_final_outcome():
    group = RerunTestGroup(nodeid="foo")
    assert group.final_outcome is None
    assert group.to_dict()["tests"] == []


def test_reruntestgroup_all_skipped():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tr = TestResult(
        "foo",
        TestOutcome.SKIPPED,
        start,
        stop_time=start + timedelta(seconds=1),
        duration=1,
    )
    group = RerunTestGroup(nodeid="foo")
    group.add_test(tr)
    assert group.final_outcome == TestOutcome.SKIPPED


def test_testsession_add_and_to_from_dict():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=10)
    tr = TestResult(
        "foo",
        TestOutcome.PASSED,
        start,
        stop_time=start + timedelta(seconds=2),
        duration=2,
    )
    group = RerunTestGroup(nodeid="foo")
    group.add_test(tr)
    session = TestSession(
        sut_name="my-sut",
        testing_system={"host": "localhost"},
        session_id="abc123",
        session_start_time=start,
        session_stop_time=stop,
        session_duration=None,
        session_tags={"env": "dev"},
        rerun_test_groups=[group],
        test_results=[tr],
    )
    d = session.to_dict()
    assert d["sut_name"] == "my-sut"
    assert d["session_id"] == "abc123"
    assert d["testing_system"]["host"] == "localhost"
    session2 = TestSession.from_dict(d)
    assert session2.sut_name == "my-sut"
    assert session2.session_id == "abc123"
    assert session2.testing_system["host"] == "localhost"
    assert session2.test_results[0].nodeid == "foo"
    assert session2.rerun_test_groups[0].nodeid == "foo"
    assert session2.session_start_time == start
    assert session2.session_stop_time == stop


def test_testsession_empty():
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=10)
    session = TestSession(
        sut_name=None,
        testing_system=None,
        session_id=None,
        session_start_time=start,
        session_stop_time=stop,
        session_duration=None,
        session_tags=None,
        rerun_test_groups=[],
        test_results=[],
    )
    d = session.to_dict()
    assert d["test_results"] == []
    assert d["rerun_test_groups"] == []


def test_testsession_from_dict_missing_fields():
    # Only required fields
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = start + timedelta(seconds=10)
    d = {
        "session_start_time": start.isoformat(),
        "session_stop_time": stop.isoformat(),
        "test_results": [],
        "rerun_test_groups": [],
    }
    session = TestSession.from_dict(d)
    assert session.session_start_time == start
    assert session.session_stop_time == stop
    assert session.test_results == []
    assert session.rerun_test_groups == []


def test_testsession_both_stop_and_duration_match(caplog):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    duration = 10.0
    stop = start + timedelta(seconds=duration)
    with caplog.at_level("WARNING"):
        session = TestSession(
            sut_name="test",
            testing_system=None,
            session_id="id",
            session_start_time=start,
            session_stop_time=stop,
            session_duration=duration,
            session_tags=None,
            rerun_test_groups=[],
            test_results=[],
        )
    # stop_time wins, duration is recomputed
    assert session.session_stop_time == stop
    assert session.session_duration == duration
    assert any("Ignoring session_duration" in r.message for r in caplog.records)


def test_testsession_both_stop_and_duration_mismatch(caplog):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    duration = 10.0
    stop = start + timedelta(seconds=8)  # mismatch
    with caplog.at_level("WARNING"):
        session = TestSession(
            sut_name="test",
            testing_system=None,
            session_id="id",
            session_start_time=start,
            session_stop_time=stop,
            session_duration=duration,
            session_tags=None,
            rerun_test_groups=[],
            test_results=[],
        )
    # stop_time wins, duration is recomputed
    assert session.session_stop_time == stop
    assert session.session_duration == 8.0
    assert any("Ignoring session_duration" in r.message for r in caplog.records)


"""
This test isn't quite right, and it might be more appropriate in test_plugin.py, because you want to run the
tests and then analyze the TestSession and RerunTestGroup objects.

def test_rerun_test_group_entries_identical_except_outcome():
    # Create a base TestResult
    base_result = TestResult(
        nodeid="test_demo.py::test_flaky[1]",
        outcome=TestOutcome.FAILED,
        start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        stop_time=datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc),
        duration=5.0,
        caplog="log1",
        capstderr="stderr1",
        capstdout="stdout1",
        longreprtext="longrepr1",
        has_warning=False,
    )
    # Create rerun variants with different outcomes
    rerun_results = [
        base_result,
        TestResult(**{**base_result.__dict__, "outcome": TestOutcome.RERUN}),
        TestResult(**{**base_result.__dict__, "outcome": TestOutcome.RERUN}),
        TestResult(**{**base_result.__dict__, "outcome": TestOutcome.RERUN}),
        TestResult(**{**base_result.__dict__, "outcome": TestOutcome.FAILED}),
    ]
    # Simulate rerun group
    rerun_group = RerunTestGroup(nodeid="test_demo.py::test_flaky[1]")
    rerun_group.add_test(base_result)
    rerun_group.add_test(TestResult(**{**base_result.__dict__, "outcome": TestOutcome.RERUN}))
    rerun_group.add_test(TestResult(**{**base_result.__dict__, "outcome": TestOutcome.RERUN}))
    rerun_group.add_test(TestResult(**{**base_result.__dict__, "outcome": TestOutcome.FAILED}))
    # Place all in test_results for TestSession
    session = TestSession(
        sut_name="test",
        testing_system=None,
        session_id="id",
        session_start_time=base_result.start_time,
        session_stop_time=base_result.stop_time,
        session_duration=base_result.duration,
        session_tags=None,
        rerun_test_groups=[rerun_group],
        test_results=rerun_results,
    )
    # For each rerun group, check all entries are identical except for outcome
    for group in session.rerun_test_groups:
        base = group.tests[0]
        for rerun in group.tests[1:]:
            # Compare all attributes except outcome
            for field in base.__dataclass_fields__:
                if field == "outcome":
                    continue
                assert getattr(rerun, field) == getattr(base, field), f"Mismatch in field {field}"
        # Check that all rerun group entries are present in test_results
        for rerun in group.tests:
            found = False
            for orig in session.test_results:
                if all(getattr(rerun, f) == getattr(orig, f) for f in rerun.__dataclass_fields__ if f != "outcome"):
                    found = True
                    break
            assert found, f"Rerun entry {rerun.nodeid} not found in test_results"
"""
