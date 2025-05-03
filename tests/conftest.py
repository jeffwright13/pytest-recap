from importlib.metadata import version

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def tester(request):
    """Version-agnostic fixture that returns appropriate test directory fixture (pytester or testdir)."""
    pytest_version = version("pytest")
    fixture_name = "pytester" if pytest_version >= "7.0" else "testdir"
    return request.getfixturevalue(fixture_name)
