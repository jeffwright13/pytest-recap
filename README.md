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

### Example Recap JSON

<details>
  <summary>Show Example</summary>

  ```json
  {
    "session_id": "20250503-074257_pytest-recap",
    ...
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

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes and version history.

---

## License

MIT License. Copyright (c) 2025 Jeff Wright.
