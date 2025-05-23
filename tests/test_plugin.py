import json

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
                # The recap destination should always be set to a file path ending with -recap.json
                assert isinstance(config._recap_destination, str)
                assert config._recap_destination.endswith("-recap.json")
        """
        )
        result = tester.runpytest()
        result.assert_outcomes(passed=1)
    else:
        try:
            assert hasattr(config, "_recap_enabled")
            assert hasattr(config, "_recap_destination")
            assert config._recap_enabled is False
            # The recap destination should always be set to a file path ending with -recap.json
            assert isinstance(config._recap_destination, str)
            assert config._recap_destination.endswith("-recap.json")
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
    # Set RECAP_DESTINATION to a known file in tmp_path
    recap_file = tmp_path / "custom_recap.json"
    monkeypatch.setenv("RECAP_DESTINATION", str(recap_file))
    tester.makepyfile(
        """
        def test_dummy():
            assert True
        """
    )
    result = tester.runpytest("--recap")
    result.assert_outcomes(passed=1)
    # Check that the file was written
    assert recap_file.exists(), f"Expected recap file at {recap_file}"
    content = recap_file.read_text().strip()
    assert content, f"Expected recap file {recap_file} to be non-empty"


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


@pytest.mark.parametrize(
    "cli,env,ini,expected",
    [
        # CLI wins
        ('{"name": "cli"}', '{"name": "env"}', '{"name": "ini"}', {"name": "cli"}),
        # Env wins over ini
        ("", '{"name": "env"}', '{"name": "ini"}', {"name": "env"}),
        # Ini fallback
        ("", "", '{"name": "ini"}', {"name": "ini"}),
        # Default fallback
        ("", "", "", {"name": "pytest-recap"}),
        # Python dict string
        ("{'name': 'cli-dict'}", "", "", {"name": "cli-dict"}),
    ],
)
def test_system_under_test_precedence(monkeypatch, tester, tmp_path, cli, env, ini, expected):
    monkeypatch.setenv("RECAP_ENABLE", "1")
    dest_file = tmp_path / "recap-sut.json"
    if env:
        monkeypatch.setenv("RECAP_SYSTEM_UNDER_TEST", env)
    if ini:
        tester.makeini(f"[pytest]\nrecap_system_under_test = {ini}\n")
    tester.makepyfile("def test_dummy(): assert True\n")
    args = [f"--recap-destination={dest_file}"]
    if cli:
        args += ["--recap-system-under-test", cli]
    result = tester.runpytest(*args)
    result.assert_outcomes(passed=1)
    assert dest_file.exists()
    data = json.loads(dest_file.read_text())
    assert data["system_under_test"] == expected


@pytest.mark.parametrize(
    "cli,env,ini,expected",
    [
        ('{"host": "cli"}', '{"host": "env"}', '{"host": "ini"}', {"host": "cli"}),
        ("", '{"host": "env"}', '{"host": "ini"}', {"host": "env"}),
        ("", "", '{"host": "ini"}', {"host": "ini"}),
        ("", "", "", None),  # Will check for default keys
        ("{'host': 'cli-dict'}", "", "", {"host": "cli-dict"}),
    ],
)
def test_testing_system_precedence(monkeypatch, tester, tmp_path, cli, env, ini, expected):
    monkeypatch.setenv("RECAP_ENABLE", "1")
    dest_file = tmp_path / "recap-tsys.json"
    if env:
        monkeypatch.setenv("RECAP_TESTING_SYSTEM", env)
    if ini:
        tester.makeini(f"[pytest]\nrecap_testing_system = {ini}\n")
    tester.makepyfile("def test_dummy(): assert True\n")
    args = [f"--recap-destination={dest_file}"]
    if cli:
        args += ["--recap-testing-system", cli]
    result = tester.runpytest(*args)
    result.assert_outcomes(passed=1)
    assert dest_file.exists()
    data = json.loads(dest_file.read_text())
    if expected is not None:
        assert all(item in data["testing_system"].items() for item in expected.items())
    else:
        # Should have default keys
        for key in ["hostname", "platform", "python_version", "pytest_version", "environment"]:
            assert key in data["testing_system"]


@pytest.mark.parametrize(
    "cli,env,ini,expected",
    [
        ('{"tag": "cli"}', '{"tag": "env"}', '{"tag": "ini"}', {"tag": "cli"}),
        ("", '{"tag": "env"}', '{"tag": "ini"}', {"tag": "env"}),
        ("", "", '{"tag": "ini"}', {"tag": "ini"}),
        ("", "", "", {}),
        ("{'tag': 'cli-dict'}", "", "", {"tag": "cli-dict"}),
    ],
)
def test_session_tags_precedence(monkeypatch, tester, tmp_path, cli, env, ini, expected):
    monkeypatch.setenv("RECAP_ENABLE", "1")
    dest_file = tmp_path / "recap-tags.json"
    if env:
        monkeypatch.setenv("RECAP_SESSION_TAGS", env)
    if ini:
        tester.makeini(f"[pytest]\nrecap_session_tags = {ini}\n")
    tester.makepyfile("def test_dummy(): assert True\n")
    args = [f"--recap-destination={dest_file}"]
    if cli:
        args += ["--recap-session-tags", cli]
    result = tester.runpytest(*args)
    result.assert_outcomes(passed=1)
    assert dest_file.exists()
    data = json.loads(dest_file.read_text())
    assert data["session_tags"] == expected


@pytest.mark.parametrize(
    "opt,envvar,expected_key",
    [
        ("--recap-system-under-test", "RECAP_SYSTEM_UNDER_TEST", "system_under_test"),
        ("--recap-testing-system", "RECAP_TESTING_SYSTEM", "testing_system"),
        ("--recap-session-tags", "RECAP_SESSION_TAGS", "session_tags"),
    ],
)
def test_invalid_json(monkeypatch, tester, tmp_path, opt, envvar, expected_key):
    monkeypatch.setenv("RECAP_ENABLE", "1")
    dest_file = tmp_path / "recap-invalid.json"
    monkeypatch.setenv(envvar, "not a dict")
    tester.makepyfile("def test_dummy(): assert True\n")
    args = [f"--recap-destination={dest_file}"]
    result = tester.runpytest(*args)
    result.assert_outcomes(passed=1)
    data = json.loads(dest_file.read_text())
    # Should fallback to default
    if expected_key == "system_under_test":
        assert data[expected_key]["name"] == "pytest-recap"
    elif expected_key == "testing_system":
        for key in ["hostname", "platform", "python_version", "pytest_version", "environment"]:
            assert key in data[expected_key]
    else:
        assert data[expected_key] == {}


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
    mock_upload = mocker.patch("pytest_recap.plugin.upload_to_cloud")
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


@pytest.mark.parametrize(
    "cli_flag,env_val,ini_val,should_pretty",
    [
        ("--recap-pretty", None, None, True),  # CLI flag
        (None, "1", None, True),  # ENV var
        (None, None, "1", True),  # INI option
        (None, None, None, False),  # Default (minified)
        (None, "0", None, False),  # ENV explicitly off
        (None, None, "0", False),  # INI explicitly off
    ],
)
def test_recap_pretty_and_minified(monkeypatch, tester, tmp_path, cli_flag, env_val, ini_val, should_pretty):
    dest_file = tmp_path / "recap-pretty.json"
    monkeypatch.setenv("RECAP_ENABLE", "1")
    if env_val is not None:
        monkeypatch.setenv("RECAP_PRETTY", env_val)
    if ini_val is not None:
        tester.makeini(f"[pytest]\nrecap_pretty = {ini_val}\n")
    tester.makepyfile("def test_dummy(): assert True\n")
    args = [f"--recap-destination={dest_file}"]
    if cli_flag:
        args.append(cli_flag)
    result = tester.runpytest(*args)
    result.assert_outcomes(passed=1)
    assert dest_file.exists()
    text = dest_file.read_text()
    # Pretty JSON will have newlines and indents, minified will not
    if should_pretty:
        assert text.count("\n") > 1, "Expected pretty output with newlines"
        assert text.startswith("{\n") or text.startswith("{\r\n")
    else:
        assert text.count("\n") <= 1, "Expected minified output"
        assert text.replace(" ", "").startswith('{"')
