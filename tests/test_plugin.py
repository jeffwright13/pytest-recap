import pytest


def test_pytest_addoption_help_message(tester):
    # Run pytest with --help and check for recap options
    result = tester.runpytest("--help")
    help_output = result.stdout.str() if hasattr(result.stdout, "str") else str(result.stdout)
    # Accept either variant for help message
    assert "Enable recap plugin" in help_output or "enable recap plugin" in help_output or "recap plugin" in help_output
    assert (
        "Destination for recap output" in help_output
        or "destination for recap output" in help_output
        or "recap output" in help_output
        or "Specify the storage destination" in help_output
        or "--recap-destination" in help_output
        or "pytest-recap storage destination" in help_output
        or "RECAP_DESTINATION" in help_output
        or "storage destination" in help_output
    )


def test_pytest_addoption_defaults(tester):
    # Run a dummy test and check that recap options are set to their defaults
    tester.makepyfile(
        """
        def test_dummy():
            pass
    """
    )
    result = tester.runpytest()
    # Access the config object from the test session
    config = result.session.config if hasattr(result, "session") and hasattr(result.session, "config") else None
    # If config is not available, rerun with a plugin that inspects config
    if config is None:
        # Use a conftest.py to inspect config
        tester.makeconftest(
            """
            def pytest_sessionfinish(session):
                config = session.config
                assert hasattr(config, "_recap_enabled")
                assert hasattr(config, "_recap_destination")
                assert config._recap_enabled is False
                assert config._recap_destination in (None, "")
        """
        )
        result = tester.runpytest()
        result.assert_outcomes(passed=1)
    else:
        try:
            assert hasattr(config, "_recap_enabled")
            assert hasattr(config, "_recap_destination")
            assert config._recap_enabled is False
            assert config._recap_destination in (None, "")
        except ValueError:
            pytest.skip("Pytest terminal summary report not found; skipping test.")


def test_pytest_addoption_set_values(tester):
    # Run pytest with recap options set
    tester.makepyfile(
        """
        def test_dummy():
            pass
    """
    )
    result = tester.runpytest("--recap", "--recap-destination=custom.json")
    # Access the config object from the test session
    config = result.session.config if hasattr(result, "session") and hasattr(result.session, "config") else None
    if config is None:
        # Use a conftest.py to inspect config
        tester.makeconftest(
            """
            def pytest_sessionfinish(session):
                config = session.config
                assert config._recap_enabled is True
                assert config._recap_destination == "custom.json"
        """
        )
        result = tester.runpytest("--recap", "--recap-destination=custom.json")
        result.assert_outcomes(passed=1)
    else:
        assert config._recap_enabled is True
        assert config._recap_destination == "custom.json"


def test_recap_destination_file_written(tester, tmp_path):
    # Create a simple test file
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    # Use a temp file for the destination
    dest_file = tmp_path / "recap-session.json"
    result = tester.runpytest("--recap", f"--recap-destination={dest_file}")
    # Should pass
    result.assert_outcomes(passed=1)
    # Check that the recap file exists and is not empty
    assert dest_file.exists(), f"Expected recap file {dest_file} to exist"
    content = dest_file.read_text().strip()
    assert content, f"Expected recap file {dest_file} to be non-empty"


def test_recap_destination_directory_written(tester, tmp_path):
    # Create a simple test file
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    # Use a temp directory for the destination
    dest_dir = tmp_path / "recap_dir"
    dest_dir.mkdir()
    result = tester.runpytest("--recap", f"--recap-destination={dest_dir}")
    result.assert_outcomes(passed=1)
    # Check for a .json file written to dest_dir
    json_files = list(dest_dir.glob("*.json"))
    assert json_files, f"Expected at least one .json file in {dest_dir}"
    for file in json_files:
        content = file.read_text().strip()
        assert content, f"Expected recap file {file} to be non-empty"


def test_recap_default_env_dir_written(tester, monkeypatch, tmp_path):
    # Patch SESSION_WRITE_BASE_DIR to a temp directory
    base_dir = tmp_path / "custom_sess_dir"
    monkeypatch.setenv("SESSION_WRITE_BASE_DIR", str(base_dir))
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest("--recap")
    result.assert_outcomes(passed=1)
    # Should have written to base_dir/YYYY/MM/<session_timestamp>_pytest-recap.json
    # Find the correct subdirectory
    from datetime import datetime

    now = datetime.now()
    date_dir = base_dir / now.strftime("%Y/%m")
    json_files = list(date_dir.glob("*.json"))
    assert json_files, f"Expected at least one .json file in {date_dir}"
    for file in json_files:
        content = file.read_text().strip()
        assert content, f"Expected recap file {file} to be non-empty"


