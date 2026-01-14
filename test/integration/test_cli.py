"""Integration tests for CLI module."""

from pathlib import Path
from test.conftest import create_test_files, run_main_with_args
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


@pytest.mark.integration
class TestCliConfigParsing:
    """Integration tests for config parsing through CLI."""

    def test_parses_full_config(self, tmp_path: Path) -> None:
        """Test that full config is parsed correctly."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
ami_name: my-custom-ami
region: us-west-2
source_ami: ubuntu-22.04-*
subnet_ids:
  - subnet-aaa
  - subnet-bbb
instance_types:
  - t3.micro
  - t3.small
ami_description: My custom AMI for testing
iam_instance_profile: my-profile
ssh_username: ubuntu
ssh_timeout: 600
ssh_retries: 60
platform: linux
tags:
  Name: test
  Environment: dev
""")
        setup_file = tmp_path / "setup.sh"
        setup_file.write_text("#!/bin/bash\necho 'Hello'")

        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-12345"
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_SUCCESS
            call_args = mock_builder.call_args
            config = call_args[0][0]
            assert config.ami.name == "my-custom-ami"
            assert config.region == "us-west-2"
            assert config.instance.subnet_ids == ["subnet-aaa", "subnet-bbb"]
            assert config.instance.instance_types == ["t3.micro", "t3.small"]
            assert config.ssh.username == "ubuntu"


@pytest.mark.integration
class TestCliExtraFiles:
    """Integration tests for extra files handling."""

    def test_passes_extra_files_to_builder(self, tmp_path: Path) -> None:
        """Test that extra files are passed to builder."""
        config_file, setup_file = create_test_files(tmp_path)
        extra1 = tmp_path / "extra1.txt"
        extra1.write_text("extra1")
        extra2 = tmp_path / "extra2.txt"
        extra2.write_text("extra2")

        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = "ami-12345"
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
                "--extra-files", str(extra1), str(extra2),
            ])
            assert exit_code == EXIT_SUCCESS
            call_args = mock_builder.call_args
            extra_files = call_args[0][2]
            assert len(extra_files) == 2
