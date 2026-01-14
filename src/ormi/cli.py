"""Command-line interface for ORMI."""

import argparse
import logging
import sys
from pathlib import Path

from .builder import AmiBuilder
from .config import ConfigError, load_config

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ormi",
        description="Open Rainforest Machine Image - Create AWS AMIs from configuration.",
    )
    parser.add_argument(
        "--config-file",
        required=True,
        type=Path,
        metavar="FILE",
        help="Path to the YAML configuration file.",
    )
    parser.add_argument(
        "--setup-file",
        required=True,
        type=Path,
        metavar="FILE",
        help="Path to the setup script (bash for Linux, PowerShell for Windows).",
    )
    parser.add_argument(
        "--extra-files",
        type=Path,
        nargs="*",
        metavar="FILE",
        help="Additional files to upload to the instance.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress output except for errors and the final AMI ID.",
    )
    return parser


def setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )


def validate_files(config_file: Path, setup_file: Path) -> bool:
    """Validate that required files exist.

    Returns:
        True if all files exist, False otherwise.
    """
    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        return False
    if not setup_file.exists():
        print(f"Error: Setup file not found: {setup_file}", file=sys.stderr)
        return False
    return True


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose, args.quiet)

    if not validate_files(args.config_file, args.setup_file):
        sys.exit(EXIT_ERROR)

    try:
        config = load_config(args.config_file)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    extra_files = args.extra_files or []
    builder = AmiBuilder(config, args.setup_file, extra_files)

    try:
        ami_id = builder.build()
        print(f"AMI_ID={ami_id}")
        sys.exit(EXIT_SUCCESS)
    except RuntimeError as e:
        logging.error("Build failed: %s", e)
        sys.exit(EXIT_FAILURE)
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        sys.exit(EXIT_ERROR)
