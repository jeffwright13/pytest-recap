import ast
import json
import logging
import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Dict, Generator, List, Optional, Tuple
from warnings import WarningMessage

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from _pytest.terminal import TerminalReporter

from pytest_recap.cloud import upload_to_cloud
from pytest_recap.models import RecapEvent, RerunTestGroup, TestResult, TestSession, TestSessionStats
from pytest_recap.storage import JSONStorage

# --- Global warning collection. This is required because Pytest hook pytest-warning-recorded
# does not pass the Config object, so it cannot be used to store warnings.
_collected_warnings = []


# --- pytest hooks --- #
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
    if recap_dest_env:
        recap_dest_default = recap_dest_env
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        default_dir = os.path.expanduser("~/.pytest-recap-sessions")
        os.makedirs(default_dir, exist_ok=True)
        recap_dest_default = os.path.join(default_dir, f"{timestamp}-recap.json")
    group.addoption(
        "--recap-destination",
        action="store",
        default=recap_dest_default,
        help="Specify pytest-recap storage destination (filepath) (or set environment variable RECAP_DESTINATION)",
    )
    group.addoption(
        "--recap-system-under-test",
        action="store",
        default=None,
        help="JSON or Python dict string for system under test metadata (or set RECAP_SYSTEM_UNDER_TEST)",
    )
    group.addoption(
        "--recap-testing-system",
        action="store",
        default=None,
        help="JSON or Python dict string for testing system metadata (or set RECAP_TESTING_SYSTEM)",
    )
    group.addoption(
        "--recap-session-tags",
        action="store",
        default=None,
        help="JSON or Python dict string for session tags (or set RECAP_SESSION_TAGS)",
    )
    group.addoption(
        "--recap-pretty",
        action="store_true",
        default=None,
        help="Pretty-print recap JSON output (or set RECAP_PRETTY=1, or ini: recap_pretty=1)",
    )

    parser.addini("recap_system_under_test", "System under test dict (JSON or Python dict string)", default="")
    parser.addini("recap_testing_system", "Testing system dict (JSON or Python dict string)", default="")
    parser.addini("recap_session_tags", "Session tags dict (JSON or Python dict string)", default="")
    parser.addini("recap_pretty", "Pretty-print recap JSON output (1 for pretty, 0 for minified)", default="0")


def pytest_configure(config: Config) -> None:
    """Configure pytest-recap plugin.

    Args:
        config (Config): The pytest Config object.
    """
    config._recap_enabled: bool = config.getoption("--recap")
    config._recap_destination: str = config.getoption("--recap-destination")
    pretty = get_recap_option(config, "recap_pretty", "recap_pretty", "RECAP_PRETTY", default="0")
    config._recap_pretty: bool = str(pretty).strip().lower() in {"1", "true", "yes", "y"}


def pytest_sessionstart(session):
    """Reset collected warnings at the start of each test session."""
    global _collected_warnings
    _collected_warnings = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo) -> Generator:
    """Hook into pytest's test report generation to generate start and stop times, if not set already."""
    outcome = yield

    logger = logging.getLogger(__name__)

    report: TestReport = outcome.get_result()
    if report.when == "setup" and not hasattr(report, "start"):
        logger.warning(f"Setting start time for {report.nodeid} since it was not set previously")
        setattr(report, "start", datetime.now(timezone.utc).timestamp())

    if report.when == "teardown" and not hasattr(report, "stop"):
        logger.warning(f"Setting stop time for {report.nodeid} since it was not set previously")
        setattr(report, "stop", datetime.now(timezone.utc).timestamp())


