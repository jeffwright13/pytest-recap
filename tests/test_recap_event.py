from pytest_recap.models import RecapEvent, RecapEventType


def test_recap_event_warning_to_dict():
    warning = RecapEvent(
        nodeid="mytest.py::test_warn",
        when="call",
        message="This is a warning!",
        category="UserWarning",
        filename="mytest.py",
        lineno=42,
        location=("mytest.py", 42, "test_warn"),
        event_type=RecapEventType.WARNING,
    )
    d = warning.to_dict()
    assert d["nodeid"] == "mytest.py::test_warn"
    assert d["when"] == "call"
    assert d["message"] == "This is a warning!"
    assert d["category"] == "UserWarning"
    assert d["filename"] == "mytest.py"
    assert d["lineno"] == 42
    assert d["location"] == ("mytest.py", 42, "test_warn")
    # Error-specific fields should be None or default
    assert d["outcome"] is None
    assert d["longrepr"] is None
    assert d["sections"] == []
    assert d["keywords"] == []
    # Check is_warning/is_error
    assert warning.is_warning()
    assert not warning.is_error()


def test_recap_event_error_to_dict():
    error = RecapEvent(
        nodeid="mytest.py::test_fail",
        when="call",
        outcome="failed",
        longrepr="AssertionError: fail",
        sections=[("Captured stdout call", "output")],
        keywords=["fail", "mytest"],
        event_type=RecapEventType.ERROR,
    )
    d = error.to_dict()
    assert d["nodeid"] == "mytest.py::test_fail"
    assert d["when"] == "call"
    assert d["outcome"] == "failed"
    assert d["longrepr"] == "AssertionError: fail"
    assert d["sections"] == [("Captured stdout call", "output")]
    assert d["keywords"] == ["fail", "mytest"]
    # Warning-specific fields should be None
    assert d["message"] is None
    assert d["category"] is None
    assert d["filename"] is None
    assert d["lineno"] is None
    assert d["location"] is None
    # Check is_warning/is_error
    assert not error.is_warning()
    assert error.is_error()


def test_recap_event_summary_helpers():
    warning = RecapEvent(message="warn", category="UserWarning", event_type=RecapEventType.WARNING)
    error = RecapEvent(outcome="failed", longrepr="fail", event_type=RecapEventType.ERROR)
    info = RecapEvent(
        message="info", category=None, outcome="passed", event_type=RecapEventType.WARNING
    )  # treat as warning for now
    events = [warning, error, info]
    warning_count = sum(1 for e in events if e.is_warning())
    error_count = sum(1 for e in events if e.is_error())
    assert warning_count == 2  # warning + info (since default is WARNING)
    assert error_count == 1
