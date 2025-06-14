import pytest
import time
import logging
import warnings

logger = logging.getLogger("demo")

@pytest.fixture
def noisy_fixture():
    print("fixture stdout")
    logger.info("fixture log")
    warnings.warn("fixture warning", UserWarning)
    yield
    print("teardown stdout")
    logger.info("teardown log")

def test_pass(noisy_fixture):
    print("passing stdout")
    logger.info("passing log")
    warnings.warn("passing warning", UserWarning)
    time.sleep(0.2)
    assert True

def test_fail(noisy_fixture):
    print("failing stdout")
    logger.info("failing log")
    warnings.warn("failing warning", UserWarning)
    time.sleep(0.3)
    assert False, "Intentional failure"

@pytest.mark.skip(reason="demonstrate skip")
def test_skip():
    time.sleep(0.1)

@pytest.mark.xfail(reason="expected fail", strict=True)
def test_xfail():
    time.sleep(0.15)
    assert False

@pytest.mark.xfail(reason="unexpected pass", strict=False)
def test_xpass():
    time.sleep(0.15)
    assert True

@pytest.mark.flaky(reruns=1)
def test_rerun():
    # Fails first, passes second
    if not hasattr(test_rerun, "called"):
        test_rerun.called = True
        time.sleep(0.1)
        assert False, "fail for rerun"
    time.sleep(0.1)
    assert True

@pytest.fixture
def error_fixture():
    raise Exception("Error in fixture")

def test_error(error_fixture):
    time.sleep(0.1)
    logger.error("ERROR")
    raise RuntimeError("Intentional error outside assert")


def test_warning():
    time.sleep(0.1)
    warnings.warn("explicit test warning", UserWarning)

def test_long_output():
    print("Long output the first..." * 50)
    logger.warning("Long output the second..." * 50)
    time.sleep(0.2)
    assert True

def test_stdout_stderr():
    import sys
    print("some stdout")
    print("some stderr", file=sys.stderr)
    time.sleep(0.1)
    assert True
