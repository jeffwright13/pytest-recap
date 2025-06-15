import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class TestOutcome(Enum):
    """Test outcome states.

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
        """Convert string to TestOutcome, always uppercase internally.

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
        """Convert TestOutcome to string, always lowercase externally.

        Returns:
            str: Lowercase outcome string.

        """
        return self.value.lower()

    @classmethod
    def to_list(cls) -> List[str]:
        """Convert entire TestOutcome enum to a list of possible string values.

        Returns:
            List[str]: List of lowercase outcome strings.

        """
        return [outcome.value.lower() for outcome in cls]

    def is_failed(self) -> bool:
        """Check if the outcome represents a failure.

        Returns:
            bool: True if outcome is failure or error, else False.

        """
        return self in (self.FAILED, self.ERROR)


@dataclass
class TestResult:
    """Represents a single test result for an individual test run.

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
    has_error: bool = False

    def __post_init__(self):
        """Validate and process initialization data.

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
        """Convert test result to a dictionary for JSON serialization.

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
        )


@dataclass
class RerunTestGroup:
    """Groups test results for tests that were rerun, chronologically ordered with final result last.

    Attributes:
        nodeid (str): Test node ID.
        tests (List[TestResult]): List of TestResult objects for each rerun.
    """

    __test__ = False
    nodeid: str
    tests: List["TestResult"] = field(default_factory=list)

    @property
    def final_outcome(self) -> Optional[str]:
        """Compute the final outcome for the group based on test results.

        Returns:
            Optional[str]: The computed final outcome (e.g., "passed", "failed", "error"), or None if no tests.
        """
        if not self.tests:
            return None

        # Make sure only one test has an outcome that is not "rerun"
        non_rerun_count = sum(test.outcome.value.lower() != "rerun" for test in self.tests)
        assert non_rerun_count == 1, f"Expected at most one non-rerun test, got {non_rerun_count} instead"

        # The final outcome is the outcome of the only test that is not a rerun
        for test in self.tests:
            if test.outcome.value.lower() != "rerun":
                return test.outcome.value.lower()
        return None

    def add_test(self, result: "TestResult"):
        """Add a test result and maintain chronological order."""
        self.tests.append(result)
        self.tests.sort(key=lambda t: t.start_time)

    def to_dict(self) -> Dict:
        d = {"nodeid": self.nodeid, "tests": [t.to_dict() for t in self.tests]}
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "RerunTestGroup":
        if not isinstance(data, dict):
            raise ValueError(f"Invalid data for RerunTestGroup. Expected dict, got {type(data)}")
        group = cls(
            nodeid=data["nodeid"],
            tests=[TestResult.from_dict(test_dict) for test_dict in data.get("tests", [])],
        )
        return group


class TestSessionStats:
    """Aggregates session-level statistics, including test outcomes and other events (e.g., warnings).

    Attributes:
        passed (int): Number of passed tests
        failed (int): Number of failed tests
        skipped (int): Number of skipped tests
        xfailed (int): Number of unexpectedly failed tests
        xpassed (int): Number of unexpectedly passed tests
        error (int): Number of error tests
        rerun (int): Number of rerun tests
        warnings (int): Number of warnings encountered in this session
    """

    __test__ = False  # Tell Pytest this is NOT a test class

    def __init__(self, test_results: Iterable[Any], warnings_count: int = 0):
        """
        Args:
            test_results (Iterable[TestResult]): List of TestResult objects.
            warning_count (int): Number of warnings in the session.
        """
        # Aggregate test outcomes (e.g., passed, failed, etc.)
        self.counter = Counter(
            str(getattr(test_result, "outcome", test_result)).lower() for test_result in test_results
        )
        self.total = len(test_results)
        # Add warnings as a separate count (always present, even if zero)
        self.counter["warnings"] = warnings_count

    def count(self, key: str) -> int:
        """Return the count for a given outcome or event (case-insensitive string)."""
        return self.counter.get(key.lower(), 0)

    def as_dict(self) -> Dict[str, int]:
        """Return all session-level event counts as a dict, with 'testoutcome.' prefix removed from keys. Always include 'warnings' if present in counter, even if zero."""
        d = {
            (k[len("testoutcome.") :] if k.startswith("testoutcome.") else k): v
            for k, v in self.counter.items()
            if v > 0
        }
        # Always include 'warnings' if present in counter, even if zero
        if "warnings" in self.counter and "warnings" not in d:
            d["warnings"] = 0
        return d

    def __str__(self) -> str:
        """Return a string representation of the TestSessionStats object."""
        return f"TestSessionStats(total={self.total}, {dict(self.counter)})"


@dataclass
class TestSession:
    """Represents a test session recap with session-level metadata, results.

    Attributes:
        session_id (str): Unique session identifier.
        session_start_time (datetime): Start time of the session.
        session_stop_time (datetime): Stop time of the session.
        system_under_test (dict): Information about the system under test (user-extensible).
        session_tags (Dict[str, str]): Arbitrary tags for the session.
        testing_system (Dict[str, Any]): Metadata about the testing system.
        test_results (List[TestResult]): List of test results in the session.
        rerun_test_groups (List[RerunTestGroup]): Groups of rerun tests.
        session_stats (TestSessionStats): Test session statistics.

    """

    __test__ = False  # Tell Pytest this is NOT a test class

    def __init__(
        self,
        session_id: str,
        session_start_time: datetime,
        session_stop_time: datetime = None,
        system_under_test: dict = None,
        session_tags: dict = None,
        testing_system: dict = None,
        test_results: list = None,
        rerun_test_groups: list = None,
        warnings: Optional[List["RecapEvent"]] = None,
        errors: Optional[List["RecapEvent"]] = None,
        session_stats: TestSessionStats = None,
    ):
        self.session_id = session_id
        self.session_start_time = session_start_time
        self.session_stop_time = session_stop_time or datetime.now(timezone.utc)
        self.system_under_test = system_under_test or {}
        self.session_tags = session_tags or {}
        self.testing_system = testing_system or {}
        self.test_results = test_results or []
        self.rerun_test_groups = rerun_test_groups or []
        self.warnings = warnings or []
        self.errors = errors or []
        self.session_stats = session_stats or TestSessionStats(self.test_results, len(self.warnings))

    def to_dict(self) -> Dict:
        """Convert TestSession to a dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the test session.
        """
        return {
            "session_id": self.session_id,
            "session_tags": self.session_tags or {},
            "session_start_time": self.session_start_time.isoformat(),
            "session_stop_time": self.session_stop_time.isoformat(),
            "system_under_test": self.system_under_test or {},
            "testing_system": self.testing_system or {},
            "test_results": [test.to_dict() for test in self.test_results],
            "rerun_test_groups": [
                {"nodeid": group.nodeid, "tests": [t.to_dict() for t in group.tests]}
                for group in self.rerun_test_groups
            ],
            "warnings": [w.to_dict() for w in self.warnings],
            "errors": [e.to_dict() for e in self.errors],
            "session_stats": self.session_stats.as_dict() if self.session_stats else {},
        }

    @classmethod
    def from_dict(cls, d):
        """Create a TestSession from a dictionary. Ensures warnings count is passed to TestSessionStats."""
        if not isinstance(d, dict):
            raise ValueError(f"Invalid data for TestSession. Expected dict, got {type(d)}")
        session_start_time = d.get("session_start_time")
        if isinstance(session_start_time, str):
            session_start_time = datetime.fromisoformat(session_start_time)
        session_stop_time = d.get("session_stop_time")
        if isinstance(session_stop_time, str):
            session_stop_time = datetime.fromisoformat(session_stop_time)
        test_results = [TestResult.from_dict(test_result) for test_result in d.get("test_results", [])]
        warnings = [RecapEvent(**w) if not isinstance(w, RecapEvent) else w for w in d.get("warnings", [])]
        session_stats = TestSessionStats(test_results, warnings_count=len(warnings))
        return cls(
            session_id=d.get("session_id"),
            session_start_time=session_start_time,
            session_stop_time=session_stop_time,
            system_under_test=d.get("system_under_test", {}),
            session_tags=d.get("session_tags", {}),
            testing_system=d.get("testing_system", {}),
            test_results=test_results,
            rerun_test_groups=[RerunTestGroup.from_dict(g) for g in d.get("rerun_test_groups", [])],
            warnings=warnings,
            errors=d.get("errors", []),
            session_stats=session_stats,
        )

    def add_test_result(self, result: TestResult) -> None:
        """Add a test result to this session.

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
        """Add a rerun test group to this session.

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


class RecapEventType(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class RecapEvent:
    event_type: RecapEventType = RecapEventType.WARNING
    nodeid: Optional[str] = None
    when: Optional[str] = None
    outcome: Optional[str] = None
    message: Optional[str] = None
    category: Optional[str] = None
    filename: Optional[str] = None
    lineno: Optional[int] = None
    longrepr: Optional[Any] = None
    sections: List[Any] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    location: Optional[Any] = None

    def to_dict(self) -> dict:
        """Convert the RecapEvent to a dictionary."""
        return asdict(self)

    def is_warning(self) -> bool:
        """Return True if this event is classified as a warning."""
        return self.event_type == RecapEventType.WARNING

    def is_error(self) -> bool:
        """Return True if this event is classified as an error."""
        return self.event_type == RecapEventType.ERROR
