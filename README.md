# pytest-recap

Capture your test sessions. Recap the results.

## Overview

**pytest-recap** is a [pytest](https://pytest.org/) plugin that captures detailed information about your test sessions and creates a well-structured JSON file written to the location of your choice. It is designed to help you analyze, summarize, and store test outcomes for reporting and analytics.

### Key Features

- **Comprehensive session recap**: Records all test outcomes, timings, logs, and more.
- **Cloud storage support**: Write recaps directly to AWS S3 (`s3://`), Google Cloud Storage (`gs://`), or Azure Blob Storage (`azure://`).
- **Flexible output**: Supports local file, directory, or cloud URI destinations.
- **Rerun group tracking**: Handles flaky/rerun tests with group summaries.
- **Color-highlighted output**: Recap file path/URI is colorized in the terminal.
- **Tested with pytest-mock and moto**: Full test suite with cloud mocks and coverage.

---

## Installation

```bash
uv pip install pytest-recap
```

For cloud storage support in tests:
- S3: `uv add --dev moto boto3`
- GCS: `uv add --dev google-cloud-storage`
- Azure: `uv add --dev azure-storage-blob`

---

## Usage

Run pytest as usual. Recap output is written to `recap-session.json` by default, or to a custom file/directory/cloud URI using the `--recap-destination` option.

```bash
pytest --recap-destination=gs://mybucket/recap-session.json
pytest --recap-destination=azure://mycontainer/recap-session.json
pytest --recap-destination=./output_dir/
```

### Recap Session Schema

The structure of the recap JSON is governed by a [JSON Schema](schema/pytest-recap-session.schema.json) ([view raw](./schema/pytest-recap-session.schema.json)).

- **`system_under_test`** and **`testing_system`** are extensible objects. You can add any custom keys relevant to your context (e.g., version, type, description).
- Recommended keys for `system_under_test` include: `name`, `version`, `type`, `description`.
- See the [schema file](schema/pytest-recap-session.schema.json) for details and validation rules.

### Example Recap JSON

<details>
  <summary>Show Example</summary>

  ```json
  {
    "session_id": "20250503-074257_pytest-recap",
    ...
    "system_under_test": { "name": "pytest-recap", "version": "0.7.0", "type": "pytest-plugin" },
    "testing_system": { "hostname": "devbox", "python_version": "3.9.16" },
    "test_results": [ ... ],
    "rerun_test_groups": [ ... ]
  }
  ```
</details>

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
