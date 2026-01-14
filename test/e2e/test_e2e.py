"""End-to-end tests for ORFMI CLI."""

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


@pytest.mark.e2e
class TestCliExitCodes:
    """E2E tests for CLI exit codes."""

    def test_exit_2_missing_arguments(self) -> None:
        """Test exit code 2 when required arguments are missing."""
        result = run_cli()
        assert result.returncode == 2

    def test_exit_2_missing_config_file(self, tmp_path: Path) -> None:
        """Test exit code 2 when config file doesn't exist."""
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        result = run_cli(
            "--config-file", str(tmp_path / "nonexistent.yml"),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "Configuration file not found" in result.stderr

    def test_exit_2_missing_setup_file(self, tmp_path: Path) -> None:
        """Test exit code 2 when setup file doesn't exist."""
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
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(tmp_path / "nonexistent.sh"),
        )
        assert result.returncode == 2
        assert "Setup file not found" in result.stderr

    def test_exit_2_invalid_yaml(self, tmp_path: Path) -> None:
        """Test exit code 2 for invalid YAML."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("invalid: yaml: :")
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "Invalid YAML" in result.stderr

    def test_exit_2_missing_required_fields(self, tmp_path: Path) -> None:
        """Test exit code 2 when required fields are missing."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("ami_name: test")
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "Missing required fields" in result.stderr


@pytest.mark.e2e
class TestCliHelp:
    """E2E tests for CLI help."""

    def test_help_flag(self) -> None:
        """Test --help flag shows usage."""
        result = run_cli("--help")
        assert result.returncode == 0
        assert "Open Rainforest Machine Image" in result.stdout
        assert "--config-file" in result.stdout
        assert "--setup-file" in result.stdout

    def test_help_shows_all_options(self) -> None:
        """Test that help shows all options."""
        result = run_cli("--help")
        assert "--extra-files" in result.stdout
        assert "--verbose" in result.stdout
        assert "--quiet" in result.stdout


@pytest.mark.e2e
class TestConfigValidation:
    """E2E tests for configuration validation."""

    def test_invalid_platform(self, tmp_path: Path) -> None:
        """Test error for invalid platform."""
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
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "Invalid platform" in result.stderr

    def test_empty_subnet_ids(self, tmp_path: Path) -> None:
        """Test error for empty subnet_ids."""
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
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "subnet_ids must be a non-empty list" in result.stderr

    def test_empty_instance_types(self, tmp_path: Path) -> None:
        """Test error for empty instance_types."""
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
        result = run_cli(
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        )
        assert result.returncode == 2
        assert "instance_types must be a non-empty list" in result.stderr


@pytest.mark.e2e
class TestModuleExecution:
    """E2E tests for module execution."""

    def test_python_m_orfmi(self) -> None:
        """Test running via python -m orfmi."""
        result = subprocess.run(
            [sys.executable, "-m", "orfmi", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "Open Rainforest Machine Image" in result.stdout