def pytest_warning_recorded(warning_message: WarningMessage, when: str, nodeid: str, location: tuple):
    """Collect warnings during pytest session for recap reporting.

    Args:
        warning_message (WarningMessage): The warning message object.
        when (str): When the warning was recorded (e.g., 'call', 'setup', etc.).
        nodeid (str): Node ID of the test (if any).
        location (tuple): Location tuple (filename, lineno, function).
    """
    _collected_warnings.append(
        RecapEvent(
            nodeid=nodeid,
            when=when,
            message=str(warning_message.message),
            category=getattr(warning_message.category, "__name__", str(warning_message.category)),
            filename=warning_message.filename,
            lineno=warning_message.lineno,
            location=location,
        )
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(terminalreporter: TerminalReporter, exitstatus: int, config: Config) -> None:
    """Hook into pytest's terminal summary to collect test results, errors, warnings, and write recap file.

    Args:
        terminalreporter (TerminalReporter): The pytest terminal reporter object.
        exitstatus (int): Exit status of the pytest session.
        config (Config): The pytest config object.
    """
    yield

    if not getattr(config, "_recap_enabled", False):
        return

    test_results_tuple: Tuple[List[TestResult], datetime, datetime] = collect_test_results_and_session_times(
        terminalreporter
    )
    test_results, session_start, session_end = test_results_tuple
    rerun_groups: List[RerunTestGroup] = build_rerun_groups(test_results)

    errors = [
        RecapEvent(
            nodeid=getattr(rep, "nodeid", None),
            when=getattr(rep, "when", None),
            outcome=getattr(rep, "outcome", None),
            longrepr=str(getattr(rep, "longrepr", "")),
            sections=list(getattr(rep, "sections", [])),
            keywords=list(getattr(rep, "keywords", [])),
            # message, category, filename, lineno, location use defaults
        )
        for rep in terminalreporter.stats.get("error", [])
    ]

    warnings = _collected_warnings.copy()

    session: TestSession = build_recap_session(
        test_results, session_start, session_end, rerun_groups, errors, warnings, terminalreporter, config
    )
    # Print summary of warnings and errors using RecapEvent helpers
    warning_count = sum(bool(w.is_warning()) for w in warnings)
    error_count = sum(bool(e.is_error()) for e in errors)
    terminalreporter.write_sep("-", f"Recap: {warning_count} warnings, {error_count} errors collected")

    # Optionally, print details
    if warning_count > 0:
        terminalreporter.write_line("\nWarnings:")
        for w in warnings:
            if w.is_warning():
                terminalreporter.write_line(f"  {w.filename}:{w.lineno} [{w.category}] {w.message}")
    if error_count > 0:
        terminalreporter.write_line("\nErrors:")
        for e in errors:
            if e.is_error():
                terminalreporter.write_line(f"  {e.nodeid} [{e.when}] {e.longrepr}")

    write_recap_file(session, getattr(config, "_recap_destination", None), terminalreporter)


# --- pytest-recap-specific functions, only used internally --- #
def to_datetime(val: Optional[float]) -> Optional[datetime]:
    """Convert a timestamp to a datetime object.

    Args:
        val (Optional[float]): The timestamp to convert.

    Returns:
        Optional[datetime]: The datetime object, or None if the timestamp is None.
    """
    return datetime.fromtimestamp(val, timezone.utc) if val is not None else None


def collect_test_results_and_session_times(
    terminalreporter: TerminalReporter,
) -> Tuple[List[TestResult], datetime, datetime]:
    """Collect test results and session times from the terminal reporter.

    Args:
        terminalreporter (TerminalReporter): The terminal reporter object.

    Returns:
        tuple: A tuple containing the list of test results, session start time, and session end time.
    """
    stats: Dict[str, List[TestReport]] = terminalreporter.stats
    test_results: List[TestResult] = []
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None

    for outcome, report_list in stats.items():
        # Skip orocessing '' outcomes (which are for setup phase), and 'warnings'
        # (which we count warnings elsewhere, in pytest_warning_recorded)
        if not outcome or outcome == "warnings":
            continue

        for report in report_list:
            if not isinstance(report, TestReport):
                continue

            # Only process 'call' phase, and 'setup'/'teardown' phases for failed, error, or skipped tests
            # TODO: why did i do this again?
            if report.when == "call" or (
                report.when in ("setup", "teardown") and report.outcome in ("failed", "error", "skipped")
            ):
                # Get start and end times from TestReport, and store them as datetime objects
                report_time = to_datetime(getattr(report, "start", None) or getattr(report, "starttime", None))
                report_end = to_datetime(getattr(report, "stop", None) or getattr(report, "stoptime", None))

                # Update session start and end times if necessary
                if session_start is None or (report_time and report_time < session_start):
                    session_start = report_time
                if session_end is None or (report_end and report_end > session_end):
                    session_end = report_end

                # longrepr can be a string, and object or None; whereas capstdout, capstderr, and caplog
                # are always strings
                longrepr = getattr(report, "longrepr", "")
                longreprtext = str(longrepr) if longrepr is not None else ""
                capstdout = getattr(report, "capstdout", "")
                capstderr = getattr(report, "capstderr", "")
                caplog = getattr(report, "caplog", "")

                # Create TestResult object and append to list to return
                test_results.append(
                    {
                        "nodeid": report.nodeid,
                        "outcome": outcome,
                        "start_time": report_time,
                        "stop_time": report_end,
                        "longreprtext": longreprtext,
                        "capstdout": capstdout,
                        "capstderr": capstderr,
                        "caplog": caplog,
                    }
                )

    # Set session start and end times to either the times found in the test results or the current time
    session_start = session_start or datetime.now(timezone.utc)
    session_end = session_end or datetime.now(timezone.utc)

    return test_results, session_start, session_end


def build_rerun_groups(test_results: List[TestResult]) -> List[RerunTestGroup]:
    """Build a list of RerunTestGroup objects from a list of test results.

    Args:
        test_results (list): List of TestResult objects.

    Returns:
        list: List of RerunTestGroup objects, each containing reruns for a nodeid.

    """
    test_result_objs = [
        TestResult(
            nodeid=test_result["nodeid"],
            outcome=test_result["outcome"],
            longreprtext=test_result["longreprtext"],
            start_time=test_result["start_time"],
            stop_time=test_result["stop_time"],
        )
        for test_result in test_results
    ]
    rerun_test_groups: Dict[str, RerunTestGroup] = {}
    for test_result in test_result_objs:
        if test_result.nodeid not in rerun_test_groups:
            rerun_test_groups[test_result.nodeid] = RerunTestGroup(nodeid=test_result.nodeid)
        rerun_test_groups[test_result.nodeid].add_test(test_result)
    return [group for group in rerun_test_groups.values() if len(group.tests) > 1]


def parse_dict_option(
    option_value: str,
    default: dict,
    option_name: str,
    terminalreporter: TerminalReporter,
    envvar: str = None,
    source: str = None,
) -> dict:
    """Parse a recap option string value into a Python dict.
    Supports both JSON and Python dict literal formats.
    Returns the provided default if parsing fails.
    """
    if not option_value:
        return default
    try:
        return json.loads(option_value)
    except Exception:
        pass
    try:
        return ast.literal_eval(option_value)
    except Exception as e:
        src = f" from {source}" if source else ""
        env_info = f" (env var: {envvar})" if envvar else ""
        msg = (
            f"WARNING: Invalid RECAP_{option_name.upper()} value{src}{env_info}: {option_value!r}. "
            f"Could not parse as dict: {e}. Using default."
        )
        if terminalreporter:
            terminalreporter.write_line(msg)
        else:
            print(msg)
        return default


def get_recap_option(config: Config, opt: str, ini: str, envvar: str, default: str = "") -> str:
    """Retrieve the raw option value for a recap option from CLI, environment variable, pytest.ini, or default.
    This function is responsible for determining the source (precedence order: CLI > env > ini > default),
    but does NOT parse the value into a dict—it always returns a string.

    Args:
        config (Config): The pytest Config object.
        opt (str): The option name (the pytest cmd-line flag).
        ini (str): The ini option name (the pytest ini file option).
        envvar (str): The environment variable name.
        default (str, optional): The default value. Defaults to "".

    Returns:
        str: The option value to use.
    """
    cli_val = getattr(config.option, opt, None)
    if cli_val is not None and str(cli_val).strip() != "":
        return cli_val
    env_val = os.environ.get(envvar)
    if env_val is not None and str(env_val).strip() != "":
        return env_val
    ini_val = config.getini(ini)
    # If ini_val is a list (possible for ini options), join to string
    if isinstance(ini_val, list):
        ini_val = " ".join(str(x) for x in ini_val).strip()
    if ini_val is not None and str(ini_val).strip() != "":
        return ini_val.strip()
    return default


def build_recap_session(
    test_results: List[TestResult],
    session_start: datetime,
    session_end: datetime,
    rerun_groups: List[RerunTestGroup],
    errors: List[Dict],
    warnings: List[Dict],
    terminalreporter: TerminalReporter,
    config: Config,
) -> TestSession:
    """Build a TestSession object summarizing the test session.

    Args:
        test_results (list): List of test result dicts.
        session_start (datetime): Session start time.
        session_end (datetime): Session end time.
        rerun_groups (list): List of RerunTestGroup objects.
        terminalreporter: Pytest terminal reporter.
        config: Pytest config object.

    Returns:
        TestSession: The constructed test session object.

    Notes:
        - session_tags, system_under_test, and testing_system can be set via CLI, env, or pytest.ini.

    """
    session_timestamp: str = session_start.strftime("%Y%m%d-%H%M%S")
    session_id: str = f"{session_timestamp}-{str(uuid.uuid4())[:8]}".lower()

    # Session tags
    session_tags = parse_dict_option(
        get_recap_option(config, "recap_session_tags", "recap_session_tags", "RECAP_SESSION_TAGS"),
        {},
        "session_tags",
        terminalreporter,
    )
    if not isinstance(session_tags, dict):
        session_tags = {}

    # System Under Test
    system_under_test = parse_dict_option(
        get_recap_option(config, "recap_system_under_test", "recap_system_under_test", "RECAP_SYSTEM_UNDER_TEST"),
        {"name": "pytest-recap"},
        "system_under_test",
        terminalreporter,
        envvar="RECAP_SYSTEM_UNDER_TEST",
    )
    if not isinstance(system_under_test, dict):
        system_under_test = {"name": "pytest-recap"}

    # Testing System
    default_testing_system = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "pytest_version": pytest.__version__,
        "environment": os.environ.get("RECAP_ENV", "test"),
    }
    testing_system = parse_dict_option(
        get_recap_option(config, "recap_testing_system", "recap_testing_system", "RECAP_TESTING_SYSTEM"),
        default_testing_system,
        "testing_system",
        terminalreporter,
        envvar="RECAP_TESTING_SYSTEM",
    )
    if not isinstance(testing_system, dict):
        testing_system = default_testing_system

    # Session tags
    session_tags = parse_dict_option(
        get_recap_option(config, "recap_session_tags", "recap_session_tags", "RECAP_SESSION_TAGS"),
        {},
        "session_tags",
        terminalreporter,
    )
    if not isinstance(session_tags, dict):
        session_tags = {}

    # Session stats
    test_result_objs: List[TestResult] = [TestResult.from_dict(test_result) for test_result in test_results]
    session_stats = TestSessionStats(test_result_objs, warnings_count=len(warnings))

    # Build and return session
    session = TestSession(
        session_id=session_id,
        session_tags=session_tags,
        system_under_test=system_under_test,
        testing_system=testing_system,
        session_start_time=session_start,
        session_stop_time=session_end,
        test_results=test_result_objs,
        rerun_test_groups=rerun_groups,
        errors=errors,
        warnings=warnings,
        session_stats=session_stats,
    )
    return session


