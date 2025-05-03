def test_pytest_addoption_help_message(tester):
    # Run pytest with --help and check for recap options
    result = tester.runpytest("--help")
    stdout = result.stdout.str() if hasattr(result.stdout, "str") else str(result.stdout)
    assert "--recap" in stdout
    assert "Enable pytest recap plugin." in stdout
    assert "--recap-destination" in stdout
    assert "Specify the storage destination" in stdout


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
                assert config._recap_destination is None
        """
        )
        result = tester.runpytest()
        result.assert_outcomes(passed=1)
    else:
        assert hasattr(config, "_recap_enabled")
        assert hasattr(config, "_recap_destination")
        assert config._recap_enabled is False
        assert config._recap_destination is None


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
