"""Integration tests for CLI module."""

from pathlib import Path
from test.conftest import create_test_files, run_main_with_args
from typing import Any
from unittest.mock import patch

import pytest

from orfmi.cli import EXIT_ERROR, EXIT_FAILURE, EXIT_SUCCESS


@pytest.mark.integration
class TestCliExitCodes:
    """Integration tests for CLI exit codes."""

    def test_exit_error_missing_config(self, tmp_path: Path) -> None:
        """Test exit code for missing config file."""
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(tmp_path / "missing.yml"),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_exit_error_invalid_yaml(self, tmp_path: Path) -> None:
        """Test exit code for invalid YAML config."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("invalid: yaml: :")
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_exit_error_missing_required_fields(self, tmp_path: Path) -> None:
        """Test exit code for missing required config fields."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("ami_name: test")
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_exit_success_with_mock_builder(self, tmp_path: Path) -> None:
        """Test exit code for successful build."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-12345"
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_SUCCESS

    def test_exit_failure_on_build_error(self, tmp_path: Path) -> None:
        """Test exit code when build fails."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.side_effect = RuntimeError("Build failed")
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_FAILURE


@pytest.mark.integration
class TestCliOutput:
    """Integration tests for CLI output."""

    def test_outputs_ami_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that AMI ID is output on success."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-output123"
            run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            captured = capsys.readouterr()
            assert "AMI_ID=ami-output123" in captured.out

    def test_outputs_ami_id_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that AMI ID output is in correct format."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-xyz789"
            run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            captured = capsys.readouterr()
            assert captured.out.strip().startswith("AMI_ID=")


@pytest.mark.integration
class TestCliConfigParsing:
    """Integration tests for config parsing through CLI."""

    def test_full_config_exit_code(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that full config parsing returns success."""
        exit_code, _ = full_config_result
        assert exit_code == EXIT_SUCCESS

    def test_full_config_ami_name(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that ami_name is parsed correctly."""
        _, config = full_config_result
        assert config.ami.name == "my-custom-ami"

    def test_full_config_region(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that region is parsed correctly."""
        _, config = full_config_result
        assert config.region == "us-west-2"

    def test_full_config_subnet_ids(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that subnet_ids are parsed correctly."""
        _, config = full_config_result
        assert config.instance.subnet_ids == ["subnet-aaa", "subnet-bbb"]

    def test_full_config_instance_types(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that instance_types are parsed correctly."""
        _, config = full_config_result
        assert config.instance.instance_types == ["t3.micro", "t3.small"]

    def test_full_config_ssh_username(
        self, full_config_result: tuple[int, Any]
    ) -> None:
        """Test that ssh_username is parsed correctly."""
        _, config = full_config_result
        assert config.ssh.username == "ubuntu"

@pytest.mark.integration
class TestCliExtraFiles:
    """Integration tests for extra files handling."""

    def test_extra_files_exit_code(
        self, extra_files_result: tuple[int, list[Path]]
    ) -> None:
        """Test that extra files handling returns success."""
        exit_code, _ = extra_files_result
        assert exit_code == EXIT_SUCCESS

    def test_extra_files_count(
        self, extra_files_result: tuple[int, list[Path]]
    ) -> None:
        """Test that correct number of extra files are passed."""
        _, extra_files = extra_files_result
        assert len(extra_files) == 2

    def test_no_extra_files_by_default(self, tmp_path: Path) -> None:
        """Test that no extra files are passed by default."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-12345"
            run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            call_args = mock_builder.call_args
            extra_files = call_args[0][2]
            assert not extra_files