def write_recap_file(session: TestSession, destination: str, terminalreporter: TerminalReporter):
    """Write the recap session data to a file in JSON format.

    Args:
        session (TestSession): The session recap object to write.
        destination (str): File or directory path for output. If None, a default location is used.
        terminalreporter: Pytest terminal reporter for output.

    Raises:
        Exception: If writing the recap file fails.

    """
    recap_data: Dict = session.to_dict()
    now: datetime = datetime.now(timezone.utc)
    pretty: bool = getattr(getattr(terminalreporter, "config", None), "_recap_pretty", False)
    indent: Optional[int] = 2 if pretty else None
    json_bytes: bytes = json.dumps(recap_data, indent=indent).encode("utf-8")

    # Cloud URI detection and dispatch
    if destination and (
        destination.startswith("s3://")
        or destination.startswith("gs://")
        or destination.startswith("azure://")
        or destination.startswith("https://")
    ):
        try:
            upload_to_cloud(destination, json_bytes)
            filepath = destination
        except Exception as e:
            terminalreporter.write_line(f"RECAP PLUGIN ERROR (cloud upload): {e}")
            filepath = destination  # Still print the path for test assertions
    else:
        # Determine the output file path (local)
        if destination:
            if os.path.isdir(destination) or destination.endswith("/"):
                os.makedirs(destination, exist_ok=True)
                filename = f"{now.strftime('%Y%m%d-%H%M%S')}_{getattr(session, 'system_under_test', {}).get('name', 'sut')}.json"
                filepath = os.path.join(destination, filename)
            else:
                filepath = destination
                parent_dir = os.path.dirname(filepath)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
        else:
            base_dir = os.environ.get("SESSION_WRITE_BASE_DIR", os.path.expanduser("~/.pytest_recap_sessions"))
            base_dir = os.path.abspath(base_dir)
            date_dir = os.path.join(base_dir, now.strftime("%Y/%m"))
            os.makedirs(date_dir, exist_ok=True)
            filename = (
                f"{now.strftime('%Y%m%d-%H%M%S')}_{getattr(session, 'system_under_test', {}).get('name', 'sut')}.json"
            )
            filepath = os.path.join(date_dir, filename)
            filepath = os.path.abspath(filepath)
        try:
            storage = JSONStorage(filepath)
            # Pass indent to storage for pretty/minified output
            storage.save_single_session(recap_data, indent=indent)
        except Exception as e:
            terminalreporter.write_line(f"RECAP PLUGIN ERROR: {e}")
            raise

    # Write recap file path/URI to terminal
    terminalreporter.write_sep("=", "pytest-recap")
    BLUE = "\033[34m"
    RESET = "\033[0m"

    # Print cloud URI directly if applicable, else absolute file path
    def is_cloud_uri(uri):
        return isinstance(uri, str) and (
            uri.startswith("s3://") or uri.startswith("gs://") or uri.startswith("azure://")
        )

    recap_uri = filepath if is_cloud_uri(filepath) else os.path.abspath(filepath)
    blue_path = f"Recap JSON written to: {BLUE}{recap_uri}{RESET}"
    terminalreporter.write_line(blue_path)
