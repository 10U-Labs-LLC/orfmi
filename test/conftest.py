"""Pytest configuration and shared fixtures."""

from unittest.mock import patch

import pytest

from orfmi.cli import main


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "e2e: end-to-end tests")


def run_main_with_args(args: list[str]) -> int:
    """Run main() with given args and return exit code."""
    with patch("sys.argv", ["orfmi", *args]):
        try:
            main()
            return 0
        except SystemExit as e:
            return int(e.code) if e.code is not None else 0
