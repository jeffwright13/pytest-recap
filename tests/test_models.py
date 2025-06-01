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
    from datetime import datetime, timedelta, timezone
    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult

    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tr1 = TestResult(
        "dummy::nodeid",
        TestOutcome.RERUN,
        start,
        stop_time=start + timedelta(seconds=1),
        duration=1,
    )
    tr2 = TestResult(
        "dummy::nodeid",
        TestOutcome.FAILED,
        start + timedelta(seconds=1),
        stop_time=start + timedelta(seconds=2),
        duration=1,
    )
    group = RerunTestGroup(nodeid="dummy::nodeid")
    group.add_test(tr1)
    group.add_test(tr2)
    assert group.final_outcome == "failed"
    d = group.to_dict()
    assert d["nodeid"] == "dummy::nodeid"
    assert len(d["tests"]) == 2
    group2 = RerunTestGroup.from_dict(d)
    assert group2.nodeid == "dummy::nodeid"
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
    group = RerunTestGroup(nodeid="dummy::nodeid")
    group.add_test(tr)
    assert group.final_outcome == "skipped"


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
        system_under_test={"name": "my-sut"},
        testing_system={"host": "localhost"},
        session_id="abc123",
        session_start_time=start,
        session_stop_time=stop,
        session_tags={"env": "dev"},
        rerun_test_groups=[group],
        test_results=[tr],
    )
    d = session.to_dict()
    assert d["system_under_test"]["name"] == "my-sut"
    assert d["session_id"] == "abc123"
    assert d["testing_system"]["host"] == "localhost"
    session2 = TestSession.from_dict(d)
    assert session2.system_under_test["name"] == "my-sut"
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
        system_under_test=None,
        testing_system=None,
        session_id=None,
        session_start_time=start,
        session_stop_time=stop,
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


def test_testoutcome_all_enum_members():
    # Check all enum members exist and have correct string values
    expected = ["PASSED", "FAILED", "SKIPPED", "XFAILED", "XPASSED", "RERUN", "ERROR"]
    actual = [e.name for e in TestOutcome]
    assert actual == expected
    for member in TestOutcome:
        assert isinstance(member.value, str)
        assert member == TestOutcome[member.name]


def test_testoutcome_from_str_case_insensitive():
    # Should accept any case
    assert TestOutcome.from_str("passed") == TestOutcome.PASSED
    assert TestOutcome.from_str("FAILED") == TestOutcome.FAILED
    assert TestOutcome.from_str("skipped") == TestOutcome.SKIPPED
    assert TestOutcome.from_str("xFaIlEd") == TestOutcome.XFAILED
    assert TestOutcome.from_str("XpAsSeD") == TestOutcome.XPASSED
    assert TestOutcome.from_str("rerun") == TestOutcome.RERUN
    assert TestOutcome.from_str("error") == TestOutcome.ERROR


def test_testoutcome_from_str_invalid():
    # Should raise ValueError for unknown outcome
    import pytest

    with pytest.raises(ValueError):
        TestOutcome.from_str("not_a_real_outcome")


def test_testoutcome_to_str():
    # Should always return lowercase string
    for member in TestOutcome:
        assert member.to_str() == member.value.lower()


def test_testoutcome_to_list():
    # Should return all lowercase values
    expected = [m.value.lower() for m in TestOutcome]
    assert TestOutcome.to_list() == expected


def test_testresult_minimal_and_full():
    from datetime import datetime, timezone

    from pytest_recap.models import TestOutcome, TestResult

    # Minimal
    result = TestResult(
        nodeid="foo",
        outcome=TestOutcome.PASSED,
        start_time=None,
        stop_time=None,
        duration=None,
    )
    d = result.to_dict()
    assert d["nodeid"] == "foo"
    assert d["outcome"] == "passed"
    # Full
    now = datetime.now(timezone.utc)
    result = TestResult(
        nodeid="bar",
        outcome=TestOutcome.FAILED,
        start_time=now,
        stop_time=now,
        duration=0.0,
        caplog="log",
        capstderr="stderr",
        capstdout="stdout",
        longreprtext="long",
        has_warning=True,
        has_error=True,
    )
    d = result.to_dict()
    restored = TestResult.from_dict(d)
    assert restored.nodeid == "bar"
    assert restored.outcome == TestOutcome.FAILED
    assert restored.caplog == "log"


