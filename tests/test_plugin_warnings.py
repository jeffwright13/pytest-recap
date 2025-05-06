"""
Tests for warning collection and recap plugin warning integration.
"""


def test_warning_collection(pytester):
    """Test that warnings are collected in pytest_recap.plugin.all_warnings."""
    # Create a test file that triggers a warning
    pytester.makepyfile(
        test_warns="""
        import warnings
        def test_warns():
            warnings.warn("my test warning", UserWarning)
        """
    )
    # Run pytest with recap plugin enabled
    pytester.runpytest("--recap")
    # Import the plugin's all_warnings after run
    from pytest_recap import plugin as recap_plugin

    # There should be at least one warning collected
    assert any(
        w.get("message") == "my test warning" and w.get("category") == "UserWarning" for w in recap_plugin.all_warnings
    )


def test_warning_in_recap_session(pytester):
    """Test that warnings appear in the recap session object if supported."""
    pytester.makepyfile(
        test_warns="""
        import warnings
        def test_warns():
            warnings.warn("session warning", RuntimeWarning)
        """
    )
    # Run pytest with recap plugin enabled
    pytester.runpytest("--recap")
    # Try to access recap session output if available
    # (Assumes plugin exposes or writes session data for test inspection)
    # This is a placeholder for integration logic; adjust to your actual recap output
    # For now, just check that the global warnings list contains the warning
    from pytest_recap import plugin as recap_plugin

    assert any(
        w.get("message") == "session warning" and w.get("category") == "RuntimeWarning"
        for w in recap_plugin.all_warnings
    )
