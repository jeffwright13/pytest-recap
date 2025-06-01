import pytest
from pytest_recap.models import TestOutcome, TestResult, RerunTestGroup
from datetime import datetime, timezone
from recap_json_to_html import main, render_rerun_group_table

import json

from recap_json_to_html import format_human_duration


def test_format_human_duration_basic():
    assert format_human_duration(0) == "0s"
    assert format_human_duration(59) == "59s"
    assert format_human_duration(60) == "1m 0s"
    assert format_human_duration(60 + 1) == "1m 1s"
    assert format_human_duration(3600) == "1h 0m 0s"
    assert format_human_duration(3600 + 1) == "1h 0m 1s"
    assert format_human_duration(3600 + 60) == "1h 1m 0s"
    assert format_human_duration(3600 + 60 + 1) == "1h 1m 1s"
    assert format_human_duration(86400) == "24h 0m 0s"
    assert format_human_duration(86400 + 1) == "24h 0m 1s"
    assert format_human_duration(86400 + 3600) == "25h 0m 0s"
    assert format_human_duration(86400 + 3600 + 60) == "25h 1m 0s"
    assert format_human_duration(86400 + 3600 + 60 + 1) == "25h 1m 1s"
    assert format_human_duration(86400 + 3600 + 60 + 60) == "25h 2m 0s"
    assert format_human_duration(86400 + 3600 + 60 + 60 + 1) == "25h 2m 1s"


def test_html_report_generation(tmp_path):
    # Minimal JSON input
    recap_data = {
        "session_id": "test-session",
        "session_start_time": "2024-01-01T00:00:00+00:00",
        "session_stop_time": "2024-01-01T00:00:10+00:00",
        "test_results": [
            {"nodeid": "test_a", "outcome": "passed", "duration": 1.0},
            {"nodeid": "test_b", "outcome": "failed", "duration": 2.0, "longreprtext": "AssertionError"},
        ],
        "warnings": [{"nodeid": "test_a", "message": "warn"}],
        "errors": [{"nodeid": "test_b", "message": "err"}],
        "rerun_test_groups": [
            {
                "nodeid": "test_b",
                "tests": [{"nodeid": "test_b", "outcome": "rerun"}, {"nodeid": "test_b", "outcome": "failed"}],
            }
        ],
    }
    json_file = tmp_path / "input.json"
    html_file = tmp_path / "output.html"
    json_file.write_text(json.dumps(recap_data))
    main(str(json_file), str(html_file))
    html = html_file.read_text()
    # Check for key HTML sections
    assert "<!DOCTYPE html>" in html
    assert "pytest-recap Test Report" in html
    assert "Warnings" in html
    assert "Errors" in html
    assert "Rerun Test Groups" in html
    assert "test_a" in html
    assert "test_b" in html


def test_html_handles_empty_input(tmp_path):
    recap_data = {}
    json_file = tmp_path / "input.json"
    html_file = tmp_path / "output.html"
    json_file.write_text(json.dumps(recap_data))
    main(str(json_file), str(html_file))
    html = html_file.read_text()
    assert "<!DOCTYPE html>" in html
    assert "pytest-recap Test Report" in html


def test_render_rerun_group_table_computed_final_outcome():
    now = datetime.now(timezone.utc)
    # Simulate a group with two test results: rerun then failed
    group = RerunTestGroup(
        nodeid="foo::bar",
        tests=[
            TestResult(nodeid="foo::bar", outcome=TestOutcome.RERUN, start_time=now, stop_time=now, duration=0.1),
            TestResult(nodeid="foo::bar", outcome=TestOutcome.FAILED, start_time=now, stop_time=now, duration=0.2),
        ]
    )
    group_dict = group.to_dict()
    # Should match what recap.json would contain
    html = render_rerun_group_table([group_dict])
    assert "failed" in html
    assert "foo::bar" in html
    assert "<table" in html
