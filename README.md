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
  "session_id": "20250528-054714-c9089ccf",
  "session_tags": {},
  "session_start_time": "2025-05-28T05:47:14.637005+00:00",
  "session_stop_time": "2025-05-28T05:47:14.675832+00:00",
  "system_under_test": {
    "name": "pytest-recap"
  },
  "testing_system": {
    "hostname": "GPYVQ4KGXY.local",
    "platform": "macOS-15.5-x86_64-i386-64bit",
    "python_version": "3.9.16",
    "pytest_version": "8.3.5",
    "environment": "test"
  },
  "test_results": [
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_1_pass_capturing",
      "outcome": "passed",
      "start_time": "2025-05-28T05:47:14.637005+00:00",
      "stop_time": "2025-05-28T05:47:14.637661+00:00",
      "duration": 0.000656,
      "caplog": "\u001b[32mINFO    \u001b[0m conftest:test_0.py:18 \u200b\u200b\u200b\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:21 FAIL this log is captured\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:25 FAIL is this log captured?\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:28 FAIL this log is also captured\n\u001b[32mINFO    \u001b[0m conftest:test_0.py:32 Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo;",
      "capstderr": "FAIL this stderr is captured\nFAIL this stderr is also captured\n",
      "capstdout": "FAIL this stdout is captured\nFAIL this stdout is also captured\n",
      "longreprtext": "None"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_with_warning",
      "outcome": "passed",
      "start_time": "2025-05-28T05:47:14.650280+00:00",
      "stop_time": "2025-05-28T05:47:14.650409+00:00",
      "duration": 0.000129,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "None"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_1_fail_capturing",
      "outcome": "failed",
      "start_time": "2025-05-28T05:47:14.638547+00:00",
      "stop_time": "2025-05-28T05:47:14.639152+00:00",
      "duration": 0.000605,
      "caplog": "\u001b[32mINFO    \u001b[0m conftest:test_0.py:39 \u200b\u200b\u200b\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:42 FAIL this log is captured\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:46 FAIL is this log captured?\n\u001b[33mWARNING \u001b[0m conftest:test_0.py:49 FAIL this log is also captured\n\u001b[31mCRITICAL\u001b[0m conftest:test_0.py:50 Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum;\n\u001b[1m\u001b[31mERROR   \u001b[0m conftest:test_0.py:51 Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum;\n\u001b[32mINFO    \u001b[0m conftest:test_0.py:53 Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum;",
      "capstderr": "FAIL this stderr is captured\nFAIL this stderr is also captured\n",
      "capstdout": "FAIL this stdout is captured\nFAIL this stdout is also captured\n",
      "longreprtext": "capsys = <_pytest.capture.CaptureFixture object at 0x10c3071c0>\nfake_data = 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, ...ariatur Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum;'\nlogger = <Logger conftest (DEBUG)>\n\n    def test0_1_fail_capturing(capsys, fake_data, logger):\n        logger.info(ZWS_X3)\n        print(\"FAIL this stdout is captured\")\n        print(\"FAIL this stderr is captured\", file=sys.stderr)\n        logger.warning(\"FAIL this log is captured\")\n        with capsys.disabled():\n            print(\"FAIL stdout not captured, going directly to sys.stdout\")\n            print(\"FAIL stderr not captured, going directly to sys.stderr\", file=sys.stderr)\n            logger.warning(\"FAIL is this log captured?\")\n        print(\"FAIL this stdout is also captured\")\n        print(\"FAIL this stderr is also captured\", file=sys.stderr)\n        logger.warning(\"FAIL this log is also captured\")\n        logger.critical(fake_data)\n        logger.error(fake_data)\n        # logger.warning(fake_data)\n        logger.info(fake_data)\n        # logger.debug(fake_data)\n        # logger.info(ZWJ_X3)\n>       assert False\nE       assert False\n\ndemo-tests/orig/test_0.py:56: AssertionError"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
      "outcome": "failed",
      "start_time": "2025-05-28T05:47:14.675488+00:00",
      "stop_time": "2025-05-28T05:47:14.675832+00:00",
      "duration": 0.000344,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun2')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_skip",
      "outcome": "skipped",
      "start_time": "2025-05-28T05:47:14.650800+00:00",
      "stop_time": "2025-05-28T05:47:14.650965+00:00",
      "duration": 0.000165,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "('/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py', 74, 'Skipped: Skipping this test with decorator.')"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_xfail",
      "outcome": "xfailed",
      "start_time": "2025-05-28T05:47:14.651410+00:00",
      "stop_time": "2025-05-28T05:47:14.651561+00:00",
      "duration": 0.000151,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 82\n  @pytest.mark.xfail()\n  def test0_xfail(logger, capstderr):\nE       fixture 'capstderr' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:82"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_xpass",
      "outcome": "xfailed",
      "start_time": "2025-05-28T05:47:14.653573+00:00",
      "stop_time": "2025-05-28T05:47:14.653733+00:00",
      "duration": 0.00016,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 104\n  @pytest.mark.xfail()\n  def test0_xpass(logger, capstdout):\nE       fixture 'capstdout' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:104"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_xpass_demo",
      "outcome": "xpassed",
      "start_time": "2025-05-28T05:47:14.653101+00:00",
      "stop_time": "2025-05-28T05:47:14.653214+00:00",
      "duration": 0.000113,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "None"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_warning",
      "outcome": "error",
      "start_time": "2025-05-28T05:47:14.654700+00:00",
      "stop_time": "2025-05-28T05:47:14.654801+00:00",
      "duration": 0.000101,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 122\n  def test0_warning(capstdlog):\nE       fixture 'capstdlog' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:122"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_flaky_3",
      "outcome": "error",
      "start_time": "2025-05-28T05:47:14.658394+00:00",
      "stop_time": "2025-05-28T05:47:14.658502+00:00",
      "duration": 0.000108,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 131\n  @pytest.mark.flaky(reruns=3)\n  def test_flaky_3(capstderr):\nE       fixture 'capstderr' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:131"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
      "outcome": "rerun",
      "start_time": "2025-05-28T05:47:14.666805+00:00",
      "stop_time": "2025-05-28T05:47:14.667215+00:00",
      "duration": 0.00041,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun0')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
      "outcome": "rerun",
      "start_time": "2025-05-28T05:47:14.671333+00:00",
      "stop_time": "2025-05-28T05:47:14.671757+00:00",
      "duration": 0.000424,
      "caplog": "",
      "capstderr": "",
      "capstdout": "",
      "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun1')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
    }
  ],
  "rerun_test_groups": [
    {
      "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
      "tests": [
        {
          "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
          "outcome": "rerun",
          "start_time": "2025-05-28T05:47:14.666805+00:00",
          "stop_time": "2025-05-28T05:47:14.667215+00:00",
          "duration": 0.00041,
          "caplog": "",
          "capstderr": "",
          "capstdout": "",
          "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun0')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
        },
        {
          "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
          "outcome": "rerun",
          "start_time": "2025-05-28T05:47:14.671333+00:00",
          "stop_time": "2025-05-28T05:47:14.671757+00:00",
          "duration": 0.000424,
          "caplog": "",
          "capstderr": "",
          "capstdout": "",
          "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun1')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
        },
        {
          "nodeid": "demo-tests/orig/test_0.py::test_always_rerun",
          "outcome": "failed",
          "start_time": "2025-05-28T05:47:14.675488+00:00",
          "stop_time": "2025-05-28T05:47:14.675832+00:00",
          "duration": 0.000344,
          "caplog": "",
          "capstderr": "",
          "capstdout": "",
          "longreprtext": "tmp_path = PosixPath('/private/var/folders/pd/fvjgwfx97wb95q5t2k168sxr0000gn/T/pytest-of-jwr003/pytest-118/test_always_rerun2')\n\n    @pytest.mark.flaky(reruns=2)\n    def test_always_rerun(tmp_path):\n        state_file = tmp_path / \"rerun_state.txt\"\n        if not state_file.exists():\n            state_file.write_text(\"fail\")\n>           assert False, \"Fail first run\"\nE           AssertionError: Fail first run\nE           assert False\n\ndemo-tests/orig/test_0.py:144: AssertionError"
        }
      ]
    }
  ],
  "warnings": [],
  "errors": [
    {
      "nodeid": "demo-tests/orig/test_0.py::test0_warning",
      "when": "setup",
      "outcome": "failed",
      "message": null,
      "category": null,
      "filename": null,
      "lineno": null,
      "longrepr": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 122\n  def test0_warning(capstdlog):\nE       fixture 'capstdlog' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:122",
      "sections": [],
      "keywords": [
        "test0_warning",
        "test_0.py",
        "orig",
        "demo-tests",
        "pytest-recap",
        ""
      ],
      "location": null
    },
    {
      "nodeid": "demo-tests/orig/test_0.py::test_flaky_3",
      "when": "setup",
      "outcome": "failed",
      "message": null,
      "category": null,
      "filename": null,
      "lineno": null,
      "longrepr": "file /Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py, line 131\n  @pytest.mark.flaky(reruns=3)\n  def test_flaky_3(capstderr):\nE       fixture 'capstderr' not found\n>       available fixtures: cache, capfd, capfdbinary, caplog, capsys, capsysbinary, class_mocker, cov, doctest_namespace, error_fixture, fake_data, include_metadata_in_junit_xml, json_metadata, logger, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, random_sleep, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, test_data, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory\n>       use 'pytest --fixtures [testpath]' for help on them.\n\n/Users/jwr003/coding/pytest-recap/demo-tests/orig/test_0.py:131",
      "sections": [],
      "keywords": [
        "test_flaky_3",
        "flaky",
        "pytestmark",
        "test_0.py",
        "orig",
        "demo-tests",
        "pytest-recap",
        ""
      ],
      "location": null
    }
  ],
  "session_stats": {
    "passed": 2,
    "failed": 2,
    "skipped": 1,
    "xfailed": 2,
    "xpassed": 1,
    "error": 2,
    "rerun": 2,
    "warnings": 0
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
