"""Pytest configuration and shared fixtures."""

from pathlib import Path
from unittest.mock import patch

import pytest

from orfmi.cli import main


VALID_CONFIG_YAML = """
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
""".strip()


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


def create_test_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create valid config and setup files for testing."""
    config_file = tmp_path / "config.yml"
    config_file.write_text(VALID_CONFIG_YAML)
    setup_file = tmp_path / "setup.sh"
    setup_file.write_text("#!/bin/bash\necho 'Hello'")
    return config_file, setup_file
