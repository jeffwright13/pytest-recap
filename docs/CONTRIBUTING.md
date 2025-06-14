# Contributing to pytest-recap

Thank you for your interest in contributing to **pytest-recap**!

## Development Environment

- Requires Python >=3.9
- Use [uv](https://github.com/astral-sh/uv) for dependency and environment management.
- All development and test dependencies are managed in `pyproject.toml` under `[dependency-groups.dev]`.

### Setting Up

```bash
uv pip install -e .
```

To install all dependencies (core + dev, including cloud and test tools) using uv's dependency groups:

```bash
uv pip install --group all
```

### Running Tests

- Run all tests with coverage:
  ```bash
  uv run pytest tests -v
  ```
- S3 tests require `moto` and `boto3` (optional; skipped if not installed).
- GCS and Azure tests use direct mocking (no real cloud needed).

### Pre-commit Hooks

- Run `pre-commit install` to enable code quality checks (ruff, ruff-format, pytest-check).
- See `.pre-commit-config.yaml` for configuration.

### Linting & Formatting

- Run `ruff check pytest_recap` for linting.
- Run `ruff format pytest_recap` for formatting.
- All code should be auto-formatted and linted before PRs.

## Pull Requests

- Write clear, atomic commits.
- Add/modify tests for all changes.
- Update documentation and changelog as needed.
- Ensure all tests and pre-commit hooks pass before submitting.

## Release Process

1. Ensure docs and changelog are up to date.
2. Bump version in `pyproject.toml`.
3. Tag and push release commit.
4. Publish to PyPI if appropriate.

---

For questions, open an issue or discussion on GitHub.
