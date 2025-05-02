"""Models for test session data.

Core models:
1. TestOutcome - Enum for test result outcomes
2. TestResult - Single test execution result
3. TestSession - Collection of test results with metadata
4. RerunTestGroup - Group of related test reruns
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestOutcome(Enum):
    """
    Test outcome states.

    Enum values:
        PASSED: Test passed
        FAILED: Test failed
        SKIPPED: Test skipped
        XFAILED: Expected failure
        XPASSED: Unexpected pass
        RERUN: Test was rerun
        ERROR: Test errored
    """

    __test__ = False  # Tell Pytest this is NOT a test class

    PASSED = "PASSED"  # Internal representation in UPPERCASE
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    XFAILED = "XFAILED"
    XPASSED = "XPASSED"
    RERUN = "RERUN"
    ERROR = "ERROR"

    @classmethod
    def from_str(cls, outcome: Optional[str]) -> "TestOutcome":
        """
        Convert string to TestOutcome, always uppercase internally.

        Args:
            outcome (Optional[str]): Outcome string.
        Returns:
            TestOutcome: Corresponding enum value.
        """
        if not outcome:
            return cls.SKIPPED  # Return a default enum value instead of None
        try:
            return cls[outcome.upper()]
        except KeyError:
            raise ValueError(f"Invalid test outcome: {outcome}")

    def to_str(self) -> str:
        """
        Convert TestOutcome to string, always lowercase externally.

        Returns:
            str: Lowercase outcome string.
        """
        return self.value.lower()

    @classmethod
    def to_list(cls) -> List[str]:
        """
        Convert entire TestOutcome enum to a list of possible string values.

        Returns:
            List[str]: List of lowercase outcome strings.
        """
        return [outcome.value.lower() for outcome in cls]

    def is_failed(self) -> bool:
        """
        Check if the outcome represents a failure.

        Returns:
            bool: True if outcome is failure or error, else False.
        """
        return self in (self.FAILED, self.ERROR)


@dataclass
class TestResult:
    """
    Represents a single test result for an individual test run.

    Attributes:
        nodeid (str): Unique identifier for the test node.
        outcome (TestOutcome): Result outcome.
        start_time (Optional[datetime]): Start time of the test.
        stop_time (Optional[datetime]): Stop time of the test.
        duration (Optional[float]): Duration in seconds.
        caplog (str): Captured log output.
        capstderr (str): Captured stderr output.
        capstdout (str): Captured stdout output.
        longreprtext (str): Long representation of failure, if any.
        has_warning (bool): Whether the test had a warning.
    """

    __test__ = False  # Tell Pytest this is NOT a test class

    nodeid: str
    outcome: TestOutcome
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    duration: Optional[float] = None
    caplog: str = ""
    capstderr: str = ""
    capstdout: str = ""
    longreprtext: str = ""
    has_warning: bool = False

    def __post_init__(self):
        """
        Validate and process initialization data.

        Raises:
            ValueError: If neither stop_time nor duration is provided.
        """
        # Only compute stop_time if both start_time and duration are present and stop_time is missing
        if self.stop_time is None and self.start_time is not None and self.duration is not None:
            self.stop_time = self.start_time + timedelta(seconds=self.duration)
        # Only compute duration if both start_time and stop_time are present and duration is missing
        elif self.duration is None and self.start_time is not None and self.stop_time is not None:
            self.duration = (self.stop_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict:
        """
        Convert test result to a dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the test result.
        """
        # Handle both string and enum outcomes for backward compatibility
        if not hasattr(self.outcome, "to_str"):
            logger.warning(
                "Non-enum (probably string outcome detected where TestOutcome enum expected. "
                f"nodeid={self.nodeid}, outcome={self.outcome}, type={type(self.outcome)}. "
                "For proper session context and query filtering, use TestOutcome enum: "
                "outcome=TestOutcome.FAILED instead of outcome='failed'. "
                "String outcomes are deprecated and will be removed in a future version."
            )
            outcome_str = str(self.outcome).lower()
        else:
            outcome_str = self.outcome.to_str()

        return {
            "nodeid": self.nodeid,
            "outcome": outcome_str,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "stop_time": self.stop_time.isoformat() if self.stop_time else None,
            "duration": self.duration,
            "caplog": self.caplog,
            "capstderr": self.capstderr,
            "capstdout": self.capstdout,
            "longreprtext": self.longreprtext,
            "has_warning": self.has_warning,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TestResult":
        """Create a TestResult from a dictionary."""
        start_time = data.get("start_time")
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        stop_time = data.get("stop_time")
        if isinstance(stop_time, str):
            stop_time = datetime.fromisoformat(stop_time)

        return cls(
            nodeid=data["nodeid"],
            outcome=TestOutcome.from_str(data["outcome"]),
            start_time=start_time,
            stop_time=stop_time,
            duration=data.get("duration"),
            caplog=data.get("caplog", ""),
            capstderr=data.get("capstderr", ""),
            capstdout=data.get("capstdout", ""),
            longreprtext=data.get("longreprtext", ""),
            has_warning=data.get("has_warning", False),
        )


@dataclass
class RerunTestGroup:
    """
    Groups test results for tests that were rerun, chronologically ordered with final result last.

    Attributes:
        nodeid (str): Test node ID.
        tests (List[TestResult]): List of TestResult objects for each rerun.
    """

    __test__ = False

    nodeid: str
    tests: List[TestResult] = field(default_factory=list)

    def add_test(self, result: "TestResult"):
        """
        Add a test result and maintain chronological order.

        Args:
            result (TestResult): TestResult to add.
        """
        self.tests.append(result)
        self.tests.sort(key=lambda t: t.start_time)

    @property
    def final_outcome(self):
        """
        Get the outcome of the final test (non-RERUN and non-ERROR).

        Returns:
            Optional[TestOutcome]: Final outcome if available.
        """
        outcomes = [t.outcome for t in self.tests]
        if TestOutcome.FAILED in outcomes:
            return TestOutcome.FAILED
        return outcomes[-1] if outcomes else None

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the rerun group.
        """
        return {"nodeid": self.nodeid, "tests": [t.to_dict() for t in self.tests]}

    @classmethod
    def from_dict(cls, data: Dict) -> "RerunTestGroup":
        """
        Create RerunTestGroup from dictionary.

        Args:
            data (Dict): Dictionary representation of the rerun group.
        Returns:
            RerunTestGroup: Instantiated RerunTestGroup object.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Invalid data for RerunTestGroup. Expected dict, got {type(data)}")

        group = cls(nodeid=data["nodeid"])

        tests = [TestResult.from_dict(test_dict) for test_dict in data.get("tests", [])]
        group.tests = tests
        return group


@dataclass
class TestSession:
    """
    Represents a single test session for a single SUT.

    Attributes:
        sut_name (str): Name of the system under test.
        testing_system (Dict[str, Any]): Metadata about the testing system.
        session_id (str): Unique session identifier.
        session_start_time (datetime): Start time of the session.
        session_stop_time (Optional[datetime]): Stop time of the session.
        session_duration (Optional[float]): Duration of the session in seconds.
        atta (Dict[str, str]): Arbitrary tags for the session.
        rerun_test_groups (List[RerunTestGroup]): Groups of rerun tests.
        test_results (List[TestResult]): List of test results in the session.
    """

    __test__ = False  # Tell Pytest this is NOT a test class

    sut_name: str = ""
    testing_system: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    session_start_time: datetime = None
    session_stop_time: Optional[datetime] = None
    session_duration: Optional[float] = None
    session_tags: Dict[str, str] = field(default_factory=dict)
    rerun_test_groups: List[RerunTestGroup] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)

    def __post_init__(self):
        """
        Calculate timing information once at initialization.
        """
        # Always set a start time
        if self.session_start_time is None:
            self.session_start_time = datetime.now(timezone.utc)
        # Require at least one of stop_time or duration
        if self.session_stop_time is None and self.session_duration is None:
            raise ValueError("Either session_stop_time or session_duration must be provided")
        if self.session_stop_time is None:
            self.session_stop_time = self.session_start_time + timedelta(seconds=self.session_duration)
        elif self.session_duration is None:
            self.session_duration = (self.session_stop_time - self.session_start_time).total_seconds()
        else:
            # Both are provided: ignore duration, use stop_time, log a warning
            logger.warning(
                "Both session_stop_time and session_duration provided. "
                "Ignoring session_duration and using session_stop_time as authoritative."
            )
            self.session_duration = (self.session_stop_time - self.session_start_time).total_seconds()

    def to_dict(self) -> Dict:
        """
        Convert TestSession to a dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the test session.
        """
        return {
            "session_id": self.session_id,
            "session_start_time": self.session_start_time.isoformat(),
            "session_stop_time": self.session_stop_time.isoformat(),
            "session_duration": self.session_duration,
            "sut_name": self.sut_name,
            "testing_system": self.testing_system or {},
            "test_results": [test.to_dict() for test in self.test_results],
            "rerun_test_groups": [
                {"nodeid": group.nodeid, "tests": [t.to_dict() for t in group.tests]}
                for group in self.rerun_test_groups
            ],
            "session_tags": self.session_tags or {},
        }

    @classmethod
    def from_dict(cls, d):
        """Create a TestSession from a dictionary."""
        if not isinstance(d, dict):
            raise ValueError(f"Invalid data for TestSession. Expected dict, got {type(d)}")

        # Convert datetime strings to datetime objects
        session_start_time = d.get("session_start_time")
        if isinstance(session_start_time, str):
            session_start_time = datetime.fromisoformat(session_start_time)

        session_stop_time = d.get("session_stop_time")
        if isinstance(session_stop_time, str):
            session_stop_time = datetime.fromisoformat(session_stop_time)

        test_results = [TestResult.from_dict(tr_dict) for tr_dict in d.get("test_results", [])]

        rerun_test_groups = [RerunTestGroup.from_dict(group_dict) for group_dict in d.get("rerun_test_groups", [])]

        # Create the TestSession with proper datetime objects
        return cls(
            sut_name=d.get("sut_name"),
            testing_system=d.get("testing_system", {}),
            session_id=d.get("session_id"),
            session_start_time=session_start_time,
            session_stop_time=session_stop_time,
            session_duration=d.get("session_duration"),
            session_tags=d.get("session_tags", {}),
            rerun_test_groups=rerun_test_groups,
            test_results=test_results,
        )

    def add_test_result(self, result: TestResult) -> None:
        """
        Add a test result to this session.

        Args:
            result (TestResult): TestResult to add.
        Raises:
            ValueError: If result is not a TestResult instance.
        """
        if not isinstance(result, TestResult):
            raise ValueError(
                f"Invalid test result {result}; must be a TestResult object, nistead was type {type(result)}"
            )

        self.test_results.append(result)

    def add_rerun_group(self, group: RerunTestGroup) -> None:
        """
        Add a rerun test group to this session.

        Args:
            group (RerunTestGroup): RerunTestGroup to add.
        Raises:
            ValueError: If group is not a RerunTestGroup instance.
        """
        if not isinstance(group, RerunTestGroup):
            raise ValueError(
                f"Invalid rerun group {group}; must be a RerunTestGroup object, instead was type {type(group)}"
            )

        self.rerun_test_groups.append(group)
