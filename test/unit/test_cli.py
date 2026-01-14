"""Unit tests for CLI module."""

import argparse
import logging
from pathlib import Path
from test.conftest import create_test_files, run_main_with_args
from unittest.mock import MagicMock, patch

import pytest

from orfmi.cli import (
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

    def test_valid_arguments_config_file(self, parsed_valid_args: argparse.Namespace) -> None:
        """Test parsing valid arguments - config_file."""
        assert parsed_valid_args.config_file == Path("config.yml")

    def test_valid_arguments_setup_file(self, parsed_valid_args: argparse.Namespace) -> None:
        """Test parsing valid arguments - setup_file."""
        assert parsed_valid_args.setup_file == Path("setup.sh")

    def test_valid_arguments_verbose_default(self, parsed_valid_args: argparse.Namespace) -> None:
        """Test parsing valid arguments - verbose default."""
        assert parsed_valid_args.verbose is False

    def test_valid_arguments_quiet_default(self, parsed_valid_args: argparse.Namespace) -> None:
        """Test parsing valid arguments - quiet default."""
        assert parsed_valid_args.quiet is False

    def test_valid_arguments_extra_files_default(
        self, parsed_valid_args: argparse.Namespace
    ) -> None:
        """Test parsing valid arguments - extra_files default."""
        assert parsed_valid_args.extra_files is None

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
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs["level"] == logging.INFO

    def test_default_calls_basic_config(self) -> None:
        """Test default setup calls basicConfig once."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False, quiet=False)
            assert mock_config.call_count == 1

    def test_verbose_level(self) -> None:
        """Test verbose logging level is DEBUG."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=True, quiet=False)
            call_kwargs = mock_config.call_args.kwargs
            assert call_kwargs["level"] == logging.DEBUG

    def test_quiet_level(self) -> None:
        """Test quiet logging level is ERROR."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False, quiet=True)
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

    def test_config_file_missing_returns_false(
        self, missing_config_validation: tuple[bool, str]
    ) -> None:
        """Test when config file is missing returns False."""
        result, _ = missing_config_validation
        assert result is False

    def test_config_file_missing_message(
        self, missing_config_validation: tuple[bool, str]
    ) -> None:
        """Test when config file is missing shows error message."""
        _, stderr = missing_config_validation
        assert "Configuration file not found" in stderr

    def test_setup_file_missing_returns_false(
        self, missing_setup_validation: tuple[bool, str]
    ) -> None:
        """Test when setup file is missing returns False."""
        result, _ = missing_setup_validation
        assert result is False

    def test_setup_file_missing_message(
        self, missing_setup_validation: tuple[bool, str]
    ) -> None:
        """Test when setup file is missing shows error message."""
        _, stderr = missing_setup_validation
        assert "Setup file not found" in stderr


@pytest.mark.unit
class TestMain:
    """Tests for main function."""

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test exit code when config file is missing."""
        setup_file = tmp_path / "setup.sh"
        setup_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(tmp_path / "nonexistent.yml"),
            "--setup-file", str(setup_file),
        ])
        assert exit_code == EXIT_ERROR

    def test_missing_setup_file(self, tmp_path: Path) -> None:
        """Test exit code when setup file is missing."""
        config_file = tmp_path / "config.yml"
        config_file.touch()
        exit_code = run_main_with_args([
            "--config-file", str(config_file),
            "--setup-file", str(tmp_path / "nonexistent.sh"),
        ])
        assert exit_code == EXIT_ERROR

    def test_invalid_config(self, tmp_path: Path) -> None:
        """Test exit code when config is invalid."""
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
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
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
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.AmiBuilder") as mock_builder:
            mock_instance = MagicMock()
            mock_instance.build.side_effect = RuntimeError("Build failed")
            mock_builder.return_value = mock_instance
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_FAILURE

    def test_file_not_found_from_load_config(self, tmp_path: Path) -> None:
        """Test exit code when load_config raises FileNotFoundError."""
        config_file, setup_file = create_test_files(tmp_path)
        with patch("orfmi.cli.load_config") as mock_load:
            mock_load.side_effect = FileNotFoundError("File disappeared")
            exit_code = run_main_with_args([
                "--config-file", str(config_file),
                "--setup-file", str(setup_file),
            ])
            assert exit_code == EXIT_ERROR
