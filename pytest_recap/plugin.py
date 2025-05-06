import json
import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.reports import TestReport
from _pytest.terminal import TerminalReporter

from pytest_recap.models import RerunTestGroup, TestResult, TestSession
from pytest_recap.storage import JSONStorage

# --- Global storage for all warnings --- #
all_warnings = []


def pytest_addoption(parser: Parser) -> None:
    """Add command line options for pytest-recap, supporting environment variable defaults.

    Args:
        parser (Parser): The pytest parser object.
    """
    group = parser.getgroup("Pytest Recap")
    recap_env = os.environ.get("RECAP_ENABLE", "0").lower()
    recap_default = recap_env in ("1", "true", "yes", "y")
    group.addoption(
        "--recap",
        action="store_true",
        default=recap_default,
        help="Enable pytest-recap plugin (or set environment variable RECAP_ENABLE)",
    )
    recap_dest_env = os.environ.get("RECAP_DESTINATION")
    recap_dest_default = recap_dest_env or ""
    group.addoption(
        "--recap-destination",
        action="store",
        default=recap_dest_default,
        help="Specify pytest-recap storage destination (filepath) (or set environment variable RECAP_DESTINATION)",
    )


def pytest_configure(config: Config) -> None:
    """Configure pytest-recap plugin.

    Args:
        config (Config): The pytest config object.
    """
    config._recap_enabled = config.getoption("--recap")
    config._recap_destination = config.getoption("--recap-destination")


def pytest_warning_recorded(warning_message, when, nodeid, location):
    """Collect warnings for the recap session.

    Args:
        warning_message (WarningMessage): The warning message object.
        when (str): When the warning was recorded.
        nodeid (str): The node ID of the test that generated the warning.
        location (tuple): The location of the warning.

    (Note: this signatuire supports Pyetst 6.2.5+)
    """
    all_warnings.append(
        {
            "message": str(warning_message.message),
            "category": warning_message.category.__name__,
            "when": when,
            "nodeid": nodeid,
            "location": location,
        }
    )


# --- pytest-recap-specific functions only used internally --- #
def collect_test_results_and_session_times(
    terminalreporter: TerminalReporter,
) -> Tuple[List[TestResult], datetime, datetime]:
    """Collect test results and session times from the terminal reporter.

    Args:
        terminalreporter (TerminalReporter): The terminal reporter object.
    Returns:
        tuple: A tuple containing the list of test results, session start time, and session end time.
    """
    stats = terminalreporter.stats
    test_results = []
    session_start = None
    session_end = None

    def to_dt(val):
        return datetime.fromtimestamp(val, timezone.utc) if val is not None else None

    for outcome, reports in stats.items():
        if not outcome or outcome == "warnings":
            continue
        for report in reports:
            if not isinstance(report, TestReport):
                continue
            # Always include skipped, xfailed, xpassed, error, etc.
            if report.when == "call" or (
                report.when in ("setup", "teardown") and report.outcome in ("failed", "error", "skipped")
            ):
                report_time = to_dt(getattr(report, "start", None) or getattr(report, "starttime", None))
                report_end = to_dt(getattr(report, "stop", None) or getattr(report, "stoptime", None))
                if session_start is None or (report_time and report_time < session_start):
                    session_start = report_time
                if session_end is None or (report_end and report_end > session_end):
                    session_end = report_end
                test_results.append(
                    {
                        "nodeid": report.nodeid,
                        "outcome": outcome,
                        "longreprtext": str(getattr(report, "longrepr", "")),
                        "start_time": report_time,
                        "stop_time": report_end,
                    }
                )
    session_start = session_start or datetime.now(timezone.utc)
    session_end = session_end or datetime.now(timezone.utc)
    return test_results, session_start, session_end


def collect_warnings(terminalreporter: TerminalReporter) -> List[str]:
    """Collect warnings from the terminal reporter.

    Args:
        terminalreporter (TerminalReporter): The terminal reporter object.
    Returns:
        list: List of warning messages.
    """
    stats = terminalreporter.stats
    warnings = []
    if "warnings" in stats:
        for report in stats["warnings"]:
            # Use whatever structure your warnings expect
            warnings.append(str(getattr(report, "message", getattr(report, "longrepr", ""))))
    return warnings


def build_rerun_groups(test_results: List[TestResult]) -> List[RerunTestGroup]:
    """Build a list of RerunTestGroup objects from a list of test results.

    Args:
        test_results (list): List of TestResult objects.
    Returns:
        list: List of RerunTestGroup objects, each containing reruns for a nodeid.
    """
    test_result_objs = [
        TestResult(
            nodeid=tr["nodeid"],
            outcome=tr["outcome"],
            longreprtext=tr["longreprtext"],
            start_time=tr["start_time"],
            stop_time=tr["stop_time"],
        )
        for tr in test_results
    ]
    rerun_test_groups: Dict[str, RerunTestGroup] = {}
    for test_result in test_result_objs:
        if test_result.nodeid not in rerun_test_groups:
            rerun_test_groups[test_result.nodeid] = RerunTestGroup(nodeid=test_result.nodeid)
        rerun_test_groups[test_result.nodeid].add_test(test_result)
    return [group for group in rerun_test_groups.values() if len(group.tests) > 1]


