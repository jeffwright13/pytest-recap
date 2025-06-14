import json

from scripts.recap_json_to_html import format_human_duration, main


def test_format_human_duration_basic():
    assert format_human_duration(0) == "0.000000s"
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
    assert "<table" in html
