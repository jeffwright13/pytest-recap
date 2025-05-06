# pytest-recap

Capture your test sessions. Recap the results.

## Overview

**pytest-recap** is a [pytest](https://pytest.org/) plugin that captures detailed information about your test sessions and creates a well-structured JSON file writtten to the location of your choice. It is designed to help you analyze, summarize, and store test outcomes for reporting and analytics.

<details>
  <summary>Example JSON file</summary>

  ```json
  {
    "session_id": "20250503-074257_pytest-recap",
    "sut_name": "pytest-recap",
    "testing_system": {
      "platform": "linux",
      "python_version": "3.9.16",
      "pytest_version": "8.3.5"
    },
    "session_start_time": "2025-05-03T07:42:57.123456+00:00",
    "session_stop_time": "2025-05-03T07:43:01.654321+00:00",
    "session_duration": 4.53,
    "session_tags": {
      "ci": "github",
      "branch": "main"
    },
    "test_results": [
      {
        "nodeid": "demo-tests/orig/test_basic.py::test_basic_pass_1",
        "outcome": "passed",
        "start_time": "2025-05-03T07:42:58.111111+00:00",
        "stop_time": "2025-05-03T07:42:58.211111+00:00",
        "duration": 0.1,
        "caplog": "DEBUG: some debug log",
        "capstdout": "",
        "capstderr": "",
        "longreprtext": "",
        "has_warning": false
      },
      {
        "nodeid": "demo-tests/orig/test_basic.py::test_basic_fail_1",
        "outcome": "failed",
        "start_time": "2025-05-03T07:42:58.311111+00:00",
        "stop_time": "2025-05-03T07:42:58.411111+00:00",
        "duration": 0.1,
        "caplog": "DEBUG: some debug log",
        "capstdout": "",
        "capstderr": "",
        "longreprtext": "assert 1 == 2",
        "has_warning": false
      },
      {
        "nodeid": "demo-tests/orig/test_basic.py::test_basic_skip",
        "outcome": "skipped",
        "start_time": "2025-05-03T07:42:58.511111+00:00",
        "stop_time": "2025-05-03T07:42:58.511111+00:00",
        "duration": 0.0,
        "caplog": "",
        "capstdout": "",
        "capstderr": "",
        "longreprtext": "Skipped: Skipping this test with decorator.",
        "has_warning": false
      }
    ],
    "rerun_test_groups": [
      {
        "nodeid": "demo-tests/orig/test_basic.py::test_flaky",
        "tests": [
          {
            "nodeid": "demo-tests/orig/test_basic.py::test_flaky",
            "outcome": "rerun",
            "start_time": "2025-05-03T07:42:59.000001+00:00",
            "stop_time": "2025-05-03T07:42:59.100001+00:00",
            "duration": 0.1,
            "caplog": "",
            "capstdout": "",
            "capstderr": "",
            "longreprtext": "",
            "has_warning": false
          },
          {
            "nodeid": "demo-tests/orig/test_basic.py::test_flaky",
            "outcome": "passed",
            "start_time": "2025-05-03T07:42:59.200001+00:00",
            "stop_time": "2025-05-03T07:42:59.300001+00:00",
            "duration": 0.1,
            "caplog": "",
            "capstdout": "",
            "capstderr": "",
            "longreprtext": "",
            "has_warning": false
          }
        ]
      }
    ]
  }
  ```
</details>

## Features
- Captures all test outcomes, reruns, and session metadata
- Provides a JSON-serialized summary of test sessions
- Handles rerun and flaky test tracking

## Recap File Storage Modes

Pytest-recap supports two recap file storage modes:

- **Single-session mode (default for plugin output):**
  - Each recap file contains a single test session as a JSON object (dict).
  - Used when specifying a `--recap-destination` file or allowing the plugin to write a session recap.
  - Example output:

    ```json
    {
      "session_id": "pytest-recap-20250503-141259",
      "session_tags": {"ci": "github", "branch": "main"},
      ...
    }
    ```

- **Multi-session/archive mode:**
  - Used internally and for archival/testing purposes.
  - Each recap file contains a list of session objects.
  - Appending sessions is supported.
  - Example output:

    ```json
    [
      {"session_id": "id-1", ...},
      {"session_id": "id-2", ...}
    ]
    ```

The plugin always writes recap files as a single dict. The storage backend (`JSONStorage`) supports both modes for flexibility and testability.

## Installation

```bash
uv pip install pytest-recap
```

Or install from source:

```bash
git clone https://github.com/yourusername/pytest-recap.git
cd pytest-recap
uv pip install . -e
```

## Usage

Simply add `pytest-recap` to your test environment/venv. The plugin will automatically capture test session data when you run pytest with the `--recap` option enabled.

```bash
pytest --recap
```

Session data will be captured and can be accessed or exported as needed. Look in the terminal for the location your file was written to:

```bash
Pytest Recap session written to: /tmp/pytest_recap_sessions/2025/05/20250503-070851_pytest-recap.json
```

You can specify a custom location for the session file using the `--recap-destination` option:

```bash
pytest --recap --recap-destination=/path/to/your/session/file.json
```

### CI/Environment Variable Support

You can also control pytest-recap via environment variables, which is especially useful for CI servers:

| Environment Variable           | Description                                                | Example Value                     |
|-------------------------------|------------------------------------------------------------|-----------------------------------|
| `RECAP_ENABLE`         | Enable recap plugin (same as `--recap`)                    | `1`, `true`, `yes`                |
| `RECAP_DESTINATION`    | Output file or directory (same as `--recap-destination`)   | `/tmp/my-recap.json`              |
| `RECAP_ENV`                   | Specifies the environment (e.g., `staging`, `prod`). Default is `test`. | `staging`                         |
| `RECAP_SESSION_TAGS`          | JSON string for additional session tags. Must be a JSON object (dict). If invalid, an empty dictionary `{}` is used and a warning is printed. | `{"env": "ci", "branch": "main"}` |

- CLI flags always take precedence over environment variables.
- If neither is set, recap is disabled by default.

**Example (CI/CD):**

```bash
export RECAP_ENABLE=1
export RECAP_DESTINATION=/tmp/ci-session.json
export RECAP_ENV=ci
export RECAP_SESSION_TAGS='{"env": "ci", "branch": "main"}'
pytest
```

## Error Handling

- If `RECAP_SESSION_TAGS` is not a valid JSON object, the plugin will print a warning and use an empty dictionary `{}` for session tags.
- Recap files are always written, even if environment variables are invalid.

## Development

Install development dependencies:

```bash
uv pip install .[dev]
```

Run tests and check coverage:

```bash
pytest -v tests/
```

Format and lint code:

```bash
ruff check pytest_recap
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Jeff Wright (<jeff.washcloth@gmail.com>)
