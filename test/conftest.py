"""Pytest configuration and shared fixtures."""

import argparse
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from orfmi.cli import create_parser, main, validate_files
from orfmi.config import (
    AmiConfig,
    AmiIdentity,
    InstanceSettings,
    SSHSettings,
    load_config,
)
from orfmi.ssh import SshConfig


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


@pytest.fixture
def builder_mocks() -> Generator[dict[str, Any], None, None]:
    """Create all mocks needed for builder tests."""
    patches = {
        "ec2_client": patch("orfmi.builder.create_ec2_client"),
        "unique_id": patch("orfmi.builder.generate_unique_id"),
        "get_vpc": patch("orfmi.builder.get_vpc_from_subnet"),
        "create_key": patch("orfmi.builder.create_key_pair"),
        "create_sg": patch("orfmi.builder.create_security_group"),
        "lookup": patch("orfmi.builder.lookup_source_ami"),
        "create_template": patch("orfmi.builder.create_launch_template"),
        "create_fleet": patch("orfmi.builder.create_fleet_instance"),
        "wait": patch("orfmi.builder.wait_for_instance"),
        "run_script": patch("orfmi.builder.run_setup_script"),
        "create_ami": patch("orfmi.builder.create_ami"),
        "terminate": patch("orfmi.builder.terminate_instance"),
        "delete_template": patch("orfmi.builder.delete_launch_template"),
        "delete_key": patch("orfmi.builder.delete_key_pair"),
        "delete_sg": patch("orfmi.builder.delete_security_group"),
    }
    mocks = {name: p.start() for name, p in patches.items()}
    mock_ec2 = MagicMock()
    mocks["ec2_client"].return_value = mock_ec2
    mocks["unique_id"].return_value = "abc12345"
    mocks["get_vpc"].return_value = "vpc-12345"
    mocks["create_key"].return_value = "private-key"
    mocks["create_sg"].return_value = "sg-12345"
    mocks["lookup"].return_value = "ami-source"
    mocks["create_fleet"].return_value = "i-12345"
    mocks["wait"].return_value = "1.2.3.4"
    mocks["create_ami"].return_value = "ami-result"
    yield mocks
    for p in patches.values():
        p.stop()


# CLI fixtures
@pytest.fixture
def valid_args() -> list[str]:
    """Return valid argument list for parsing."""
    return ["--config-file", "config.yml", "--setup-file", "setup.sh"]


@pytest.fixture
def parsed_valid_args() -> argparse.Namespace:
    """Return parsed valid arguments."""
    parser = create_parser()
    return parser.parse_args(["--config-file", "config.yml", "--setup-file", "setup.sh"])


@pytest.fixture
def missing_config_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[bool, str]:
    """Run validate_files with missing config file."""
    config_file = tmp_path / "nonexistent.yml"
    setup_file = tmp_path / "setup.sh"
    setup_file.touch()
    result = validate_files(config_file, setup_file)
    captured = capsys.readouterr()
    return result, captured.err


@pytest.fixture
def missing_setup_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[bool, str]:
    """Run validate_files with missing setup file."""
    config_file = tmp_path / "config.yml"
    setup_file = tmp_path / "nonexistent.sh"
    config_file.touch()
    result = validate_files(config_file, setup_file)
    captured = capsys.readouterr()
    return result, captured.err


# Config fixtures
@pytest.fixture
def minimal_config() -> AmiConfig:
    """Create a minimal AmiConfig with defaults."""
    ami = AmiIdentity(name="test-ami")
    instance = InstanceSettings(subnet_ids=["subnet-1"], instance_types=["t3.micro"])
    return AmiConfig(
        ami=ami,
        region="us-east-1",
        source_ami="ami-12345",
        instance=instance,
    )


@pytest.fixture
def full_config() -> AmiConfig:
    """Create a full AmiConfig with all fields."""
    ami = AmiIdentity(name="test-ami", description="Test AMI")
    ssh_settings = SSHSettings(username="ec2-user", timeout=600, retries=60)
    instance = InstanceSettings(
        subnet_ids=["subnet-1", "subnet-2"],
        instance_types=["t3.micro", "t3.small"],
        iam_instance_profile="my-profile",
    )
    return AmiConfig(
        ami=ami,
        region="us-west-2",
        source_ami="ami-67890",
        instance=instance,
        tags={"Name": "test"},
        ssh=ssh_settings,
        platform="windows",
    )


@pytest.fixture
def loaded_minimal_config(tmp_path: Path) -> AmiConfig:
    """Load a minimal config from file."""
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
    return load_config(config_file)


@pytest.fixture
def loaded_full_config(tmp_path: Path) -> AmiConfig:
    """Load a full config from file."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("""
ami_name: my-ami
region: us-west-2
source_ami: ubuntu-22.04-*
subnet_ids:
  - subnet-1
  - subnet-2
instance_types:
  - t3.micro
  - t3.small
ami_description: My custom AMI
iam_instance_profile: my-profile
ssh_username: ubuntu
ssh_timeout: 600
ssh_retries: 60
platform: linux
tags:
  Name: test
  Environment: dev
""")
    return load_config(config_file)


# SSH fixtures
@pytest.fixture
def default_ssh_config() -> SshConfig:
    """Create SSH config with defaults."""
    return SshConfig(
        ip_address="1.2.3.4",
        key_material="private-key",
        username="admin",
    )


@pytest.fixture
def full_ssh_config() -> SshConfig:
    """Create SSH config with all values."""
    return SshConfig(
        ip_address="1.2.3.4",
        key_material="private-key",
        username="admin",
        timeout=600,
        retries=60,
    )
