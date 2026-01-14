"""Unit tests for CLI module."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ormi.cli import (
    EXIT_ERROR,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    create_parser,
    setup_logging,
    validate_files,
)


@pytest.mark.unit
class TestCreateParser:
    """Tests for create_parser function."""

    def test_required_arguments(self) -> None:
        """Test that required arguments are enforced."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_config_file_required(self) -> None:
        """Test that --config-file is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--setup-file", "setup.sh"])

    def test_setup_file_required(self) -> None:
        """Test that --setup-file is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--config-file", "config.yml"])

    def test_valid_arguments(self) -> None:
        """Test parsing valid arguments."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
        ])
        assert args.config_file == Path("config.yml")
        assert args.setup_file == Path("setup.sh")
        assert args.verbose is False
        assert args.quiet is False
        assert args.extra_files is None

    def test_verbose_flag(self) -> None:
        """Test --verbose flag."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
            "--verbose",
        ])
        assert args.verbose is True

    def test_quiet_flag(self) -> None:
        """Test --quiet flag."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
            "--quiet",
        ])
        assert args.quiet is True

    def test_extra_files(self) -> None:
        """Test --extra-files argument."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
            "--extra-files", "file1.txt", "file2.txt",
        ])
        assert args.extra_files == [Path("file1.txt"), Path("file2.txt")]

    def test_short_verbose(self) -> None:
        """Test -v short flag for verbose."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
            "-v",
        ])
        assert args.verbose is True

    def test_short_quiet(self) -> None:
        """Test -q short flag for quiet."""
        parser = create_parser()
        args = parser.parse_args([
            "--config-file", "config.yml",
            "--setup-file", "setup.sh",
            "-q",
        ])
        assert args.quiet is True


@pytest.mark.unit
class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_default_level(self) -> None:
        """Test default logging level is INFO."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False, quiet=False)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs["level"] == logging.INFO

    def test_verbose_level(self) -> None:
        """Test verbose logging level is DEBUG."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=True, quiet=False)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs["level"] == logging.DEBUG

    def test_quiet_level(self) -> None:
        """Test quiet logging level is ERROR."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False, quiet=True)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs["level"] == logging.ERROR


@pytest.mark.unit
class TestValidateFiles:
    """Tests for validate_files function."""

    def test_both_files_exist(self, tmp_path: Path) -> None:
        """Test when both files exist."""
        config_file = tmp_path / "config.yml"
        setup_file = tmp_path / "setup.sh"
        config_file.touch()
        setup_file.touch()
        assert validate_files(config_file, setup_file) is True

    def test_config_file_missing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test when config file is missing."""
        config_file = tmp_path / "nonexistent.yml"
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        assert validate_files(config_file, setup_file) is False
        captured = capsys.readouterr()
        assert "Configuration file not found" in captured.err

    def test_setup_file_missing(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test when setup file is missing."""
        config_file = tmp_path / "config.yml"
        setup_file = tmp_path / "nonexistent.sh"
        config_file.touch()
        assert validate_files(config_file, setup_file) is False
        captured = capsys.readouterr()
        assert "Setup file not found" in captured.err


@pytest.mark.unit
class TestMain:
    """Tests for main function."""

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test exit code when config file is missing."""
        from test.conftest import run_main_with_args
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(tmp_path / "nonexistent.yml"),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_missing_setup_file(self, tmp_path: Path) -> None:
        """Test exit code when setup file is missing."""
        from test.conftest import run_main_with_args
        config_file = tmp_path / "config.yml"
        config_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(tmp_path / "nonexistent.sh"),
        ])
        assert exit_code == EXIT_ERROR

    def test_invalid_config(self, tmp_path: Path) -> None:
        """Test exit code when config is invalid."""
        from test.conftest import run_main_with_args
        config_file = tmp_path / "config.yml"
        setup_file = tmp_path / "setup.sh"
        config_file.write_text("invalid: yaml: syntax:")
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_successful_build(self, tmp_path: Path) -> None:
        """Test successful build returns AMI ID."""
        from test.conftest import run_main_with_args
        config_file = tmp_path / "config.yml"
        setup_file = tmp_path / "setup.sh"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
""")
        setup_file.write_text("#!/bin/bash\necho 'Hello'")
        with patch("ormi.cli.AmiBuilder") as mock_builder:
            mock_instance = MagicMock()
            mock_instance.build.return_value = "ami-test123"
            mock_builder.return_value = mock_instance
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_SUCCESS

    def test_build_failure(self, tmp_path: Path) -> None:
        """Test build failure returns failure exit code."""
        from test.conftest import run_main_with_args
        config_file = tmp_path / "config.yml"
        setup_file = tmp_path / "setup.sh"
        config_file.write_text("""
ami_name: test-ami
region: us-east-1
source_ami: debian-12-*
subnet_ids:
  - subnet-12345
instance_types:
  - t3.micro
""")
        setup_file.write_text("#!/bin/bash\necho 'Hello'")
        with patch("ormi.cli.AmiBuilder") as mock_builder:
            mock_instance = MagicMock()
            mock_instance.build.side_effect = RuntimeError("Build failed")
            mock_builder.return_value = mock_instance
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_FAILURE
