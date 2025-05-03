import os
import platform
import socket
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.terminal import TerminalReporter

from pytest_recap.models import RerunTestGroup, TestOutcome, TestResult, TestSession
from pytest_recap.storage import JSONStorage


def group_tests_into_rerun_test_groups(
    test_results: List[TestResult],
) -> List[RerunTestGroup]:
    rerun_test_groups: Dict[str, RerunTestGroup] = {}
    for test_result in test_results:
        if test_result.nodeid not in rerun_test_groups:
            rerun_test_groups[test_result.nodeid] = RerunTestGroup(nodeid=test_result.nodeid)
        rerun_test_groups[test_result.nodeid].add_test(test_result)
    return [group for group in rerun_test_groups.values() if len(group.tests) > 1]


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("Pytest Recap")
    group.addoption(
        "--recap",
        action="store_true",
        default=False,
        help="Enable pytest recap plugin.",
    )
    group.addoption(
        "--recap-destination",
        action="store",
        default=None,
        help="Specify the storage destination (filepath) for pytest-recap to use",
    )


def pytest_configure(config: Config) -> None:
    config._recap_enabled = config.getoption("--recap")
    config._recap_destination = config.getoption("--recap-destination")


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(terminalreporter: TerminalReporter, exitstatus: int, config: Config):
    yield

    if not getattr(config, "_recap_enabled", False):
        return

    # Get the destination URI if specified
    recap_destination = getattr(config, "_recap_destination", None)

    # Gather SUT and system info
    sut_name = os.environ.get("SBP_QA_NAME") or "pytest-recap"
    hostname = socket.gethostname()
    testing_system_name = hostname
    now = datetime.now(timezone.utc)
    session_start = None
    session_end = None

    test_results = []
    stats = terminalreporter.stats
    for outcome, reports in stats.items():
        if not outcome or outcome == "warnings":
            continue
        for report in reports:
            # Only handle TestReport instances with nodeid
            if not hasattr(report, "nodeid") or not hasattr(report, "when"):
                continue
            if report.when == "call" or (
                report.when in ("setup", "teardown") and getattr(report, "outcome", None) in ("failed", "error")
            ):
                # Use report.start if available, else fallback to now
                report_time = (
                    datetime.fromtimestamp(getattr(report, "start", now.timestamp()), tz=timezone.utc)
                    if hasattr(report, "start")
                    else now
                )
                if session_start is None or report_time < session_start:
                    session_start = report_time
                report_end = report_time + timedelta(seconds=getattr(report, "duration", 0) or 0)
                if session_end is None or report_end > session_end:
                    session_end = report_end
                test_results.append(
                    TestResult(
                        nodeid=report.nodeid,
                        outcome=TestOutcome.from_str(outcome) if outcome else TestOutcome.SKIPPED,
                        start_time=report_time,
                        stop_time=report_end,
                        duration=getattr(report, "duration", None),
                        caplog=getattr(report, "caplog", ""),
                        capstderr=getattr(report, "capstderr", ""),
                        capstdout=getattr(report, "capstdout", ""),
                        longreprtext=str(getattr(report, "longrepr", "")),
                        has_warning=bool(getattr(report, "warning_messages", [])),
                    )
                )

    # Handle warnings
    if "warnings" in stats:
        for report in stats["warnings"]:
            if hasattr(report, "nodeid"):
                for test_result in test_results:
                    if test_result.nodeid == report.nodeid:
                        test_result.has_warning = True
                        break

    # Create/process rerun test groups
    rerun_test_groups = group_tests_into_rerun_test_groups(test_results)

    session_timestamp = now.strftime("%Y%m%d-%H%M%S")
    session_id = f"{sut_name}-{session_timestamp}"
    if session_start and session_end:
        session_duration = (session_end - session_start).total_seconds()
    else:
        session_duration = 0.0

    session = TestSession(
        sut_name=sut_name,
        testing_system={
            "hostname": hostname,
            "name": testing_system_name,
            "type": "local",
            "sys_platform": sys.platform,
            "platform_platform": platform.platform(),
            "python_version": platform.python_version(),
            "pytest_version": getattr(config, "version", "unknown"),
            "environment": os.environ.get("TEST_ENV", "test"),
        },
        session_id=session_id,
        session_start_time=session_start,
        session_stop_time=session_end,
        session_duration=session_duration,
        session_tags={
            "tag_1": "value_1",
            "tag_2": "value_2",
            "tag_3": "value_3",
        },
        rerun_test_groups=rerun_test_groups,
        test_results=test_results,
    )

    # Determine the output file path
    if recap_destination:
        if os.path.isdir(recap_destination) or recap_destination.endswith("/"):
            os.makedirs(recap_destination, exist_ok=True)
            filename = f"{session_timestamp}_{sut_name}.json"
            filepath = os.path.join(recap_destination, filename)
        else:
            filepath = recap_destination
            parent_dir = os.path.dirname(filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
    else:
        base_dir = os.environ.get("SESSION_WRITE_BASE_DIR", "/tmp/pytest_recap_sessions")
        date_dir = os.path.join(base_dir, now.strftime("%Y/%m"))
        os.makedirs(date_dir, exist_ok=True)
        filename = f"{session_timestamp}_{sut_name}.json"
        filepath = os.path.join(date_dir, filename)

    # Write the session to file
    storage = JSONStorage(filepath)
    storage.save_session(session.to_dict())
    terminalreporter.write_sep("-")
    terminalreporter.write_line(f"Pytest Recap session written to: {filepath}")