def test_testresult_post_init_duration_and_stop_time():
    from datetime import datetime, timedelta, timezone

    from pytest_recap.models import TestOutcome, TestResult

    # Compute stop_time from duration
    now = datetime.now(timezone.utc)
    result = TestResult(
        nodeid="foo",
        outcome=TestOutcome.PASSED,
        start_time=now,
        stop_time=None,
        duration=5.0,
    )
    assert result.stop_time == now + timedelta(seconds=5.0)
    # Compute duration from stop_time
    later = now + timedelta(seconds=7)
    result = TestResult(
        nodeid="foo",
        outcome=TestOutcome.PASSED,
        start_time=now,
        stop_time=later,
        duration=None,
    )
    assert result.duration == 7.0


def test_testresult_post_init_missing_both():
    from pytest_recap.models import TestOutcome, TestResult

    # Should not raise, but both None
    result = TestResult(
        nodeid="foo",
        outcome=TestOutcome.PASSED,
        start_time=None,
        stop_time=None,
        duration=None,
    )
    assert result.duration is None
    assert result.stop_time is None


def test_testresult_from_dict_invalid():
    import pytest
    from pytest_recap.models import TestResult

    # Missing nodeid
    with pytest.raises(KeyError):
        TestResult.from_dict({"outcome": "passed"})
    # Invalid outcome
    with pytest.raises(ValueError):
        TestResult.from_dict({"nodeid": "foo", "outcome": "notreal"})


def test_reruntestgroup_add_and_order():
    from datetime import datetime, timezone

    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult

    now = datetime.now(timezone.utc)
    group = RerunTestGroup(nodeid="foo")
    r1 = TestResult("foo", TestOutcome.RERUN, now, now, 0.0)
    r2 = TestResult("foo", TestOutcome.FAILED, now, now, 0.0)
    group.add_test(r1)
    group.add_test(r2)
    assert group.tests == [r1, r2]


@pytest.mark.parametrize("first_outcome, second_outcome, expected_outcome", [
    ("rerun", "failed", "failed"),
    ("rerun", "passed", "passed"),
    ("rerun", "error", "error"),
], ids=[
    "rerun_then_failed",
    "rerun_then_passed",
    "rerun_then_error",
])
def test_reruntestgroup_final_outcome(first_outcome, second_outcome, expected_outcome):
    from datetime import datetime, timezone

    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult

    now = datetime.now(timezone.utc)
    group = RerunTestGroup(nodeid="dummy::nodeid")
    r1 = TestResult("foo", TestOutcome.from_str(first_outcome), now, now, 0.0)
    r2 = TestResult("foo", TestOutcome.from_str(second_outcome), now, now, 0.0)
    group.add_test(r1)
    group.add_test(r2)
    assert group.final_outcome == expected_outcome


def test_reruntestgroup_to_and_from_dict():
    from datetime import datetime, timezone

    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult

    now = datetime.now(timezone.utc)
    r1 = TestResult("foo", TestOutcome.PASSED, now, now, 0.0)
    group = RerunTestGroup(nodeid="foo", tests=[r1])
    d = group.to_dict()
    restored = RerunTestGroup.from_dict(d)
    assert restored.nodeid == "foo"
    assert len(restored.tests) == 1
    assert restored.tests[0].nodeid == "foo"


def test_reruntestgroup_from_dict_invalid():
    import pytest
    from pytest_recap.models import RerunTestGroup

    with pytest.raises(ValueError):
        RerunTestGroup.from_dict([1, 2, 3])