def test_recap_env_enable(monkeypatch, tester):
    """Test that RECAP_ENABLE enables the plugin if CLI flag is absent."""
    monkeypatch.setenv("RECAP_ENABLE", "1")
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest()
    # Check that _recap_enabled is True
    tester.makeconftest(
        """
        def pytest_sessionfinish(session):
            config = session.config
            assert config._recap_enabled is True
    """
    )
    result = tester.runpytest()
    result.assert_outcomes(passed=1)


def test_recap_env_destination(monkeypatch, tester, tmp_path):
    """Test that RECAP_DESTINATION sets the destination if CLI flag is absent."""
    dest_file = tmp_path / "recap-env.json"
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_DESTINATION", str(dest_file))
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest()
    result.assert_outcomes(passed=1)
    assert dest_file.exists(), f"Expected recap file {dest_file} to exist"
    assert dest_file.read_text().strip(), f"Expected recap file {dest_file} to be non-empty"


def test_recap_cli_overrides_env(monkeypatch, tester, tmp_path):
    """Test that CLI flags override environment variables."""
    monkeypatch.setenv("RECAP_ENABLE", "0")
    monkeypatch.setenv("RECAP_DESTINATION", str(tmp_path / "should_not_use.json"))
    dest_file = tmp_path / "cli.json"
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest("--recap", f"--recap-destination={dest_file}")
    result.assert_outcomes(passed=1)
    assert dest_file.exists(), f"Expected recap file {dest_file} to exist"
    assert dest_file.read_text().strip(), f"Expected recap file {dest_file} to be non-empty"


def test_recap_disabled_by_default(monkeypatch, tester):
    """Test that both env and CLI off disables the plugin."""
    monkeypatch.delenv("RECAP_ENABLE", raising=False)
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    tester.makeconftest(
        """
        def pytest_sessionfinish(session):
            config = session.config
            assert config._recap_enabled is False
    """
    )
    result = tester.runpytest()
    result.assert_outcomes(passed=1)


def test_recap_env_and_tags(monkeypatch, tester, tmp_path):
    """Test RECAP_ENV and RECAP_SESSION_TAGS environment variables."""
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_ENV", "staging")
    tags = {"ci": "github", "branch": "main", "build": "123"}
    import json

    dest_file = tmp_path / "session-env-tags.json"
    monkeypatch.setenv("RECAP_SESSION_TAGS", json.dumps(tags))
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest(f"--recap-destination={dest_file}")
    result.assert_outcomes(passed=1)
    # Now check the file directly
    assert dest_file.exists(), f"Recap file was not created: {dest_file}"
    with open(dest_file) as f:
        data = json.load(f)
    print(f"DEBUG: Recap file content: {data}")
    assert isinstance(data, dict), f"Expected dict, got {type(data)}: {data}"
    assert data["testing_system"]["environment"] == "staging"
    assert data["session_tags"] == tags


def test_recap_session_tags_invalid(monkeypatch, tester, tmp_path):
    """Test fallback to default tags if RECAP_SESSION_TAGS is invalid."""
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_SESSION_TAGS", "not a dict")
    dest_file = tmp_path / "session-tags-invalid.json"
    tester.makepyfile(
        """
        def test_dummy():
            assert True
    """
    )
    result = tester.runpytest(f"--recap-destination={dest_file}")
    result.assert_outcomes(passed=1)
    assert dest_file.exists(), f"Recap file was not created: {dest_file}"
    import json

    with open(dest_file) as f:
        data = json.load(f)
    tags = data["session_tags"]
    assert tags == {}


@pytest.mark.parametrize(
    "cloud_uri",
    [
        "s3://mybucket/recap-session.json",
        "gs://mybucket/recap-session.json",
        "azure://mycontainer/recap-session.json",
    ],
)
def test_recap_cloud_destination(monkeypatch, tester, mocker, cloud_uri):
    """
    Test that specifying a cloud URI as recap destination triggers cloud upload
    and prints the URI in the terminal output.
    """
    mock_upload = mocker.patch("pytest_recap.cloud.upload_to_cloud")
    monkeypatch.setenv("RECAP_ENABLE", "1")
    monkeypatch.setenv("RECAP_DESTINATION", cloud_uri)
    tester.makepyfile(
        """
        def test_dummy():
            assert True
        """
    )
    result = tester.runpytest()
    result.assert_outcomes(passed=1)
    # Ensure cloud upload was called with correct URI and bytes
    assert mock_upload.called, f"Expected upload_to_cloud to be called for {cloud_uri}"
    args, kwargs = mock_upload.call_args
    assert args[0] == cloud_uri
    assert isinstance(args[1], bytes)
    # Ensure the terminal output mentions the cloud URI
    assert cloud_uri in result.stdout.str()
