# demo-tests

This folder contains sample test suites for generating recap JSON files as they would be produced by a real pytest run using the pytest-recap plugin (via `--recap`).

- The `orig/` subfolder is designed to exercise every possible test outcome and reporting scenario supported by pytest, using a variety of test structures and patterns. It serves as a comprehensive demonstration and regression suite for the plugin's output capabilities.

- The `realistic/` subfolder contains more modular, domain-focused test suites that mimic real-world project organization (e.g., API, DB, integration, UI, performance). These are intended to showcase recap generation in production-like settings.

You can run these tests through `pytest --recap` to produce example recap-session JSON files for documentation, testing, or integration purposes.