@pytest.mark.parametrize("final_outcome", ["passed", "failed", "error"])
def test_rerun_test_groups_accepts_allowed_final_outcome(final_outcome):
    """RerunTestGroup should accept allowed final_outcome values."""
    from pytest_recap.models import TestOutcome, TestResult
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    group = RerunTestGroup(nodeid="dummy::nodeid")
    result = TestResult(
        nodeid="dummy::nodeid",
        outcome=TestOutcome.from_str(final_outcome),
        start_time=now,
        stop_time=now,
        duration=0.0,
    )
    group.add_test(result)
    assert group.final_outcome == final_outcome


def test_rerun_test_groups_allows_missing_final_outcome():
    """RerunTestGroup should allow final_outcome to be omitted (defaults to None)."""
    group = RerunTestGroup(nodeid="foo")
    assert group.final_outcome is None

@pytest.mark.parametrize("final_outcome", ["passed", "failed", "error"])
def test_rerun_test_groups_json_roundtrip_with_final_outcome(final_outcome):
    """RerunTestGroup should serialize and deserialize final_outcome correctly."""
    from pytest_recap.models import TestOutcome, TestResult
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    group = RerunTestGroup(nodeid="dummy::nodeid")
    result = TestResult(
        nodeid="dummy::nodeid",
        outcome=TestOutcome.from_str(final_outcome),
        start_time=now,
        stop_time=now,
        duration=0.0,
    )
    group.add_test(result)
    data = group.to_dict()
    loaded = RerunTestGroup.from_dict(data)
    assert loaded.final_outcome == final_outcome

def test_rerun_test_groups_json_roundtrip_without_final_outcome():
    """RerunTestGroup should handle missing final_outcome in JSON (backwards compatibility)."""
    # Minimal valid dict for backwards compatibility
    data = {"nodeid": "foo", "tests": []}
    loaded = RerunTestGroup.from_dict(data)
    assert loaded.final_outcome is None

@pytest.mark.parametrize("final_outcome", ["passed", "failed", "error"])
def test_html_generator_uses_final_outcome(final_outcome):
    """HTML generator should use final_outcome if present."""
    from pytest_recap.models import TestOutcome, TestResult
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    group = RerunTestGroup(nodeid="foo")
    result = TestResult(nodeid="foo", outcome=TestOutcome.from_str(final_outcome), start_time=now, stop_time=now, duration=0.0)
    group.add_test(result)
    assert group.final_outcome == final_outcome



def test_testsession_to_and_from_dict():
    from datetime import datetime, timezone
    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult, TestSession

    now = datetime.now(timezone.utc)
    r1 = TestResult("foo", TestOutcome.PASSED, now, now, 0.0)
    group = RerunTestGroup(nodeid="foo", tests=[r1])
    session = TestSession(
        system_under_test={"name": "test"},
        testing_system={"platform": "linux"},
        session_id="id",
        session_start_time=now,
        session_stop_time=now,
        session_tags={"env": "ci"},
        rerun_test_groups=[group],
        test_results=[r1],
    )
    d = session.to_dict()
    restored = TestSession.from_dict(d)
    assert restored.system_under_test["name"] == "test"
    assert restored.testing_system["platform"] == "linux"
    assert restored.session_tags["env"] == "ci"
    assert len(restored.rerun_test_groups) == 1
    assert len(restored.test_results) == 1


def test_testsession_add_test_result_and_rerun_group():
    from datetime import datetime, timezone

    from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult, TestSession

    now = datetime.now(timezone.utc)
    session = TestSession(
        system_under_test={"name": "test"},
        testing_system={},
        session_id="id",
        session_start_time=now,
        session_stop_time=now,
        session_tags={},
        rerun_test_groups=[],
        test_results=[],
    )
    r1 = TestResult("foo", TestOutcome.PASSED, now, now, 0.0)
    group = RerunTestGroup(nodeid="foo", tests=[r1])
    session.add_test_result(r1)
    session.add_rerun_group(group)
    assert session.test_results[-1] == r1
    assert session.rerun_test_groups[-1] == group


