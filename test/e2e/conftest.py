"""E2E test configuration."""

import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the ORFMI CLI with the given arguments."""
    return subprocess.run(
        [sys.executable, "-m", "orfmi", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


@pytest.fixture
def missing_config_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with missing config file."""
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(tmp_path / "nonexistent.yml"),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def missing_setup_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with missing setup file."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
""")
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(tmp_path / "nonexistent.sh"),
    )


@pytest.fixture
def invalid_yaml_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with invalid YAML config."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("invalid: yaml: :")
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def missing_fields_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with missing required fields."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("ami_name: test")
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def help_result() -> subprocess.CompletedProcess[str]:
    """Run CLI with --help flag."""
    return run_cli("--help")


@pytest.fixture
def invalid_platform_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with invalid platform."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
platform: macos
""")
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def empty_subnets_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with empty subnet_ids."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids: []
instance_types:
  - t3.micro
""")
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def empty_instance_types_result(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run CLI with empty instance_types."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types: []
""")
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    return run_cli(
        "--config-file", str(config_file),
        "--setup-file", str(setup_file),
    )


@pytest.fixture
def module_help_result() -> subprocess.CompletedProcess[str]:
    """Run python -m orfmi --help."""
    return subprocess.run(
        [sys.executable, "-m", "orfmi", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
