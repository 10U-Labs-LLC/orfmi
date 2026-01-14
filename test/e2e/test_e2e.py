"""End-to-end tests for ORFMI CLI."""

import subprocess
from test.e2e.conftest import run_cli

import pytest


@pytest.mark.e2e
class TestCliExitCodes:
    """E2E tests for CLI exit codes."""

    def test_exit_2_missing_arguments(self) -> None:
        """Test exit code 2 when required arguments are missing."""
        result = run_cli()
        assert result.returncode == 2

    def test_exit_2_missing_config_file(
        self, missing_config_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code 2 when config file doesn't exist."""
        assert missing_config_result.returncode == 2

    def test_missing_config_file_message(
        self, missing_config_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message when config file doesn't exist."""
        assert "Configuration file not found" in missing_config_result.stderr

    def test_exit_2_missing_setup_file(
        self, missing_setup_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code 2 when setup file doesn't exist."""
        assert missing_setup_result.returncode == 2

    def test_missing_setup_file_message(
        self, missing_setup_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message when setup file doesn't exist."""
        assert "Setup file not found" in missing_setup_result.stderr

    def test_exit_2_invalid_yaml(
        self, invalid_yaml_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code 2 for invalid YAML."""
        assert invalid_yaml_result.returncode == 2

    def test_invalid_yaml_message(
        self, invalid_yaml_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message for invalid YAML."""
        assert "Invalid YAML" in invalid_yaml_result.stderr

    def test_exit_2_missing_required_fields(
        self, missing_fields_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code 2 when required fields are missing."""
        assert missing_fields_result.returncode == 2

    def test_missing_required_fields_message(
        self, missing_fields_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message when required fields are missing."""
        assert "Missing required fields" in missing_fields_result.stderr


@pytest.mark.e2e
class TestCliHelp:
    """E2E tests for CLI help."""

    def test_help_exit_code(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help flag returns exit code 0."""
        assert help_result.returncode == 0

    def test_help_shows_description(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows tool description."""
        assert "Open Rainforest Machine Image" in help_result.stdout

    def test_help_shows_config_file_option(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows --config-file option."""
        assert "--config-file" in help_result.stdout

    def test_help_shows_setup_file_option(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows --setup-file option."""
        assert "--setup-file" in help_result.stdout

    def test_help_shows_extra_files_option(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows --extra-files option."""
        assert "--extra-files" in help_result.stdout

    def test_help_shows_verbose_option(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows --verbose option."""
        assert "--verbose" in help_result.stdout

    def test_help_shows_quiet_option(
        self, help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test --help shows --quiet option."""
        assert "--quiet" in help_result.stdout


@pytest.mark.e2e
class TestConfigValidation:
    """E2E tests for configuration validation."""

    def test_invalid_platform_exit_code(
        self, invalid_platform_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code for invalid platform."""
        assert invalid_platform_result.returncode == 2

    def test_invalid_platform_message(
        self, invalid_platform_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message for invalid platform."""
        assert "Invalid platform" in invalid_platform_result.stderr

    def test_empty_subnet_ids_exit_code(
        self, empty_subnets_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code for empty subnet_ids."""
        assert empty_subnets_result.returncode == 2

    def test_empty_subnet_ids_message(
        self, empty_subnets_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message for empty subnet_ids."""
        assert "subnet_ids must be a non-empty list" in empty_subnets_result.stderr

    def test_empty_instance_types_exit_code(
        self, empty_instance_types_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test exit code for empty instance_types."""
        assert empty_instance_types_result.returncode == 2

    def test_empty_instance_types_message(
        self, empty_instance_types_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test error message for empty instance_types."""
        assert "instance_types must be a non-empty list" in \
            empty_instance_types_result.stderr


@pytest.mark.e2e
class TestModuleExecution:
    """E2E tests for module execution."""

    def test_module_exit_code(
        self, module_help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test python -m orfmi --help returns exit code 0."""
        assert module_help_result.returncode == 0

    def test_module_shows_description(
        self, module_help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test python -m orfmi --help shows description."""
        assert "Open Rainforest Machine Image" in module_help_result.stdout

    def test_module_shows_config_option(
        self, module_help_result: subprocess.CompletedProcess[str]
    ) -> None:
        """Test python -m orfmi --help shows --config-file option."""
        assert "--config-file" in module_help_result.stdout
