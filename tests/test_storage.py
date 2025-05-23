import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pytest_recap.models import TestOutcome, TestResult, TestSession
from pytest_recap.storage import JSONStorage


def make_session(session_id="test-123", start=None, stop=None):
    start = start or datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    stop = stop or (start + timedelta(seconds=10))
    tr = TestResult(
        nodeid="foo",
        outcome=TestOutcome.PASSED,
        start_time=start,
        stop_time=start + timedelta(seconds=2),
        duration=2,
    )
    return TestSession(
        system_under_test={"name": "my-sut"},
        testing_system={"host": "localhost"},
        session_id=session_id,
        session_start_time=start,
        session_stop_time=stop,
        session_tags={"env": "dev"},
        rerun_test_groups=[],
        test_results=[tr],
    )


def test_save_and_load_session(tmp_path):
    file_path = tmp_path / "sessions.json"
    storage = JSONStorage(file_path=file_path)
    session = make_session()
    storage.save_session(session.to_dict())
    loaded = storage.load_sessions()
    assert len(loaded) == 1
    assert loaded[0]["session_id"] == "test-123"


def test_default_file_path(tmp_path, monkeypatch):
    # Patch Path.home to tmp_path for isolation
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    storage = JSONStorage()
    session = make_session()
    storage.save_session(session.to_dict())
    assert (tmp_path / ".pytest_recap" / "sessions.json").exists()


def test_path_override(tmp_path):
    custom_path = tmp_path / "custom.json"
    storage = JSONStorage(file_path=custom_path)
    session = make_session(session_id="override")
    storage.save_session(session.to_dict())
    assert custom_path.exists()
    data = json.loads(custom_path.read_text())
    assert any(s["session_id"] == "override" for s in data)


def test_handles_missing_and_corrupt_file(tmp_path):
    file_path = tmp_path / "bad.json"
    storage = JSONStorage(file_path=file_path)
    # Should not crash on missing file
    assert storage.load_sessions() == []
    # Write corrupt JSON
    file_path.write_text("{bad json}")
    assert storage.load_sessions() == []


def test_concurrent_access(tmp_path):
    file_path = tmp_path / "sessions.json"
    storage = JSONStorage(file_path=file_path)
    session = make_session()

    def writer():
        for _ in range(10):
            storage.save_session(session.to_dict())

    threads = [threading.Thread(target=writer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Should have 50 sessions (5 threads x 10 writes)
    loaded = storage.load_sessions()
    assert len(loaded) == 50


def test_data_integrity(tmp_path):
    file_path = tmp_path / "sessions.json"
    storage = JSONStorage(file_path=file_path)
    session = make_session(session_id="integrity")
    storage.save_session(session.to_dict())
    loaded = storage.load_sessions()
    assert loaded[0]["session_id"] == "integrity"
    # Save another
    session2 = make_session(session_id="integrity2")
    storage.save_session(session2.to_dict())
    loaded = storage.load_sessions()
    ids = [s["session_id"] for s in loaded]
    assert "integrity" in ids and "integrity2" in ids


def test_storage_file_is_directory(tmp_path):
    dir_path = tmp_path / "sessions.json"
    dir_path.mkdir()
    storage = JSONStorage(file_path=dir_path)
    # Should handle gracefully and not crash
    with pytest.raises((IsADirectoryError, OSError, PermissionError)):
        storage.save_session({"foo": "bar"})


def test_storage_permission_error(tmp_path):
    import pytest

    file_path = tmp_path / "sessions.json"
    file_path.write_text("[]")
    # Make the directory unwritable
    tmp_path.chmod(0o500)
    try:
        storage = JSONStorage(file_path=file_path)
        with pytest.raises(PermissionError):
            storage.save_session({"foo": "bar"})
    finally:
        # Restore permissions so pytest can clean up
        tmp_path.chmod(0o700)


def test_storage_file_is_dict(tmp_path):
    file_path = tmp_path / "sessions.json"
    file_path.write_text(json.dumps({"not": "a list"}))
    storage = JSONStorage(file_path=file_path)
    assert storage.load_sessions() == []


def test_storage_partial_write(tmp_path):
    file_path = tmp_path / "sessions.json"
    file_path.write_text("[{}")  # Truncated JSON
    storage = JSONStorage(file_path=file_path)
    assert storage.load_sessions() == []


def test_storage_non_serializable(tmp_path):
    file_path = tmp_path / "sessions.json"
    storage = JSONStorage(file_path=file_path)

    class NotSerializable:
        pass

    with pytest.raises(TypeError):
        storage.save_session({"obj": NotSerializable()})


def test_storage_bulk_sessions(tmp_path):
    import json

    file_path = tmp_path / "sessions.json"
    big_list = [make_session(session_id=f"id-{i}").to_dict() for i in range(1000)]
    file_path.write_text(json.dumps(big_list))
    storage = JSONStorage(file_path=file_path)
    loaded = storage.load_sessions()
    assert len(loaded) == 1000


def test_storage_append_sessions(tmp_path):
    storage = JSONStorage(file_path=tmp_path / "sessions.json")
    big_list = [make_session(session_id=f"id-{i}").to_dict() for i in range(200)]
    for session in big_list:
        storage.save_session(session)
    loaded = storage.load_sessions()
    assert len(loaded) == 200


def test_storage_minified_and_pretty(tmp_path):
    data = {"foo": [1, 2, 3], "bar": {"baz": "qux"}}
    file_min = tmp_path / "minified.json"
    file_pretty = tmp_path / "pretty.json"

    # Minified (indent=None)
    storage_min = JSONStorage(file_path=file_min)
    storage_min.save_single_session(data, indent=None)
    minified = file_min.read_text()
    assert minified.count("\n") <= 1
    assert minified.replace(" ", "").startswith('{"foo"')

    # Pretty (indent=2)
    storage_pretty = JSONStorage(file_path=file_pretty)
    storage_pretty.save_single_session(data, indent=2)
    pretty = file_pretty.read_text()
    assert pretty.count("\n") > 1
    assert pretty.startswith("{\n") or pretty.startswith("{\r\n")
