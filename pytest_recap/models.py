"""Models for test session data.

Core models:
1. TestOutcome - Enum for test result outcomes
2. SessionStats - Aggregates test outcome statistics for a single session
3. TestResult - Single test execution result
4. TestSession - Collection of test results with metadata
5. RerunTestGroup - Group of related test reruns
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

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


class SessionStats:
    """Aggregates test outcome statistics for a session."""

    def __init__(self, test_results):
        """
        Args:
            test_results (Iterable[TestResult]): List of TestResult objects.
        """
        self.counter = Counter(
            str(getattr(test_result, "outcome", test_result)).lower() for test_result in test_results
        )
        self.total = len(test_results)

    def count(self, outcome):
        """Return the count for a given outcome (case-insensitive string)."""
        return self.counter.get(str(outcome).lower(), 0)

    def as_dict(self):
        """Return all outcome counts as a dict."""
        return dict(self.counter)

    def __str__(self):
        return f"SessionStats(total={self.total}, {dict(self.counter)})"


@dataclass
class TestSession:
    """
    Represents a test session recap with session-level metadata, results, warnings, and errors.

    Attributes:
        session_id (str): Unique session identifier.
        session_start_time (datetime): Start time of the session.
        session_stop_time (datetime): Stop time of the session.
        sut_name (str): Name of the system under test.
        session_tags (Dict[str, str]): Arbitrary tags for the session.
        testing_system (Dict[str, Any]): Metadata about the testing system.
        test_results (List[TestResult]): List of test results in the session.
        rerun_test_groups (List[RerunTestGroup]): Groups of rerun tests.
        warnings (List[Any]): List of session-level warnings.
        errors (List[Any]): List of session-level errors.
        session_stats (SessionStats): Session statistics.
    """

    __test__ = False  # Tell Pytest this is NOT a test class

    def __init__(
        self,
        session_id: str,
        session_start_time: datetime,
        session_stop_time: datetime = None,
        sut_name: str = None,
        session_tags: dict = None,
        testing_system: dict = None,
        test_results: list = None,
        rerun_test_groups: list = None,
        warnings: list = None,
        errors: list = None,
        session_stats: SessionStats = None,
    ):
        self.session_id = session_id
        self.session_start_time = session_start_time
        self.session_stop_time = session_stop_time or datetime.utcnow()
        self.sut_name = sut_name
        self.session_tags = session_tags or {}
        self.testing_system = testing_system or {}
        self.test_results = test_results or []
        self.rerun_test_groups = rerun_test_groups or []
        self.warnings = warnings or []
        self.errors = errors or []
        self.session_stats = session_stats or SessionStats(self.test_results)

    def to_dict(self) -> Dict:
        """
        Convert TestSession to a dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the test session.
        """
        return {
            "session_id": self.session_id,
            "session_tags": self.session_tags or {},
            "session_start_time": self.session_start_time.isoformat(),
            "session_stop_time": self.session_stop_time.isoformat(),
            "sut_name": self.sut_name,
            "testing_system": self.testing_system or {},
            "test_results": [test.to_dict() for test in self.test_results],
            "rerun_test_groups": [
                {"nodeid": group.nodeid, "tests": [t.to_dict() for t in group.tests]}
                for group in self.rerun_test_groups
            ],
            "warnings": self.warnings,
            "errors": self.errors,
            "session_stats": self.session_stats.as_dict() if self.session_stats else {},
        }

    @classmethod
    def from_dict(cls, d):
        """Create a TestSession from a dictionary."""
        if not isinstance(d, dict):
            raise ValueError(f"Invalid data for TestSession. Expected dict, got {type(d)}")
        session_start_time = d.get("session_start_time")
        if isinstance(session_start_time, str):
            session_start_time = datetime.fromisoformat(session_start_time)
        session_stop_time = d.get("session_stop_time")
        if isinstance(session_stop_time, str):
            session_stop_time = datetime.fromisoformat(session_stop_time)
        test_results = [TestResult.from_dict(tr) for tr in d.get("test_results", [])]
        session_stats = SessionStats(test_results)
        return cls(
            session_id=d.get("session_id"),
            session_start_time=session_start_time,
            session_stop_time=session_stop_time,
            sut_name=d.get("sut_name"),
            session_tags=d.get("session_tags", {}),
            testing_system=d.get("testing_system", {}),
            test_results=test_results,
            rerun_test_groups=[RerunTestGroup.from_dict(g) for g in d.get("rerun_test_groups", [])],
            warnings=d.get("warnings", []),
            errors=d.get("errors", []),
            session_stats=session_stats,
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
