"""Command-line interface for ORFMI."""

import argparse
import logging
import sys
from pathlib import Path

from .builder import AmiBuilder
from .config import (
    AmiConfig,
    AmiIdentity,
    ConfigError,
    InstanceSettings,
    load_config,
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="orfmi",
        description="Open Rainforest Machine Image - Create AWS AMIs from configuration.",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        metavar="FILE",
        help="Path to the YAML configuration file.",
    )
    parser.add_argument(
        "--ami-name",
        type=str,
        metavar="NAME",
        help="Name for the AMI (required if not using --config-file).",
    )
    parser.add_argument(
        "--region",
        type=str,
        metavar="REGION",
        help="AWS region (required if not using --config-file).",
    )
    parser.add_argument(
        "--source-ami",
        type=str,
        metavar="AMI_ID",
        help="Source AMI ID (required if not using --config-file).",
    )
    parser.add_argument(
        "--subnet-ids",
        type=str,
        nargs="+",
        metavar="SUBNET",
        help="Subnet IDs for instance launch (required if not using --config-file).",
    )
    parser.add_argument(
        "--instance-types",
        type=str,
        nargs="+",
        metavar="TYPE",
        help="Instance types to try (required if not using --config-file).",
    )
    parser.add_argument(
        "--purchase-type",
        type=str,
        choices=["on-demand", "spot"],
        metavar="TYPE",
        help="Purchase type: on-demand or spot (default: on-demand).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        metavar="N",
        help="Maximum retries on capacity errors (default: 3).",
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


def validate_args(args: argparse.Namespace) -> None:
    """Validate mutual exclusivity of config sources.

    Raises:
        SystemExit: If validation fails.
    """
    config_flags = [
        args.ami_name,
        args.region,
        args.source_ami,
        args.subnet_ids,
        args.instance_types,
    ]
    has_config_flags = any(f is not None for f in config_flags)

    if args.config_file and has_config_flags:
        print(
            "Error: --config-file cannot be used with "
            "--ami-name, --region, --source-ami, --subnet-ids, --instance-types",
            file=sys.stderr,
        )
        sys.exit(EXIT_ERROR)

    if not args.config_file:
        missing = []
        if not args.ami_name:
            missing.append("--ami-name")
        if not args.region:
            missing.append("--region")
        if not args.source_ami:
            missing.append("--source-ami")
        if not args.subnet_ids:
            missing.append("--subnet-ids")
        if not args.instance_types:
            missing.append("--instance-types")
        if missing:
            print(
                f"Error: Required when not using --config-file: {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(EXIT_ERROR)


def validate_files(
    config_file: Path | None,
    setup_file: Path,
) -> bool:
    """Validate that required files exist.

    Returns:
        True if all files exist, False otherwise.
    """
    if config_file and not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        return False
    if not setup_file.exists():
        print(f"Error: Setup file not found: {setup_file}", file=sys.stderr)
        return False
    return True


def build_config_from_args(args: argparse.Namespace) -> AmiConfig:
    """Build AmiConfig from CLI arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        AmiConfig constructed from CLI arguments.
    """
    ami_identity = AmiIdentity(name=args.ami_name)
    instance_settings = InstanceSettings(
        subnet_ids=args.subnet_ids,
        instance_types=args.instance_types,
        purchase_type=args.purchase_type or "on-demand",
        max_retries=args.max_retries if args.max_retries is not None else 3,
    )
    return AmiConfig(
        ami=ami_identity,
        region=args.region,
        source_ami=args.source_ami,
        instance=instance_settings,
    )


def apply_overrides(config: AmiConfig, args: argparse.Namespace) -> AmiConfig:
    """Apply CLI overrides to a config loaded from file.

    Args:
        config: Original AmiConfig from file.
        args: Parsed command-line arguments.

    Returns:
        New AmiConfig with overrides applied.
    """
    if args.purchase_type is None and args.max_retries is None:
        return config

    new_instance = InstanceSettings(
        subnet_ids=config.instance.subnet_ids,
        instance_types=config.instance.instance_types,
        iam_instance_profile=config.instance.iam_instance_profile,
        purchase_type=args.purchase_type or config.instance.purchase_type,
        max_retries=(
            args.max_retries
            if args.max_retries is not None
            else config.instance.max_retries
        ),
    )
    return AmiConfig(
        ami=config.ami,
        region=config.region,
        source_ami=config.source_ami,
        instance=new_instance,
        tags=config.tags,
        ssh=config.ssh,
        platform=config.platform,
    )


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose, args.quiet)
    validate_args(args)

    if not validate_files(args.config_file, args.setup_file):
        sys.exit(EXIT_ERROR)

    try:
        if args.config_file:
            config = load_config(args.config_file)
            config = apply_overrides(config, args)
        else:
            config = build_config_from_args(args)
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
