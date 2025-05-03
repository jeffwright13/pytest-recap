# pytest-recap

Capture your test sessions. Recap the results.

## Overview

**pytest-recap** is a [pytest](https://pytest.org/) plugin that captures detailed information about your test sessions and creates a well-structured JSON file writtten to the location of your choice. It is designed to help you analyze, summarize, and store test outcomes for reporting and analytics.

## Features
- Captures all test outcomes, reruns, and session metadata
- Provides a JSON-serialized summary of test sessions
- Handles rerun and flaky test tracking

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

Session data will be captured and can be accessed or exported as needed. Look in ther terminal for the location your file was written to:

```bash
Pytest Recap session written to: /tmp/pytest_recap_sessions/2025/05/20250503-070851_pytest-recap.json
```

You can specify a custom location for the session file using the `--recap-file` option:

```bash
pytest --recap --recap-file=/path/to/your/session/file.json
```

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
