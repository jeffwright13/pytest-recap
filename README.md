# pytest-recap

Capture your test sessions. Recap the results.

![pytest-recap logo](./assets/pytest-recap-160x160.png)

## Overview

**pytest-recap** is a [pytest](https://pytest.org/) plugin that captures detailed information about your test sessions and creates a well-structured JSON file written to the location of your choice. It is designed to help you analyze, summarize, and store test outcomes for reporting and analytics.

### Key Features

- **Comprehensive session recap**: Records all test outcomes, timings, logs, and more.
- **Cloud storage support**: Write recaps directly to AWS S3 (`s3://`), Google Cloud Storage (`gs://`), or Azure Blob Storage (`azure://`).
- **User-definable metadata**: Configure system under test, testing system, and session tags.
- **Rerun group tracking**: Handles flaky/rerun tests with group summaries.
- **Color-highlighted output**: Recap file path/URI is colorized in the terminal.

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

### Example Recap JSON

<details>
  <summary>Show Example</summary>

  ```json
  {
    "session_id": "20250522-064200_pytest-recap",
    "session_tags": { "run_type": "smoke", "branch": "main" },
    "session_start_time": "2025-05-22T06:42:00Z",
    "session_stop_time": "2025-05-22T06:45:12Z",
    "system_under_test": {
      "name": "pytest-recap",
      "version": "0.8.0",
      "type": "pytest-plugin",
      "description": "Pytest plugin for session recaps"
    },
    "testing_system": {
      "hostname": "ci-runner-01",
      "platform": "Linux",
      "python_version": "3.11.2",
      "pytest_version": "8.3.5"
    },
    "test_results": [
      {
        "nodeid": "tests/test_example.py::test_foo",
        "outcome": "passed",
        "start_time": "2025-05-22T06:42:01Z",
        "stop_time": "2025-05-22T06:42:01Z",
        "caplog": "INFO: test log message",
        "capstderr": "",
        "capstdout": "stdout output here\n",
        "longreprtext": ""
      },
      {
        "nodeid": "tests/test_example.py::test_bar",
        "outcome": "failed",
        "start_time": "2025-05-22T06:42:02Z",
        "stop_time": "2025-05-22T06:42:02Z",
        "caplog": "ERROR: test failure log",
        "capstderr": "error output\n",
        "capstdout": "",
        "longreprtext": "AssertionError: expected 1, got 0"
      }
    ],
    "rerun_test_groups": [
      {
        "nodeid": "tests/test_example.py::test_flaky",
        "tests": [
          {
            "nodeid": "tests/test_example.py::test_flaky",
            "outcome": "failed",
            "start_time": "2025-05-22T06:42:03Z",
            "stop_time": "2025-05-22T06:42:03Z",
            "caplog": "ERROR: intermittent failure",
            "capstderr": "",
            "capstdout": "",
            "longreprtext": "AssertionError: flaky failure"
          },
          {
            "nodeid": "tests/test_example.py::test_flaky",
            "outcome": "passed",
            "start_time": "2025-05-22T06:42:04Z",
            "stop_time": "2025-05-22T06:42:04Z",
            "caplog": "",
            "capstderr": "",
            "capstdout": "",
            "longreprtext": ""
          }
        ]
      }
    ],
    "session_stats": {
      "passed": 2,
      "failed": 1
    }
  }
  ```
</details>

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
