import random
import sys
import warnings

import pytest

# 3 consecutive ZWS
ZWS_X3 = r"""​​​"""
# 1 BOM followed by 1 ZWS
BOM_ZWS = r"""￼​"""
# 3 consecutive ZWJ
ZWJ_X3 = r"""‍‍‍"""
# 1 BOM followed by 1 ZWJ
BOM_ZWJ = r"""￼‍"""


def test0_1_pass_capturing(capsys, fake_data, logger):
    logger.info(ZWS_X3)
    print("FAIL this stdout is captured")
    print("FAIL this stderr is captured", file=sys.stderr)
    logger.warning("FAIL this log is captured")
    with capsys.disabled():
        print("FAIL stdout not captured, going directly to sys.stdout")
        print("FAIL stderr not captured, going directly to sys.stderr", file=sys.stderr)
        logger.warning("FAIL is this log captured?")
    print("FAIL this stdout is also captured")
    print("FAIL this stderr is also captured", file=sys.stderr)
    logger.warning("FAIL this log is also captured")
    # logger.critical(fake_data)
    # logger.error(fake_data)
    # logger.warning(fake_data)
    logger.info(fake_data)
    # logger.debug(fake_data)
    # logger.info(ZWJ_X3)
    assert True


def test0_1_fail_capturing(capsys, fake_data, logger):
    logger.info(ZWS_X3)
    print("FAIL this stdout is captured")
    print("FAIL this stderr is captured", file=sys.stderr)
    logger.warning("FAIL this log is captured")
    with capsys.disabled():
        print("FAIL stdout not captured, going directly to sys.stdout")
        print("FAIL stderr not captured, going directly to sys.stderr", file=sys.stderr)
        logger.warning("FAIL is this log captured?")
    print("FAIL this stdout is also captured")
    print("FAIL this stderr is also captured", file=sys.stderr)
    logger.warning("FAIL this log is also captured")
    logger.critical(fake_data)
    logger.error(fake_data)
    # logger.warning(fake_data)
    logger.info(fake_data)
    # logger.debug(fake_data)
    # logger.info(ZWJ_X3)
    assert False


def test_with_warning(recwarn):
    warnings.warn("something!")
    assert any("something!" in str(w.message) for w in recwarn)




@pytest.fixture
def error_fixture(logger):
    raise Exception("Error in fixture")





@pytest.mark.skip(reason="Skipping this test with decorator.")
def test0_skip(logger, capstdlog):
    logger.info("Skipping!")
    logs = capstdlog.text
    assert "Skipping!" in logs
    assert True


@pytest.mark.xfail()
def test0_xfail(logger, capstderr):
    print("Test 0 XFail")
    print("XFail to stderr!", file=sys.stderr)
    err = capstderr.readouterr().err
    assert "XFail to stderr!" in err
    logger.info(ZWS_X3)
    logger.critical("CRITICAL")
    logger.error("ERROR")
    logger.warning("WARNING")
    logger.info("INFO")
    logger.debug("DEBUG")
    logger.info(ZWJ_X3)
    assert False


@pytest.mark.xfail(reason="Demonstrate XPASS (unexpected pass)")
def test0_xpass_demo():
    """This test is expected to fail, but will pass (XPASS)."""
    assert True


@pytest.mark.xfail()
def test0_xpass(logger, capstdout):
    print("Test 0 XPass")
    out = capstdout.readouterr().out
    assert "Test 0 XPass" in out
    logger.warning("WARNING")
    logger.info("INFO")
    logger.debug("DEBUG")
    logger.info(ZWJ_X3)
    assert True


# Method and its test that causes warnings
def api_v1():
    warnings.warn(UserWarning("api v1, should use functions from v2"))
    return 1


def test0_warning(capstdlog):
    import warnings

    warnings.warn("Test warning from test0_warning!")
    assert True
    assert api_v1() == 1


# Has a 1 in 8 chance of failing after 3 reruns
@pytest.mark.flaky(reruns=3)
def test_flaky_3(capstderr):
    print("Flaky test running", file=sys.stderr)
    err = capstderr.readouterr().err
    assert "Flaky test running" in err
    assert random.choice([True, False])


@pytest.mark.flaky(reruns=2)
def test_always_rerun(tmp_path):
    state_file = tmp_path / "rerun_state.txt"
    if not state_file.exists():
        state_file.write_text("fail")
        assert False, "Fail first run"
    else:
        assert True