def build_recap_session(test_results, session_start, session_end, warnings, rerun_groups, terminalreporter, config):
    """
    Build a TestSession object summarizing the test session.

    Args:
        test_results (list): List of test result dicts.
        session_start (datetime): Session start time.
        session_end (datetime): Session end time.
        warnings (list): List of warnings.
        rerun_groups (list): List of RerunTestGroup objects.
        terminalreporter: Pytest terminal reporter.
        config: Pytest config object.
    Returns:
        TestSession: The constructed test session object.
    Notes:
        - Session tags are loaded from the RECAP_SESSION_TAGS environment variable. If not set or invalid, defaults to an empty dict `{}`.
    """
    from pytest_recap.models import TestResult

    hostname = socket.gethostname()
    sut_name = os.environ.get("SBP_QA_NAME") or "pytest-recap"
    testing_system_name = hostname
    session_timestamp = session_start.strftime("%Y%m%d-%H%M%S")
    session_id = f"{sut_name}-{session_timestamp}-{str(uuid.uuid4())[:8]}".lower()
    # Session tags logic (can be improved or made more dynamic)
    tags_env = os.environ.get("RECAP_SESSION_TAGS")
    if not tags_env:
        session_tags = {}
    else:
        try:
            session_tags = json.loads(tags_env)
            if not isinstance(session_tags, dict):
                terminalreporter.write_line("WARNING: RECAP_SESSION_TAGS must be a JSON object. Using empty dict.")
                session_tags = {}
        except Exception:
            terminalreporter.write_line("WARNING: Invalid RECAP_SESSION_TAGS: Using empty dict {}.")
            session_tags = {}
    environment = os.environ.get("RECAP_ENV", "test")
    test_result_objs = [TestResult.from_dict(tr) for tr in test_results]
    session = TestSession(
        session_id=session_id,
        session_tags=session_tags,
        sut_name=sut_name,
        testing_system={
            "hostname": hostname,
            "name": testing_system_name,
            "type": "local",
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "pytest_version": pytest.__version__,
            "environment": environment,
        },
        session_start_time=session_start,
        session_stop_time=session_end,
        test_results=test_result_objs,
        rerun_test_groups=rerun_groups,
        warnings=warnings,
        errors=[],
    )
    return session


def write_recap_file(session, destination, terminalreporter):
    """
    Write the recap session data to a file in JSON format.

    Args:
        session (TestSession): The session recap object to write.
        destination (str): File or directory path for output. If None, a default location is used.
        terminalreporter: Pytest terminal reporter for output.
    Raises:
        Exception: If writing the recap file fails.
    """
    recap_data = session.to_dict()
    now = datetime.now(timezone.utc)

    # Determine the output file path
    if destination:
        if os.path.isdir(destination) or destination.endswith("/"):
            os.makedirs(destination, exist_ok=True)
            filename = f"{now.strftime('%Y%m%d-%H%M%S')}_{session.sut_name}.json"
            filepath = os.path.join(destination, filename)
        else:
            filepath = destination
            parent_dir = os.path.dirname(filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
    else:
        base_dir = os.environ.get("SESSION_WRITE_BASE_DIR", os.path.expanduser("~/.pytest_recap_sessions"))
        date_dir = os.path.join(base_dir, now.strftime("%Y/%m"))
        os.makedirs(date_dir, exist_ok=True)
        filename = f"{now.strftime('%Y%m%d-%H%M%S')}_{session.sut_name}.json"
        filepath = os.path.join(date_dir, filename)
    try:
        storage = JSONStorage(filepath)
        storage.save_single_session(recap_data)
    except Exception as e:
        terminalreporter.write_line(f"RECAP PLUGIN ERROR: {e}")
        raise

    # Write recap file path to terminal
    terminalreporter.write_sep("=", "pytest-recap")
    BLUE = "\033[34m"
    RESET = "\033[0m"
    blue_path = f"Recap JSON written to: {BLUE}{filepath}{RESET}"
    terminalreporter.write_line(blue_path)


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(terminalreporter: TerminalReporter, exitstatus: int, config: Config) -> None:
    """Hook into pytest's terminal summary to collect test results and write recap file."""
    yield

    if not getattr(config, "_recap_enabled", False):
        return

    test_results, session_start, session_end = collect_test_results_and_session_times(terminalreporter)
    warnings = collect_warnings(terminalreporter)
    rerun_groups = build_rerun_groups(test_results)
    session = build_recap_session(
        test_results, session_start, session_end, warnings, rerun_groups, terminalreporter, config
    )
    write_recap_file(session, getattr(config, "_recap_destination", None), terminalreporter)
