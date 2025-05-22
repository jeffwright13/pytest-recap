import json

import pytest
from pytest_recap.storage import JSONStorage


def test_e2e_basic_plugin_run(pytester, tmp_path):
    """E2E: Run pytest with recap enabled, verify recap file, and load with storage."""
    # Create a dummy test file
    pytester.makepyfile(
        """
        def test_success():
            assert 1 == 1
    """
    )
    recap_file = tmp_path / "recap.json"
    result = pytester.runpytest("--recap", f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1)
    # Verify recap file exists and structure
    assert recap_file.exists(), f"Recap file not found: {recap_file}"
    with open(recap_file) as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert data["test_results"][0]["outcome"] == "passed"
    # Load with storage in archive mode
    archive_file = tmp_path / "archive.json"
    storage = JSONStorage(file_path=archive_file)
    storage.save_session(data)  # append mode
    loaded = storage.load_sessions()
    assert any(s["session_id"] == data["session_id"] for s in loaded)


@pytest.mark.parametrize(
    "env,session_tags",
    [
        ("staging", {"ci": "github", "branch": "main"}),
        ("prod", {"ci": "gitlab", "branch": "release"}),
    ],
)
def test_e2e_env_and_tags(pytester, tmp_path, env, session_tags):
    """E2E: Run pytest with RECAP_ENV and RECAP_SESSION_TAGS set, verify output."""
    recap_file = tmp_path / "recap.json"
    pytester.makepyfile(
        """
        def test_env():
            assert True
    """
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_ENV", env)
    monkeypatch.setenv("RECAP_SESSION_TAGS", json.dumps(session_tags))
    result = pytester.runpytest(f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1)
    with open(recap_file) as f:
        data = json.load(f)
    print("\nRECAP JSON for env=", env, ":\n", json.dumps(data, indent=2))
    assert data["testing_system"]["environment"] == env
    # Only check that all user-supplied tags are present and correct
    for k, v in session_tags.items():
        assert data["session_tags"][k] == v
    # No duration field expected
    assert "session_duration" not in data
    monkeypatch.undo()


def test_e2e_invalid_session_tags(pytester, tmp_path):
    """E2E: Invalid RECAP_SESSION_TAGS falls back to defaults and prints warning."""
    recap_file = tmp_path / "recap.json"
    pytester.makepyfile(
        """
        def test_invalid_tags():
            assert True
    """
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_SESSION_TAGS", "not a dict")
    result = pytester.runpytest(f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1)
    with open(recap_file) as f:
        data = json.load(f)
    tags = data["session_tags"]
    assert tags == {}
    monkeypatch.undo()


def test_e2e_cli_overrides_env(pytester, tmp_path):
    """E2E: CLI flags should override environment variables."""
    recap_file = tmp_path / "cli.json"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RECAP_ENABLE", "0")
    monkeypatch.setenv("RECAP_DESTINATION", str(tmp_path / "should_not_use.json"))
    pytester.makepyfile(
        """
        def test_cli_override():
            assert True
    """
    )
    result = pytester.runpytest("--recap", f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1)
    assert recap_file.exists(), f"Recap file not found: {recap_file}"
    monkeypatch.undo()


def test_e2e_directory_destination(pytester, tmp_path):
    """E2E: Recap destination as directory should create recap file inside it."""
    recap_dir = tmp_path / "recap_dir"
    recap_dir.mkdir()
    pytester.makepyfile(
        """
        def test_dir_dest():
            assert True
    """
    )
    result = pytester.runpytest("--recap", f"--recap-destination={recap_dir}")
    result.assert_outcomes(passed=1)
    files = list(recap_dir.glob("*.json"))
    assert files, "No recap file created in directory"


def test_e2e_multiple_outcomes(pytester, tmp_path):
    """E2E: Recap file reflects pass, fail, skip outcomes."""
    recap_file = tmp_path / "recap.json"
    pytester.makepyfile(
        """
        import pytest
        def test_pass():
            assert True
        def test_fail():
            assert False
        @pytest.mark.skip(reason="skip reason")
        def test_skip():
            pass
    """
    )
    result = pytester.runpytest("--recap", f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1, failed=1, skipped=1)
    with open(recap_file) as f:
        data = json.load(f)
    outcomes = {tr["outcome"] for tr in data["test_results"]}
    assert {"passed", "failed", "skipped"}.issubset(outcomes)


def test_e2e_warning_on_invalid_tags(pytester, tmp_path, capfd):
    """E2E: Invalid RECAP_SESSION_TAGS prints warning to terminal."""
    recap_file = tmp_path / "recap.json"
    pytester.makepyfile(
        """
        def test_warn():
            assert True
    """
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_SESSION_TAGS", "not a dict")
    result = pytester.runpytest(f"--recap-destination={recap_file}")
    result.assert_outcomes(passed=1)
    out, err = capfd.readouterr()
    assert "WARNING: Invalid RECAP_SESSION_TAGS" in out or "WARNING: RECAP_SESSION_TAGS must be a JSON object" in out
    monkeypatch.undo()


def test_e2e_archive_growth(pytester, tmp_path):
    """E2E: Appending multiple sessions to archive file accumulates all sessions."""
    from pytest_recap.storage import JSONStorage

    archive_file = tmp_path / "archive.json"
    session_ids = []
    for i in range(3):
        recap_file = tmp_path / f"recap_{i}.json"
        pytester.makepyfile(
            f"""
            def test_{i}():
                assert True
        """
        )
        result = pytester.runpytest("--recap", f"--recap-destination={recap_file}")
        result.assert_outcomes(passed=1)
        with open(recap_file) as f:
            data = json.load(f)
        session_ids.append(data["session_id"])
        storage = JSONStorage(file_path=archive_file)
        storage.save_session(data)
    loaded = JSONStorage(file_path=archive_file).load_sessions()
    loaded_ids = {s["session_id"] for s in loaded}
    assert set(session_ids).issubset(loaded_ids)


def test_e2e_outcome_accounting(pytester, tmp_path):
    """
    E2E: Recap file outcome counts should match pytest's internal stats (pass, fail, skip, xfail, xpass, error, warning).
    This test intentionally fails if the plugin omits any outcome.
    """
    recap_file = tmp_path / "recap.json"
    pytester.makepyfile(
        """
        import pytest
        def test_pass():
            pass
        def test_fail():
            assert False
        @pytest.mark.skip(reason="skip reason")
        def test_skip():
            pass
        @pytest.mark.xfail(reason="expected fail")
        def test_xfail():
            assert False
        @pytest.mark.xfail(reason="unexpected pass")
        def test_xpass():
            assert True
        def test_error():
            raise RuntimeError("error!")
        def test_warn():
            import warnings
            warnings.warn("warn!", UserWarning)
        """
    )
    result = pytester.runpytest("--recap", f"--recap-destination={recap_file}")
    # Get stats from pytest terminalreporter
    stats = result.parseoutcomes()
    # Read recap file
    import json

    with open(recap_file) as f:
        data = json.load(f)
    # Count outcomes in recap file
    from collections import Counter

    recap_counts = Counter(tr["outcome"] for tr in data["test_results"])
    # Map pytest stats keys to recap outcomes
    mapping = {
        "passed": "passed",
        "failed": "failed",
        "skipped": "skipped",
        "xfailed": "xfailed",
        "xpassed": "xpassed",
        "error": "error",
    }
    # Compare counts
    mismatches = []
    for stat_key, recap_key in mapping.items():
        pytest_count = stats.get(stat_key, 0)
        recap_count = recap_counts.get(recap_key, 0)
        if pytest_count != recap_count:
            mismatches.append((stat_key, pytest_count, recap_key, recap_count))
    assert not mismatches, f"Outcome mismatch: {mismatches}\nPytest stats: {stats}\nRecap: {recap_counts}"
