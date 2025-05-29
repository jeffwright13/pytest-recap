# CHANGELOG

## [Unreleased]

### Added
- New HTML report generator (`recap_json_to_html.py`) for pytest-recap sessions.
  - Generates a modern, interactive HTML report from `recap.json`.
  - Features include:
    - Summary stats and pie chart of outcomes
    - Expandable/collapsible test details
    - Sortable and filterable results table
    - Session metadata section (collapsible)
    - Outcome filtering and master toggle
    - User-friendly, responsive design
- Documentation and usage instructions for the HTML report in README.

### Changed
- Recap JSON format now uses timezone-aware UTC timestamps for all session/test times.
- `TestSessionStats` constructor and usages now require `warnings_count` (plural) for consistency.
- `RecapEvent` API provides `.is_warning()` and `.is_error()` helpers for event type checks.
- All logger calls use `logger.warning` (not `logger.warnings`).
- Updated recap.json sample and documentation to match new format.
- Improved test coverage and restored/fixed test suite (including demo suite failures and expected errors).
- Codebase uses `ruff` and `ruff format` for linting/formatting; pre-commit hooks recommended.


### Added
- New `--recap-pretty` CLI flag, `RECAP_PRETTY` environment variable, and `recap_pretty` ini option for controlling recap JSON output format (pretty-printed or minified). Default is minified. Precedence: CLI > ENV > INI > default.
- Tests for pretty/minified output at both plugin and storage layers.

### Fixed
- Robust handling of ini values for session metadata (now always parsed as string, even if provided as a list by pytest).
- Warning messages for invalid session metadata now always reference the correct environment variable or CLI option, improving clarity and testability.
- Improved debug output for session metadata resolution and parsing.

## [0.8.0] - 2025-05-21

### Added
- Refactored session schema: replaced `sut_name` with `system_under_test` (now a dict), and updated all code/tests accordingly.
- Enhanced both `system_under_test` and `testing_system` fields for user-extensible metadata.
- Improved JSON schema: added recommended keys, allowed custom properties, and linked schema in README.
- Expanded and clarified README: added schema section, extensibility guidance, example output, and a neutral comparison with JUnit-XML and pytest-json-report.
- Added `demo-tests/README.md` to clarify demo structure and subfolder purposes.

### Changed
- Updated plugin logic and file naming to use new extensible fields.
- Improved concurrency: added thread/process safety to JSONStorage using threading.RLock and FileLock.
- Made session loader stricter: only accepts lists or dicts with 'sessions' key as valid session lists.
- Improved test coverage and reliability, including edge cases and permission scenarios.
- Updated pre-commit config to match pytest's standard test file naming convention (`test_*.py`).

### Fixed
- Fixed and clarified permission error handling and related tests for robust cross-platform behavior.
- Addressed linter feedback and pre-commit hook config issues.

---

## [0.7.0] - 2025-05-06

### Added
- Initial implementation of core recap models and storage logic.
- Full support for rerun test groups and session metadata.
- Pre-commit hooks for code quality: ruff, isort, pytest-cov.
- Integration tests and coverage for models, storage, and plugin.
- Support for cloud storage recap output: S3 (`s3://`), Google Cloud Storage (`gs://`), Azure Blob Storage (`azure://`).
- Parametrized tests for cloud upload logic (mocked and moto-backed).
- Color-highlighted recap output path/URI in terminal.

### Changed
- README and documentation fully updated for release, including cloud configuration, test strategy, and developer workflow.
- Test suite: S3 tests now skipped unless `moto` and `boto3` are installed; GCS/Azure use direct mocking for speed and minimal deps.
- Improved error handling and output clarity for cloud upload failures.
- Recap JSON schema: added `warnings`, `errors`, and `session_stats` fields.
- Refactored `SessionStats` to `TestSessionStats` for clarity.
- Output recap file path/URI is now color-highlighted in the terminal.
- Overhauled plugin and test structure for maintainability and extensibility.

### Fixed
- Improved test coverage and reliability.
- Various README and doc updates.

### Removed
- Obsolete `hello()` stub from `pytest_recap/__init__.py`.
- Black from dependencies (using ruff format instead).

---

### Previous (pre-v0.7.0) commit history:

```
81b2796 Release v0.7.0
46907e1 Overhaul on all fronts.
e457832 Update README.md
fd92026 Update README.
e953802 Bump version to 0.4.0, add requests dependency, and adjust session_tags serialization in models.py. Add a bunch of unit tests for models.py.
1df59dd Added conftest.py to test/ dir with ‘tester’ fixture that provides either testdir or pytester test fixture depending on version of Pytest running. Also added more coverage to plugin.py.
0621ffd Removed black from dependencies (we have ruff format now).
c8925b9 Add support for rerun test groups. Add pre-commit, ruff, isort, and pytest-cov via pyproject.toml.
96c45d2 Initial commit. models.py and storage.py in place, fully implemented, with unit tests. Next: plugin.py; dev tools/process.
b4b2aea Initial commit
