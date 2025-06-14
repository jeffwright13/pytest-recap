# pytest-recap

"Capture your test sessions. Recap the results."

![pytest-recap logo](./assets/combo.png)

## Overview

**pytest-recap** is a [pytest](https://pytest.org/) plugin that captures detailed information about your test sessions and creates a well-structured JSON file written to the location of your choice. It is designed to help you analyze, summarize, and store test outcomes for reporting and analytics.

The **recap** is a structured summary of one or more pytest test sessions, presenting key outcomes, such as passed, failed, or skipped tests; alongside supporting details—like error messages, tracebacks, warnings, and test metadata—that provide context and explanation for each summarized result. The recap enables users to quickly understand the overall state of their test suite while also allowing them to drill down into the specifics behind each summarized result.

Beyond immediate reporting, a recap serves as a robust platform for post-analysis: by organizing both summary and details in a machine-readable and navigable format, it empowers users to perform trend analysis, root cause investigation, historical comparisons, and custom reporting. This makes pytest-recap not just a reporting tool, but a foundation for deeper quality insights and continuous improvement.

- Concise overview of test outcomes (summary)
- Direct links or references to detailed supporting information (details)
- Designed for clarity, traceability, and actionable insight into pytest test runs
- Facilitates post-analysis, trend detection, and data-driven decision making
- Comprehensive session recap: records all local test outcomes, timings, logs, and more.
- Cloud storage support: write recaps to file, or to AWS S3 (`s3://`), Google Cloud Storage (`gs://`), or Azure Blob Storage (`azure://`).
- User-definable metadata: configure system-under-test, testing-system, and session-tags.
- Rerun group tracking: handles flaky/rerun tests with group summaries.

---

### Recap JSON Format

The recap JSON file is a structured summary of your test session. Key fields include:
- `session_id`, `session_tags`, `session_start_time`, `session_stop_time`: Session metadata. All timestamps are timezone-aware UTC.
- `system_under_test`, `testing_system`: Dicts for system metadata.
- `test_results`: List of objects, each with fields like `nodeid`, `outcome`, `start_time`, `stop_time`, `duration`, `caplog`, `capstderr`, `capstdout`, `longreprtext`, etc.
- `warnings`, `errors`: Lists of warning/error events.
- `rerun_test_groups`: Groups of related rerun tests.
- `session_stats`: Aggregated stats (e.g., `passed`, `failed`, `warnings`).

All fields are documented in the plugin source and schema.

#### Example Recap JSON

<details>
  <summary>Show Example</summary>

```json
{
  "session_id": "20250604-024258-69f9b186",
  "session_tags": {},
  "session_start_time": "2025-06-04T02:42:58.827303+00:00",
  "session_stop_time": "2025-06-04T02:43:00.314905+00:00",
  "system_under_test": {
    "name": "pytest-recap"
  },
  "testing_system": {
    "hostname": "GPYVQ4KGXY.local",
    "platform": "macOS-15.5-x86_64-i386-64bit",
    "python_version": "3.9.16",
    "pytest_version": "7.4.4",
    "environment": "test"
  },
  "test_results": [
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_pass",
      "outcome": "passed",
      "start_time": "2025-06-04T02:42:58.827303+00:00",
      "stop_time": "2025-06-04T02:42:59.031785+00:00",
      "duration": 0.204482,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_rerun",
      "outcome": "passed",
      "start_time": "2025-06-04T02:42:59.789393+00:00",
      "stop_time": "2025-06-04T02:42:59.893555+00:00",
      "duration": 0.104162,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_warning",
      "outcome": "passed",
      "start_time": "2025-06-04T02:42:59.904049+00:00",
      "stop_time": "2025-06-04T02:43:00.004588+00:00",
      "duration": 0.100539,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_long_output",
      "outcome": "passed",
      "start_time": "2025-06-04T02:43:00.006397+00:00",
      "stop_time": "2025-06-04T02:43:00.209279+00:00",
      "duration": 0.202882,
      "caplog": "\u001b[33mWARNING \u001b[0m demo:test_realistic_minimal.py:71 Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...Long output the second...",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_stdout_stderr",
      "outcome": "passed",
      "start_time": "2025-06-04T02:43:00.210150+00:00",
      "stop_time": "2025-06-04T02:43:00.314905+00:00",
      "duration": 0.104755,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_fail",
      "outcome": "failed",
      "start_time": "2025-06-04T02:42:59.035346+00:00",
      "stop_time": "2025-06-04T02:42:59.340679+00:00",
      "duration": 0.305333,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "noisy_fixture = None\n\n    def test_fail(noisy_fixture):\n        print(\"failing stdout\")\n        logger.info(\"failing log\")\n        warnings.warn(\"failing warning\", UserWarning)\n        time.sleep(0.3)\n>       assert False, \"Intentional failure\"\nE       AssertionError: Intentional failure\nE       assert False\n\ndemo-tests/test_realistic_minimal.py:29: AssertionError"
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_skip",
      "outcome": "skipped",
      "start_time": "2025-06-04T02:42:59.358949+00:00",
      "stop_time": "2025-06-04T02:42:59.359087+00:00",
      "duration": 0.000138,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "('/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py', 31, 'Skipped: demonstrate skip')"
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_xfail",
      "outcome": "xfailed",
      "start_time": "2025-06-04T02:42:59.359766+00:00",
      "stop_time": "2025-06-04T02:42:59.515335+00:00",
      "duration": 0.155569,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "@pytest.mark.xfail(reason=\"expected fail\", strict=True)\n    def test_xfail():\n        time.sleep(0.15)\n>       assert False\nE       assert False\n\ndemo-tests/test_realistic_minimal.py:38: AssertionError"
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_xpass",
      "outcome": "xpassed",
      "start_time": "2025-06-04T02:42:59.522685+00:00",
      "stop_time": "2025-06-04T02:42:59.677639+00:00",
      "duration": 0.154954,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": ""
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_rerun",
      "outcome": "rerun",
      "start_time": "2025-06-04T02:42:59.679639+00:00",
      "stop_time": "2025-06-04T02:42:59.782916+00:00",
      "duration": 0.103277,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "@pytest.mark.flaky(reruns=1)\n    def test_rerun():\n        # Fails first, passes second\n        if not hasattr(test_rerun, \"called\"):\n            test_rerun.called = True\n            time.sleep(0.1)\n>           assert False, \"fail for rerun\"\nE           AssertionError: fail for rerun\nE           assert False\n\ndemo-tests/test_realistic_minimal.py:51: AssertionError"
    },
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_error",
      "outcome": "error",
      "start_time": "2025-06-04T02:42:59.894893+00:00",
      "stop_time": "2025-06-04T02:42:59.895318+00:00",
      "duration": 0.000425,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "@pytest.fixture\n    def error_fixture():\n>       raise Exception(\"Error in fixture\")\nE       Exception: Error in fixture\n\ndemo-tests/test_realistic_minimal.py:57: Exception"
    }
  ],
  "rerun_test_groups": [
    {
      "nodeid": "demo-tests/test_realistic_minimal.py::test_rerun",
      "tests": [
        {
          "nodeid": "demo-tests/test_realistic_minimal.py::test_rerun",
          "outcome": "rerun",
          "start_time": "2025-06-04T02:42:59.679639+00:00",
          "stop_time": "2025-06-04T02:42:59.782916+00:00",
          "duration": 0.103277,
          "caplog": "",
          "capstderr": "",
          "capstdout": "",
          "longreprtext": "@pytest.mark.flaky(reruns=1)\n    def test_rerun():\n        # Fails first, passes second\n        if not hasattr(test_rerun, \"called\"):\n            test_rerun.called = True\n            time.sleep(0.1)\n>           assert False, \"fail for rerun\"\nE           AssertionError: fail for rerun\nE           assert False\n\ndemo-tests/test_realistic_minimal.py:51: AssertionError"
        },
        {
          "nodeid": "demo-tests/test_realistic_minimal.py::test_rerun",
          "outcome": "passed",
          "start_time": "2025-06-04T02:42:59.789393+00:00",
          "stop_time": "2025-06-04T02:42:59.893555+00:00",
          "duration": 0.104162,
          "caplog": "",
          "capstderr": "",
          "capstdout": "",
          "longreprtext": ""
        }
      ]
    }
  ],
  "warnings": [
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_pass",
      "when": "runtest",
      "outcome": null,
      "message": "fixture warning",
      "category": "UserWarning",
      "filename": "/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py",
      "lineno": 12,
      "longrepr": null,
      "sections": [],
      "keywords": [],
      "location": null
    },
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_pass",
      "when": "runtest",
      "outcome": null,
      "message": "passing warning",
      "category": "UserWarning",
      "filename": "/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py",
      "lineno": 20,
      "longrepr": null,
      "sections": [],
      "keywords": [],
      "location": null
    },
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_fail",
      "when": "runtest",
      "outcome": null,
      "message": "fixture warning",
      "category": "UserWarning",
      "filename": "/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py",
      "lineno": 12,
      "longrepr": null,
      "sections": [],
      "keywords": [],
      "location": null
    },
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_fail",
      "when": "runtest",
      "outcome": null,
      "message": "failing warning",
      "category": "UserWarning",
      "filename": "/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py",
      "lineno": 27,
      "longrepr": null,
      "sections": [],
      "keywords": [],
      "location": null
    },
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_warning",
      "when": "runtest",
      "outcome": null,
      "message": "explicit test warning",
      "category": "UserWarning",
      "filename": "/Users/jwr003/coding/pytest-recap/demo-tests/test_realistic_minimal.py",
      "lineno": 67,
      "longrepr": null,
      "sections": [],
      "keywords": [],
      "location": null
    }
  ],
  "errors": [
    {
      "event_type": "warning",
      "nodeid": "demo-tests/test_realistic_minimal.py::test_error",
      "when": "setup",
      "outcome": "failed",
      "message": null,
      "category": null,
      "filename": null,
      "lineno": null,
      "longrepr": "@pytest.fixture\n    def error_fixture():\n>       raise Exception(\"Error in fixture\")\nE       Exception: Error in fixture\n\ndemo-tests/test_realistic_minimal.py:57: Exception",
      "sections": [],
      "keywords": [
        "test_error",
        "demo-tests/test_realistic_minimal.py",
        "pytest-recap"
      ],
      "location": null
    }
  ],
  "session_stats": {
    "passed": 5,
    "failed": 1,
    "skipped": 1,
    "xfailed": 1,
    "xpassed": 1,
    "rerun": 1,
    "error": 1,
    "warnings": 5
  }
}
```
</details>

---

### API/Plugin Usage Highlights

- **TestSessionStats**: Uses `warnings_count` argument (plural) for consistency.
- **RecapEvent**: Provides `.is_warning()` and `.is_error()` helpers for event type checks.
- **Logger**: Use `logger.warning` for warnings (not `logger.warnings`).
- **Timestamps**: All times are timezone-aware UTC (ISO8601 with offset).
- **Linting/Formatting**: Run `ruff check --fix` and `ruff format` for code style. Pre-commit hooks are recommended.

### Running with pytest-recap

```sh
pytest --recap --recap-pretty --recap-destination=recap.json
```

### Sample recap.json output

See the [Example Recap JSON](#example-recap-json) above for a real output snippet.

### Changelog
See [CHANGELOG.md](./CHANGELOG.md) for a summary of recent changes.

---

## Installation

```bash
uv pip install pytest-recap
```

To install all dependencies (core + dev, including cloud and test tools) using uv's dependency groups:

```bash
uv pip install --group all
```

For cloud storage support in tests:
- S3: `uv add --dev moto boto3`
- GCS: `uv add --dev google-cloud-storage`
- Azure: `uv add --dev azure-storage-blob`

---

## Usage

### Generating an Interactive HTML Report

- Durations in the HTML report are now displayed with 6 decimal places for values under 10 seconds, and as human-friendly strings (e.g., `1m 2s`, `2h 3m 4s`) for longer durations.
- Session metadata (start/stop time, duration) is always shown if available, and robustly extracted from recap JSON.
- Warnings and errors are deduplicated to avoid repeated messages.
- The report summary includes outcome percentages for each result type.


After running your tests with pytest-recap, you can convert the `recap.json` file to a modern, interactive HTML report:

```bash
python recap_json_to_html.py recap.json report.html
```

- The HTML report includes:
  - A summary section with total tests, outcome stats, and a pie chart
  - A collapsible Session Metadata panel
  - A sortable and filterable results table
  - Expandable/collapsible test details (click the test name)
  - Outcome filtering with a master toggle
  - Responsive, user-friendly design

Open `report.html` in your browser to explore the results interactively.


**Troubleshooting tip:** If you encounter issues with session metadata not being picked up, run pytest with `-s` to see debug output for ini/env/CLI value resolution.

### Controlling Recap JSON Output Format

By default, recap JSON output is minified (compact, no whitespace). To enable pretty-printed (indented, human-readable) output, use any of the following:

- **CLI:**
  ```bash
  pytest --recap-pretty
  ```
- **Environment variable:**
  ```bash
  export RECAP_PRETTY=1
  pytest
  ```
- **pytest.ini:**
  ```ini
  [pytest]
  recap_pretty = 1
  ```

**Precedence:** CLI > Environment variable > pytest.ini > default (minified).

**Tip:** Pretty-printed output is easier to read and diff, while minified output is smaller and faster to parse.

Run pytest as usual. Recap output is written to `recap-session.json` by default, or to a custom file/directory/cloud URI using the `--recap-destination` option.

```bash
pytest --recap-destination=gs://mybucket/recap-session.json
pytest --recap-destination=azure://mycontainer/recap-session.json
pytest --recap-destination=./output_dir/
```

### Recap Session Schema

The structure of the recap JSON is governed by a [JSON Schema](schema/pytest-recap-session.schema.json) ([view raw](./schema/pytest-recap-session.schema.json)).

- **`system_under_test`**, **`testing_system`**, and **`session_tags`** can be customized for each run.
- You can set these via:
  - **CLI options:**
    ```bash
    pytest --recap-system-under-test='{"name": "myapp"}' \
           --recap-testing-system='{"hostname": "ci"}' \
           --recap-session-tags='{"run_type": "smoke"}'
    ```
  - **Environment variables:**
    ```bash
    export RECAP_SYSTEM_UNDER_TEST='{"name": "myapp"}'
    export RECAP_TESTING_SYSTEM='{"hostname": "ci"}'
    export RECAP_SESSION_TAGS='{"run_type": "smoke"}'
    ```
  - **pytest.ini:**
    ```ini
    [pytest]
    recap_system_under_test = {"name": "myapp"}
    recap_testing_system = {"hostname": "ci"}
    recap_session_tags = {"run_type": "smoke"}
    ```
- Accepted formats: JSON or Python dict string.
- Precedence: CLI > Environment variable > pytest.ini > default. This precedence is strictly enforced, with robust handling of whitespace and ini list/string edge cases.
- If invalid input is provided, a warning is printed referencing the relevant CLI option or environment variable, and a default is used.
- Warnings for invalid session metadata (e.g., `RECAP_SESSION_TAGS`) will always mention the relevant environment variable or option name for clarity.
- **`system_under_test`** and **`testing_system`** are extensible objects. You can add any custom keys relevant to your context (e.g., version, type, description).
- Recommended keys for `system_under_test` include: `name`, `version`, `type`, `description`.
- See the [schema file](schema/pytest-recap-session.schema.json) for details and validation rules.

### Test Result Fields

| Field Name | Description |
| --- | --- |
| `nodeid` | Unique identifier for the test (e.g., `tests/test_example.py::test_foo`) |
| `outcome` | Test outcome (e.g., `passed`, `failed`, `skipped`) |
| `start_time` | Timestamp when the test started |
| `stop_time` | Timestamp when the test finished |
| `longreprtext` | Detailed error message (if applicable) |
| `capstdout` | Captured standard output |
| `capstderr` | Captured standard error |
| `caplog` | Captured log messages |

---

## Cloud Storage Configuration

- **AWS S3**: Requires `boto3` and valid AWS credentials (see [boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)).
- **Google Cloud Storage**: Requires `google-cloud-storage` and valid GCP credentials (see [GCP auth docs](https://cloud.google.com/docs/authentication/getting-started)).
- **Azure Blob Storage**: Requires `azure-storage-blob` and valid Azure credentials (see [Azure auth docs](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage)).

---

## Development & Testing

- The `recap_json_to_html.py` script now provides a `main(json_path, html_path)` function for programmatic and CLI use.
- Tests have been improved for robustness and now match the new duration formatting and report structure.


- Dev dependencies: `uv pip install -r requirements-dev.txt` or use `uv add --dev ...` as above.
- Run all tests: `uv run pytest tests -v`
- S3 tests require `moto` and `boto3` (optional; skipped if not installed).
- GCS/Azure tests use direct mocking for fast, dependency-light testing.
- Pre-commit hooks: see `.pre-commit-config.yaml` for ruff, pytest-check, etc.
- The test suite covers all precedence and fallback logic for session metadata (CLI, env, ini, default), including edge cases and warning output.

---

## Comparison with Other Pytest Reporting Plugins

**pytest-recap** is intended to complement existing pytest reporting options, such as JUnit-XML export and [pytest-json-report](https://github.com/pytest-dev/pytest-json-report). Each has its own strengths and is suited to different workflows:

- **JUnit-XML Export** (`--junitxml=...`):
  - Produces XML output in the JUnit format, which is widely supported by CI systems and legacy tools.
  - The structure is standardized and best for integrations that require XML or expect the JUnit schema.

- **pytest-json-report**:
  - Outputs test results as JSON in a fixed structure, suitable for dashboards and basic reporting.
  - Well-established and widely used for generating machine-readable JSON reports.

- **pytest-recap**:
  - Uses a JSON format with an extensible schema, allowing users to add custom metadata (e.g., system under test, environment details, tags).
  - Designed for scenarios where capturing rich session metadata and supporting analytics or archiving is important.
  - Provides native support for writing recap files directly to cloud storage (S3, GCS, Azure) as well as local files.
  - Validates output against a JSON Schema for consistency and reliability.

When choosing a reporting plugin, consider your downstream needs: if you require a widely supported standard (like JUnit XML), or a simple JSON report, those plugins are excellent choices. If you need extensibility, custom metadata, or cloud-native workflows, pytest-recap may be a good fit.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes and version history.

---

## License

MIT License. Copyright (c) 2025 Jeff Wright.