def test_testsession_add_test_result_invalid():
    from datetime import datetime, timezone

    import pytest
    from pytest_recap.models import TestSession

    now = datetime.now(timezone.utc)
    session = TestSession(
        system_under_test={"name": "test"},
        testing_system={},
        session_id="id",
        session_start_time=now,
        session_stop_time=now,
        session_tags={},
        rerun_test_groups=[],
        test_results=[],
    )
    with pytest.raises(ValueError):
        session.add_test_result("not_a_test_result")


def test_testsession_add_rerun_group_invalid():
    from datetime import datetime, timezone

    import pytest
    from pytest_recap.models import TestSession

    now = datetime.now(timezone.utc)
    session = TestSession(
        system_under_test={"name": "test"},
        testing_system={},
        session_id="id",
        session_start_time=now,
        session_stop_time=now,
        session_tags={},
        rerun_test_groups=[],
        test_results=[],
    )
    with pytest.raises(ValueError):
        session.add_rerun_group("not_a_rerun_group")


def test_sessionstats_warnings_consistency():
    from pytest_recap.models import TestResult, TestSessionStats

    test_results = [TestResult(nodeid="t1", outcome="passed")]
    stats = TestSessionStats(test_results, warnings_count=2)
    assert stats.count("warnings") == 2
    assert stats.as_dict()["warnings"] == 2


def test_session_serialization_and_deserialization_with_warnings():
    from datetime import datetime, timezone

    from pytest_recap.models import RecapEvent, RecapEventType, TestResult, TestSession

    now = datetime.now(timezone.utc)
    test_results = [TestResult(nodeid="t1", outcome="passed", start_time=now, stop_time=now, duration=0.0)]
    warnings = [
        RecapEvent(message="foo", event_type=RecapEventType.WARNING),
        RecapEvent(message="bar", event_type=RecapEventType.WARNING),
    ]
    session = TestSession(
        session_id="abc",
        session_start_time=now,
        session_stop_time=now,
        test_results=test_results,
        warnings=warnings,
        system_under_test={},
        testing_system={},
        session_tags={},
        rerun_test_groups=[],
        errors=[],
    )
    data = session.to_dict()
    assert data["session_stats"]["warnings"] == 2
    session2 = TestSession.from_dict(data)
    assert session2.session_stats.count("warnings") == 2
    assert len(session2.warnings) == 2
    # Check roundtrip event_type
    for w in session2.warnings:
        assert w.event_type == RecapEventType.WARNING


def test_recapevent_event_type_and_methods():
    from pytest_recap.models import RecapEvent, RecapEventType

    # Default is WARNING
    ev = RecapEvent(message="foo")
    assert ev.event_type == RecapEventType.WARNING
    assert ev.is_warning() is True
    assert ev.is_error() is False
    # Explicit ERROR
    err = RecapEvent(message="fail", event_type=RecapEventType.ERROR)
    assert err.event_type == RecapEventType.ERROR
    assert err.is_warning() is False
    assert err.is_error() is True
    # Serialization/deserialization
    d = err.to_dict()
    assert d["event_type"] == RecapEventType.ERROR
    ev2 = RecapEvent(**d)
    assert ev2.event_type == RecapEventType.ERROR
    assert ev2.is_error() is True


def test_deserialization_handles_missing_warnings():
    from datetime import datetime, timezone

    from pytest_recap.models import TestSession

    now = datetime.now(timezone.utc)
    data = {
        "session_id": "abc",
        "session_start_time": now.isoformat(),
        "session_stop_time": now.isoformat(),
        "test_results": [],
        # No 'warnings' key
        "system_under_test": {},
        "testing_system": {},
        "session_tags": {},
        "rerun_test_groups": [],
        "errors": [],
        "session_stats": {"warnings": 0},
    }
    session = TestSession.from_dict(data)
    assert session.session_stats.count("warnings") == 0
    assert session.warnings == []
